import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import re


class FilterModule:
    """销售数据筛选模块"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.filtered_df = df.copy()
        self.applied_filters = {}
        self._column_mapping: Dict[str, str] = {}
        
        self._identify_columns()
        self._validate_date_columns()
        self._validate_numeric_columns()
    
    @staticmethod
    def _normalize_column_name(col: str) -> str:
        """标准化列名：去除空格、特殊字符，转换为小写
        
        Args:
            col: 原始列名
            
        Returns:
            标准化后的列名
        """
        if not isinstance(col, str):
            col = str(col)
        
        col = col.strip()
        col = re.sub(r'[\s_\-\.]+', '', col)
        col = col.lower()
        
        return col
    
    def _find_column(self, candidates: List[str]) -> Optional[str]:
        """在数据框中查找匹配的列名（不区分大小写，处理空格和特殊字符）
        
        支持灵活的匹配方式：
        1. 精确匹配：normalized_actual == normalized_candidate
        2. 包含匹配：normalized_actual 包含 normalized_candidate（适用于英文列名）
        
        例如：'Actual_Amount' 标准化为 'actualamount'，会匹配候选列名 'amount'
        
        Args:
            candidates: 候选列名列表
            
        Returns:
            匹配到的原始列名，未找到返回 None
        """
        for candidate in candidates:
            normalized_candidate = self._normalize_column_name(candidate)
            
            for actual_col in self.df.columns:
                normalized_actual = self._normalize_column_name(str(actual_col))
                
                if normalized_actual == normalized_candidate:
                    return actual_col
                
                if normalized_candidate in normalized_actual:
                    return actual_col
                
                if normalized_actual in normalized_candidate and len(normalized_actual) > 2:
                    return actual_col
        
        return None
    
    def _validate_numeric_columns(self):
        """验证数值列是否为正确的数值类型，非数值类型尝试转换
        
        验证金额列和数量列，确保它们可以用于数值计算。
        """
        if self.amount_col:
            self._convert_to_numeric(self.amount_col, '金额')
        
        if self.quantity_col:
            self._convert_to_numeric(self.quantity_col, '数量')
    
    def _validate_date_columns(self):
        """验证日期列是否为正确的日期类型，非日期类型尝试解析
        
        解析日期列，确保它们可以用于日期筛选。
        """
        if self.date_col:
            self._parse_date_column(self.date_col)
    
    def _parse_date_column(self, col: str) -> bool:
        """尝试将列解析为日期类型
        
        尝试多种日期格式进行解析，处理转换失败的情况。
        
        Args:
            col: 列名
            
        Returns:
            是否解析成功
        """
        if col not in self.df.columns:
            return False
        
        series = self.df[col]
        
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
        
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%Y年%m月%d日',
            '%Y年%m月%d日 %H时%M分%S秒',
        ]
        
        original_series = series.copy()
        result_series = pd.to_datetime(original_series, errors='coerce')
        
        na_count_before = result_series.isna().sum()
        
        if na_count_before > 0:
            for fmt in date_formats:
                mask = result_series.isna() & original_series.notna()
                if mask.sum() == 0:
                    break
                
                try:
                    parsed = pd.to_datetime(original_series[mask], format=fmt, errors='coerce')
                    result_series.loc[mask] = parsed
                except:
                    continue
        
        success_count = result_series.notna().sum()
        
        if success_count > 0:
            self.df[col] = result_series
            self.filtered_df[col] = result_series
            return True
        else:
            return False
    
    def is_date_column(self, col: str) -> bool:
        """检查列是否为日期类型
        
        Args:
            col: 列名
            
        Returns:
            是否为日期类型
        """
        if col not in self.df.columns:
            return False
        return pd.api.types.is_datetime64_any_dtype(self.df[col])
    
    def _convert_to_numeric(self, col: str, col_type: str) -> bool:
        """尝试将列转换为数值类型
        
        Args:
            col: 列名
            col_type: 列类型描述（用于错误信息）
            
        Returns:
            是否转换成功
        """
        if col not in self.df.columns:
            return False
        
        series = self.df[col]
        
        if pd.api.types.is_numeric_dtype(series):
            return True
        
        try:
            converted = pd.to_numeric(series, errors='coerce')
            
            success_count = converted.notna().sum()
            total_count = len(converted)
            
            if success_count > 0:
                self.df[col] = converted
                self.filtered_df[col] = converted
                
                failed_count = total_count - success_count
                if failed_count > 0:
                    pass
                
                return True
            else:
                return False
        except Exception:
            return False
    
    def is_numeric_column(self, col: str) -> bool:
        """检查列是否为数值类型
        
        Args:
            col: 列名
            
        Returns:
            是否为数值类型
        """
        if col not in self.df.columns:
            return False
        return pd.api.types.is_numeric_dtype(self.df[col])
    
    def _identify_columns(self):
        """识别数据中的关键列"""
        self._column_mapping = {}
        for col in self.df.columns:
            normalized = self._normalize_column_name(str(col))
            self._column_mapping[normalized] = col
        
        date_candidates = ['日期', 'date', '时间', 'time', '交易日期', '订单日期', '销售日期']
        self.date_col = self._find_column(date_candidates)
        
        region_candidates = ['地区', '区域', 'region', 'area', '销售区域', '地区名称', '区域名称']
        self.region_col = self._find_column(region_candidates)
        
        category_candidates = ['品类', '类别', 'category', '产品类别', '产品分类', '商品类别', '商品分类']
        self.category_col = self._find_column(category_candidates)
        
        amount_candidates = ['实际金额', '金额', '销售额', 'amount', 'sales', '总金额', '销售金额', '实付金额']
        self.amount_col = self._find_column(amount_candidates)
        
        quantity_candidates = ['数量', '销量', 'quantity', '销售数量', '商品数量']
        self.quantity_col = self._find_column(quantity_candidates)
    
    def get_column_mapping(self) -> Dict[str, str]:
        """获取列名映射关系
        
        Returns:
            标准化列名 -> 原始列名 的映射字典
        """
        return self._column_mapping.copy()
    
    def filter_by_region(self, regions: List[str]):
        """按地区筛选"""
        if not regions or not self.region_col:
            return
        
        self.filtered_df = self.filtered_df[self.filtered_df[self.region_col].isin(regions)]
        self.applied_filters['地区'] = regions
    
    def filter_by_category(self, categories: List[str]):
        """按品类筛选"""
        if not categories or not self.category_col:
            return
        
        self.filtered_df = self.filtered_df[self.filtered_df[self.category_col].isin(categories)]
        self.applied_filters['品类'] = categories
    
    def filter_by_date(self, start_date: datetime, end_date: datetime):
        """按日期范围筛选（处理 NaT 值）"""
        if not self.date_col:
            return
        
        date_series = self.filtered_df[self.date_col]
        
        valid_date_mask = date_series.notna()
        
        date_range_mask = (
            (date_series >= start_date) &
            (date_series <= end_date)
        )
        
        final_mask = valid_date_mask & date_range_mask
        
        nat_count = (~valid_date_mask).sum()
        if nat_count > 0:
            pass
        
        self.filtered_df = self.filtered_df[final_mask]
        self.applied_filters['日期'] = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
    
    def filter_by_month(self, year: int, month: int):
        """按月份筛选"""
        if not self.date_col:
            return
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - pd.Timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - pd.Timedelta(days=1)
        
        self.filter_by_date(start_date, end_date)
        self.applied_filters['月份'] = f"{year}年{month}月"
    
    def filter_by_quarter(self, year: int, quarter: int):
        """按季度筛选"""
        if not self.date_col:
            return
        
        quarter_months = {
            1: (1, 3),
            2: (4, 6),
            3: (7, 9),
            4: (10, 12)
        }
        
        start_month, end_month = quarter_months[quarter]
        start_date = datetime(year, start_month, 1)
        end_date = datetime(year, end_month + 1, 1) - pd.Timedelta(days=1) if end_month < 12 else datetime(year + 1, 1, 1) - pd.Timedelta(days=1)
        
        self.filter_by_date(start_date, end_date)
        self.applied_filters['季度'] = f"{year}年第{quarter}季度"
    
    def reset_filters(self):
        """重置所有筛选"""
        self.filtered_df = self.df.copy()
        self.applied_filters = {}
    
    def get_filtered_data(self) -> pd.DataFrame:
        """获取筛选后的数据"""
        return self.filtered_df.copy()
    
    def get_applied_filters(self) -> dict:
        """获取已应用的筛选条件"""
        return self.applied_filters.copy()
    
    def _build_named_aggregations(
        self,
        amount_aggs: List[str] = None,
        quantity_aggs: List[str] = None
    ) -> Dict:
        """构建命名聚合字典，避免列名冲突
        
        Args:
            amount_aggs: 金额列需要的聚合函数列表
            quantity_aggs: 数量列需要的聚合函数列表
            
        Returns:
            命名聚合字典，格式为: {'新列名': ('原列名', '聚合函数')}
        """
        named_aggs = {}
        
        agg_display_names = {
            'sum': '汇总',
            'mean': '平均',
            'count': '记录数',
            'min': '最小值',
            'max': '最大值',
            'std': '标准差',
            'var': '方差'
        }
        
        if self.amount_col and amount_aggs:
            for agg_func in amount_aggs:
                display_name = agg_display_names.get(agg_func, agg_func)
                new_col_name = f'销售金额{display_name}'
                
                counter = 1
                while new_col_name in named_aggs:
                    new_col_name = f'销售金额{display_name}_{counter}'
                    counter += 1
                
                named_aggs[new_col_name] = (self.amount_col, agg_func)
        
        if self.quantity_col and quantity_aggs:
            for agg_func in quantity_aggs:
                display_name = agg_display_names.get(agg_func, agg_func)
                new_col_name = f'销售数量{display_name}'
                
                counter = 1
                while new_col_name in named_aggs:
                    new_col_name = f'销售数量{display_name}_{counter}'
                    counter += 1
                
                named_aggs[new_col_name] = (self.quantity_col, agg_func)
        
        return named_aggs
    
    def group_by_region(self) -> pd.DataFrame:
        """按地区分组汇总"""
        if not self.region_col:
            return pd.DataFrame()
        
        group_cols = [self.region_col]
        
        named_aggs = self._build_named_aggregations(
            amount_aggs=['sum', 'mean', 'count'],
            quantity_aggs=['sum', 'mean']
        )
        
        if not named_aggs:
            return pd.DataFrame()
        
        result = self.filtered_df.groupby(group_cols).agg(**named_aggs).reset_index()
        
        return result
    
    def group_by_category(self) -> pd.DataFrame:
        """按品类分组汇总"""
        if not self.category_col:
            return pd.DataFrame()
        
        group_cols = [self.category_col]
        
        named_aggs = self._build_named_aggregations(
            amount_aggs=['sum', 'mean', 'count'],
            quantity_aggs=['sum', 'mean']
        )
        
        if not named_aggs:
            return pd.DataFrame()
        
        result = self.filtered_df.groupby(group_cols).agg(**named_aggs).reset_index()
        
        return result
    
    def group_by_month(self) -> pd.DataFrame:
        """按月份分组汇总（处理 NaT 值）"""
        if not self.date_col:
            return pd.DataFrame()
        
        df = self.filtered_df.copy()
        
        valid_date_mask = df[self.date_col].notna()
        
        if valid_date_mask.sum() == 0:
            return pd.DataFrame()
        
        df_valid = df[valid_date_mask].copy()
        df_valid['月份'] = df_valid[self.date_col].dt.to_period('M')
        
        named_aggs = self._build_named_aggregations(
            amount_aggs=['sum', 'mean', 'count'],
            quantity_aggs=['sum', 'mean']
        )
        
        if not named_aggs:
            return pd.DataFrame()
        
        result = df_valid.groupby('月份').agg(**named_aggs).reset_index()
        result['月份'] = result['月份'].astype(str)
        
        return result
    
    def group_by_region_category(self) -> pd.DataFrame:
        """按地区和品类交叉分组汇总"""
        group_cols = []
        if self.region_col:
            group_cols.append(self.region_col)
        if self.category_col:
            group_cols.append(self.category_col)
        
        if not group_cols:
            return pd.DataFrame()
        
        named_aggs = self._build_named_aggregations(
            amount_aggs=['sum', 'count'],
            quantity_aggs=['sum']
        )
        
        if not named_aggs:
            return pd.DataFrame()
        
        result = self.filtered_df.groupby(group_cols).agg(**named_aggs).reset_index()
        
        return result
    
    def get_summary_statistics(self) -> dict:
        """获取汇总统计信息"""
        summary = {
            '总记录数': len(self.filtered_df),
            '总销售金额': 0,
            '平均客单价': 0,
            '总销售数量': 0,
            '涉及地区数': 0,
            '涉及品类数': 0
        }
        
        if self.amount_col and self.amount_col in self.filtered_df.columns:
            summary['总销售金额'] = self.filtered_df[self.amount_col].sum()
            summary['平均客单价'] = self.filtered_df[self.amount_col].mean()
        
        if self.quantity_col and self.quantity_col in self.filtered_df.columns:
            summary['总销售数量'] = self.filtered_df[self.quantity_col].sum()
        
        if self.region_col and self.region_col in self.filtered_df.columns:
            summary['涉及地区数'] = self.filtered_df[self.region_col].nunique()
        
        if self.category_col and self.category_col in self.filtered_df.columns:
            summary['涉及品类数'] = self.filtered_df[self.category_col].nunique()
        
        return summary
