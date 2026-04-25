"""
ODS层数据同步主程序入口
支持命令行参数调度，可直接用于调度系统
"""
import argparse
import sys
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ods_sync.config import ConfigLoader, SyncConfig
from ods_sync.utils.logger import get_logger
from ods_sync.utils.mysql_client import MySQLClient
from ods_sync.extractors.mysql_incremental_extractor import IncrementalExtractor


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='ODS层数据同步脚本 - 支持MySQL增量抽取',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        required=True,
        help='配置文件路径 (YAML或JSON格式)'
    )
    
    parser.add_argument(
        '-d', '--date',
        type=str,
        default=None,
        help='业务日期 (格式: YYYY-MM-DD)，默认为今天'
    )
    
    parser.add_argument(
        '-t', '--tables',
        type=str,
        default=None,
        help='指定要同步的表名，多个表用逗号分隔，不指定则同步配置中的所有表'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        default=False,
        help='强制全量同步（忽略增量模式）'
    )
    
    parser.add_argument(
        '--start-watermark',
        type=str,
        default=None,
        help='指定起始水印值（优先级高于水印文件）'
    )
    
    parser.add_argument(
        '--end-watermark',
        type=str,
        default=None,
        help='指定结束水印值'
    )
    
    return parser.parse_args()


def validate_date(date_str: str) -> str:
    """
    验证日期格式并标准化
    
    Args:
        date_str: 日期字符串
        
    Returns:
        标准化后的日期字符串 (YYYY-MM-DD)
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
        return parsed_date.strftime('%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"日期格式错误: {date_str}，正确格式应为 YYYY-MM-DD") from e


def get_table_list(config: SyncConfig, specified_tables: Optional[str]) -> List[Dict[str, Any]]:
    """
    获取要同步的表列表
    
    Args:
        config: 同步配置
        specified_tables: 指定的表名（逗号分隔）
        
    Returns:
        表配置列表
    """
    all_tables = config.tables
    
    if not all_tables:
        raise ValueError("配置文件中未配置任何表")
    
    if not specified_tables:
        return all_tables
    
    specified = [t.strip() for t in specified_tables.split(',') if t.strip()]
    
    result = []
    for table_name in specified:
        table_config = config.get_table_config(table_name)
        if table_config:
            result.append(table_config)
        else:
            raise ValueError(f"未找到表 {table_name} 的配置")
    
    return result


def sync_table(
    table_config: Dict[str, Any],
    mysql_client: MySQLClient,
    config: SyncConfig,
    business_date: str,
    force_full: bool,
    start_watermark: Optional[str],
    end_watermark: Optional[str],
    logger
) -> Dict[str, Any]:
    """
    同步单个表
    
    Args:
        table_config: 表配置
        mysql_client: MySQL客户端
        config: 全局配置
        business_date: 业务日期
        force_full: 是否强制全量
        start_watermark: 起始水印
        end_watermark: 结束水印
        logger: 日志记录器
        
    Returns:
        同步结果
    """
    table_name = table_config['name']
    increment_mode = table_config.get('increment_mode', 'timestamp')
    increment_column = table_config.get('increment_column', 'create_time')
    batch_size = table_config.get('batch_size', config.batch_size)
    
    logger.info(f"{'='*60}")
    logger.info(f"开始同步表: {table_name}")
    logger.info(f"增量模式: {increment_mode}")
    logger.info(f"增量列: {increment_column}")
    logger.info(f"批处理大小: {batch_size}")
    
    extractor = IncrementalExtractor(
        mysql_client=mysql_client,
        table_name=table_name,
        increment_mode=increment_mode,
        increment_column=increment_column,
        batch_size=batch_size,
        output_dir=config.output_dir,
        watermark_dir=config.watermark_dir,
        logger=logger
    )
    
    result = extractor.extract(
        business_date=business_date,
        start_watermark=start_watermark,
        end_watermark=end_watermark,
        force_full=force_full
    )
    
    return result


def main():
    """主函数"""
    args = parse_args()
    
    try:
        config_dict = ConfigLoader.load(args.config)
        config = SyncConfig(config_dict)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    try:
        business_date = validate_date(args.date)
    except ValueError as e:
        print(f"日期参数错误: {e}")
        sys.exit(1)
    
    logger = get_logger(
        name='ods_sync',
        log_dir=config.log_dir,
        level=config.log_level
    )
    
    logger.info(f"{'='*60}")
    logger.info("ODS层数据同步任务开始")
    logger.info(f"配置文件: {args.config}")
    logger.info(f"业务日期: {business_date}")
    if args.tables:
        logger.info(f"指定表: {args.tables}")
    if args.full:
        logger.info("模式: 强制全量同步")
    if args.start_watermark:
        logger.info(f"起始水印: {args.start_watermark}")
    if args.end_watermark:
        logger.info(f"结束水印: {args.end_watermark}")
    
    try:
        tables_to_sync = get_table_list(config, args.tables)
        logger.info(f"待同步表数量: {len(tables_to_sync)}")
    except ValueError as e:
        logger.error(f"获取表列表失败: {e}")
        sys.exit(1)
    
    mysql_config = config.mysql_config
    mysql_client = None
    
    try:
        logger.info(f"连接MySQL: {mysql_config.get('host')}:{mysql_config.get('port')}")
        mysql_client = MySQLClient(
            host=mysql_config['host'],
            port=mysql_config['port'],
            user=mysql_config['user'],
            password=mysql_config['password'],
            database=mysql_config['database'],
            charset=mysql_config.get('charset', 'utf8mb4'),
            connect_timeout=mysql_config.get('connect_timeout', 30),
            logger=logger
        )
    except Exception as e:
        logger.error(f"连接MySQL失败: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    results = []
    success_count = 0
    failed_count = 0
    
    for table_config in tables_to_sync:
        try:
            result = sync_table(
                table_config=table_config,
                mysql_client=mysql_client,
                config=config,
                business_date=business_date,
                force_full=args.full,
                start_watermark=args.start_watermark,
                end_watermark=args.end_watermark,
                logger=logger
            )
            results.append(result)
            success_count += 1
            logger.info(f"表 {table_config['name']} 同步成功，记录数: {result['total_rows']}")
        except Exception as e:
            failed_count += 1
            error_msg = f"表 {table_config['name']} 同步失败: {e}"
            logger.error(error_msg)
            traceback.print_exc()
            results.append({
                'table_name': table_config['name'],
                'success': False,
                'error': str(e)
            })
    
    if mysql_client:
        mysql_client.close()
    
    logger.info(f"{'='*60}")
    logger.info("ODS层数据同步任务完成")
    logger.info(f"总表数: {len(tables_to_sync)}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {failed_count}")
    
    if failed_count > 0:
        logger.error("存在失败的同步任务")
        sys.exit(1)
    else:
        logger.info("所有任务同步完成")
        sys.exit(0)


if __name__ == '__main__':
    main()
