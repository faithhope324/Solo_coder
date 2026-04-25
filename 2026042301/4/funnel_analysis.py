#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
电商用户行为漏斗分析器
- 性能优化：尽量使用向量化操作
- 集成日志系统
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from logger_setup import get_logger


class FunnelAnalyzer:
    """电商用户行为漏斗分析器"""
    
    def __init__(self):
        """初始化漏斗分析器"""
        self.logger = get_logger('FunnelAnalyzer')
        self.default_funnel_stages = ['view', 'search', 'click', 'add_to_cart', 'purchase']
        self.analysis_results = {}
    
    def _get_event_counts(self, df: pd.DataFrame, event_type_col: str = 'event_type') -> pd.Series:
        """
        统计各事件类型的数量
        
        Args:
            df: 数据框
            event_type_col: 事件类型列名
        
        Returns:
            事件类型数量的 Series
        """
        return df[event_type_col].value_counts()
    
    def _calculate_funnel_metrics(self, funnel_data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算漏斗指标（转化率、流失率等）
        
        Args:
            funnel_data: 漏斗数据，包含 stage 和 count 列
        
        Returns:
            漏斗指标字典
        """
        metrics = {
            'stages': [],
            'total_users': funnel_data['user_count'].iloc[0] if 'user_count' in funnel_data.columns else 0,
            'overall_conversion_rate': 0.0
        }
        
        for i, row in funnel_data.iterrows():
            stage_metrics = {
                'stage': row['stage'],
                'count': int(row['user_count']) if 'user_count' in row else int(row['count']),
                'conversion_rate': 1.0,
                'drop_off_rate': 0.0,
                'overall_conversion': 0.0
            }
            
            if i > 0:
                prev_count = funnel_data.iloc[i-1]['user_count'] if 'user_count' in funnel_data.columns else funnel_data.iloc[i-1]['count']
                current_count = stage_metrics['count']
                
                if prev_count > 0:
                    stage_metrics['conversion_rate'] = current_count / prev_count
                    stage_metrics['drop_off_rate'] = 1 - stage_metrics['conversion_rate']
            
            if metrics['total_users'] > 0:
                stage_metrics['overall_conversion'] = stage_metrics['count'] / metrics['total_users']
            
            metrics['stages'].append(stage_metrics)
        
        if metrics['total_users'] > 0 and len(metrics['stages']) > 0:
            last_stage_count = metrics['stages'][-1]['count']
            metrics['overall_conversion_rate'] = last_stage_count / metrics['total_users']
        
        return metrics
    
    def analyze_basic_funnel(self, df: pd.DataFrame, 
                               user_id_col: str = 'user_id',
                               event_type_col: str = 'event_type',
                               funnel_stages: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        分析基本漏斗转化（基于用户数）
        
        Args:
            df: 数据框
            user_id_col: 用户ID列名
            event_type_col: 事件类型列名
            funnel_stages: 漏斗阶段列表，如果为None则使用默认阶段
        
        Returns:
            漏斗分析结果字典
        """
        if funnel_stages is None:
            funnel_stages = self.default_funnel_stages
        
        self.logger.info(f"分析漏斗转化，阶段: {funnel_stages}")
        
        valid_events = df[df[event_type_col].isin(funnel_stages)]
        
        funnel_data = []
        for stage in funnel_stages:
            stage_users = valid_events[valid_events[event_type_col] == stage][user_id_col].nunique()
            funnel_data.append({
                'stage': stage,
                'user_count': stage_users
            })
        
        funnel_df = pd.DataFrame(funnel_data)
        
        metrics = self._calculate_funnel_metrics(funnel_df)
        
        result = {
            'funnel_stages': funnel_stages,
            'funnel_data': funnel_df,
            'metrics': metrics,
            'total_events': len(valid_events),
            'total_users': valid_events[user_id_col].nunique()
        }
        
        self.analysis_results['basic_funnel'] = result
        
        self.logger.info("\n基本漏斗分析结果:")
        for stage in metrics['stages']:
            self.logger.info(f"  {stage['stage']}: {stage['count']} 用户, "
                  f"转化率: {stage['conversion_rate']:.2%}, "
                  f"整体转化: {stage['overall_conversion']:.2%}")
        self.logger.info(f"  整体转化率: {metrics['overall_conversion_rate']:.2%}")
        
        print("\n基本漏斗分析结果:")
        for stage in metrics['stages']:
            print(f"  {stage['stage']}: {stage['count']} 用户, "
                  f"转化率: {stage['conversion_rate']:.2%}, "
                  f"整体转化: {stage['overall_conversion']:.2%}")
        print(f"  整体转化率: {metrics['overall_conversion_rate']:.2%}")
        
        return result
    
    def _analyze_session_strict(self, df: pd.DataFrame,
                                   session_id_col: str,
                                   event_type_col: str,
                                   timestamp_col: str,
                                   funnel_stages: List[str],
                                   max_time_window_minutes: int = 30,
                                   allow_skipped_stages: bool = False) -> pd.DataFrame:
        """
        严格版会话漏斗分析：
        - 检查时间顺序（后一阶段时间必须晚于前一阶段）
        - 检查时间窗口（相邻阶段间隔不超过阈值）
        - 检查阶段完整性（可选是否允许跳阶段）
        
        Args:
            df: 数据框
            session_id_col: 会话ID列名
            event_type_col: 事件类型列名
            timestamp_col: 时间戳列名
            funnel_stages: 漏斗阶段列表
            max_time_window_minutes: 最大时间窗口（分钟），相邻阶段超过则中断
            allow_skipped_stages: 是否允许跳阶段，默认为 False（严格顺序）
        
        Returns:
            会话分析结果数据框
        """
        df = df.copy()
        
        stage_to_idx = {stage: i for i, stage in enumerate(funnel_stages)}
        df['event_idx'] = df[event_type_col].map(stage_to_idx)
        
        max_time_window = pd.Timedelta(minutes=max_time_window_minutes)
        
        def analyze_single_session(session_df):
            session_df = session_df.sort_values(timestamp_col).reset_index(drop=True)
            
            session_df = session_df.dropna(subset=['event_idx'])
            session_df['event_idx'] = session_df['event_idx'].astype(int)
            
            if len(session_df) == 0:
                return pd.Series({
                    'stages_reached': [],
                    'max_stage_reached': None,
                    'max_stage_idx': -1,
                    'first_stage_time': None,
                    'last_stage_time': None,
                    'total_duration_minutes': 0,
                    'valid_conversion_path': False,
                    'break_reason': None
                })
            
            valid_stages = []
            valid_timestamps = []
            current_expected_stage_idx = 0
            
            for _, row in session_df.iterrows():
                event_idx = row['event_idx']
                event_time = row[timestamp_col]
                
                if allow_skipped_stages:
                    if event_idx >= current_expected_stage_idx:
                        if len(valid_timestamps) > 0:
                            time_diff = event_time - valid_timestamps[-1]
                            if time_diff > max_time_window:
                                continue
                        
                        valid_stages.append(funnel_stages[event_idx])
                        valid_timestamps.append(event_time)
                        current_expected_stage_idx = event_idx + 1
                else:
                    if event_idx == current_expected_stage_idx:
                        if len(valid_timestamps) > 0:
                            time_diff = event_time - valid_timestamps[-1]
                            if time_diff > max_time_window:
                                continue
                        
                        valid_stages.append(funnel_stages[event_idx])
                        valid_timestamps.append(event_time)
                        current_expected_stage_idx = event_idx + 1
                    elif event_idx < current_expected_stage_idx:
                        if len(valid_timestamps) > 0:
                            time_diff = event_time - valid_timestamps[-1]
                            if time_diff <= max_time_window:
                                continue
            
            break_reason = None
            if len(valid_stages) > 0:
                expected_stages = funnel_stages[:len(valid_stages)]
                if valid_stages != expected_stages and not allow_skipped_stages:
                    break_reason = '阶段顺序不匹配'
            
            first_time = valid_timestamps[0] if len(valid_timestamps) > 0 else None
            last_time = valid_timestamps[-1] if len(valid_timestamps) > 0 else None
            duration = (last_time - first_time).total_seconds() / 60 if first_time and last_time else 0
            
            max_stage_idx = len(valid_stages) - 1 if len(valid_stages) > 0 else -1
            max_stage_reached = valid_stages[-1] if len(valid_stages) > 0 else None
            
            valid_conversion_path = len(valid_stages) > 0 and (break_reason is None)
            
            return pd.Series({
                'stages_reached': valid_stages,
                'max_stage_reached': max_stage_reached,
                'max_stage_idx': max_stage_idx,
                'first_stage_time': first_time,
                'last_stage_time': last_time,
                'total_duration_minutes': round(duration, 2),
                'valid_conversion_path': valid_conversion_path,
                'break_reason': break_reason
            })
        
        session_analysis = df.groupby(session_id_col).apply(analyze_single_session).reset_index()
        
        return session_analysis
    
    def _analyze_session_optimized(self, df: pd.DataFrame,
                                      session_id_col: str,
                                      event_type_col: str,
                                      funnel_stages: List[str]) -> pd.DataFrame:
        """
        优化版会话分析：使用向量化方法替代 apply（简化版，不检查时间顺序）
        
        Args:
            df: 按会话排序的数据框
            session_id_col: 会话ID列名
            event_type_col: 事件类型列名
            funnel_stages: 漏斗阶段列表
        
        Returns:
            会话分析结果数据框
        """
        df = df.copy()
        
        stage_to_idx = {stage: i for i, stage in enumerate(funnel_stages)}
        df['event_idx'] = df[event_type_col].map(stage_to_idx)
        
        df['max_stage_reached'] = df.groupby(session_id_col)['event_idx'].cummax()
        
        session_max_stage = df.groupby(session_id_col)['max_stage_reached'].max().reset_index()
        session_max_stage.columns = [session_id_col, 'max_stage_idx']
        
        session_max_stage['max_stage_reached'] = session_max_stage['max_stage_idx'].apply(
            lambda x: funnel_stages[int(x)] if pd.notna(x) and x >= 0 else None
        )
        
        def get_stages_reached(max_idx):
            if pd.isna(max_idx) or max_idx < 0:
                return []
            return funnel_stages[:int(max_idx) + 1]
        
        session_max_stage['stages_reached'] = session_max_stage['max_stage_idx'].apply(get_stages_reached)
        
        return session_max_stage[[session_id_col, 'stages_reached', 'max_stage_reached']]
    
    def analyze_session_funnel(self, df: pd.DataFrame,
                                 session_id_col: str = 'session_id',
                                 event_type_col: str = 'event_type',
                                 user_id_col: str = 'user_id',
                                 timestamp_col: str = 'timestamp',
                                 funnel_stages: Optional[List[str]] = None,
                                 max_time_window_minutes: int = 30,
                                 allow_skipped_stages: bool = False,
                                 use_strict_check: bool = True) -> Dict[str, Any]:
        """
        分析基于会话的漏斗（严格版）
        
        关键特性：
        1. 严格时间顺序检查：后一阶段事件时间必须晚于前一阶段
        2. 时间窗口检查：相邻阶段时间间隔不超过阈值（默认30分钟）
        3. 阶段完整性检查：可选是否允许跳阶段（默认不允许）
        
        Args:
            df: 数据框
            session_id_col: 会话ID列名
            event_type_col: 事件类型列名
            user_id_col: 用户ID列名
            timestamp_col: 时间戳列名
            funnel_stages: 漏斗阶段列表
            max_time_window_minutes: 最大时间窗口（分钟），相邻阶段超过则中断
            allow_skipped_stages: 是否允许跳阶段，默认为 False（严格顺序）
            use_strict_check: 是否使用严格检查（包含时间顺序、时间窗口、阶段完整性）
        
        Returns:
            会话漏斗分析结果
        """
        if funnel_stages is None:
            funnel_stages = self.default_funnel_stages
        
        if use_strict_check:
            self.logger.info(f"分析会话漏斗转化（严格版）:")
            self.logger.info(f"  阶段: {funnel_stages}")
            self.logger.info(f"  时间窗口: {max_time_window_minutes} 分钟")
            self.logger.info(f"  允许跳阶段: {'是' if allow_skipped_stages else '否'}")
        else:
            self.logger.info(f"分析会话漏斗转化（简化版），阶段: {funnel_stages}")
        
        df_sorted = df.sort_values([session_id_col, timestamp_col])
        
        if use_strict_check:
            session_analysis = self._analyze_session_strict(
                df_sorted, 
                session_id_col, 
                event_type_col, 
                timestamp_col,
                funnel_stages,
                max_time_window_minutes,
                allow_skipped_stages
            )
        else:
            session_analysis = self._analyze_session_optimized(
                df_sorted, session_id_col, event_type_col, funnel_stages
            )
        
        funnel_data = []
        total_sessions = len(session_analysis)
        
        for stage in funnel_stages:
            if use_strict_check:
                sessions_at_stage = sum(
                    1 for stages in session_analysis['stages_reached'] 
                    if stage in stages
                )
            else:
                sessions_at_stage = sum(
                    1 for stages in session_analysis['stages_reached'] 
                    if stage in stages
                )
            
            funnel_data.append({
                'stage': stage,
                'session_count': sessions_at_stage
            })
        
        funnel_df = pd.DataFrame(funnel_data)
        funnel_df = funnel_df.rename(columns={'session_count': 'user_count'})
        
        metrics = self._calculate_funnel_metrics(funnel_df)
        
        drop_off_points = []
        for i in range(len(funnel_stages) - 1):
            current_stage = funnel_stages[i]
            next_stage = funnel_stages[i + 1]
            
            current_count = funnel_df[funnel_df['stage'] == current_stage]['user_count'].iloc[0]
            next_count = funnel_df[funnel_df['stage'] == next_stage]['user_count'].iloc[0]
            
            drop_off = current_count - next_count
            drop_off_rate = drop_off / current_count if current_count > 0 else 0
            
            drop_off_points.append({
                'from_stage': current_stage,
                'to_stage': next_stage,
                'drop_off_count': int(drop_off),
                'drop_off_rate': drop_off_rate
            })
        
        time_stats = {}
        if use_strict_check and 'total_duration_minutes' in session_analysis.columns:
            valid_sessions = session_analysis[session_analysis['valid_conversion_path']]
            if len(valid_sessions) > 0:
                time_stats = {
                    'avg_duration_minutes': round(valid_sessions['total_duration_minutes'].mean(), 2),
                    'median_duration_minutes': round(valid_sessions['total_duration_minutes'].median(), 2),
                    'min_duration_minutes': round(valid_sessions['total_duration_minutes'].min(), 2),
                    'max_duration_minutes': round(valid_sessions['total_duration_minutes'].max(), 2),
                    'valid_conversion_sessions': len(valid_sessions)
                }
        
        result = {
            'funnel_stages': funnel_stages,
            'funnel_data': funnel_df,
            'metrics': metrics,
            'total_sessions': total_sessions,
            'drop_off_points': drop_off_points,
            'session_analysis': session_analysis,
            'time_stats': time_stats,
            'check_params': {
                'max_time_window_minutes': max_time_window_minutes,
                'allow_skipped_stages': allow_skipped_stages,
                'use_strict_check': use_strict_check
            }
        }
        
        self.analysis_results['session_funnel'] = result
        
        self.logger.info("\n会话漏斗分析结果:")
        for stage in metrics['stages']:
            self.logger.info(f"  {stage['stage']}: {stage['count']} 会话, "
                  f"转化率: {stage['conversion_rate']:.2%}")
        self.logger.info(f"  整体转化率: {metrics['overall_conversion_rate']:.2%}")
        
        self.logger.info("\n流失点分析:")
        for point in drop_off_points:
            self.logger.info(f"  {point['from_stage']} -> {point['to_stage']}: "
                  f"流失 {point['drop_off_count']} 会话 ({point['drop_off_rate']:.2%})")
        
        if time_stats:
            self.logger.info(f"\n时间统计（有效转化路径）:")
            self.logger.info(f"  有效转化会话数: {time_stats['valid_conversion_sessions']}")
            self.logger.info(f"  平均转化时长: {time_stats['avg_duration_minutes']} 分钟")
            self.logger.info(f"  中位数转化时长: {time_stats['median_duration_minutes']} 分钟")
            self.logger.info(f"  最小转化时长: {time_stats['min_duration_minutes']} 分钟")
            self.logger.info(f"  最大转化时长: {time_stats['max_duration_minutes']} 分钟")
        
        print("\n会话漏斗分析结果:")
        for stage in metrics['stages']:
            print(f"  {stage['stage']}: {stage['count']} 会话, "
                  f"转化率: {stage['conversion_rate']:.2%}")
        print(f"  整体转化率: {metrics['overall_conversion_rate']:.2%}")
        
        print("\n流失点分析:")
        for point in drop_off_points:
            print(f"  {point['from_stage']} -> {point['to_stage']}: "
                  f"流失 {point['drop_off_count']} 会话 ({point['drop_off_rate']:.2%})")
        
        if time_stats:
            print(f"\n时间统计（有效转化路径）:")
            print(f"  有效转化会话数: {time_stats['valid_conversion_sessions']}")
            print(f"  平均转化时长: {time_stats['avg_duration_minutes']} 分钟")
            print(f"  中位数转化时长: {time_stats['median_duration_minutes']} 分钟")
            print(f"  最小转化时长: {time_stats['min_duration_minutes']} 分钟")
            print(f"  最大转化时长: {time_stats['max_duration_minutes']} 分钟")
        
        return result
    
    def analyze_funnel_by_dimension(self, df: pd.DataFrame,
                                      dimension_col: str,
                                      user_id_col: str = 'user_id',
                                      event_type_col: str = 'event_type',
                                      funnel_stages: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        按维度分析漏斗（如按设备、渠道等）
        
        Args:
            df: 数据框
            dimension_col: 维度列名
            user_id_col: 用户ID列名
            event_type_col: 事件类型列名
            funnel_stages: 漏斗阶段列表
        
        Returns:
            按维度分析的漏斗结果
        """
        if funnel_stages is None:
            funnel_stages = self.default_funnel_stages
        
        self.logger.info(f"按维度 '{dimension_col}' 分析漏斗转化")
        
        if dimension_col not in df.columns:
            raise ValueError(f"维度列 '{dimension_col}' 不存在于数据中")
        
        dimension_values = df[dimension_col].unique()
        
        dimension_results = {}
        
        for dim_value in dimension_values:
            dim_df = df[df[dimension_col] == dim_value]
            
            if len(dim_df) == 0:
                continue
            
            valid_events = dim_df[dim_df[event_type_col].isin(funnel_stages)]
            
            funnel_data = []
            for stage in funnel_stages:
                stage_users = valid_events[valid_events[event_type_col] == stage][user_id_col].nunique()
                funnel_data.append({
                    'stage': stage,
                    'user_count': stage_users
                })
            
            funnel_df = pd.DataFrame(funnel_data)
            
            metrics = self._calculate_funnel_metrics(funnel_df)
            
            dimension_results[dim_value] = {
                'funnel_data': funnel_df,
                'metrics': metrics,
                'total_users': valid_events[user_id_col].nunique(),
                'total_events': len(valid_events)
            }
        
        result = {
            'dimension': dimension_col,
            'dimension_values': list(dimension_results.keys()),
            'results_by_dimension': dimension_results,
            'funnel_stages': funnel_stages
        }
        
        self.analysis_results['funnel_by_dimension'] = result
        
        self.logger.info(f"\n按维度 '{dimension_col}' 的漏斗分析结果:")
        for dim_value, dim_result in dimension_results.items():
            self.logger.info(f"\n  维度值: {dim_value}")
            self.logger.info(f"    总用户数: {dim_result['total_users']}")
            self.logger.info(f"    整体转化率: {dim_result['metrics']['overall_conversion_rate']:.2%}")
            for stage in dim_result['metrics']['stages']:
                self.logger.info(f"    {stage['stage']}: {stage['count']} 用户, "
                      f"转化率: {stage['conversion_rate']:.2%}")
        
        print(f"\n按维度 '{dimension_col}' 的漏斗分析结果:")
        for dim_value, dim_result in dimension_results.items():
            print(f"\n  维度值: {dim_value}")
            print(f"    总用户数: {dim_result['total_users']}")
            print(f"    整体转化率: {dim_result['metrics']['overall_conversion_rate']:.2%}")
            for stage in dim_result['metrics']['stages']:
                print(f"    {stage['stage']}: {stage['count']} 用户, "
                      f"转化率: {stage['conversion_rate']:.2%}")
        
        return result
    
    def get_funnel_summary(self) -> Dict[str, Any]:
        """
        获取所有漏斗分析的摘要
        
        Returns:
            漏斗分析摘要
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
    
    analyzer = FunnelAnalyzer()
    
    print("\n" + "="*50)
    print("基本漏斗分析")
    print("="*50)
    basic_result = analyzer.analyze_basic_funnel(cleaned_data)
    
    print("\n" + "="*50)
    print("会话漏斗分析")
    print("="*50)
    session_result = analyzer.analyze_session_funnel(cleaned_data)
    
    print("\n" + "="*50)
    print("按设备维度分析漏斗")
    print("="*50)
    device_result = analyzer.analyze_funnel_by_dimension(cleaned_data, 'device_type')
