import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

from logger_setup import get_logger

# 尝试导入plotly，如果没有安装则提供降级方案
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("警告: plotly未安装，将使用文本格式输出替代交互式图表")
    print("请运行: pip install plotly 以获得完整的可视化功能")


class HTMLReportGenerator:
    """HTML交互式报表生成器"""
    
    def __init__(self, title: str = "电商用户行为分析报告"):
        """
        初始化报表生成器
        
        Args:
            title: 报表标题
        """
        self.logger = get_logger('HTMLReportGenerator')
        self.title = title
        self.report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.figures = {}
        self.sections = []
        
        if PLOTLY_AVAILABLE:
            self.logger.info("plotly已安装，将生成完整的交互式图表")
        else:
            self.logger.warning("plotly未安装，将生成简化版报告")
        
    def create_funnel_chart(self, funnel_data: pd.DataFrame, 
                              stage_col: str = 'stage',
                              count_col: str = 'user_count',
                              chart_title: str = "用户转化漏斗") -> Optional[Any]:
        """
        创建漏斗图
        
        Args:
            funnel_data: 漏斗数据
            stage_col: 阶段列名
            count_col: 数量列名
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        
        # 准备数据
        stages = funnel_data[stage_col].tolist()
        values = funnel_data[count_col].tolist()
        
        # 计算转化率
        conversion_rates = []
        for i in range(len(values)):
            if i == 0:
                conversion_rates.append(100)
            else:
                conversion_rates.append((values[i] / values[i-1]) * 100 if values[i-1] > 0 else 0)
        
        # 创建漏斗图
        fig = go.Figure()
        
        # 添加漏斗图
        fig.add_trace(go.Funnel(
            name='用户数',
            y=stages,
            x=values,
            textinfo='value+percent initial',
            textposition='inside',
            marker=dict(
                color=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'],
                line=dict(width=2, color='white')
            ),
            connector=dict(
                line=dict(color='rgba(128, 128, 128, 0.5)', width=2),
                fillcolor='rgba(128, 128, 128, 0.1)'
            )
        ))
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            showlegend=True,
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig
    
    def create_retention_curve(self, retention_df: pd.DataFrame,
                                 retention_days: List[int],
                                 chart_title: str = "用户留存曲线") -> Optional[Any]:
        """
        创建留存曲线图
        
        Args:
            retention_df: 留存数据
            retention_days: 留存天数列表
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        
        # 计算平均留存率
        avg_rates = []
        for day in retention_days:
            rate_col = f'day_{day}_rate'
            if rate_col in retention_df.columns:
                avg_rates.append(retention_df[rate_col].mean() * 100)
            else:
                avg_rates.append(0)
        
        # 创建折线图
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[f'Day {d}' for d in retention_days],
            y=avg_rates,
            mode='lines+markers+text',
            name='平均留存率',
            line=dict(color='#636EFA', width=3),
            marker=dict(size=12, color='#636EFA', line=dict(width=2, color='white')),
            text=[f'{r:.1f}%' for r in avg_rates],
            textposition='top center',
            textfont=dict(size=12, color='#2c3e50')
        ))
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            xaxis_title='留存天数',
            yaxis_title='留存率 (%)',
            yaxis=dict(
                range=[0, 100],
                gridcolor='rgba(128, 128, 128, 0.1)',
                tickformat='.0f'
            ),
            xaxis=dict(
                gridcolor='rgba(128, 128, 128, 0.1)'
            ),
            showlegend=True,
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        return fig
    
    def create_cohort_heatmap(self, cohort_pivot: pd.DataFrame,
                                chart_title: str = "同期群分析热力图") -> Optional[Any]:
        """
        创建同期群热力图
        
        Args:
            cohort_pivot: 同期群透视表
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        
        # 准备数据
        # 将DataFrame转换为矩阵
        z_data = (cohort_pivot.values * 100).round(1)
        x_labels = [f'Period {int(c)}' for c in cohort_pivot.columns]
        y_labels = cohort_pivot.index.tolist()
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            colorscale='Blues',
            showscale=True,
            colorbar=dict(
                title=dict(
                    text='留存率 (%)',
                    side='right'
                ),
                tickformat='.0f'
            ),
            text=[[f'{val:.1f}%' if not np.isnan(val) else '-' for val in row] for row in z_data],
            texttemplate='%{text}',
            textfont=dict(size=10),
            hoverongaps=False
        ))
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            xaxis_title='周期数',
            yaxis_title='同期群',
            xaxis=dict(
                side='bottom',
                type='category'
            ),
            yaxis=dict(
                type='category',
                autorange='reversed'
            ),
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=100, r=50, t=80, b=50)
        )
        
        return fig
    
    def create_event_distribution_chart(self, df: pd.DataFrame,
                                          event_type_col: str = 'event_type',
                                          chart_title: str = "事件类型分布") -> Optional[Any]:
        """
        创建事件类型分布图
        
        Args:
            df: 数据框
            event_type_col: 事件类型列名
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        # 统计事件类型
        event_counts = df[event_type_col].value_counts().reset_index()
        event_counts.columns = ['event_type', 'count']
        
        # 计算百分比
        total = event_counts['count'].sum()
        event_counts['percentage'] = (event_counts['count'] / total * 100).round(1)
        
        # 创建饼图
        fig = go.Figure()
        
        fig.add_trace(go.Pie(
            labels=event_counts['event_type'],
            values=event_counts['count'],
            textinfo='label+percent',
            textposition='inside',
            insidetextorientation='radial',
            hole=0.4,
            marker=dict(
                colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3'],
                line=dict(color='white', width=2)
            ),
            hoverinfo='label+value+percent',
            textfont=dict(size=12, color='white')
        ))
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='middle',
                xanchor='right',
                x=1.2,
                y=0.5
            ),
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=50, r=150, t=80, b=50)
        )
        
        return fig
    
    def create_device_distribution_chart(self, df: pd.DataFrame,
                                           device_col: str = 'device_type',
                                           event_type_col: str = 'event_type',
                                           chart_title: str = "设备类型分布") -> Optional[Any]:
        """
        创建设备类型分布图
        
        Args:
            df: 数据框
            device_col: 设备类型列名
            event_type_col: 事件类型列名
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        # 统计各设备类型的事件数
        device_stats = df.groupby(device_col)[event_type_col].count().reset_index()
        device_stats.columns = ['device_type', 'event_count']
        
        # 统计各设备类型的用户数
        user_device = df.groupby(device_col)['user_id'].nunique().reset_index()
        user_device.columns = ['device_type', 'user_count']
        
        # 合并数据
        device_stats = device_stats.merge(user_device, on='device_type')
        
        # 创建柱状图
        fig = make_subplots(rows=1, cols=2, subplot_titles=('用户数', '事件数'))
        
        # 用户数
        fig.add_trace(
            go.Bar(
                x=device_stats['device_type'],
                y=device_stats['user_count'],
                name='用户数',
                marker_color='#636EFA',
                text=device_stats['user_count'],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # 事件数
        fig.add_trace(
            go.Bar(
                x=device_stats['device_type'],
                y=device_stats['event_count'],
                name='事件数',
                marker_color='#EF553B',
                text=device_stats['event_count'],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            showlegend=False,
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        # 更新子图布局
        fig.update_xaxes(title_text='设备类型', row=1, col=1)
        fig.update_xaxes(title_text='设备类型', row=1, col=2)
        fig.update_yaxes(title_text='数量', row=1, col=1)
        fig.update_yaxes(title_text='数量', row=1, col=2)
        
        return fig
    
    def create_daily_activity_chart(self, df: pd.DataFrame,
                                      timestamp_col: str = 'timestamp',
                                      event_type_col: str = 'event_type',
                                      chart_title: str = "每日活动趋势") -> Optional[Any]:
        """
        创建每日活动趋势图
        
        Args:
            df: 数据框
            timestamp_col: 时间戳列名
            event_type_col: 事件类型列名
            chart_title: 图表标题
        
        Returns:
            Plotly图表对象或None（如果plotly未安装）
        """
        if not PLOTLY_AVAILABLE:
            print(f"跳过创建图表: {chart_title} (plotly未安装)")
            return None
        # 提取日期
        df = df.copy()
        df['date'] = df[timestamp_col].dt.date
        
        # 统计每日事件数
        daily_stats = df.groupby('date')[event_type_col].count().reset_index()
        daily_stats.columns = ['date', 'event_count']
        
        # 统计每日用户数
        daily_users = df.groupby('date')['user_id'].nunique().reset_index()
        daily_users.columns = ['date', 'user_count']
        
        # 合并数据
        daily_stats = daily_stats.merge(daily_users, on='date')
        daily_stats = daily_stats.sort_values('date')
        
        # 创建双轴图
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加事件数折线
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['event_count'],
                mode='lines+markers',
                name='事件数',
                line=dict(color='#636EFA', width=2),
                marker=dict(size=6, color='#636EFA')
            ),
            secondary_y=False
        )
        
        # 添加用户数折线
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['user_count'],
                mode='lines+markers',
                name='用户数',
                line=dict(color='#EF553B', width=2),
                marker=dict(size=6, color='#EF553B')
            ),
            secondary_y=True
        )
        
        # 更新布局
        fig.update_layout(
            title={
                'text': chart_title,
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color='#2c3e50')
            },
            xaxis_title='日期',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                xanchor='center',
                x=0.5,
                y=1.02
            ),
            paper_bgcolor='white',
            plot_bgcolor='white',
            margin=dict(l=50, r=50, t=100, b=50)
        )
        
        fig.update_yaxes(title_text='事件数', secondary_y=False, gridcolor='rgba(128, 128, 128, 0.1)')
        fig.update_yaxes(title_text='用户数', secondary_y=True, gridcolor='rgba(128, 128, 128, 0.1)')
        fig.update_xaxes(gridcolor='rgba(128, 128, 128, 0.1)')
        
        return fig
    
    def add_section(self, title: str, figures: List[Any], description: str = ""):
        """
        添加报表章节
        
        Args:
            title: 章节标题
            figures: 图表列表（可能包含None值，将被过滤）
            description: 章节描述
        """
        # 过滤掉None值的图表
        valid_figures = [fig for fig in figures if fig is not None]
        
        # 只有当有有效图表时才添加章节
        if valid_figures:
            section = {
                'title': title,
                'figures': valid_figures,
                'description': description
            }
            self.sections.append(section)
        else:
            print(f"跳过添加章节 '{title}': 没有有效的图表")
    
    def _generate_simple_report(self, output_path: str, 
                                  summary_data: Dict[str, Any] = None) -> str:
        """
        生成简化版HTML报告（没有plotly时使用）
        
        Args:
            output_path: 输出文件路径
            summary_data: 摘要数据
        
        Returns:
            生成的HTML文件路径
        """
        print("注意: plotly未安装，生成简化版报告")
        print("提示: 运行 'pip install plotly' 以获得完整的交互式图表功能")
        
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .header .subtitle {{
            font-size: 14px;
            opacity: 0.8;
        }}
        
        .warning-box {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px 20px;
            margin: 20px;
            border-radius: 5px;
        }}
        
        .warning-box h3 {{
            color: #856404;
            margin-bottom: 5px;
        }}
        
        .warning-box p {{
            color: #856404;
            font-size: 14px;
        }}
        
        .summary-section {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .summary-card .label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        .section {{
            padding: 30px 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .section:last-child {{
            border-bottom: none;
        }}
        
        .section-title {{
            font-size: 20px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #636EFA;
            display: inline-block;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        .data-table th,
        .data-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .data-table th {{
            background: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .data-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .progress-bar {{
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }}
        
        .progress-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #636EFA, #AB63FA);
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 12px;
        }}
        
        .code-block {{
            background: #2c3e50;
            color: #00CC96;
            padding: 10px 15px;
            border-radius: 5px;
            font-family: 'Consolas', monospace;
            font-size: 13px;
            margin-top: 10px;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
            
            .section {{
                padding: 20px;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.title}</h1>
            <div class="subtitle">生成时间: {self.report_date}</div>
        </div>
        
        <div class="warning-box">
            <h3>⚠️ 简化版报告</h3>
            <p>您的系统中未安装 plotly 库，因此生成的是简化版报告（无交互式图表）。</p>
            <p>要获得完整的交互式图表功能，请运行以下命令安装 plotly：</p>
            <div class="code-block">pip install plotly</div>
        </div>
'''
        
        # 添加摘要数据
        if summary_data:
            html_content += '''
        <div class="summary-section">
            <h2 class="section-title">数据摘要</h2>
            <div class="summary-grid">
'''
            if 'total_users' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['total_users']:,}</div>
                    <div class="label">总用户数</div>
                </div>
'''
            
            if 'total_events' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['total_events']:,}</div>
                    <div class="label">总事件数</div>
                </div>
'''
            
            if 'overall_conversion_rate' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['overall_conversion_rate']:.2%}</div>
                    <div class="label">整体转化率</div>
                </div>
'''
            
            if 'avg_day_1_rate' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['avg_day_1_rate']:.2%}</div>
                    <div class="label">次日留存率</div>
                </div>
'''
            
            html_content += '''
            </div>
        </div>
'''
        
        # 添加页脚
        html_content += f'''
        <div class="footer">
            <p>电商用户行为分析系统 | 生成时间: {self.report_date}</p>
            <p>提示: 安装 plotly 后可获得完整的交互式图表功能</p>
        </div>
    </div>
</body>
</html>
'''
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"简化版HTML报表已生成: {output_path}")
        
        return output_path
    
    def generate_html_report(self, output_path: str, 
                               summary_data: Dict[str, Any] = None) -> str:
        """
        生成完整的HTML报表
        
        Args:
            output_path: 输出文件路径
            summary_data: 摘要数据
        
        Returns:
            生成的HTML文件路径
        """
        print(f"正在生成HTML报表: {output_path}")
        
        # 如果没有安装plotly，生成简化版报告
        if not PLOTLY_AVAILABLE:
            return self._generate_simple_report(output_path, summary_data)
        
        # 创建HTML内容
        html_content = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.8;
        }}
        
        .summary-section {{
            background: #f8f9fa;
            padding: 30px 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .summary-card .label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        .section {{
            padding: 40px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .section:last-child {{
            border-bottom: none;
        }}
        
        .section-title {{
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #636EFA;
            display: inline-block;
        }}
        
        .section-description {{
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 14px;
            line-height: 1.6;
        }}
        
        .chart-container {{
            margin-bottom: 30px;
            background: #fafafa;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }}
        
        .chart-container:last-child {{
            margin-bottom: 0;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 12px;
        }}
        
        .footer a {{
            color: #636EFA;
            text-decoration: none;
        }}
        
        .nav-tabs {{
            display: flex;
            background: #f8f9fa;
            padding: 0 40px;
            border-bottom: 1px solid #e9ecef;
            overflow-x: auto;
        }}
        
        .nav-tab {{
            padding: 15px 25px;
            color: #7f8c8d;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            white-space: nowrap;
        }}
        
        .nav-tab:hover {{
            color: #2c3e50;
            background: rgba(99, 110, 250, 0.1);
        }}
        
        .nav-tab.active {{
            color: #636EFA;
            border-bottom-color: #636EFA;
            font-weight: bold;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .header h1 {{
                font-size: 24px;
            }}
            
            .section {{
                padding: 20px;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.title}</h1>
            <div class="subtitle">生成时间: {self.report_date}</div>
        </div>
'''
        
        # 添加摘要数据
        if summary_data:
            html_content += '''
        <div class="summary-section">
            <div class="summary-grid">
'''
            if 'total_users' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['total_users']:,}</div>
                    <div class="label">总用户数</div>
                </div>
'''
            
            if 'total_events' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['total_events']:,}</div>
                    <div class="label">总事件数</div>
                </div>
'''
            
            if 'overall_conversion_rate' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['overall_conversion_rate']:.2%}</div>
                    <div class="label">整体转化率</div>
                </div>
'''
            
            if 'avg_day_1_rate' in summary_data:
                html_content += f'''
                <div class="summary-card">
                    <div class="value">{summary_data['avg_day_1_rate']:.2%}</div>
                    <div class="label">次日留存率</div>
                </div>
'''
            
            html_content += '''
            </div>
        </div>
'''
        
        # 添加导航标签
        if len(self.sections) > 0:
            html_content += '''
        <div class="nav-tabs">
'''
            for i, section in enumerate(self.sections):
                active_class = 'active' if i == 0 else ''
                html_content += f'''
            <div class="nav-tab {active_class}" onclick="switchTab({i})">{section['title']}</div>
'''
            html_content += '''
        </div>
'''
        
        # 添加章节内容
        for i, section in enumerate(self.sections):
            active_class = 'active' if i == 0 else ''
            html_content += f'''
        <div class="tab-content {active_class}" id="tab-content-{i}">
            <div class="section">
                <h2 class="section-title">{section['title']}</h2>
'''
            
            if section['description']:
                html_content += f'''
                <p class="section-description">{section['description']}</p>
'''
            
            # 添加图表
            for j, fig in enumerate(section['figures']):
                # 转换图表为HTML
                chart_html = fig.to_html(
                    full_html=False,
                    include_plotlyjs=False,
                    config={'displayModeBar': True, 'responsive': True}
                )
                
                html_content += f'''
                <div class="chart-container" id="chart-{i}-{j}">
                    {chart_html}
                </div>
'''
            
            html_content += '''
            </div>
        </div>
'''
        
        # 添加页脚
        html_content += f'''
        <div class="footer">
            <p>电商用户行为分析系统 | 生成时间: {self.report_date}</p>
            <p>此报表包含交互式图表，支持缩放、悬停查看详细数据</p>
        </div>
    </div>
    
    <script>
        function switchTab(tabIndex) {{
            // 隐藏所有标签内容
            document.querySelectorAll('.tab-content').forEach(function(el) {{
                el.classList.remove('active');
            }});
            
            // 移除所有标签的active状态
            document.querySelectorAll('.nav-tab').forEach(function(el) {{
                el.classList.remove('active');
            }});
            
            // 显示选中的标签内容
            document.getElementById('tab-content-' + tabIndex).classList.add('active');
            
            // 激活选中的标签
            document.querySelectorAll('.nav-tab')[tabIndex].classList.add('active');
            
            // 重新渲染图表（解决切换标签时图表显示问题）
            setTimeout(function() {{
                window.dispatchEvent(new Event('resize'));
            }}, 100);
        }}
        
        // 页面加载完成后调整图表大小
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                window.dispatchEvent(new Event('resize'));
            }}, 500);
        }});
        
        // 响应式调整
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize(document.querySelectorAll('.js-plotly-plot'));
        }});
    </script>
</body>
</html>
'''
        
        # 保存HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML报表已生成: {output_path}")
        print(f"HTML报表已生成: {output_path}")
        
        return output_path
    
    def add_all_charts(self, 
                        funnel_data: pd.DataFrame = None,
                        retention_df: pd.DataFrame = None,
                        retention_days: List[int] = None,
                        cohort_pivot: pd.DataFrame = None,
                        event_df: pd.DataFrame = None,
                        daily_activity_df: pd.DataFrame = None):
        """
        添加所有预定义的图表
        
        Args:
            funnel_data: 漏斗数据
            retention_df: 留存数据
            retention_days: 留存天数
            cohort_pivot: 同期群透视表
            event_df: 事件数据
            daily_activity_df: 每日活动数据
        """
        # 漏斗分析章节
        if funnel_data is not None:
            funnel_fig = self.create_funnel_chart(funnel_data)
            self.add_section(
                title="漏斗转化分析",
                figures=[funnel_fig],
                description="漏斗图展示了用户从浏览到购买的转化路径。每个阶段显示了用户数量和相对于前一阶段的转化率。"
            )
        
        # 留存分析章节
        figures = []
        if retention_df is not None and retention_days is not None:
            retention_fig = self.create_retention_curve(retention_df, retention_days)
            figures.append(retention_fig)
        
        if cohort_pivot is not None:
            cohort_fig = self.create_cohort_heatmap(cohort_pivot)
            figures.append(cohort_fig)
        
        if figures:
            self.add_section(
                title="用户留存分析",
                figures=figures,
                description="留存分析展示了用户在首次使用后的持续活跃情况。留存曲线显示了不同天数的留存率，热力图展示了同期群的留存趋势。"
            )
        
        # 事件分布章节
        figures = []
        if event_df is not None:
            event_dist_fig = self.create_event_distribution_chart(event_df)
            figures.append(event_dist_fig)
            
            device_fig = self.create_device_distribution_chart(event_df)
            figures.append(device_fig)
        
        if figures:
            self.add_section(
                title="用户行为分布",
                figures=figures,
                description="展示了用户行为类型和设备类型的分布情况，帮助了解用户的行为偏好和使用习惯。"
            )
        
        # 每日活动趋势章节
        if daily_activity_df is not None:
            daily_fig = self.create_daily_activity_chart(daily_activity_df)
            self.add_section(
                title="每日活动趋势",
                figures=[daily_fig],
                description="展示了用户活动的时间趋势，包括每日事件数和用户数的变化情况。"
            )


if __name__ == '__main__':
    # 示例用法
    from data_generator import ECommerceDataGenerator
    from data_cleaner import DataCleaner
    from funnel_analysis import FunnelAnalyzer
    from retention_analysis import RetentionAnalyzer
    
    # 生成测试数据
    generator = ECommerceDataGenerator(num_events=10000)
    events, _, _ = generator.generate(add_dirty_data=True)
    
    # 清洗数据
    cleaner = DataCleaner()
    cleaned_data, _ = cleaner.clean(events)
    
    # 漏斗分析
    funnel_analyzer = FunnelAnalyzer()
    funnel_result = funnel_analyzer.analyze_basic_funnel(cleaned_data)
    
    # 留存分析
    retention_analyzer = RetentionAnalyzer()
    retention_result = retention_analyzer.calculate_daily_retention(cleaned_data)
    cohort_result = retention_analyzer.create_cohort_analysis(cleaned_data, cohort_type='weekly')
    
    # 创建报表
    report = HTMLReportGenerator(title="电商用户行为分析报告")
    
    # 准备摘要数据
    summary_data = {
        'total_users': cleaned_data['user_id'].nunique(),
        'total_events': len(cleaned_data),
        'overall_conversion_rate': funnel_result['metrics']['overall_conversion_rate'],
        'avg_day_1_rate': retention_result['avg_retention'].get('avg_day_1_rate', 0)
    }
    
    # 添加所有图表
    report.add_all_charts(
        funnel_data=funnel_result['funnel_data'],
        retention_df=retention_result['retention_df'],
        retention_days=retention_result['retention_days'],
        cohort_pivot=cohort_result['cohort_pivot'],
        event_df=cleaned_data,
        daily_activity_df=cleaned_data
    )
    
    # 生成HTML报表
    report.generate_html_report('test_report.html', summary_data)
