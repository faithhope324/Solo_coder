#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商用户行为分析系统
完整的数据分析流程：数据生成 -> 数据清洗 -> 漏斗分析 -> 留存分析 -> 生成HTML报表
"""

import argparse
import os
from datetime import datetime
from typing import Dict, Any, Optional

from logger_setup import get_logger, get_log_dir

# 导入各模块
from data_generator import ECommerceDataGenerator
from data_cleaner import DataCleaner
from funnel_analysis import FunnelAnalyzer
from retention_analysis import RetentionAnalyzer
from html_report import HTMLReportGenerator

logger = get_logger('Main')


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='电商用户行为分析系统 - 完整的数据分析流程',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 使用默认参数运行完整分析
  python main.py
  
  # 自定义数据规模
  python main.py --users 20000 --products 10000 --events 200000
  
  # 指定数据时间范围
  python main.py --start-date 2024-01-01 --end-date 2024-06-30
  
  # 从现有CSV文件加载数据（不生成新数据）
  python main.py --load-data ./data/user_events.csv
  
  # 保存生成的数据到文件
  python main.py --save-data --output-dir ./output
        '''
    )
    
    # 数据生成参数
    data_group = parser.add_argument_group('数据生成参数')
    data_group.add_argument('--users', type=int, default=10000,
                            help='用户数量 (默认: 10000)')
    data_group.add_argument('--products', type=int, default=5000,
                            help='商品数量 (默认: 5000)')
    data_group.add_argument('--events', type=int, default=100000,
                            help='行为事件数量 (默认: 100000)')
    data_group.add_argument('--start-date', type=str, default='2024-01-01',
                            help='数据开始日期 (默认: 2024-01-01)')
    data_group.add_argument('--end-date', type=str, default='2024-03-31',
                            help='数据结束日期 (默认: 2024-03-31)')
    data_group.add_argument('--no-dirty-data', action='store_true',
                            help='不生成脏数据（默认会生成脏数据用于测试清洗功能）')
    
    # 数据加载/保存参数
    io_group = parser.add_argument_group('数据输入输出参数')
    io_group.add_argument('--load-data', type=str, default=None,
                          help='从指定CSV文件加载数据，不生成新数据')
    io_group.add_argument('--save-data', action='store_true',
                          help='保存生成的数据到CSV文件')
    io_group.add_argument('--output-dir', type=str, default='./output',
                          help='输出目录 (默认: ./output)')
    io_group.add_argument('--report-name', type=str, default='ecommerce_analysis_report',
                          help='报表文件名 (默认: ecommerce_analysis_report)')
    
    # 分析参数
    analysis_group = parser.add_argument_group('分析参数')
    analysis_group.add_argument('--retention-days', type=str, default='1,3,7,14,30',
                                help='留存天数列表，逗号分隔 (默认: 1,3,7,14,30)')
    analysis_group.add_argument('--cohort-type', type=str, default='weekly',
                                choices=['weekly', 'monthly'],
                                help='同期群分析类型: weekly 或 monthly (默认: weekly)')
    
    # 其他参数
    parser.add_argument('--random-seed', type=int, default=42,
                        help='随机种子 (默认: 42)')
    parser.add_argument('--verbose', action='store_true',
                        help='显示详细输出信息')
    
    return parser.parse_args()


def run_analysis(args) -> Optional[str]:
    """
    执行完整的分析流程
    
    Args:
        args: 命令行参数
    
    Returns:
        报表文件路径（如果成功），否则返回 None
    """
    start_time = datetime.now()
    
    logger.info("=" * 70)
    logger.info("电商用户行为分析系统 - 开始执行分析流程")
    logger.info("=" * 70)
    logger.info(f"分析开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"日志目录: {get_log_dir()}")
    
    print("=" * 70)
    print("电商用户行为分析系统")
    print("=" * 70)
    print(f"分析开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info("步骤1: 获取数据")
    print("-" * 70)
    print("步骤1: 获取数据")
    print("-" * 70)
    
    if args.load_data:
        logger.info(f"从文件加载数据: {args.load_data}")
        print(f"从文件加载数据: {args.load_data}")
        cleaner = DataCleaner()
        raw_data = cleaner.load_data(args.load_data)
    else:
        logger.info("生成模拟电商用户行为数据...")
        print("生成模拟电商用户行为数据...")
        generator = ECommerceDataGenerator(
            num_users=args.users,
            num_products=args.products,
            num_events=args.events,
            start_date=args.start_date,
            end_date=args.end_date,
            random_seed=args.random_seed
        )
        
        raw_data, products_data, sessions_data = generator.generate(
            add_dirty_data=not args.no_dirty_data
        )
        
        if args.save_data:
            logger.info("保存生成的数据到文件...")
            generator.save_to_csv(raw_data, products_data, sessions_data, args.output_dir)
    
    print()
    
    logger.info("步骤2: 数据清洗")
    print("-" * 70)
    print("步骤2: 数据清洗")
    print("-" * 70)
    
    cleaner = DataCleaner()
    cleaned_data, cleaning_stats = cleaner.clean(raw_data)
    cleaning_report = cleaner.get_cleaning_report()
    
    if args.verbose:
        logger.info(f"清洗报告详情:")
        logger.info(f"  原始数据形状: {cleaning_report['original_shape']}")
        logger.info(f"  清洗后数据形状: {cleaning_report['cleaned_shape']}")
        logger.info(f"  删除行数: {cleaning_report['rows_removed']}")
        print(f"\n清洗报告详情:")
        print(f"  原始数据形状: {cleaning_report['original_shape']}")
        print(f"  清洗后数据形状: {cleaning_report['cleaned_shape']}")
        print(f"  删除行数: {cleaning_report['rows_removed']}")
    
    print()
    
    logger.info("步骤3: 漏斗转化分析")
    print("-" * 70)
    print("步骤3: 漏斗转化分析")
    print("-" * 70)
    
    funnel_analyzer = FunnelAnalyzer()
    
    basic_funnel = funnel_analyzer.analyze_basic_funnel(cleaned_data)
    session_funnel = funnel_analyzer.analyze_session_funnel(cleaned_data)
    
    if 'device_type' in cleaned_data.columns:
        device_funnel = funnel_analyzer.analyze_funnel_by_dimension(
            cleaned_data, 'device_type'
        )
    else:
        device_funnel = None
    
    print()
    
    logger.info("步骤4: 用户留存分析")
    print("-" * 70)
    print("步骤4: 用户留存分析")
    print("-" * 70)
    
    retention_days = [int(d.strip()) for d in args.retention_days.split(',')]
    
    retention_analyzer = RetentionAnalyzer()
    
    daily_retention = retention_analyzer.calculate_daily_retention(
        cleaned_data,
        retention_days=retention_days
    )
    
    weekly_retention = retention_analyzer.calculate_weekly_retention(cleaned_data)
    
    cohort_analysis = retention_analyzer.create_cohort_analysis(
        cleaned_data,
        cohort_type=args.cohort_type
    )
    
    print()
    
    logger.info("步骤5: 生成HTML交互式报表")
    print("-" * 70)
    print("步骤5: 生成HTML交互式报表")
    print("-" * 70)
    
    summary_data = {
        'total_users': cleaned_data['user_id'].nunique(),
        'total_events': len(cleaned_data),
        'overall_conversion_rate': basic_funnel['metrics']['overall_conversion_rate'],
        'avg_day_1_rate': daily_retention['avg_retention'].get('avg_day_1_rate', 0)
    }
    
    report = HTMLReportGenerator(title="电商用户行为分析报告")
    
    report.add_all_charts(
        funnel_data=basic_funnel['funnel_data'],
        retention_df=daily_retention['retention_df'],
        retention_days=daily_retention['retention_days'],
        cohort_pivot=cohort_analysis['cohort_pivot'],
        event_df=cleaned_data,
        daily_activity_df=cleaned_data
    )
    
    report_path = os.path.join(args.output_dir, f"{args.report_name}.html")
    report.generate_html_report(report_path, summary_data)
    
    print()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("=" * 70)
    logger.info("分析完成摘要")
    logger.info("=" * 70)
    logger.info(f"分析结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"总耗时: {duration:.2f} 秒")
    
    logger.info(f"\n1. 数据统计:")
    logger.info(f"   - 总用户数: {summary_data['total_users']:,}")
    logger.info(f"   - 总事件数: {summary_data['total_events']:,}")
    logger.info(f"   - 数据时间范围: {args.start_date} 至 {args.end_date}")
    
    logger.info(f"\n2. 漏斗转化分析:")
    logger.info(f"   - 整体转化率: {summary_data['overall_conversion_rate']:.2%}")
    for stage in basic_funnel['metrics']['stages']:
        logger.info(f"   - {stage['stage']}: {stage['count']:,} 用户 "
              f"(转化率: {stage['conversion_rate']:.2%}, "
              f"整体转化: {stage['overall_conversion']:.2%})")
    
    logger.info(f"\n3. 留存分析:")
    logger.info(f"   - 总新增用户: {daily_retention['total_new_users']:,}")
    for day in retention_days:
        rate_key = f'avg_day_{day}_rate'
        if rate_key in daily_retention['avg_retention']:
            logger.info(f"   - 第{day}日留存率: {daily_retention['avg_retention'][rate_key]:.2%}")
    
    logger.info(f"\n4. 输出文件:")
    logger.info(f"   - HTML报表: {os.path.abspath(report_path)}")
    logger.info(f"   - 日志文件: {get_log_dir()}/")
    if args.save_data and not args.load_data:
        logger.info(f"   - 数据文件: {os.path.abspath(args.output_dir)}/")
    
    print("=" * 70)
    print("分析完成摘要")
    print("=" * 70)
    
    print(f"\n1. 数据统计:")
    print(f"   - 总用户数: {summary_data['total_users']:,}")
    print(f"   - 总事件数: {summary_data['total_events']:,}")
    print(f"   - 数据时间范围: {args.start_date} 至 {args.end_date}")
    
    print(f"\n2. 漏斗转化分析:")
    print(f"   - 整体转化率: {summary_data['overall_conversion_rate']:.2%}")
    for stage in basic_funnel['metrics']['stages']:
        print(f"   - {stage['stage']}: {stage['count']:,} 用户 "
              f"(转化率: {stage['conversion_rate']:.2%}, "
              f"整体转化: {stage['overall_conversion']:.2%})")
    
    print(f"\n3. 留存分析:")
    print(f"   - 总新增用户: {daily_retention['total_new_users']:,}")
    for day in retention_days:
        rate_key = f'avg_day_{day}_rate'
        if rate_key in daily_retention['avg_retention']:
            print(f"   - 第{day}日留存率: {daily_retention['avg_retention'][rate_key]:.2%}")
    
    print(f"\n4. 输出文件:")
    print(f"   - HTML报表: {os.path.abspath(report_path)}")
    print(f"   - 日志文件: {get_log_dir()}/")
    if args.save_data and not args.load_data:
        print(f"   - 数据文件: {os.path.abspath(args.output_dir)}/")
    
    print(f"\n分析结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration:.2f} 秒")
    print("=" * 70)
    
    logger.info(f"分析流程完成，总耗时: {duration:.2f} 秒")
    
    return report_path


def interactive_mode():
    """
    交互式模式 - 允许用户通过问答方式配置分析参数
    """
    print("=" * 70)
    print("电商用户行为分析系统 - 交互式模式")
    print("=" * 70)
    print()
    
    # 询问用户是否需要生成数据
    print("数据来源:")
    print("  1. 生成模拟数据（推荐）")
    print("  2. 从CSV文件加载数据")
    
    choice = input("\n请选择 (1/2, 默认: 1): ").strip() or '1'
    
    class Args:
        def __init__(self):
            self.load_data = None
            self.users = 10000
            self.products = 5000
            self.events = 100000
            self.start_date = '2024-01-01'
            self.end_date = '2024-03-31'
            self.no_dirty_data = False
            self.save_data = False
            self.output_dir = './output'
            self.report_name = 'ecommerce_analysis_report'
            self.retention_days = '1,3,7,14,30'
            self.cohort_type = 'weekly'
            self.random_seed = 42
            self.verbose = False
    
    args = Args()
    
    if choice == '2':
        file_path = input("请输入CSV文件路径: ").strip()
        if os.path.exists(file_path):
            args.load_data = file_path
        else:
            print(f"文件不存在: {file_path}，将使用默认参数生成数据")
            choice = '1'
    
    if choice == '1':
        # 询问数据规模
        print("\n数据规模配置 (直接回车使用默认值):")
        
        users_input = input(f"  用户数量 (默认: {args.users}): ").strip()
        if users_input and users_input.isdigit():
            args.users = int(users_input)
        
        products_input = input(f"  商品数量 (默认: {args.products}): ").strip()
        if products_input and products_input.isdigit():
            args.products = int(products_input)
        
        events_input = input(f"  事件数量 (默认: {args.events}): ").strip()
        if events_input and events_input.isdigit():
            args.events = int(events_input)
        
        # 询问时间范围
        print("\n时间范围配置:")
        start_input = input(f"  开始日期 (默认: {args.start_date}): ").strip()
        if start_input:
            args.start_date = start_input
        
        end_input = input(f"  结束日期 (默认: {args.end_date}): ").strip()
        if end_input:
            args.end_date = end_input
        
        # 询问是否生成脏数据
        dirty_input = input("\n  是否生成脏数据用于测试清洗功能? (y/n, 默认: y): ").strip().lower()
        args.no_dirty_data = dirty_input == 'n'
        
        # 询问是否保存数据
        save_input = input("\n  是否保存生成的数据到CSV文件? (y/n, 默认: n): ").strip().lower()
        args.save_data = save_input == 'y'
    
    # 输出配置
    print("\n输出配置:")
    output_input = input(f"  输出目录 (默认: {args.output_dir}): ").strip()
    if output_input:
        args.output_dir = output_input
    
    report_input = input(f"  报表文件名 (默认: {args.report_name}): ").strip()
    if report_input:
        args.report_name = report_input
    
    # 确认配置
    print("\n" + "-" * 70)
    print("配置确认:")
    print("-" * 70)
    if args.load_data:
        print(f"  数据来源: 从文件加载 - {args.load_data}")
    else:
        print(f"  数据来源: 生成模拟数据")
        print(f"  用户数量: {args.users:,}")
        print(f"  商品数量: {args.products:,}")
        print(f"  事件数量: {args.events:,}")
        print(f"  时间范围: {args.start_date} 至 {args.end_date}")
        print(f"  生成脏数据: {'否' if args.no_dirty_data else '是'}")
        print(f"  保存数据: {'是' if args.save_data else '否'}")
    print(f"  输出目录: {args.output_dir}")
    print(f"  报表文件名: {args.report_name}.html")
    
    confirm = input("\n确认执行分析? (y/n, 默认: y): ").strip().lower()
    if confirm and confirm != 'y':
        print("分析已取消。")
        return None
    
    print()
    return run_analysis(args)


def main():
    """主函数"""
    # 检查是否有命令行参数
    import sys
    if len(sys.argv) > 1:
        # 命令行模式
        args = parse_arguments()
        results = run_analysis(args)
    else:
        # 交互式模式
        results = interactive_mode()
    
    return results


if __name__ == '__main__':
    main()
