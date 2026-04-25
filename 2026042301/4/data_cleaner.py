#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商用户行为数据清洗器
- 性能优化：使用向量化操作替代 apply
- 集成日志系统
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

from logger_setup import get_logger


class DataCleaner:
    """电商用户行为数据清洗器"""
    
    def __init__(self):
        """初始化数据清洗器"""
        self.logger = get_logger('DataCleaner')
        self.cleaning_stats = {}
        self.original_shape = None
        self.cleaned_shape = None
    
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        从 CSV 文件加载数据
        
        Args:
            file_path: CSV 文件路径
        
        Returns:
            加载的 DataFrame
        """
        self.logger.info(f"正在加载数据: {file_path}")
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        self.original_shape = df.shape
        self.logger.info(f"加载完成，原始数据形状: {df.shape}")
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        处理缺失值（向量化实现）
        
        Args:
            df: 原始数据
        
        Returns:
            处理后的数据和处理统计信息
        """
        stats = {}
        stats['initial_missing'] = df.isnull().sum().to_dict()
        stats['initial_missing_total'] = int(df.isnull().sum().sum())
        
        self.logger.info(f"开始处理缺失值，初始缺失总数: {stats['initial_missing_total']}")
        
        key_columns = ['user_id', 'event_id', 'event_type']
        initial_rows = len(df)
        df = df.dropna(subset=key_columns)
        stats['rows_removed_key_columns'] = initial_rows - len(df)
        
        if 'price' in df.columns:
            valid_price_mask = df['price'].between(1, 10000) & df['price'].notna()
            price_median = df.loc[valid_price_mask, 'price'].median()
            
            missing_price_mask = df['price'].isna()
            stats['price_missing_count'] = int(missing_price_mask.sum())
            
            df.loc[missing_price_mask, 'price'] = price_median
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            
            outlier_price_mask = ~df['price'].between(1, 10000) & df['price'].notna()
            df.loc[outlier_price_mask, 'price'] = price_median
        
        if 'product_id' in df.columns:
            df['product_id'] = pd.to_numeric(df['product_id'], errors='coerce').fillna(0).astype(int)
        
        categorical_cols = ['category', 'device_type', 'referrer', 'page_url']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].fillna('unknown')
        
        stats['final_missing'] = df.isnull().sum().to_dict()
        stats['final_missing_total'] = int(df.isnull().sum().sum())
        stats['rows_removed_missing'] = self.original_shape[0] - len(df) if self.original_shape else 0
        
        self.logger.info(f"缺失值处理完成，剩余缺失数: {stats['final_missing_total']}")
        
        return df, stats
    
    def _handle_outliers(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        处理异常值（向量化实现）
        
        Args:
            df: 原始数据
        
        Returns:
            处理后的数据和处理统计信息
        """
        stats = {}
        
        if 'price' in df.columns:
            valid_price_mask = df['price'].between(1, 10000)
            initial_outliers = int((~valid_price_mask).sum())
            stats['initial_price_outliers'] = initial_outliers
            
            if initial_outliers > 0:
                price_median = df.loc[valid_price_mask, 'price'].median()
                df.loc[~valid_price_mask, 'price'] = price_median
                stats['price_outliers_fixed'] = initial_outliers
                self.logger.info(f"修复了 {initial_outliers} 个价格异常值")
        
        return df, stats
    
    def _handle_format_conversion(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        处理格式转换（向量化实现，替代 apply）
        
        Args:
            df: 原始数据
        
        Returns:
            处理后的数据和处理统计信息
        """
        stats = {}
        stats['timestamp_errors'] = 0
        
        if 'timestamp' in df.columns:
            self.logger.info("开始处理时间戳格式转换（向量化）")
            
            original_count = len(df)
            
            parsed_timestamps = pd.to_datetime(
                df['timestamp'],
                errors='coerce'
            )
            
            unix_mask = pd.to_numeric(df['timestamp'], errors='coerce').notna() & parsed_timestamps.isna()
            if unix_mask.any():
                unix_values = pd.to_numeric(df.loc[unix_mask, 'timestamp'], errors='coerce')
                parsed_unix = pd.to_datetime(unix_values, unit='s', errors='coerce')
                parsed_timestamps.loc[unix_mask] = parsed_unix
            
            df['timestamp'] = parsed_timestamps
            
            invalid_timestamps = int(df['timestamp'].isnull().sum())
            stats['timestamp_errors'] = invalid_timestamps
            
            if invalid_timestamps > 0:
                self.logger.warning(f"发现 {invalid_timestamps} 个无法解析的时间戳，将删除这些行")
                df = df.dropna(subset=['timestamp'])
            
            now = pd.Timestamp.now()
            earliest_valid = pd.Timestamp('2020-01-01')
            
            invalid_time_mask = (df['timestamp'] > now) | (df['timestamp'] < earliest_valid)
            invalid_time_count = int(invalid_time_mask.sum())
            
            if invalid_time_count > 0:
                stats['time_range_errors'] = invalid_time_count
                self.logger.warning(f"发现 {invalid_time_count} 个时间范围异常的行，将删除这些行")
                df = df[~invalid_time_mask]
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            self.logger.info(f"时间戳处理完成，有效时间戳: {len(df)} 个")
        
        numeric_cols = ['user_id', 'product_id', 'session_id', 'event_id']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        return df, stats
    
    def _handle_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        处理重复数据（向量化实现）
        
        Args:
            df: 原始数据
        
        Returns:
            处理后的数据和处理统计信息
        """
        stats = {}
        
        initial_duplicates = int(df.duplicated().sum())
        stats['initial_duplicates'] = initial_duplicates
        
        if initial_duplicates > 0:
            df = df.drop_duplicates(keep='first')
            stats['duplicates_removed'] = initial_duplicates
            self.logger.info(f"删除了 {initial_duplicates} 个重复行")
        
        if 'event_id' in df.columns:
            event_id_duplicates = int(df['event_id'].duplicated().sum())
            stats['event_id_duplicates'] = event_id_duplicates
            
            if event_id_duplicates > 0:
                df = df.drop_duplicates(subset=['event_id'], keep='first')
                self.logger.info(f"删除了 {event_id_duplicates} 个重复的 event_id")
        
        return df, stats
    
    def _validate_cleaned_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        验证清洗后的数据质量
        
        Args:
            df: 清洗后的数据
        
        Returns:
            数据质量报告
        """
        validation = {}
        
        validation['missing_values'] = df.isnull().sum().to_dict()
        validation['total_missing'] = int(df.isnull().sum().sum())
        
        validation['data_types'] = df.dtypes.astype(str).to_dict()
        validation['duplicate_rows'] = int(df.duplicated().sum())
        
        if 'price' in df.columns:
            validation['price_range'] = {
                'min': float(df['price'].min()),
                'max': float(df['price'].max()),
                'median': float(df['price'].median())
            }
        
        if 'timestamp' in df.columns:
            validation['time_range'] = {
                'min': str(df['timestamp'].min()),
                'max': str(df['timestamp'].max())
            }
        
        if 'event_type' in df.columns:
            validation['event_types'] = df['event_type'].value_counts().to_dict()
        
        return validation
    
    def clean(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        执行完整的数据清洗流程
        
        Args:
            df: 原始数据
        
        Returns:
            清洗后的数据和清洗统计信息
        """
        self.logger.info("=" * 70)
        self.logger.info("开始数据清洗流程")
        self.logger.info("=" * 70)
        self.logger.info(f"原始数据形状: {df.shape}")
        
        self.original_shape = df.shape
        
        self.logger.info("\n步骤1: 处理重复数据...")
        df, dup_stats = self._handle_duplicates(df)
        self.cleaning_stats['duplicates'] = dup_stats
        
        self.logger.info("\n步骤2: 处理格式转换...")
        df, format_stats = self._handle_format_conversion(df)
        self.cleaning_stats['format'] = format_stats
        
        self.logger.info("\n步骤3: 处理缺失值...")
        df, missing_stats = self._handle_missing_values(df)
        self.cleaning_stats['missing'] = missing_stats
        
        self.logger.info("\n步骤4: 处理异常值...")
        df, outlier_stats = self._handle_outliers(df)
        self.cleaning_stats['outliers'] = outlier_stats
        
        self.logger.info("\n步骤5: 验证数据质量...")
        validation = self._validate_cleaned_data(df)
        self.cleaning_stats['validation'] = validation
        
        self.cleaned_shape = df.shape
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info("数据清洗完成总结")
        self.logger.info("=" * 70)
        self.logger.info(f"  原始数据: {self.original_shape[0]} 行, {self.original_shape[1]} 列")
        self.logger.info(f"  清洗后数据: {self.cleaned_shape[0]} 行, {self.cleaned_shape[1]} 列")
        self.logger.info(f"  删除行数: {self.original_shape[0] - self.cleaned_shape[0]}")
        
        print("\n数据清洗完成:")
        print(f"  原始数据: {self.original_shape[0]} 行, {self.original_shape[1]} 列")
        print(f"  清洗后数据: {self.cleaned_shape[0]} 行, {self.cleaned_shape[1]} 列")
        print(f"  删除行数: {self.original_shape[0] - self.cleaned_shape[0]}")
        
        return df, self.cleaning_stats
    
    def get_cleaning_report(self) -> Dict[str, Any]:
        """
        获取数据清洗报告
        
        Returns:
            完整的清洗报告字典
        """
        return {
            'original_shape': self.original_shape,
            'cleaned_shape': self.cleaned_shape,
            'cleaning_stats': self.cleaning_stats,
            'rows_removed': self.original_shape[0] - self.cleaned_shape[0] if self.original_shape and self.cleaned_shape else 0,
            'processing_time': str(datetime.now())
        }


if __name__ == '__main__':
    from data_generator import ECommerceDataGenerator
    
    generator = ECommerceDataGenerator(num_events=10000)
    events, _, _ = generator.generate(add_dirty_data=True)
    
    cleaner = DataCleaner()
    cleaned_data, stats = cleaner.clean(events)
    
    print("\n清洗报告:")
    report = cleaner.get_cleaning_report()
    for key, value in report.items():
        print(f"  {key}: {value}")
