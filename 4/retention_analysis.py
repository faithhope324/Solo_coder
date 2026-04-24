#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商用户留存分析器
- 性能优化：使用向量化操作替代 apply
- 集成日志系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from logger_setup import get_logger


class RetentionAnalyzer:
    """电商用户留存分析器"""
    
    def __init__(self):
        """初始化留存分析器"""
        self.logger = get_logger('RetentionAnalyzer')
        self.analysis_results = {}
    
    def _get_user_first_activity(self, df: pd.DataFrame,
                                   user_id_col: str = 'user_id',
                                   timestamp_col: str = 'timestamp',
                                   event_type_col: Optional[str] = None,
                                   first_event_types: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取每个用户的首次活动时间
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
            event_type_col: 事件类型列名（可选）
            first_event_types: 用于定义首次活动的事件类型列表
        
        Returns:
            包含用户ID和首次活动时间的数据框
        """
        if event_type_col and first_event_types:
            df = df[df[event_type_col].isin(first_event_types)]
        
        user_first_activity = df.groupby(user_id_col)[timestamp_col].min().reset_index()
        user_first_activity.columns = [user_id_col, 'first_activity_time']
        
        user_first_activity['first_activity_date'] = user_first_activity['first_activity_time'].dt.floor('D')
        
        return user_first_activity
    
    def _get_user_activity_dates(self, df: pd.DataFrame,
                                   user_id_col: str = 'user_id',
                                   timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """
        获取每个用户的所有活动日期
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
        
        Returns:
            包含用户ID和活动日期的数据框（去重）
        """
        df = df.copy()
        df['activity_date'] = df[timestamp_col].dt.floor('D')
        
        user_activity_dates = df[[user_id_col, 'activity_date']].drop_duplicates()
        
        return user_activity_dates
    
    def calculate_daily_retention(self, df: pd.DataFrame,
                                    user_id_col: str = 'user_id',
                                    timestamp_col: str = 'timestamp',
                                    event_type_col: Optional[str] = None,
                                    first_event_types: Optional[List[str]] = None,
                                    retention_days: List[int] = [1, 3, 7, 14, 30]) -> Dict[str, Any]:
        """
        计算日留存率
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
            event_type_col: 事件类型列名
            first_event_types: 用于定义首次活动的事件类型列表
            retention_days: 需要计算的留存天数列表
        
        Returns:
            日留存分析结果
        """
        self.logger.info(f"计算日留存率，留存天数: {retention_days}")
        
        user_first = self._get_user_first_activity(
            df, user_id_col, timestamp_col, event_type_col, first_event_types
        )
        
        user_activity = self._get_user_activity_dates(df, user_id_col, timestamp_col)
        
        user_retention = user_activity.merge(
            user_first[[user_id_col, 'first_activity_date']],
            on=user_id_col,
            how='left'
        )
        
        user_retention['days_since_first'] = (
            user_retention['activity_date'] - user_retention['first_activity_date']
        ).dt.days
        
        retention_results = []
        
        for first_date, group in user_retention.groupby('first_activity_date'):
            new_users = group[user_id_col].nunique()
            
            retention_record = {
                'first_activity_date': first_date,
                'new_users': new_users
            }
            
            for day in retention_days:
                retained_users = group[group['days_since_first'] == day][user_id_col].nunique()
                retention_rate = retained_users / new_users if new_users > 0 else 0
                
                retention_record[f'day_{day}_retained'] = retained_users
                retention_record[f'day_{day}_rate'] = retention_rate
            
            retention_results.append(retention_record)
        
        retention_df = pd.DataFrame(retention_results)
        retention_df = retention_df.sort_values('first_activity_date')
        
        avg_retention = {}
        for day in retention_days:
            rate_col = f'day_{day}_rate'
            if rate_col in retention_df.columns:
                avg_retention[f'avg_day_{day}_rate'] = retention_df[rate_col].mean()
                avg_retention[f'total_day_{day}_retained'] = retention_df[f'day_{day}_retained'].sum()
        
        result = {
            'retention_df': retention_df,
            'avg_retention': avg_retention,
            'retention_days': retention_days,
            'total_new_users': retention_df['new_users'].sum() if 'new_users' in retention_df.columns else 0
        }
        
        self.analysis_results['daily_retention'] = result
        
        self.logger.info("\n日留存分析结果:")
        self.logger.info(f"  总新增用户: {result['total_new_users']}")
        self.logger.info("\n  平均留存率:")
        for key, value in avg_retention.items():
            if 'rate' in key:
                self.logger.info(f"    {key}: {value:.2%}")
        
        print("\n日留存分析结果:")
        print(f"  总新增用户: {result['total_new_users']}")
        print("\n  平均留存率:")
        for key, value in avg_retention.items():
            if 'rate' in key:
                print(f"    {key}: {value:.2%}")
        
        return result
    
    def calculate_weekly_retention(self, df: pd.DataFrame,
                                     user_id_col: str = 'user_id',
                                     timestamp_col: str = 'timestamp',
                                     event_type_col: Optional[str] = None,
                                     first_event_types: Optional[List[str]] = None,
                                     retention_weeks: List[int] = [1, 2, 3, 4, 8]) -> Dict[str, Any]:
        """
        计算周留存率（向量化实现，替代 apply）
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
            event_type_col: 事件类型列名
            first_event_types: 用于定义首次活动的事件类型列表
            retention_weeks: 需要计算的留存周数列表
        
        Returns:
            周留存分析结果
        """
        self.logger.info(f"计算周留存率，留存周数: {retention_weeks}")
        
        user_first = self._get_user_first_activity(
            df, user_id_col, timestamp_col, event_type_col, first_event_types
        )
        
        user_first['first_week'] = user_first['first_activity_time'].dt.isocalendar().week.astype(int)
        user_first['first_year'] = user_first['first_activity_time'].dt.isocalendar().year.astype(int)
        
        user_first['first_week_str'] = (
            user_first['first_year'].astype(str) + 
            'W' + 
            user_first['first_week'].astype(str).str.zfill(2)
        )
        
        df = df.copy()
        df['activity_week'] = df[timestamp_col].dt.isocalendar().week.astype(int)
        df['activity_year'] = df[timestamp_col].dt.isocalendar().year.astype(int)
        
        df['activity_week_str'] = (
            df['activity_year'].astype(str) + 
            'W' + 
            df['activity_week'].astype(str).str.zfill(2)
        )
        
        user_weekly_activity = df[[user_id_col, 'activity_week', 'activity_year', 'activity_week_str']].drop_duplicates()
        
        user_retention = user_weekly_activity.merge(
            user_first[[user_id_col, 'first_week', 'first_year', 'first_week_str']],
            on=user_id_col,
            how='left'
        )
        
        first_week_dates = pd.to_datetime(
            user_retention['first_year'].astype(str) + 
            '-W' + 
            user_retention['first_week'].astype(str) + 
            '-1',
            format='%G-W%V-%u',
            errors='coerce'
        )
        
        activity_week_dates = pd.to_datetime(
            user_retention['activity_year'].astype(str) + 
            '-W' + 
            user_retention['activity_week'].astype(str) + 
            '-1',
            format='%G-W%V-%u',
            errors='coerce'
        )
        
        user_retention['weeks_since_first'] = ((activity_week_dates - first_week_dates).dt.days / 7).astype(int)
        
        retention_results = []
        
        for first_week, group in user_retention.groupby('first_week_str'):
            new_users = group[user_id_col].nunique()
            
            retention_record = {
                'first_week': first_week,
                'new_users': new_users
            }
            
            for week in retention_weeks:
                retained_users = group[group['weeks_since_first'] == week][user_id_col].nunique()
                retention_rate = retained_users / new_users if new_users > 0 else 0
                
                retention_record[f'week_{week}_retained'] = retained_users
                retention_record[f'week_{week}_rate'] = retention_rate
            
            retention_results.append(retention_record)
        
        retention_df = pd.DataFrame(retention_results)
        retention_df = retention_df.sort_values('first_week')
        
        avg_retention = {}
        for week in retention_weeks:
            rate_col = f'week_{week}_rate'
            if rate_col in retention_df.columns:
                avg_retention[f'avg_week_{week}_rate'] = retention_df[rate_col].mean()
        
        result = {
            'retention_df': retention_df,
            'avg_retention': avg_retention,
            'retention_weeks': retention_weeks,
            'total_new_users': retention_df['new_users'].sum() if 'new_users' in retention_df.columns else 0
        }
        
        self.analysis_results['weekly_retention'] = result
        
        self.logger.info("\n周留存分析结果:")
        self.logger.info(f"  总新增用户: {result['total_new_users']}")
        self.logger.info("\n  平均留存率:")
        for key, value in avg_retention.items():
            if 'rate' in key:
                self.logger.info(f"    {key}: {value:.2%}")
        
        print("\n周留存分析结果:")
        print(f"  总新增用户: {result['total_new_users']}")
        print("\n  平均留存率:")
        for key, value in avg_retention.items():
            if 'rate' in key:
                print(f"    {key}: {value:.2%}")
        
        return result
    
    def create_cohort_analysis(self, df: pd.DataFrame,
                                 user_id_col: str = 'user_id',
                                 timestamp_col: str = 'timestamp',
                                 cohort_type: str = 'weekly') -> Dict[str, Any]:
        """
        创建同期群分析（向量化实现，替代 apply）
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
            cohort_type: 同期群类型，'weekly'（按周）或 'monthly'（按月）
        
        Returns:
            同期群分析结果
        """
        self.logger.info(f"创建同期群分析，类型: {cohort_type}")
        
        user_first = self._get_user_first_activity(df, user_id_col, timestamp_col)
        
        if cohort_type == 'weekly':
            user_first['cohort'] = user_first['first_activity_time'].dt.isocalendar().week.astype(int)
            user_first['cohort_year'] = user_first['first_activity_time'].dt.isocalendar().year.astype(int)
            user_first['cohort_label'] = (
                user_first['cohort_year'].astype(str) + 
                'W' + 
                user_first['cohort'].astype(str).str.zfill(2)
            )
        elif cohort_type == 'monthly':
            user_first['cohort'] = user_first['first_activity_time'].dt.month.astype(int)
            user_first['cohort_year'] = user_first['first_activity_time'].dt.year.astype(int)
            user_first['cohort_label'] = (
                user_first['cohort_year'].astype(str) + 
                'M' + 
                user_first['cohort'].astype(str).str.zfill(2)
            )
        else:
            raise ValueError("cohort_type 必须是 'weekly' 或 'monthly'")
        
        df = df.copy()
        
        if cohort_type == 'weekly':
            df['activity_period'] = df[timestamp_col].dt.isocalendar().week.astype(int)
            df['activity_year'] = df[timestamp_col].dt.isocalendar().year.astype(int)
        else:
            df['activity_period'] = df[timestamp_col].dt.month.astype(int)
            df['activity_year'] = df[timestamp_col].dt.year.astype(int)
        
        user_activity = df.merge(
            user_first[[user_id_col, 'cohort', 'cohort_year', 'cohort_label']],
            on=user_id_col,
            how='left'
        )
        
        if cohort_type == 'weekly':
            cohort_dates = pd.to_datetime(
                user_activity['cohort_year'].astype(str) + 
                '-W' + 
                user_activity['cohort'].astype(str) + 
                '-1',
                format='%G-W%V-%u',
                errors='coerce'
            )
            activity_dates = pd.to_datetime(
                user_activity['activity_year'].astype(str) + 
                '-W' + 
                user_activity['activity_period'].astype(str) + 
                '-1',
                format='%G-W%V-%u',
                errors='coerce'
            )
            user_activity['period_number'] = ((activity_dates - cohort_dates).dt.days / 7).astype(int)
        else:
            user_activity['period_number'] = (
                (user_activity['activity_year'] - user_activity['cohort_year']) * 12 + 
                (user_activity['activity_period'] - user_activity['cohort'])
            )
        
        cohort_data = user_activity.groupby(['cohort_label', 'period_number'])[user_id_col].nunique().reset_index()
        cohort_data.columns = ['cohort', 'period_number', 'user_count']
        
        cohort_sizes = cohort_data[cohort_data['period_number'] == 0][['cohort', 'user_count']]
        cohort_sizes.columns = ['cohort', 'cohort_size']
        
        cohort_data = cohort_data.merge(cohort_sizes, on='cohort', how='left')
        cohort_data['retention_rate'] = cohort_data['user_count'] / cohort_data['cohort_size']
        
        cohort_pivot = cohort_data.pivot_table(
            index='cohort',
            columns='period_number',
            values='retention_rate'
        )
        
        cohort_user_pivot = cohort_data.pivot_table(
            index='cohort',
            columns='period_number',
            values='user_count'
        )
        
        result = {
            'cohort_type': cohort_type,
            'cohort_data': cohort_data,
            'cohort_pivot': cohort_pivot,
            'cohort_user_pivot': cohort_user_pivot,
            'cohort_sizes': cohort_sizes
        }
        
        self.analysis_results['cohort_analysis'] = result
        
        self.logger.info(f"\n同期群分析结果 ({cohort_type}):")
        self.logger.info(f"  同期群数量: {len(cohort_pivot)}")
        self.logger.info(f"  周期数量: {len(cohort_pivot.columns)}")
        self.logger.info(f"\n  同期群大小:")
        for _, row in cohort_sizes.iterrows():
            self.logger.info(f"    {row['cohort']}: {row['cohort_size']} 用户")
        
        print(f"\n同期群分析结果 ({cohort_type}):")
        print(f"  同期群数量: {len(cohort_pivot)}")
        print(f"  周期数量: {len(cohort_pivot.columns)}")
        print(f"\n  同期群大小:")
        for _, row in cohort_sizes.iterrows():
            print(f"    {row['cohort']}: {row['cohort_size']} 用户")
        
        return result
    
    def get_retention_summary(self) -> Dict[str, Any]:
        """
        获取所有留存分析的摘要
        
        Returns:
            留存分析摘要
        """
        summary = {
            'analysis_count': len(self.analysis_results),
            'analysis_types': list(self.analysis_results.keys()),
            'results': self.analysis_results
        }
        
        return summary


if __name__ == '__main__':
    from data_generator import ECommerceDataGenerator
    from data_cleaner import DataCleaner
    
    generator = ECommerceDataGenerator(num_events=10000)
    events, _, _ = generator.generate(add_dirty_data=True)
    
    cleaner = DataCleaner()
    cleaned_data, _ = cleaner.clean(events)
    
    analyzer = RetentionAnalyzer()
    
    print("\n" + "="*50)
    print("日留存分析")
    print("="*50)
    daily_result = analyzer.calculate_daily_retention(cleaned_data)
    
    print("\n" + "="*50)
    print("周留存分析")
    print("="*50)
    weekly_result = analyzer.calculate_weekly_retention(cleaned_data)
    
    print("\n" + "="*50)
    print("同期群分析（按周）")
    print("="*50)
    cohort_result = analyzer.create_cohort_analysis(cleaned_data, cohort_type='weekly')
