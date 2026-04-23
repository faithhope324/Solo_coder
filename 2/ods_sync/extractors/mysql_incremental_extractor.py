"""
MySQL增量抽取器模块 - 支持时间戳和主键ID两种增量方式
"""
import os
import csv
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ods_sync.utils.mysql_client import MySQLClient
from ods_sync.utils.retry import mysql_retry


class IncrementalExtractor:
    """MySQL增量抽取器"""
    
    INCREMENT_MODE_TIMESTAMP = 'timestamp'
    INCREMENT_MODE_PRIMARY_KEY = 'primary_key'
    INCREMENT_MODE_FULL = 'full'
    
    def __init__(self, mysql_client: MySQLClient, 
                 table_name: str,
                 increment_mode: str = INCREMENT_MODE_TIMESTAMP,
                 increment_column: str = 'create_time',
                 batch_size: int = 10000,
                 output_dir: str = './output',
                 watermark_dir: str = './watermark',
                 logger: logging.Logger = None):
        """
        初始化增量抽取器
        
        Args:
            mysql_client: MySQL客户端实例
            table_name: 源表名
            increment_mode: 增量模式 (timestamp/primary_key/full)
            increment_column: 增量列名 (时间戳列或主键列)
            batch_size: 批处理大小
            output_dir: 输出目录
            watermark_dir: 水印文件目录
            logger: 日志记录器
        """
        self.mysql_client = mysql_client
        self.table_name = table_name
        self.increment_mode = increment_mode
        self.increment_column = increment_column
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.watermark_dir = Path(watermark_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.watermark_dir.mkdir(parents=True, exist_ok=True)
        
        self._primary_keys: Optional[List[str]] = None
        self._columns: Optional[List[Dict[str, Any]]] = None
    
    def _get_primary_keys(self) -> List[str]:
        """获取表的主键列表"""
        if self._primary_keys is None:
            self._primary_keys = self.mysql_client.get_primary_keys(self.table_name)
        return self._primary_keys
    
    def _get_columns(self) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        if self._columns is None:
            self._columns = self.mysql_client.get_table_columns(self.table_name)
        return self._columns
    
    def _get_column_names(self) -> List[str]:
        """获取列名列表"""
        return [col['COLUMN_NAME'] for col in self._get_columns()]
    
    def _get_watermark_file(self) -> Path:
        """获取水印文件路径"""
        return self.watermark_dir / f'{self.table_name}.wm'
    
    def _read_watermark(self) -> Optional[str]:
        """
        读取水印值
        
        Returns:
            水印值，如果不存在则返回None
        """
        watermark_file = self._get_watermark_file()
        
        if watermark_file.exists():
            with open(watermark_file, 'r', encoding='utf-8') as f:
                watermark = f.read().strip()
                self.logger.info(f"读取到水印: {watermark}")
                return watermark
        return None
    
    def _write_watermark(self, watermark: str):
        """
        写入水印值
        
        Args:
            watermark: 水印值
        """
        watermark_file = self._get_watermark_file()
        
        with open(watermark_file, 'w', encoding='utf-8') as f:
            f.write(str(watermark))
        
        self.logger.info(f"写入水印: {watermark}")
    
    def _format_value(self, value: Any, col_info: Dict[str, Any]) -> str:
        """
        格式化值为字符串（用于CSV输出）
        
        Args:
            value: 原始值
            col_info: 列信息
            
        Returns:
            格式化后的字符串
        """
        if value is None:
            return ''
        
        data_type = col_info['DATA_TYPE'].lower()
        
        if data_type in ['datetime', 'timestamp', 'date']:
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date):
                return value.strftime('%Y-%m-%d')
            else:
                return str(value)
        elif data_type in ['tinyint', 'smallint', 'int', 'integer', 'bigint']:
            return str(int(value))
        elif data_type in ['float', 'double', 'decimal']:
            return str(float(value))
        else:
            return str(value)
    
    def _write_to_csv(self, rows: List[Dict[str, Any]], 
                       output_file: Path, 
                       is_append: bool = False) -> int:
        """
        将数据写入CSV文件
        
        Args:
            rows: 数据行列表
            output_file: 输出文件路径
            is_append: 是否追加模式
            
        Returns:
            写入的行数
        """
        if not rows:
            return 0
        
        column_names = self._get_column_names()
        columns = self._get_columns()
        
        file_exists = output_file.exists()
        write_header = is_append and file_exists
        
        with open(output_file, 'a' if is_append else 'w', 
                  encoding='utf-8', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            
            if not write_header:
                writer.writerow(column_names)
            
            for row in rows:
                formatted_row = []
                for col in columns:
                    col_name = col['COLUMN_NAME']
                    value = row.get(col_name)
                    formatted_row.append(self._format_value(value, col))
                writer.writerow(formatted_row)
        
        return len(rows)
    
    @mysql_retry(max_attempts=5, wait_seconds=2.0)
    def _fetch_batch(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        批量获取数据（带重试）
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            数据行列表
        """
        return self.mysql_client.execute_query(sql, params)
    
    def _build_increment_query(self, start_watermark: Optional[str], 
                                end_watermark: Optional[str],
                                offset: int, 
                                limit: int) -> Tuple[str, Tuple]:
        """
        构建增量查询SQL
        
        Args:
            start_watermark: 起始水印
            end_watermark: 结束水印
            offset: 偏移量
            limit: 限制数量
            
        Returns:
            (SQL语句, 参数元组)
        """
        column_names = ', '.join([f'`{col}`' for col in self._get_column_names()])
        base_sql = f"SELECT {column_names} FROM `{self.table_name}`"
        conditions = []
        params = []
        
        if self.increment_mode == self.INCREMENT_MODE_TIMESTAMP:
            if start_watermark:
                conditions.append(f"`{self.increment_column}` > %s")
                params.append(start_watermark)
            if end_watermark:
                conditions.append(f"`{self.increment_column}` <= %s")
                params.append(end_watermark)
        elif self.increment_mode == self.INCREMENT_MODE_PRIMARY_KEY:
            if start_watermark:
                conditions.append(f"`{self.increment_column}` > %s")
                params.append(int(start_watermark))
            if end_watermark:
                conditions.append(f"`{self.increment_column}` <= %s")
                params.append(int(end_watermark))
        
        if conditions:
            where_clause = " AND ".join(conditions)
            base_sql += f" WHERE {where_clause}"
        
        if self.increment_mode == self.INCREMENT_MODE_PRIMARY_KEY:
            base_sql += f" ORDER BY `{self.increment_column}`"
        else:
            primary_keys = self._get_primary_keys()
            if primary_keys:
                order_by = ', '.join([f'`{pk}`' for pk in primary_keys])
                base_sql += f" ORDER BY {order_by}"
        
        base_sql += f" LIMIT %s, %s"
        params.extend([offset, limit])
        
        return base_sql, tuple(params)
    
    def _get_current_max_watermark(self) -> Optional[str]:
        """
        获取当前表的最大水印值
        
        Returns:
            最大水印值
        """
        condition = None
        
        if self.increment_mode == self.INCREMENT_MODE_TIMESTAMP:
            min_val, max_val = self.mysql_client.get_min_max_value(
                self.table_name, self.increment_column, condition
            )
            if max_val:
                if isinstance(max_val, datetime):
                    return max_val.strftime('%Y-%m-%d %H:%M:%S')
                return str(max_val)
        elif self.increment_mode == self.INCREMENT_MODE_PRIMARY_KEY:
            min_val, max_val = self.mysql_client.get_min_max_value(
                self.table_name, self.increment_column, condition
            )
            if max_val is not None:
                return str(max_val)
        
        return None
    
    def _get_batch_max_watermark(self, rows: List[Dict[str, Any]]) -> Optional[str]:
        """
        获取批次数据中的最大水印值
        
        Args:
            rows: 数据行列表
            
        Returns:
            最大水印值
        """
        if not rows:
            return None
        
        values = [row.get(self.increment_column) for row in rows]
        valid_values = [v for v in values if v is not None]
        
        if not valid_values:
            return None
        
        max_val = max(valid_values)
        
        if isinstance(max_val, datetime):
            return max_val.strftime('%Y-%m-%d %H:%M:%S')
        
        return str(max_val)
    
    def extract(self, business_date: str = None, 
                start_watermark: str = None,
                end_watermark: str = None,
                force_full: bool = False) -> Dict[str, Any]:
        """
        执行数据抽取
        
        Args:
            business_date: 业务日期 (YYYY-MM-DD格式)
            start_watermark: 起始水印（优先于读取的水印文件）
            end_watermark: 结束水印
            force_full: 是否强制全量抽取
            
        Returns:
            抽取结果统计
        """
        if business_date is None:
            business_date = datetime.now().strftime('%Y-%m-%d')
        
        self.logger.info(f"开始抽取表: {self.table_name}")
        self.logger.info(f"业务日期: {business_date}")
        self.logger.info(f"增量模式: {self.increment_mode}")
        self.logger.info(f"增量列: {self.increment_column}")
        
        if force_full:
            self.increment_mode = self.INCREMENT_MODE_FULL
            self.logger.info("强制全量抽取模式")
        
        if start_watermark is None and self.increment_mode != self.INCREMENT_MODE_FULL:
            start_watermark = self._read_watermark()
        
        if end_watermark is None:
            if self.increment_mode == self.INCREMENT_MODE_TIMESTAMP:
                end_watermark = f"{business_date} 23:59:59"
            else:
                end_watermark = self._get_current_max_watermark()
        
        self.logger.info(f"起始水印: {start_watermark}")
        self.logger.info(f"结束水印: {end_watermark}")
        
        output_file = self.output_dir / f'{self.table_name}_{business_date}.csv'
        if output_file.exists():
            output_file.unlink()
            self.logger.info(f"删除已存在的输出文件: {output_file}")
        
        total_rows = 0
        offset = 0
        batch_count = 0
        current_max_watermark = start_watermark
        
        while True:
            batch_count += 1
            
            if self.increment_mode == self.INCREMENT_MODE_FULL:
                column_names = ', '.join([f'`{col}`' for col in self._get_column_names()])
                primary_keys = self._get_primary_keys()
                if primary_keys:
                    order_by = ', '.join([f'`{pk}`' for pk in primary_keys])
                    sql = f"SELECT {column_names} FROM `{self.table_name}` ORDER BY {order_by} LIMIT %s, %s"
                else:
                    sql = f"SELECT {column_names} FROM `{self.table_name}` LIMIT %s, %s"
                params = (offset, self.batch_size)
            else:
                sql, params = self._build_increment_query(
                    start_watermark, end_watermark, offset, self.batch_size
                )
            
            self.logger.info(f"开始第 {batch_count} 批抽取 (offset={offset})")
            
            try:
                rows = self._fetch_batch(sql, params)
            except Exception as e:
                self.logger.error(f"第 {batch_count} 批抽取失败: {e}")
                raise
            
            batch_size = len(rows)
            total_rows += batch_size
            
            self.logger.info(f"第 {batch_count} 批获取 {batch_size} 条记录")
            
            if batch_size == 0:
                break
            
            if self.increment_mode != self.INCREMENT_MODE_FULL:
                batch_max = self._get_batch_max_watermark(rows)
                if batch_max:
                    current_max_watermark = batch_max
            
            written = self._write_to_csv(rows, output_file, is_append=total_rows > batch_size)
            self.logger.info(f"第 {batch_count} 批写入 {written} 条记录到 {output_file}")
            
            if batch_size < self.batch_size:
                break
            
            offset += self.batch_size
        
        if total_rows > 0 and self.increment_mode != self.INCREMENT_MODE_FULL:
            final_watermark = end_watermark if end_watermark else current_max_watermark
            if final_watermark:
                self._write_watermark(final_watermark)
        
        result = {
            'table_name': self.table_name,
            'business_date': business_date,
            'increment_mode': self.increment_mode,
            'start_watermark': start_watermark,
            'end_watermark': end_watermark,
            'total_rows': total_rows,
            'total_batches': batch_count,
            'output_file': str(output_file) if total_rows > 0 else None,
            'success': True
        }
        
        self.logger.info(f"抽取完成: {result}")
        return result
