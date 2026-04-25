import json
import base64
from io import StringIO
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
    try:
        import plotly
        PLOTLY_VERSION = plotly.__version__
    except:
        PLOTLY_VERSION = None
except ImportError:
    PLOTLY_AVAILABLE = False
    PLOTLY_VERSION = None


class Visualizer:
    def __init__(self):
        self.figures = {}
        
    def _get_plotly_cdn_url(self) -> str:
        if PLOTLY_VERSION:
            return f"https://cdn.plot.ly/plotly-{PLOTLY_VERSION}.min.js"
        return "https://cdn.plot.ly/plotly-latest.min.js"
    
    def create_status_pie_chart(self, status_distribution: Dict[str, int]) -> str:
        if not PLOTLY_AVAILABLE:
            return self._create_fallback_chart('status')
        
        labels = list(status_distribution.keys())
        values = list(status_distribution.values())
        
        colors = {
            '2xx': '#28a745',
            '3xx': '#17a2b8',
            '4xx': '#ffc107',
            '5xx': '#dc3545',
            'other': '#6c757d'
        }
        
        color_list = [colors.get(label, '#6c757d') for label in labels]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            textinfo='label+percent',
            insidetextorientation='radial',
            marker=dict(colors=color_list),
            hole=0.4,
            textfont=dict(size=12),
            domain=dict(x=[0.1, 0.9], y=[0.2, 0.8])
        )])
        
        fig.update_layout(
            title=dict(
                text='HTTP 状态码分布',
                font=dict(size=16, color='#333'),
                x=0.5,
                y=0.95
            ),
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='middle',
                y=0.5,
                xanchor='right',
                x=1.15,
                font=dict(size=11)
            ),
            margin=dict(t=60, b=40, l=20, r=120),
            paper_bgcolor='white',
            plot_bgcolor='white',
            autosize=True
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def create_hourly_bar_chart(self, hourly_distribution: Dict[int, int]) -> str:
        if not PLOTLY_AVAILABLE:
            return self._create_fallback_chart('hourly')
        
        hours = list(range(24))
        counts = [hourly_distribution.get(hour, 0) for hour in hours]
        hour_labels = [f'{h}:00' for h in hours]
        
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 0
        peak_count = max(counts) if counts else 0
        
        fig = go.Figure(data=[go.Bar(
            x=hour_labels,
            y=counts,
            marker=dict(
                color='#007bff',
                line=dict(width=0)
            ),
            text=[str(c) if c > 0 else '' for c in counts],
            textposition='outside',
            textfont=dict(size=10)
        )])
        
        fig.update_layout(
            title=dict(
                text=f'时段访问分布 (峰值: {peak_count} 请求于 {peak_hour}:00)',
                font=dict(size=16, color='#333'),
                x=0.5
            ),
            xaxis=dict(
                title='小时',
                tickangle=45,
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1
            ),
            yaxis=dict(
                title='请求数量',
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1,
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.1)'
            ),
            margin=dict(t=80, b=80, l=60, r=40),
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.15
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def create_method_bar_chart(self, method_distribution: Dict[str, int]) -> str:
        if not PLOTLY_AVAILABLE:
            return self._create_fallback_chart('method')
        
        methods = list(method_distribution.keys())
        counts = list(method_distribution.values())
        
        colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6c757d', '#17a2b8', '#6f42c1', '#fd7e14']
        color_list = colors[:len(methods)]
        
        fig = go.Figure(data=[go.Bar(
            x=methods,
            y=counts,
            marker=dict(
                color=color_list,
                line=dict(width=0)
            ),
            text=[str(c) for c in counts],
            textposition='outside',
            textfont=dict(size=11)
        )])
        
        fig.update_layout(
            title=dict(
                text='HTTP 方法分布',
                font=dict(size=16, color='#333'),
                x=0.5
            ),
            xaxis=dict(
                title='HTTP 方法',
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1
            ),
            yaxis=dict(
                title='请求数量',
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1,
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.1)'
            ),
            margin=dict(t=80, b=80, l=60, r=40),
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.15
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def create_daily_line_chart(self, daily_distribution: Dict[str, int]) -> str:
        if not PLOTLY_AVAILABLE:
            return self._create_fallback_chart('daily')
        
        dates = list(daily_distribution.keys())
        counts = list(daily_distribution.values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=counts,
            mode='lines+markers+text',
            line=dict(color='#007bff', width=3),
            marker=dict(
                color='#007bff',
                size=8,
                line=dict(color='white', width=2)
            ),
            text=[str(c) for c in counts],
            textposition='top center',
            textfont=dict(size=10),
            fill='tozeroy',
            fillcolor='rgba(0,123,255,0.1)'
        ))
        
        fig.update_layout(
            title=dict(
                text='每日访问趋势',
                font=dict(size=16, color='#333'),
                x=0.5
            ),
            xaxis=dict(
                title='日期',
                tickangle=45,
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1
            ),
            yaxis=dict(
                title='请求数量',
                gridcolor='rgba(0,0,0,0.1)',
                showgrid=True,
                gridwidth=1,
                zeroline=True,
                zerolinecolor='rgba(0,0,0,0.1)'
            ),
            margin=dict(t=80, b=80, l=60, r=40),
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        return fig.to_html(full_html=False, include_plotlyjs=False)
    
    def _create_fallback_chart(self, chart_type: str) -> str:
        messages = {
            'status': '状态码分布图表 (需安装 plotly/matplotlib 查看)',
            'hourly': '时段访问分布图表 (需安装 plotly/matplotlib 查看)',
            'method': 'HTTP 方法分布图表 (需安装 plotly/matplotlib 查看)',
            'daily': '每日访问趋势图表 (需安装 plotly/matplotlib 查看)'
        }
        return f'''
        <div style="padding: 60px 20px; text-align: center; background: #f8f9fa; border-radius: 8px; color: #6c757d;">
            <div style="font-size: 48px; margin-bottom: 15px;">📊</div>
            <div style="font-size: 16px;">{messages.get(chart_type, '图表')}</div>
            <div style="font-size: 12px; margin-top: 10px;">提示: 运行 pip install plotly 或 pip install matplotlib 以启用图表</div>
        </div>
        '''
    
    def generate_html_dashboard(
        self,
        summary: Dict[str, Any],
        charts: Dict[str, str]
    ) -> str:
        time_range = summary.get('time_range', {})
        start_time = time_range.get('start', 'N/A') if time_range else 'N/A'
        end_time = time_range.get('end', 'N/A') if time_range else 'N/A'
        
        status_dist = summary.get('status_distribution', {})
        status_2xx = status_dist.get('2xx', 0)
        status_3xx = status_dist.get('3xx', 0)
        status_4xx = status_dist.get('4xx', 0)
        status_5xx = status_dist.get('5xx', 0)
        
        response_stats = summary.get('response_time_stats', {})
        
        plotly_cdn_url = self._get_plotly_cdn_url()
        plotly_script = f'''
        <script src="{plotly_cdn_url}" charset="utf-8"></script>
        ''' if PLOTLY_AVAILABLE else ''
        
        html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>日志分析看板</title>
    {plotly_script}
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 30px 0;
            color: white;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}
        
        .stat-card.success {{ border-top: 4px solid #28a745; }}
        .stat-card.info {{ border-top: 4px solid #17a2b8; }}
        .stat-card.warning {{ border-top: 4px solid #ffc107; }}
        .stat-card.danger {{ border-top: 4px solid #dc3545; }}
        .stat-card.primary {{ border-top: 4px solid #007bff; }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-card.success .stat-value {{ color: #28a745; }}
        .stat-card.info .stat-value {{ color: #17a2b8; }}
        .stat-card.warning .stat-value {{ color: #ffc107; }}
        .stat-card.danger .stat-value {{ color: #dc3545; }}
        .stat-card.primary .stat-value {{ color: #007bff; }}
        
        .stat-label {{
            font-size: 0.95rem;
            color: #6c757d;
        }}
        
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .chart-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .chart-card h3 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.2rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        
        .chart-card .js-plotly-plot {{
            width: 100% !important;
            height: auto !important;
        }}
        
        .tables-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .table-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .table-card h3 {{
            margin-bottom: 20px;
            color: #333;
            font-size: 1.2rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        table th, table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        
        table tr:hover {{
            background-color: #f8f9fa;
        }}
        
        table tr:hover td {{
            background-color: #f8f9fa;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        
        .footer {{
            text-align: center;
            color: white;
            padding: 20px;
            opacity: 0.8;
            font-size: 0.9rem;
        }}
        
        .time-range {{
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 8px;
            margin-top: 15px;
            display: inline-block;
            backdrop-filter: blur(10px);
        }}
        
        code {{
            background: #f1f3f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }}
        
        @media (max-width: 768px) {{
            .charts-container, .tables-container {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 1.8rem;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        
        @media (max-width: 480px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 日志分析看板</h1>
            <p>实时监控与分析服务器访问日志</p>
            <div class="time-range">
                <strong>时间范围:</strong> {start_time} ~ {end_time}
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="stat-value">{summary.get('total_requests', 0):,}</div>
                <div class="stat-label">总请求数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">{status_2xx:,}</div>
                <div class="stat-label">成功请求 (2xx)</div>
            </div>
            <div class="stat-card info">
                <div class="stat-value">{status_3xx:,}</div>
                <div class="stat-label">重定向 (3xx)</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-value">{status_4xx:,}</div>
                <div class="stat-label">客户端错误 (4xx)</div>
            </div>
            <div class="stat-card danger">
                <div class="stat-value">{status_5xx:,}</div>
                <div class="stat-label">服务器错误 (5xx)</div>
            </div>
            <div class="stat-card primary">
                <div class="stat-value">{summary.get('unique_ips', 0):,}</div>
                <div class="stat-label">独立 IP</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3>状态码分布</h3>
                {charts.get('status', '')}
            </div>
            <div class="chart-card">
                <h3>时段访问分布</h3>
                {charts.get('hourly', '')}
            </div>
            <div class="chart-card">
                <h3>HTTP 方法分布</h3>
                {charts.get('method', '')}
            </div>
            <div class="chart-card">
                <h3>每日访问趋势</h3>
                {charts.get('daily', '')}
            </div>
        </div>
        
        <div class="tables-container">
            <div class="table-card">
                <h3>🔥 热门访问路径 TOP 5</h3>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>路径</th>
                            <th>访问次数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._generate_table_rows(summary.get('top_paths', []))}
                    </tbody>
                </table>
            </div>
            
            <div class="table-card">
                <h3>🌐 活跃 IP TOP 5</h3>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>IP 地址</th>
                            <th>访问次数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._generate_ip_table_rows(summary.get('top_ips', []))}
                    </tbody>
                </table>
            </div>
            
            <div class="table-card">
                <h3>⚠️ 错误路径 TOP 5</h3>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>路径</th>
                            <th>错误次数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._generate_table_rows(summary.get('top_error_paths', []))}
                    </tbody>
                </table>
            </div>
            
            {self._generate_response_time_table(response_stats)}
        </div>
        
        <div class="footer">
            <p>日志分析程序 v1.0 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
'''
        return html
    
    def _generate_table_rows(self, items: list) -> str:
        if not items:
            return '<tr><td colspan="3" style="text-align: center; color: #6c757d; padding: 30px;">暂无数据</td></tr>'
        
        rows = []
        for i, item in enumerate(items, 1):
            path = item.get('path', 'N/A')
            count = item.get('count', 0)
            badge_class = 'badge-success' if i <= 3 else 'badge-warning' if i <= 5 else ''
            rows.append(f'''
                <tr>
                    <td><span class="badge {badge_class}">#{i}</span></td>
                    <td><code>{path}</code></td>
                    <td><strong>{count:,}</strong></td>
                </tr>
            ''')
        return ''.join(rows)
    
    def _generate_ip_table_rows(self, items: list) -> str:
        if not items:
            return '<tr><td colspan="3" style="text-align: center; color: #6c757d; padding: 30px;">暂无数据</td></tr>'
        
        rows = []
        for i, item in enumerate(items, 1):
            ip = item.get('ip', 'N/A')
            count = item.get('count', 0)
            badge_class = 'badge-success' if i <= 3 else 'badge-warning' if i <= 5 else ''
            rows.append(f'''
                <tr>
                    <td><span class="badge {badge_class}">#{i}</span></td>
                    <td><code>{ip}</code></td>
                    <td><strong>{count:,}</strong></td>
                </tr>
            ''')
        return ''.join(rows)
    
    def _generate_response_time_table(self, stats: dict) -> str:
        if not stats:
            return ''
        
        html = f'''
        <div class="table-card">
            <h3>⏱️ 响应时间统计</h3>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>值 (ms)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>最小响应时间</td>
                        <td><strong>{stats.get('min', 0)}</strong></td>
                    </tr>
                    <tr>
                        <td>最大响应时间</td>
                        <td><strong>{stats.get('max', 0)}</strong></td>
                    </tr>
                    <tr>
                        <td>平均响应时间</td>
                        <td><strong>{stats.get('avg', 0):.2f}</strong></td>
                    </tr>
                    <tr>
                        <td>中位数响应时间</td>
                        <td><strong>{stats.get('median', 0)}</strong></td>
                    </tr>
                    <tr>
                        <td>统计样本数</td>
                        <td><strong>{stats.get('count', 0):,}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''
        return html
    
    def save_html_dashboard(self, html: str, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
