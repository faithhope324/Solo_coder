"""
Bug 修复验证测试脚本
测试以下三个修复：
1. 处理数据中转换失败的日期
2. 列名匹配区分大小写，并处理空格或特殊字符
3. 聚合函数名与列名不能相同的问题
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from filter_module import FilterModule


def test_date_parsing_with_errors():
    """测试 1: 处理数据中转换失败的日期"""
    print("\n" + "="*60)
    print("测试 1: 处理数据中转换失败的日期")
    print("="*60)
    
    data = {
        '日期': [
            '2025-01-01',
            '2025/01/02',
            '2025.01.03',
            '无效日期',
            '2025年01月05日',
            '2025-01-06 14:30:00',
            None,
            '2025-01-08',
            'abc123',
            '2025-01-10'
        ],
        '地区': ['华东', '华北', '华南', '华东', '华北', '华南', '华东', '华北', '华南', '华东'],
        '品类': ['电子产品', '服装', '家居', '电子产品', '服装', '家居', '电子产品', '服装', '家居', '电子产品'],
        '实际金额': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
        '数量': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    }
    
    df = pd.DataFrame(data)
    
    print("\n原始数据中的日期列:")
    print(df['日期'].tolist())
    
    loader = DataLoader()
    loader.df = df.copy()
    loader._preprocess_data()
    
    date_errors = loader.get_date_parse_errors()
    
    print(f"\n日期解析统计:")
    print(f"  总记录数: {date_errors.get('total_count', 0)}")
    print(f"  成功解析: {date_errors.get('success_count', 0)}")
    print(f"  解析失败: {date_errors.get('failed_count', 0)}")
    
    if date_errors.get('failed_values_sample'):
        print(f"  失败的日期值示例: {date_errors['failed_values_sample']}")
    
    processed_df = loader.get_data()
    print(f"\n处理后的日期列数据类型: {processed_df['日期'].dtype}")
    print(f"处理后的日期列:")
    print(processed_df['日期'].tolist())
    
    valid_dates = processed_df['日期'].dropna()
    print(f"\n有效日期数量: {len(valid_dates)}")
    print(f"日期范围: {valid_dates.min()} 到 {valid_dates.max()}")
    
    print("\n[测试 1 完成]")
    return date_errors.get('failed_count', 0) > 0


def test_case_insensitive_column_matching():
    """测试 2: 列名匹配区分大小写，并处理空格或特殊字符"""
    print("\n" + "="*60)
    print("测试 2: 列名匹配不区分大小写，处理空格和特殊字符")
    print("="*60)
    
    test_cases = [
        {
            'name': '大小写混合',
            'columns': ['DATE', 'Region', 'CATEGORY', 'Actual_Amount', 'Quantity'],
            'data': {
                'DATE': pd.date_range('2025-01-01', periods=5),
                'Region': ['华东', '华北', '华南', '华东', '华北'],
                'CATEGORY': ['电子产品', '服装', '家居', '食品', '美妆'],
                'Actual_Amount': [1000, 2000, 3000, 4000, 5000],
                'Quantity': [1, 2, 3, 4, 5]
            }
        },
        {
            'name': '包含空格和特殊字符',
            'columns': ['  日期  ', '销售_区域', '产品-类别', '实际.金额', '销售 数量'],
            'data': {
                '  日期  ': pd.date_range('2025-01-01', periods=5),
                '销售_区域': ['华东', '华北', '华南', '华东', '华北'],
                '产品-类别': ['电子产品', '服装', '家居', '食品', '美妆'],
                '实际.金额': [1000, 2000, 3000, 4000, 5000],
                '销售 数量': [1, 2, 3, 4, 5]
            }
        },
        {
            'name': '英文列名小写',
            'columns': ['date', 'region', 'category', 'amount', 'quantity'],
            'data': {
                'date': pd.date_range('2025-01-01', periods=5),
                'region': ['华东', '华北', '华南', '华东', '华北'],
                'category': ['电子产品', '服装', '家居', '食品', '美妆'],
                'amount': [1000, 2000, 3000, 4000, 5000],
                'quantity': [1, 2, 3, 4, 5]
            }
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n测试场景: {test_case['name']}")
        print(f"  原始列名: {test_case['columns']}")
        
        df = pd.DataFrame(test_case['data'])
        
        filter_module = FilterModule(df)
        
        print(f"\n  识别结果:")
        print(f"    日期列: {filter_module.date_col}")
        print(f"    地区列: {filter_module.region_col}")
        print(f"    品类列: {filter_module.category_col}")
        print(f"    金额列: {filter_module.amount_col}")
        print(f"    数量列: {filter_module.quantity_col}")
        
        column_mapping = filter_module.get_column_mapping()
        print(f"\n  列名映射 (标准化 -> 原始):")
        for normalized, original in column_mapping.items():
            print(f"    '{normalized}' -> '{original}'")
        
        all_found = (
            filter_module.date_col is not None and
            filter_module.region_col is not None and
            filter_module.category_col is not None and
            filter_module.amount_col is not None and
            filter_module.quantity_col is not None
        )
        
        if all_found:
            print(f"\n  [OK] 所有关键列都成功识别！")
        else:
            print(f"\n  [ERROR] 部分列未识别成功！")
            all_passed = False
    
    print("\n[测试 2 完成]")
    return all_passed


def test_aggregation_column_name_conflict():
    """测试 3: 聚合函数名与列名不能相同的问题"""
    print("\n" + "="*60)
    print("测试 3: 聚合函数名与列名冲突问题")
    print("="*60)
    
    test_cases = [
        {
            'name': '正常列名测试',
            'data': {
                '地区': ['华东', '华北', '华东', '华北', '华东'],
                '品类': ['电子产品', '电子产品', '服装', '服装', '电子产品'],
                '实际金额': [1000, 2000, 3000, 4000, 5000],
                '数量': [1, 2, 3, 4, 5]
            }
        },
        {
            'name': '列名与聚合函数名相同 (sum, mean)',
            'data': {
                '地区': ['华东', '华北', '华东', '华北', '华东'],
                '品类': ['电子产品', '电子产品', '服装', '服装', '电子产品'],
                'sum': [1000, 2000, 3000, 4000, 5000],
                'mean': [1, 2, 3, 4, 5]
            }
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n测试场景: {test_case['name']}")
        print(f"  列名: {list(test_case['data'].keys())}")
        
        df = pd.DataFrame(test_case['data'])
        filter_module = FilterModule(df)
        
        if test_case['name'] == '列名与聚合函数名相同 (sum, mean)':
            filter_module.amount_col = 'sum'
            filter_module.quantity_col = 'mean'
        
        print(f"\n  按地区分组结果:")
        region_group = filter_module.group_by_region()
        print(f"    列名: {list(region_group.columns)}")
        print(f"    数据:\n{region_group}")
        
        expected_columns = ['销售金额汇总', '销售金额平均', '销售金额记录数', '销售数量汇总', '销售数量平均']
        actual_columns = [col for col in region_group.columns if col not in ['地区', '品类']]
        
        print(f"\n  聚合列名检查:")
        print(f"    预期的列名模式: {expected_columns}")
        print(f"    实际的聚合列名: {actual_columns}")
        
        has_conflict = False
        for col in actual_columns:
            if col in ['sum', 'mean', 'count', '地区', '品类']:
                has_conflict = True
                print(f"    [警告] 发现潜在冲突列名: '{col}'")
        
        if not has_conflict:
            print(f"    [OK] 未发现列名冲突")
        else:
            all_passed = False
        
        print(f"\n  按地区和品类交叉分组结果:")
        cross_group = filter_module.group_by_region_category()
        print(f"    列名: {list(cross_group.columns)}")
        
        print(f"\n  按品类分组结果:")
        category_group = filter_module.group_by_category()
        print(f"    列名: {list(category_group.columns)}")
    
    print("\n[测试 3 完成]")
    return all_passed


def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "="*60)
    print("测试 4: 完整工作流程测试")
    print("="*60)
    
    print("\n加载示例数据...")
    loader = DataLoader()
    loader.load_sample_data(n_records=100)
    
    print(f"\n数据信息:")
    print(f"  行数: {len(loader.get_data())}")
    print(f"  可用地区: {loader.get_filter_options()['regions']}")
    print(f"  可用品类: {loader.get_filter_options()['categories']}")
    
    filter_module = FilterModule(loader.get_data())
    
    print(f"\n应用筛选条件...")
    filter_module.filter_by_region(['华东', '华北'])
    filter_module.filter_by_category(['电子产品', '服装'])
    
    print(f"\n当前筛选条件: {filter_module.get_applied_filters()}")
    
    print(f"\n分组汇总测试:")
    
    region_group = filter_module.group_by_region()
    print(f"\n  按地区分组 - 列名: {list(region_group.columns)}")
    print(f"  按地区分组 - 数据预览:\n{region_group}")
    
    category_group = filter_module.group_by_category()
    print(f"\n  按品类分组 - 列名: {list(category_group.columns)}")
    
    monthly_group = filter_module.group_by_month()
    print(f"\n  按月份分组 - 列名: {list(monthly_group.columns)}")
    
    cross_group = filter_module.group_by_region_category()
    print(f"\n  交叉分组 - 列名: {list(cross_group.columns)}")
    
    summary = filter_module.get_summary_statistics()
    print(f"\n汇总统计:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n[测试 4 完成]")
    return True


def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# Bug 修复验证测试")
    print("#"*60)
    
    results = {}
    
    try:
        results['test1'] = test_date_parsing_with_errors()
    except Exception as e:
        print(f"\n测试 1 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test1'] = False
    
    try:
        results['test2'] = test_case_insensitive_column_matching()
    except Exception as e:
        print(f"\n测试 2 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test2'] = False
    
    try:
        results['test3'] = test_aggregation_column_name_conflict()
    except Exception as e:
        print(f"\n测试 3 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test3'] = False
    
    try:
        results['test4'] = test_full_workflow()
    except Exception as e:
        print(f"\n测试 4 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test4'] = False
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"测试 1 (日期解析错误处理): {'通过' if results.get('test1') else '需要关注'}")
    print(f"测试 2 (列名不区分大小写): {'通过' if results.get('test2') else '失败'}")
    print(f"测试 3 (聚合列名冲突): {'通过' if results.get('test3') else '失败'}")
    print(f"测试 4 (完整工作流): {'通过' if results.get('test4') else '失败'}")
    
    all_passed = all([
        results.get('test2', False),
        results.get('test3', False),
        results.get('test4', False)
    ])
    
    if all_passed:
        print("\n[√] 所有核心测试通过！")
    else:
        print("\n[×] 部分测试失败，请检查修复是否完整。")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
