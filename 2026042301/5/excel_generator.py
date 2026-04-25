import pandas as pd
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import os

try:
    from file_utils import safe_save_path, backup_if_exists
except ImportError:
    def safe_save_path(file_path: str, backup: bool = True, backup_dir: Optional[str] = None) -> Tuple[str, Optional[str]]:
        return file_path, None
    
    def backup_if_exists(file_path: str, backup_dir: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        return False, None


class ExcelGenerator:
    """Excel 汇总生成器"""
    
    def __init__(self, filter_module):
        self.filter = filter_module
        self._last_backup_path: Optional[str] = None
    
    def _get_column_name(self, column_type: str) -> Optional[str]:
        """获取列名"""
        column_map = {
            'region': self.filter.region_col,
            'category': self.filter.category_col,
            'date': self.filter.date_col,
            'amount': self.filter.amount_col,
            'quantity': self.filter.quantity_col
        }
        return column_map.get(column_type)
    
    def get_last_backup_path(self) -> Optional[str]:
        """获取最后一次备份的文件路径
        
        Returns:
            备份文件路径，如果没有备份则返回 None
        """
        return self._last_backup_path
    
    def generate_summary_excel(
        self,
        output_path: str,
        include_raw_data: bool = True,
        include_charts: bool = False,
        backup: bool = True,
        backup_dir: Optional[str] = None
    ) -> str:
        """生成汇总 Excel 文件（支持自动备份）
        
        Args:
            output_path: 输出文件路径
            include_raw_data: 是否包含原始数据
            include_charts: 是否包含图表（预留功能）
            backup: 是否在文件已存在时进行备份
            backup_dir: 备份文件存放目录（可选，不指定则在同一目录）
            
        Returns:
            输出文件路径
        """
        if backup:
            actual_path, backup_path = safe_save_path(output_path, backup=True, backup_dir=backup_dir)
            self._last_backup_path = backup_path
            
            if backup_path:
                pass
        else:
            actual_path = output_path
            self._last_backup_path = None
        
        output_dir = os.path.dirname(actual_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with pd.ExcelWriter(actual_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            self._create_summary_sheet(writer, workbook)
            self._create_region_summary_sheet(writer, workbook)
            self._create_category_summary_sheet(writer, workbook)
            self._create_monthly_summary_sheet(writer, workbook)
            self._create_cross_summary_sheet(writer, workbook)
            
            if include_raw_data:
                self._create_raw_data_sheet(writer, workbook)
            
            self._create_filter_info_sheet(writer, workbook)
            
            self._format_workbook(writer, workbook)
        
        return actual_path
    
    def _create_summary_sheet(self, writer, workbook):
        """创建汇总概览工作表"""
        summary = self.filter.get_summary_statistics()
        
        summary_data = {
            '指标': [
                '总记录数',
                '总销售金额 (元)',
                '平均客单价 (元)',
                '总销售数量',
                '涉及地区数',
                '涉及品类数',
                '报告生成时间'
            ],
            '数值': [
                f"{summary['总记录数']:,}",
                f"¥{summary['总销售金额']:,.2f}",
                f"¥{summary['平均客单价']:,.2f}",
                f"{summary['总销售数量']:,}",
                summary['涉及地区数'],
                summary['涉及品类数'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='数据概览', index=False, startrow=2)
        
        worksheet = writer.sheets['数据概览']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })
        worksheet.merge_range('A1:B1', '销售数据汇总报告', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(df_summary.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 30)
    
    def _create_region_summary_sheet(self, writer, workbook):
        """创建地区汇总工作表"""
        region_col = self._get_column_name('region')
        amount_col = self._get_column_name('amount')
        
        if not region_col:
            return
        
        region_data = self.filter.group_by_region()
        
        if region_data.empty:
            return
        
        region_data.to_excel(writer, sheet_name='地区汇总', index=False, startrow=2)
        
        worksheet = writer.sheets['地区汇总']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        max_col = len(region_data.columns)
        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
        worksheet.merge_range(f'A1:{end_col_letter}1', '各地区销售汇总', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#70AD47',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(region_data.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        for col_num in range(max_col):
            worksheet.set_column(col_num, col_num, 20)
    
    def _create_category_summary_sheet(self, writer, workbook):
        """创建品类汇总工作表"""
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if not category_col:
            return
        
        category_data = self.filter.group_by_category()
        
        if category_data.empty:
            return
        
        category_data.to_excel(writer, sheet_name='品类汇总', index=False, startrow=2)
        
        worksheet = writer.sheets['品类汇总']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        max_col = len(category_data.columns)
        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
        worksheet.merge_range(f'A1:{end_col_letter}1', '各品类销售汇总', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#ED7D31',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(category_data.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        for col_num in range(max_col):
            worksheet.set_column(col_num, col_num, 20)
    
    def _create_monthly_summary_sheet(self, writer, workbook):
        """创建月度汇总工作表"""
        date_col = self._get_column_name('date')
        
        if not date_col:
            return
        
        monthly_data = self.filter.group_by_month()
        
        if monthly_data.empty:
            return
        
        monthly_data.to_excel(writer, sheet_name='月度汇总', index=False, startrow=2)
        
        worksheet = writer.sheets['月度汇总']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        max_col = len(monthly_data.columns)
        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
        worksheet.merge_range(f'A1:{end_col_letter}1', '月度销售汇总', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#5B9BD5',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(monthly_data.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        for col_num in range(max_col):
            worksheet.set_column(col_num, col_num, 20)
    
    def _create_cross_summary_sheet(self, writer, workbook):
        """创建交叉汇总工作表"""
        region_col = self._get_column_name('region')
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if not region_col or not category_col:
            return
        
        cross_data = self.filter.group_by_region_category()
        
        if cross_data.empty:
            return
        
        cross_data.to_excel(writer, sheet_name='交叉分析', index=False, startrow=2)
        
        worksheet = writer.sheets['交叉分析']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        max_col = len(cross_data.columns)
        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
        worksheet.merge_range(f'A1:{end_col_letter}1', '地区-品类交叉分析', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#7030A0',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(cross_data.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        for col_num in range(max_col):
            worksheet.set_column(col_num, col_num, 20)
    
    def _create_raw_data_sheet(self, writer, workbook):
        """创建原始数据工作表"""
        raw_data = self.filter.get_filtered_data()
        
        if raw_data.empty:
            return
        
        raw_data.to_excel(writer, sheet_name='原始数据', index=False, startrow=2)
        
        worksheet = writer.sheets['原始数据']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        max_col = len(raw_data.columns)
        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
        worksheet.merge_range(f'A1:{end_col_letter}1', '筛选后的原始数据', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#44546A',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(raw_data.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        for col_num in range(max_col):
            worksheet.set_column(col_num, col_num, 15)
    
    def _create_filter_info_sheet(self, writer, workbook):
        """创建筛选条件工作表"""
        applied_filters = self.filter.get_applied_filters()
        
        filter_data = []
        for filter_name, filter_value in applied_filters.items():
            if isinstance(filter_value, list):
                value_str = ', '.join(map(str, filter_value))
            else:
                value_str = str(filter_value)
            filter_data.append({'筛选条件': filter_name, '筛选值': value_str})
        
        if not filter_data:
            filter_data.append({'筛选条件': '无', '筛选值': '未应用任何筛选条件'})
        
        df_filters = pd.DataFrame(filter_data)
        df_filters.to_excel(writer, sheet_name='筛选条件', index=False, startrow=2)
        
        worksheet = writer.sheets['筛选条件']
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        worksheet.merge_range('A1:B1', '已应用的筛选条件', title_format)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#00B050',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        for col_num, value in enumerate(df_filters.columns.values):
            worksheet.write(2, col_num, value, header_format)
        
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 60)
    
    def _format_workbook(self, writer, workbook):
        """格式化整个工作簿"""
        currency_format = workbook.add_format({
            'num_format': '¥#,##0.00',
            'align': 'right'
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right'
        })
        
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(3, 0)
    
    def _find_amount_sum_column(self, df: pd.DataFrame) -> Optional[str]:
        """在分组后的数据框中查找销售金额汇总列
        
        Args:
            df: 分组后的数据框
            
        Returns:
            找到的列名，未找到返回 None
        """
        possible_names = ['销售金额汇总', '实际金额_sum', '金额_sum', '总金额_sum', '销售额_sum']
        
        for name in possible_names:
            if name in df.columns:
                return name
        
        for col in df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in ['金额', 'amount', 'sales']) and \
               any(kw in col_lower for kw in ['sum', '汇总']):
                return col
        
        return None
    
    def generate_comparison_report(
        self,
        output_path: str,
        comparison_type: str = 'region',
        backup: bool = True,
        backup_dir: Optional[str] = None
    ) -> str:
        """生成对比分析报告（支持自动备份）
        
        Args:
            output_path: 输出文件路径
            comparison_type: 对比类型 ('region' 或 'category')
            backup: 是否在文件已存在时进行备份
            backup_dir: 备份文件存放目录（可选）
            
        Returns:
            输出文件路径
        """
        if backup:
            actual_path, backup_path = safe_save_path(output_path, backup=True, backup_dir=backup_dir)
            self._last_backup_path = backup_path
        else:
            actual_path = output_path
            self._last_backup_path = None
        
        output_dir = os.path.dirname(actual_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with pd.ExcelWriter(actual_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            if comparison_type == 'region':
                region_col = self._get_column_name('region')
                amount_col = self._get_column_name('amount')
                
                if region_col and amount_col:
                    region_data = self.filter.group_by_region()
                    amount_sum_col = self._find_amount_sum_column(region_data)
                    
                    if amount_sum_col is not None:
                        total = region_data[amount_sum_col].sum()
                        region_data['占比'] = region_data[amount_sum_col] / total * 100
                        region_data['排名'] = region_data[amount_sum_col].rank(ascending=False, method='min').astype(int)
                        region_data = region_data.sort_values(by=amount_sum_col, ascending=False)
                        
                        region_data.to_excel(writer, sheet_name='地区对比分析', index=False, startrow=2)
                        
                        worksheet = writer.sheets['地区对比分析']
                        title_format = workbook.add_format({
                            'bold': True,
                            'font_size': 14,
                            'align': 'center',
                            'valign': 'vcenter'
                        })
                        max_col = len(region_data.columns)
                        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
                        worksheet.merge_range(f'A1:{end_col_letter}1', '地区销售对比分析报告', title_format)
                        
                        header_format = workbook.add_format({
                            'bold': True,
                            'bg_color': '#2E75B6',
                            'font_color': 'white',
                            'align': 'center',
                            'valign': 'vcenter',
                            'border': 1
                        })
                        
                        for col_num, value in enumerate(region_data.columns.values):
                            worksheet.write(2, col_num, value, header_format)
                        
                        percent_format = workbook.add_format({
                            'num_format': '0.00%',
                            'align': 'right'
                        })
                        for row_num in range(3, len(region_data) + 3):
                            worksheet.write(row_num, max_col - 2, region_data.iloc[row_num - 3, max_col - 2] / 100, percent_format)
                        
                        for col_num in range(max_col):
                            worksheet.set_column(col_num, col_num, 18)
            
            elif comparison_type == 'category':
                category_col = self._get_column_name('category')
                amount_col = self._get_column_name('amount')
                
                if category_col and amount_col:
                    category_data = self.filter.group_by_category()
                    amount_sum_col = self._find_amount_sum_column(category_data)
                    
                    if amount_sum_col is not None:
                        total = category_data[amount_sum_col].sum()
                        category_data['占比'] = category_data[amount_sum_col] / total * 100
                        category_data['排名'] = category_data[amount_sum_col].rank(ascending=False, method='min').astype(int)
                        category_data = category_data.sort_values(by=amount_sum_col, ascending=False)
                        
                        category_data.to_excel(writer, sheet_name='品类对比分析', index=False, startrow=2)
                        
                        worksheet = writer.sheets['品类对比分析']
                        title_format = workbook.add_format({
                            'bold': True,
                            'font_size': 14,
                            'align': 'center',
                            'valign': 'vcenter'
                        })
                        max_col = len(category_data.columns)
                        end_col_letter = chr(65 + max_col - 1) if max_col <= 26 else 'Z'
                        worksheet.merge_range(f'A1:{end_col_letter}1', '品类销售对比分析报告', title_format)
                        
                        header_format = workbook.add_format({
                            'bold': True,
                            'bg_color': '#70AD47',
                            'font_color': 'white',
                            'align': 'center',
                            'valign': 'vcenter',
                            'border': 1
                        })
                        
                        for col_num, value in enumerate(category_data.columns.values):
                            worksheet.write(2, col_num, value, header_format)
                        
                        percent_format = workbook.add_format({
                            'num_format': '0.00%',
                            'align': 'right'
                        })
                        for row_num in range(3, len(category_data) + 3):
                            worksheet.write(row_num, max_col - 2, category_data.iloc[row_num - 3, max_col - 2] / 100, percent_format)
                        
                        for col_num in range(max_col):
                            worksheet.set_column(col_num, col_num, 18)
        
        return actual_path
