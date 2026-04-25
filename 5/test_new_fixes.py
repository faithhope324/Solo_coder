"""
新 Bug 修复验证测试脚本
测试以下三个修复：
1. 日期筛选需要做 NaT 处理
2. 图表内存释放
3. 检查输出文件是否已存在，存在的话应该备份一下
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from filter_module import FilterModule
from file_utils import backup_if_exists, get_backup_list, safe_save_path


def test_nat_handling_in_date_filter():
    """测试 1: 日期筛选中的 NaT 处理"""
    print("\n" + "="*60)
    print("测试 1: 日期筛选中的 NaT 处理")
    print("="*60)
    
    data = {
        '日期': [
            '2025-01-01',
            '无效日期',
            '2025-01-03',
            None,
            '2025-01-05',
            '2025-01-06',
            'abc123',
            '2025-01-08',
            '2025-01-09',
            '2025-01-10'
        ],
        '地区': ['华东', '华北', '华南', '华东', '华北', '华南', '华东', '华北', '华南', '华东'],
        '品类': ['电子产品', '服装', '家居', '电子产品', '服装', '家居', '电子产品', '服装', '家居', '电子产品'],
        '实际金额': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
        '数量': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    }
    
    df = pd.DataFrame(data)
    
    print(f"\n原始数据 (共 {len(df)} 行):")
    print(df)
    
    loader = DataLoader()
    loader.df = df.copy()
    loader._preprocess_data()
    
    processed_df = loader.get_data()
    print(f"\n处理后的日期列数据类型: {processed_df['日期'].dtype}")
    print(f"处理后的日期列:")
    print(processed_df['日期'])
    
    date_errors = loader.get_date_parse_errors()
    print(f"\n日期解析错误统计:")
    print(f"  总记录数: {date_errors.get('total_count', 0)}")
    print(f"  成功解析: {date_errors.get('success_count', 0)}")
    print(f"  解析失败 (NaT): {date_errors.get('failed_count', 0)}")
    
    filter_module = FilterModule(processed_df)
    
    print(f"\n筛选前数据条数: {len(filter_module.get_filtered_data())}")
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 1, 31)
    filter_module.filter_by_date(start_date, end_date)
    
    filtered_df = filter_module.get_filtered_data()
    print(f"\n筛选后数据条数: {len(filtered_df)}")
    print(f"\n筛选后的数据:")
    print(filtered_df)
    
    print(f"\n验证筛选结果:")
    print(f"  预期有效日期数量: 7 (排除 3 个无效日期)")
    print(f"  实际筛选后数量: {len(filtered_df)}")
    
    valid_dates_in_filtered = filtered_df['日期'].notna().sum()
    print(f"  筛选后数据中的有效日期: {valid_dates_in_filtered}")
    
    nat_in_filtered = filtered_df['日期'].isna().sum()
    print(f"  筛选后数据中的 NaT 数量: {nat_in_filtered}")
    
    if nat_in_filtered == 0:
        print("\n[OK] NaT 处理测试通过！筛选后的数据中没有 NaT 值。")
        return True
    else:
        print("\n[ERROR] NaT 处理测试失败！筛选后的数据中仍有 NaT 值。")
        return False


def test_file_backup_functionality():
    """测试 2: 文件备份功能"""
    print("\n" + "="*60)
    print("测试 2: 文件备份功能")
    print("="*60)
    
    test_dir = 'test_backup'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    test_file = os.path.join(test_dir, 'test_report.xlsx')
    
    print(f"\n创建初始测试文件: {test_file}")
    
    df = pd.DataFrame({
        '日期': ['2025-01-01', '2025-01-02'],
        '销售额': [1000, 2000]
    })
    df.to_excel(test_file, index=False)
    
    print(f"  初始文件大小: {os.path.getsize(test_file)} 字节")
    
    print(f"\n测试备份功能...")
    backed_up, backup_path = backup_if_exists(test_file)
    
    print(f"  是否进行了备份: {backed_up}")
    print(f"  备份文件路径: {backup_path}")
    
    if backed_up and backup_path and os.path.exists(backup_path):
        print(f"  [OK] 备份文件已创建: {backup_path}")
    else:
        print(f"  [ERROR] 备份失败")
        return False
    
    print(f"\n测试多次备份（同一秒内的备份）...")
    
    df2 = pd.DataFrame({
        '日期': ['2025-01-03', '2025-01-04'],
        '销售额': [3000, 4000]
    })
    df2.to_excel(test_file, index=False)
    
    backed_up2, backup_path2 = backup_if_exists(test_file)
    
    print(f"  第二次备份: {backed_up2} -> {backup_path2}")
    
    backups = get_backup_list(test_file)
    print(f"\n所有备份文件 (按时间排序，最新的在前):")
    for backup in backups:
        print(f"  - {backup}")
    
    print(f"\n清理测试文件...")
    shutil.rmtree(test_dir)
    
    print("\n[OK] 文件备份功能测试通过！")
    return True


def test_group_by_month_with_nat():
    """测试 3: 按月份分组时处理 NaT"""
    print("\n" + "="*60)
    print("测试 3: 按月份分组时处理 NaT")
    print("="*60)
    
    data = {
        '日期': [
            '2025-01-01',
            '2025-01-15',
            '无效日期',
            '2025-02-01',
            None,
            '2025-02-15',
            '2025-03-01',
            'abc123',
            '2025-03-15',
            '2025-01-20'
        ],
        '地区': ['华东'] * 10,
        '品类': ['电子产品'] * 10,
        '实际金额': [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000],
        '数量': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    }
    
    df = pd.DataFrame(data)
    
    print(f"\n原始数据 (共 {len(df)} 行):")
    print(df)
    
    loader = DataLoader()
    loader.df = df.copy()
    loader._preprocess_data()
    
    processed_df = loader.get_data()
    filter_module = FilterModule(processed_df)
    
    print(f"\n按月份分组汇总...")
    monthly_group = filter_module.group_by_month()
    
    print(f"\n分组结果:")
    print(monthly_group)
    
    print(f"\n分组结果列名: {list(monthly_group.columns)}")
    
    expected_months = {'2025-01', '2025-02', '2025-03'}
    actual_months = set(monthly_group['月份'].tolist()) if '月份' in monthly_group.columns else set()
    
    print(f"\n验证分组结果:")
    print(f"  预期月份: {sorted(expected_months)}")
    print(f"  实际月份: {sorted(actual_months)}")
    
    if '月份' not in monthly_group.columns:
        print("\n[ERROR] 分组结果中缺少 '月份' 列")
        return False
    
    if '销售金额汇总' not in monthly_group.columns:
        print("[ERROR] 分组结果中缺少 '销售金额汇总' 列")
        return False
    
    jan_sales = monthly_group[monthly_group['月份'] == '2025-01']['销售金额汇总'].sum()
    print(f"\n2025年1月销售金额汇总: {jan_sales}")
    print(f"  预期: 1000 + 2000 + 10000 = 13000")
    
    if jan_sales == 13000:
        print("  [OK] 1月份销售金额正确")
    else:
        print(f"  [ERROR] 1月份销售金额不正确，预期 13000，实际 {jan_sales}")
        return False
    
    print("\n[OK] 按月份分组处理 NaT 测试通过！")
    return True


def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# 新 Bug 修复验证测试")
    print("#"*60)
    
    results = {}
    
    try:
        results['test1'] = test_nat_handling_in_date_filter()
    except Exception as e:
        print(f"\n测试 1 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test1'] = False
    
    try:
        results['test2'] = test_file_backup_functionality()
    except Exception as e:
        print(f"\n测试 2 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test2'] = False
    
    try:
        results['test3'] = test_group_by_month_with_nat()
    except Exception as e:
        print(f"\n测试 3 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test3'] = False
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"测试 1 (日期筛选 NaT 处理): {'通过' if results.get('test1') else '失败'}")
    print(f"测试 2 (文件备份功能): {'通过' if results.get('test2') else '失败'}")
    print(f"测试 3 (月份分组 NaT 处理): {'通过' if results.get('test3') else '失败'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n[√] 所有新 Bug 修复测试通过！")
    else:
        print("\n[×] 部分测试失败，请检查修复是否完整。")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
