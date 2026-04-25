#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试脚本 - 验证电商用户行为分析系统的各个模块
"""

import sys
import os
import io

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("电商用户行为分析系统 - 模块测试")
print("=" * 70)

# 测试1: 导入模块
print("\n1. 测试模块导入...")
try:
    from data_generator import ECommerceDataGenerator
    print("   [OK] data_generator 模块导入成功")
except ImportError as e:
    print(f"   [FAIL] data_generator 模块导入失败: {e}")
    sys.exit(1)

try:
    from data_cleaner import DataCleaner
    print("   [OK] data_cleaner 模块导入成功")
except ImportError as e:
    print(f"   [FAIL] data_cleaner 模块导入失败: {e}")
    sys.exit(1)

try:
    from funnel_analysis import FunnelAnalyzer
    print("   [OK] funnel_analysis 模块导入成功")
except ImportError as e:
    print(f"   [FAIL] funnel_analysis 模块导入失败: {e}")
    sys.exit(1)

try:
    from retention_analysis import RetentionAnalyzer
    print("   [OK] retention_analysis 模块导入成功")
except ImportError as e:
    print(f"   [FAIL] retention_analysis 模块导入失败: {e}")
    sys.exit(1)

try:
    from html_report import HTMLReportGenerator, PLOTLY_AVAILABLE
    if PLOTLY_AVAILABLE:
        print("   [OK] html_report 模块导入成功 (plotly已安装)")
    else:
        print("   [OK] html_report 模块导入成功 (plotly未安装，将使用简化版报告)")
except ImportError as e:
    print(f"   [FAIL] html_report 模块导入失败: {e}")
    sys.exit(1)

# 测试2: 数据生成
print("\n2. 测试数据生成...")
try:
    generator = ECommerceDataGenerator(
        num_users=100,
        num_products=50,
        num_events=500,
        start_date='2024-01-01',
        end_date='2024-01-31'
    )
    events, products, sessions = generator.generate(add_dirty_data=True)
    print(f"   [OK] 数据生成成功:")
    print(f"     - 事件数据: {len(events)} 条")
    print(f"     - 商品数据: {len(products)} 条")
    print(f"     - 会话数据: {len(sessions)} 条")
except Exception as e:
    print(f"   [FAIL] 数据生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 数据清洗
print("\n3. 测试数据清洗...")
try:
    cleaner = DataCleaner()
    cleaned_data, stats = cleaner.clean(events)
    report = cleaner.get_cleaning_report()
    
    print(f"   [OK] 数据清洗成功:")
    print(f"     - 原始数据: {report['original_shape']}")
    print(f"     - 清洗后数据: {report['cleaned_shape']}")
    print(f"     - 删除行数: {report['rows_removed']}")
except Exception as e:
    print(f"   [FAIL] 数据清洗失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4: 漏斗分析
print("\n4. 测试漏斗分析...")
try:
    funnel_analyzer = FunnelAnalyzer()
    basic_funnel = funnel_analyzer.analyze_basic_funnel(cleaned_data)
    
    print(f"   [OK] 漏斗分析成功:")
    print(f"     - 漏斗阶段: {basic_funnel['funnel_stages']}")
    print(f"     - 整体转化率: {basic_funnel['metrics']['overall_conversion_rate']:.2%}")
    
    for stage in basic_funnel['metrics']['stages']:
        print(f"     - {stage['stage']}: {stage['count']} 用户 (转化率: {stage['conversion_rate']:.2%})")
except Exception as e:
    print(f"   [FAIL] 漏斗分析失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试5: 留存分析
print("\n5. 测试留存分析...")
try:
    retention_analyzer = RetentionAnalyzer()
    daily_retention = retention_analyzer.calculate_daily_retention(
        cleaned_data,
        retention_days=[1, 3, 7]
    )
    
    print(f"   [OK] 留存分析成功:")
    print(f"     - 总新增用户: {daily_retention['total_new_users']}")
    
    for key, value in daily_retention['avg_retention'].items():
        if 'rate' in key:
            print(f"     - {key}: {value:.2%}")
    
    # 测试同期群分析
    cohort_analysis = retention_analyzer.create_cohort_analysis(
        cleaned_data,
        cohort_type='weekly'
    )
    print(f"     - 同期群数量: {len(cohort_analysis['cohort_pivot'])}")
except Exception as e:
    print(f"   [FAIL] 留存分析失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试6: HTML报表生成
print("\n6. 测试HTML报表生成...")
try:
    # 创建输出目录
    output_dir = './test_output'
    os.makedirs(output_dir, exist_ok=True)
    
    # 准备摘要数据
    summary_data = {
        'total_users': cleaned_data['user_id'].nunique(),
        'total_events': len(cleaned_data),
        'overall_conversion_rate': basic_funnel['metrics']['overall_conversion_rate'],
        'avg_day_1_rate': daily_retention['avg_retention'].get('avg_day_1_rate', 0)
    }
    
    # 创建报表生成器
    report = HTMLReportGenerator(title="测试报告 - 电商用户行为分析")
    
    # 添加所有图表
    report.add_all_charts(
        funnel_data=basic_funnel['funnel_data'],
        retention_df=daily_retention['retention_df'],
        retention_days=daily_retention['retention_days'],
        cohort_pivot=cohort_analysis['cohort_pivot'],
        event_df=cleaned_data,
        daily_activity_df=cleaned_data
    )
    
    # 生成HTML报表
    report_path = os.path.join(output_dir, 'test_report.html')
    final_path = report.generate_html_report(report_path, summary_data)
    
    print(f"   [OK] HTML报表生成成功:")
    print(f"     - 文件路径: {os.path.abspath(final_path)}")
    print(f"     - 文件大小: {os.path.getsize(final_path)} 字节")
except Exception as e:
    print(f"   [FAIL] HTML报表生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试7: 检查输出文件
print("\n7. 检查输出文件...")
try:
    if os.path.exists(final_path):
        print(f"   [OK] 报表文件存在: {os.path.abspath(final_path)}")
        
        # 读取文件内容的前几行
        with open(final_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '<!DOCTYPE html>' in content:
            print("   [OK] 文件是有效的HTML格式")
        
        if '电商用户行为分析' in content:
            print("   [OK] 文件包含预期的内容")
    else:
        print(f"   [FAIL] 报表文件不存在: {final_path}")
except Exception as e:
    print(f"   [FAIL] 检查输出文件失败: {e}")

print("\n" + "=" * 70)
print("所有测试通过! [OK]")
print("=" * 70)
print("\n使用说明:")
print("  1. 运行 'python main.py' 执行完整分析流程")
print("  2. 运行 'python main.py --help' 查看所有可用参数")
print("  3. 安装 plotly 以获得完整的交互式图表功能:")
print("     pip install plotly")
print("\n生成的测试报告位于:")
print(f"  {os.path.abspath(final_path)}")
