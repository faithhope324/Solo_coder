#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import io
import os
import sys
from datetime import datetime

from log_analyzer import LogParser, LogAnalyzer, Visualizer


if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Python 日志分析程序 - 解析半结构化文本日志，生成可视化看板',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  python main.py -f access.log
  python main.py -f logs/*.log -o dashboard.html
  python main.py -f access.log --verbose
        '''
    )
    
    parser.add_argument('-f', '--files', nargs='+', required=True,
                        help='日志文件路径（支持多个文件，可用通配符）')
    
    parser.add_argument('-o', '--output', default='dashboard.html',
                        help='输出HTML看板路径（默认: dashboard.html）')
    
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细分析信息')
    
    parser.add_argument('--format', choices=['nginx', 'apache', 'custom', 'auto'], default='auto',
                        help='日志格式类型（默认: auto 自动检测）')
    
    return parser.parse_args()


def expand_file_patterns(file_patterns):
    import glob
    
    files = []
    for pattern in file_patterns:
        matches = glob.glob(pattern)
        if matches:
            files.extend(matches)
        else:
            if os.path.exists(pattern):
                files.append(pattern)
            else:
                print(f"警告: 未找到文件或匹配项: {pattern}")
    
    return list(set(files))


def print_summary(summary, verbose=False):
    print("\n" + "="*60)
    print("日志分析摘要")
    print("="*60)
    
    time_range = summary.get('time_range', {})
    if time_range:
        print(f"\n时间范围: {time_range.get('start', 'N/A')} ~ {time_range.get('end', 'N/A')}")
    
    print(f"\n基本统计:")
    print(f"  - 总请求数: {summary.get('total_requests', 0):,}")
    print(f"  - 独立 IP: {summary.get('unique_ips', 0):,}")
    print(f"  - 解析失败: {summary.get('failed_parse_count', 0):,}")
    print(f"  - HTTP 错误: {summary.get('http_error_count', 0):,}")
    
    print(f"\n状态码分布:")
    status = summary.get('status_distribution', {})
    total = sum(status.values())
    for code, count in sorted(status.items()):
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  - {code}: {count:,} ({percentage:.1f}%)")
    
    print(f"\n异常请求:")
    print(f"  - 4xx (客户端错误): {summary.get('4xx_count', 0):,}")
    print(f"  - 5xx (服务器错误): {summary.get('5xx_count', 0):,}")
    
    if verbose:
        print(f"\n热门路径 TOP 5:")
        for i, item in enumerate(summary.get('top_paths', [])[:5], 1):
            print(f"  {i}. {item.get('path')} ({item.get('count')} 次)")
        
        print(f"\n活跃 IP TOP 5:")
        for i, item in enumerate(summary.get('top_ips', [])[:5], 1):
            print(f"  {i}. {item.get('ip')} ({item.get('count')} 次)")
        
        print(f"\n错误路径 TOP 5:")
        for i, item in enumerate(summary.get('top_error_paths', [])[:5], 1):
            print(f"  {i}. {item.get('path')} ({item.get('count')} 次)")
        
        print(f"\n响应时间统计:")
        resp_stats = summary.get('response_time_stats')
        if resp_stats:
            print(f"  - 样本数: {resp_stats.get('count'):,}")
            print(f"  - 最小: {resp_stats.get('min')} ms")
            print(f"  - 最大: {resp_stats.get('max')} ms")
            print(f"  - 平均: {resp_stats.get('avg'):.2f} ms")
            print(f"  - 中位数: {resp_stats.get('median')} ms")
        else:
            print("  - 无响应时间数据")


def main():
    args = parse_arguments()
    
    print("\n" + "="*60)
    print("Python 日志分析程序 v1.0")
    print("="*60)
    
    files = expand_file_patterns(args.files)
    
    if not files:
        print("错误: 未找到任何有效的日志文件！")
        sys.exit(1)
    
    print(f"\n待分析文件 ({len(files)} 个):")
    for f in files:
        print(f"   - {f}")
    
    print("\n正在解析日志...")
    parser = LogParser()
    analyzer = LogAnalyzer()
    
    total_parsed = 0
    total_failed = 0
    
    for file_path in files:
        print(f"   正在处理: {file_path}")
        logs = list(parser.parse_file(file_path))
        total_parsed += len([l for l in logs if 'error' not in l])
        total_failed += len([l for l in logs if 'error' in l])
        analyzer.add_logs(logs)
    
    print(f"\n解析完成!")
    print(f"   成功解析: {total_parsed:,} 条")
    print(f"   解析失败: {total_failed:,} 条")
    
    print("\n正在分析数据...")
    summary = analyzer.get_summary()
    
    print("\n正在生成可视化图表...")
    visualizer = Visualizer()
    
    charts = {}
    charts['status'] = visualizer.create_status_pie_chart(summary.get('status_distribution', {}))
    charts['hourly'] = visualizer.create_hourly_bar_chart(summary.get('hourly_distribution', {}))
    charts['method'] = visualizer.create_method_bar_chart(summary.get('method_distribution', {}))
    charts['daily'] = visualizer.create_daily_line_chart(summary.get('daily_distribution', {}))
    
    print("正在生成HTML看板...")
    html = visualizer.generate_html_dashboard(summary, charts)
    
    output_path = os.path.abspath(args.output)
    visualizer.save_html_dashboard(html, output_path)
    
    print_summary(summary, args.verbose)
    
    print("\n" + "="*60)
    print("分析完成!")
    print("="*60)
    print(f"\n看板已保存至: {output_path}")
    print(f"\n提示: 请用浏览器打开上述HTML文件查看可视化报告")


if __name__ == '__main__':
    main()
