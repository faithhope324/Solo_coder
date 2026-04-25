import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
from typing import Optional, List, Tuple
import os

# 设置中文字体
mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False


class ChartGenerator:
    """销售数据图表生成器"""
    
    def __init__(self, filter_module):
        self.filter = filter_module
        self.figures = {}
        
        self._agg_column_mapping = {
            'amount_sum': ['销售金额汇总', '实际金额_sum', '金额_sum', '销售额_sum', '总金额_sum'],
            'amount_mean': ['销售金额平均', '实际金额_mean', '金额_mean'],
            'amount_count': ['销售金额记录数', '实际金额_count', '金额_count'],
            'quantity_sum': ['销售数量汇总', '数量_sum', '销量_sum'],
            'quantity_mean': ['销售数量平均', '数量_mean', '销量_mean'],
        }
    
    def _get_column_name(self, column_type: str) -> Optional[str]:
        """获取原始列名"""
        column_map = {
            'region': self.filter.region_col,
            'category': self.filter.category_col,
            'date': self.filter.date_col,
            'amount': self.filter.amount_col,
            'quantity': self.filter.quantity_col
        }
        return column_map.get(column_type)
    
    def _cache_figure(self, name: str, fig) -> None:
        """缓存图表，在缓存新图表前先关闭旧的
        
        Args:
            name: 图表名称
            fig: matplotlib Figure 对象
        """
        if name in self.figures:
            try:
                plt.close(self.figures[name])
            except:
                pass
        
        self.figures[name] = fig
    
    def _find_agg_column(self, df: pd.DataFrame, agg_type: str) -> Optional[str]:
        """在数据框中查找聚合后的列名
        
        Args:
            df: 分组聚合后的数据框
            agg_type: 聚合类型，如 'amount_sum', 'quantity_sum' 等
            
        Returns:
            找到的列名，未找到返回 None
        """
        candidates = self._agg_column_mapping.get(agg_type, [])
        
        for candidate in candidates:
            if candidate in df.columns:
                return candidate
        
        for col in df.columns:
            col_lower = str(col).lower()
            
            if agg_type == 'amount_sum':
                if any(kw in col_lower for kw in ['金额', 'amount', 'sales', 'sum', '汇总']):
                    if 'sum' in col_lower or '汇总' in col_lower:
                        return col
            
            elif agg_type == 'quantity_sum':
                if any(kw in col_lower for kw in ['数量', 'quantity', '销量']):
                    if 'sum' in col_lower or '汇总' in col_lower:
                        return col
        
        return None
    
    def create_region_bar_chart(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建地区销售金额柱状图"""
        region_col = self._get_column_name('region')
        amount_col = self._get_column_name('amount')
        
        if not region_col or not amount_col:
            raise ValueError("缺少必要的列信息")
        
        region_data = self.filter.group_by_region()
        
        amount_sum_col = self._find_agg_column(region_data, 'amount_sum')
        
        if amount_sum_col is None:
            raise ValueError("无法获取销售金额数据")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = plt.cm.Set3(range(len(region_data)))
        bars = ax.bar(
            range(len(region_data)),
            region_data[amount_sum_col],
            color=colors,
            edgecolor='black',
            linewidth=0.5
        )
        
        ax.set_xlabel('地区', fontsize=12)
        ax.set_ylabel('销售金额 (元)', fontsize=12)
        ax.set_title('各地区销售金额对比', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(region_data)))
        ax.set_xticklabels(region_data[region_col], rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height * 1.01,
                f'{int(height):,}',
                ha='center',
                va='bottom',
                fontsize=10
            )
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('region_bar', fig)
        return fig
    
    def create_category_pie_chart(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建品类销售金额饼图"""
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if not category_col or not amount_col:
            raise ValueError("缺少必要的列信息")
        
        category_data = self.filter.group_by_category()
        amount_sum_col = self._find_agg_column(category_data, 'amount_sum')
        
        if amount_sum_col is None:
            raise ValueError("无法获取销售金额数据")
        
        fig, ax = plt.subplots(figsize=(10, 10))
        
        colors = plt.cm.Paired(range(len(category_data)))
        explode = [0.05] * len(category_data)
        
        wedges, texts, autotexts = ax.pie(
            category_data[amount_sum_col],
            labels=category_data[category_col],
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            explode=explode,
            textprops={'fontsize': 10}
        )
        
        ax.set_title('各品类销售金额占比', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('category_pie', fig)
        return fig
    
    def create_monthly_trend_chart(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建月度销售趋势折线图"""
        date_col = self._get_column_name('date')
        amount_col = self._get_column_name('amount')
        
        if not date_col or not amount_col:
            raise ValueError("缺少必要的列信息")
        
        monthly_data = self.filter.group_by_month()
        amount_sum_col = self._find_agg_column(monthly_data, 'amount_sum')
        
        if amount_sum_col is None or '月份' not in monthly_data.columns:
            raise ValueError("无法获取月度销售数据")
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        ax.plot(
            range(len(monthly_data)),
            monthly_data[amount_sum_col],
            marker='o',
            linewidth=2,
            color='#2E86AB',
            markersize=8
        )
        
        ax.fill_between(
            range(len(monthly_data)),
            monthly_data[amount_sum_col],
            alpha=0.3,
            color='#2E86AB'
        )
        
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('销售金额 (元)', fontsize=12)
        ax.set_title('月度销售趋势', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(monthly_data)))
        ax.set_xticklabels(monthly_data['月份'], rotation=45, ha='right')
        ax.grid(axis='both', alpha=0.3)
        
        for i, value in enumerate(monthly_data[amount_sum_col]):
            ax.text(
                i,
                value * 1.02,
                f'{int(value):,}',
                ha='center',
                va='bottom',
                fontsize=9
            )
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('monthly_trend', fig)
        return fig
    
    def create_region_category_heatmap(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建地区-品类销售热力图"""
        region_col = self._get_column_name('region')
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if not region_col or not category_col or not amount_col:
            raise ValueError("缺少必要的列信息")
        
        cross_data = self.filter.group_by_region_category()
        amount_sum_col = self._find_agg_column(cross_data, 'amount_sum')
        
        if amount_sum_col is None:
            raise ValueError("无法获取销售金额数据")
        
        pivot_data = cross_data.pivot(
            index=region_col,
            columns=category_col,
            values=amount_sum_col
        ).fillna(0)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        im = ax.imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
        
        ax.set_xticks(range(len(pivot_data.columns)))
        ax.set_yticks(range(len(pivot_data.index)))
        ax.set_xticklabels(pivot_data.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot_data.index)
        
        ax.set_xlabel('品类', fontsize=12)
        ax.set_ylabel('地区', fontsize=12)
        ax.set_title('地区-品类销售热力图', fontsize=14, fontweight='bold')
        
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('销售金额 (元)', fontsize=10)
        
        for i in range(len(pivot_data.index)):
            for j in range(len(pivot_data.columns)):
                value = pivot_data.values[i, j]
                if value > 0:
                    text = ax.text(
                        j, i, f'{int(value):,}',
                        ha="center", va="center",
                        color="black" if value < pivot_data.values.max()/2 else "white",
                        fontsize=8
                    )
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('heatmap', fig)
        return fig
    
    def create_category_bar_chart(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建品类销售对比柱状图"""
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if not category_col or not amount_col:
            raise ValueError("缺少必要的列信息")
        
        category_data = self.filter.group_by_category()
        amount_sum_col = self._find_agg_column(category_data, 'amount_sum')
        
        if amount_sum_col is None:
            raise ValueError("无法获取销售金额数据")
        
        category_data = category_data.sort_values(by=amount_sum_col, ascending=False)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = plt.cm.tab20(range(len(category_data)))
        bars = ax.barh(
            range(len(category_data)),
            category_data[amount_sum_col],
            color=colors,
            edgecolor='black',
            linewidth=0.5
        )
        
        ax.set_ylabel('品类', fontsize=12)
        ax.set_xlabel('销售金额 (元)', fontsize=12)
        ax.set_title('各品类销售金额对比（降序）', fontsize=14, fontweight='bold')
        ax.set_yticks(range(len(category_data)))
        ax.set_yticklabels(category_data[category_col])
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)
        
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width * 1.01,
                bar.get_y() + bar.get_height()/2.,
                f'{int(width):,}',
                ha='left',
                va='center',
                fontsize=10
            )
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('category_bar', fig)
        return fig
    
    def create_combined_dashboard(self, output_path: Optional[str] = None) -> plt.Figure:
        """创建组合仪表板"""
        fig = plt.figure(figsize=(16, 12))
        
        gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, :])
        ax4 = fig.add_subplot(gs[2, 0])
        ax5 = fig.add_subplot(gs[2, 1])
        
        region_col = self._get_column_name('region')
        category_col = self._get_column_name('category')
        amount_col = self._get_column_name('amount')
        
        if region_col and amount_col:
            region_data = self.filter.group_by_region()
            amount_sum_col = self._find_agg_column(region_data, 'amount_sum')
            if amount_sum_col is not None:
                colors = plt.cm.Set3(range(len(region_data)))
                bars1 = ax1.bar(range(len(region_data)), region_data[amount_sum_col], color=colors)
                ax1.set_title('地区销售对比', fontsize=12, fontweight='bold')
                ax1.set_xticks(range(len(region_data)))
                ax1.set_xticklabels(region_data[region_col], rotation=45, ha='right')
        
        if category_col and amount_col:
            category_data = self.filter.group_by_category()
            amount_sum_col = self._find_agg_column(category_data, 'amount_sum')
            if amount_sum_col is not None:
                colors = plt.cm.Paired(range(len(category_data)))
                ax2.pie(
                    category_data[amount_sum_col],
                    labels=category_data[category_col],
                    colors=colors,
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax2.set_title('品类占比', fontsize=12, fontweight='bold')
        
        date_col = self._get_column_name('date')
        if date_col and amount_col:
            monthly_data = self.filter.group_by_month()
            amount_sum_col = self._find_agg_column(monthly_data, 'amount_sum')
            if amount_sum_col is not None and '月份' in monthly_data.columns:
                ax3.plot(
                    range(len(monthly_data)),
                    monthly_data[amount_sum_col],
                    marker='o',
                    linewidth=2,
                    color='#2E86AB'
                )
                ax3.fill_between(
                    range(len(monthly_data)),
                    monthly_data[amount_sum_col],
                    alpha=0.3,
                    color='#2E86AB'
                )
                ax3.set_title('月度销售趋势', fontsize=12, fontweight='bold')
                ax3.set_xticks(range(len(monthly_data)))
                ax3.set_xticklabels(monthly_data['月份'], rotation=45, ha='right')
                ax3.grid(alpha=0.3)
        
        if category_col and amount_col:
            category_data = self.filter.group_by_category()
            amount_sum_col = self._find_agg_column(category_data, 'amount_sum')
            if amount_sum_col is not None:
                category_data = category_data.sort_values(by=amount_sum_col, ascending=False)
                colors = plt.cm.tab20(range(len(category_data)))
                bars4 = ax4.barh(
                    range(len(category_data)),
                    category_data[amount_sum_col],
                    color=colors
                )
                ax4.set_title('品类销售排行', fontsize=12, fontweight='bold')
                ax4.set_yticks(range(len(category_data)))
                ax4.set_yticklabels(category_data[category_col])
                ax4.invert_yaxis()
        
        summary = self.filter.get_summary_statistics()
        ax5.text(0.5, 0.9, '数据汇总', fontsize=14, fontweight='bold', ha='center')
        
        info_text = f"""
        总记录数: {summary['总记录数']:,}
        总销售金额: ¥{summary['总销售金额']:,.2f}
        平均客单价: ¥{summary['平均客单价']:,.2f}
        总销售数量: {summary['总销售数量']:,}
        涉及地区数: {summary['涉及地区数']}
        涉及品类数: {summary['涉及品类数']}
        """
        
        ax5.text(0.1, 0.5, info_text, fontsize=11, va='center')
        ax5.axis('off')
        ax5.set_title('关键指标', fontsize=12, fontweight='bold')
        
        fig.suptitle('销售数据综合分析仪表板', fontsize=18, fontweight='bold', y=0.98)
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        
        self._cache_figure('dashboard', fig)
        return fig
    
    def show_all_charts(self):
        """显示所有图表"""
        for name, fig in self.figures.items():
            plt.figure(fig.number)
            plt.show()
    
    def save_all_charts(self, output_dir: str):
        """保存所有图表到指定目录"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if 'region_bar' in self.figures:
            self.figures['region_bar'].savefig(
                os.path.join(output_dir, '地区销售对比.png'),
                dpi=300,
                bbox_inches='tight'
            )
        
        if 'category_pie' in self.figures:
            self.figures['category_pie'].savefig(
                os.path.join(output_dir, '品类销售占比.png'),
                dpi=300,
                bbox_inches='tight'
            )
        
        if 'monthly_trend' in self.figures:
            self.figures['monthly_trend'].savefig(
                os.path.join(output_dir, '月度销售趋势.png'),
                dpi=300,
                bbox_inches='tight'
            )
        
        if 'heatmap' in self.figures:
            self.figures['heatmap'].savefig(
                os.path.join(output_dir, '地区品类热力图.png'),
                dpi=300,
                bbox_inches='tight'
            )
        
        if 'category_bar' in self.figures:
            self.figures['category_bar'].savefig(
                os.path.join(output_dir, '品类销售排行.png'),
                dpi=300,
                bbox_inches='tight'
            )
        
        if 'dashboard' in self.figures:
            self.figures['dashboard'].savefig(
                os.path.join(output_dir, '综合分析仪表板.png'),
                dpi=300,
                bbox_inches='tight'
            )
    
    def clear_figures(self):
        """清除所有图表，释放内存
        
        这个方法会关闭所有 matplotlib 图形并释放内存。
        在处理大量图表或长时间运行的任务后应该调用此方法。
        """
        for name, fig in list(self.figures.items()):
            try:
                plt.close(fig)
            except:
                pass
        
        self.figures.clear()
        
        plt.close('all')
        
        try:
            import gc
            gc.collect()
        except:
            pass
    
    def close_figure(self, name: str):
        """关闭指定的图表，释放内存
        
        Args:
            name: 图表名称（如 'region_bar', 'category_pie' 等）
        """
        if name in self.figures:
            try:
                plt.close(self.figures[name])
            except:
                pass
            
            del self.figures[name]
    
    def get_figure_count(self) -> int:
        """获取当前内存中的图表数量
        
        Returns:
            当前存储的图表数量
        """
        return len(self.figures)
