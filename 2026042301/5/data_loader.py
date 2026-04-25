import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
import re


class DataLoader:
    """销售数据加载和预处理类"""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.available_regions: List[str] = []
        self.available_categories: List[str] = []
        self.date_range: tuple = (None, None)
        self._column_mapping: Dict[str, str] = {}
        self._date_parse_errors: Dict = {}
    
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
        
        Args:
            candidates: 候选列名列表（标准化前）
            
        Returns:
            匹配到的原始列名，未找到返回 None
        """
        if self.df is None:
            return None
        
        for candidate in candidates:
            normalized_candidate = self._normalize_column_name(candidate)
            
            for actual_col in self.df.columns:
                normalized_actual = self._normalize_column_name(str(actual_col))
                
                if normalized_actual == normalized_candidate:
                    return actual_col
        
        return None
    
    def _parse_date_column(self, col: str) -> pd.Series:
        """解析日期列，尝试多种日期格式，处理转换失败的情况
        
        Args:
            col: 列名
            
        Returns:
            解析后的 datetime 类型 Series
        """
        if self.df is None:
            return pd.Series()
        
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
        
        original_series = self.df[col].copy()
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
        
        na_count_after = result_series.isna().sum()
        failed_count = result_series.isna().sum()
        
        if failed_count > 0:
            failed_indices = result_series[result_series.isna()].index.tolist()
            failed_values = original_series.loc[failed_indices].head(10).tolist()
            
            self._date_parse_errors = {
                'total_count': len(original_series),
                'failed_count': failed_count,
                'success_count': len(original_series) - failed_count,
                'failed_values_sample': failed_values,
                'failed_indices_sample': failed_indices[:10]
            }
        
        return result_series
    
    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        """从 CSV 文件加载数据"""
        try:
            self.df = pd.read_csv(file_path)
            self._preprocess_data()
            return self.df
        except Exception as e:
            raise Exception(f"加载 CSV 文件失败: {str(e)}")
    
    def load_from_excel(self, file_path: str, sheet_name: str = 0) -> pd.DataFrame:
        """从 Excel 文件加载数据"""
        try:
            self.df = pd.read_excel(file_path, sheet_name=sheet_name)
            self._preprocess_data()
            return self.df
        except Exception as e:
            raise Exception(f"加载 Excel 文件失败: {str(e)}")
    
    def load_sample_data(self, n_records: int = 1000) -> pd.DataFrame:
        """生成示例销售数据"""
        regions = ['华东', '华北', '华南', '华中', '西南', '西北', '东北']
        categories = ['电子产品', '服装', '家居', '食品', '美妆', '运动']
        products = {
            '电子产品': ['手机', '笔记本', '平板', '耳机', '相机'],
            '服装': ['T恤', '牛仔裤', '连衣裙', '外套', '运动鞋'],
            '家居': ['沙发', '床', '桌子', '椅子', '灯具'],
            '食品': ['零食', '饮料', '生鲜', '粮油', '调料'],
            '美妆': ['护肤品', '化妆品', '香水', '洗发水', '沐浴露'],
            '运动': ['篮球', '足球', '羽毛球', '健身器材', '瑜伽垫']
        }
        
        dates = pd.date_range(start='2025-01-01', end='2025-12-31', periods=n_records)
        
        data = []
        for date in dates:
            region = np.random.choice(regions)
            category = np.random.choice(categories)
            product = np.random.choice(products[category])
            quantity = np.random.randint(1, 20)
            unit_price = np.random.randint(10, 5000)
            total_amount = quantity * unit_price
            discount = np.random.uniform(0.8, 1.0) if np.random.random() > 0.3 else 1.0
            actual_amount = total_amount * discount
            
            data.append({
                '日期': date,
                '地区': region,
                '品类': category,
                '产品': product,
                '数量': quantity,
                '单价': unit_price,
                '总金额': total_amount,
                '折扣': round(discount, 2),
                '实际金额': round(actual_amount, 2)
            })
        
        self.df = pd.DataFrame(data)
        self._preprocess_data()
        return self.df
    
    def _preprocess_data(self):
        """数据预处理"""
        if self.df is None:
            return
        
        self._column_mapping = {}
        
        original_columns = list(self.df.columns)
        
        for col in original_columns:
            normalized = self._normalize_column_name(str(col))
            self._column_mapping[normalized] = col
        
        date_candidates = ['日期', 'date', '时间', 'time', '交易日期', '订单日期']
        date_col = self._find_column(date_candidates)
        
        if date_col:
            self.df[date_col] = self._parse_date_column(date_col)
        
        region_candidates = ['地区', '区域', 'region', 'area', '销售区域', '地区名称']
        region_col = self._find_column(region_candidates)
        
        if region_col:
            self.available_regions = sorted(self.df[region_col].dropna().unique().tolist())
        
        category_candidates = ['品类', '类别', 'category', '产品类别', '产品分类', '商品类别']
        category_col = self._find_column(category_candidates)
        
        if category_col:
            self.available_categories = sorted(self.df[category_col].dropna().unique().tolist())
        
        if date_col and self.df[date_col].notna().any():
            valid_dates = self.df[date_col].dropna()
            if len(valid_dates) > 0:
                self.date_range = (
                    valid_dates.min(),
                    valid_dates.max()
                )
    
    def get_date_parse_errors(self) -> Dict:
        """获取日期解析错误信息
        
        Returns:
            包含错误统计信息的字典
        """
        return self._date_parse_errors.copy()
    
    def get_column_mapping(self) -> Dict[str, str]:
        """获取列名映射关系（标准化列名 -> 原始列名）
        
        Returns:
            列名字典
        """
        return self._column_mapping.copy()
    
    def get_filter_options(self) -> Dict:
        """获取筛选选项"""
        return {
            'regions': self.available_regions,
            'categories': self.available_categories,
            'date_range': self.date_range
        }
    
    def get_data(self) -> Optional[pd.DataFrame]:
        """获取原始数据"""
        return self.df.copy() if self.df is not None else None
