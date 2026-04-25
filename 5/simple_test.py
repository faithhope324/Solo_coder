"""简单测试脚本"""
import pandas as pd
import sys

sys.path.insert(0, '.')

from data_loader import DataLoader
from filter_module import FilterModule

print("="*60)
print("测试 1: 列名标准化和匹配")
print("="*60)

test_df = pd.DataFrame({
    '  DATE  ': ['2025-01-01', '2025-01-02', '2025-01-03'],
    'Region_': ['华东', '华北', '华南'],
    'Product-Category': ['电子产品', '服装', '家居'],
    'Actual.Amount': [1000, 2000, 3000],
    'Sales Quantity': [1, 2, 3]
})

print(f"\n原始列名: {list(test_df.columns)}")

filter_module = FilterModule(test_df)

print(f"\n识别结果:")
print(f"  日期列: {filter_module.date_col}")
print(f"  地区列: {filter_module.region_col}")
print(f"  品类列: {filter_module.category_col}")
print(f"  金额列: {filter_module.amount_col}")
print(f"  数量列: {filter_module.quantity_col}")

all_found = (
    filter_module.date_col is not None and
    filter_module.region_col is not None and
    filter_module.category_col is not None and
    filter_module.amount_col is not None and
    filter_module.quantity_col is not None
)

print(f"\n列名匹配测试: {'通过' if all_found else '失败'}")

print("\n" + "="*60)
print("测试 2: 聚合列名（避免冲突）")
print("="*60)

region_group = filter_module.group_by_region()
print(f"\n按地区分组后的列名: {list(region_group.columns)}")
print(f"\n数据:")
print(region_group)

conflict_names = ['sum', 'mean', 'count', 'Region_', 'Product-Category']
has_conflict = any(col in conflict_names for col in region_group.columns)
print(f"\n聚合列名冲突测试: {'失败' if has_conflict else '通过'}")

print("\n" + "="*60)
print("测试 3: 日期解析错误处理")
print("="*60)

date_df = pd.DataFrame({
    '日期': ['2025-01-01', '无效日期', '2025/01/03', None, '2025年01月05日', 'abc123'],
    '地区': ['华东', '华北', '华南', '华东', '华北', '华南'],
    '实际金额': [100, 200, 300, 400, 500, 600]
})

print(f"\n原始日期数据: {date_df['日期'].tolist()}")

loader = DataLoader()
loader.df = date_df.copy()
loader._preprocess_data()

processed_df = loader.get_data()
print(f"\n处理后的日期数据:")
print(processed_df['日期'].tolist())

date_errors = loader.get_date_parse_errors()
print(f"\n日期解析错误信息:")
print(f"  总记录数: {date_errors.get('total_count', 0)}")
print(f"  成功解析: {date_errors.get('success_count', 0)}")
print(f"  解析失败: {date_errors.get('failed_count', 0)}")

if date_errors.get('failed_values_sample'):
    print(f"  失败值示例: {date_errors['failed_values_sample']}")

valid_dates = processed_df['日期'].dropna()
print(f"\n有效日期数量: {len(valid_dates)}")

print("\n" + "="*60)
print("测试结果汇总")
print("="*60)
print(f"1. 列名匹配测试: {'通过' if all_found else '失败'}")
print(f"2. 聚合列名冲突测试: {'通过' if not has_conflict else '失败'}")
print(f"3. 日期解析错误处理: 已记录 {date_errors.get('failed_count', 0)} 个失败值")

all_passed = all_found and not has_conflict
if all_passed:
    print("\n[√] 所有核心测试通过！")
else:
    print("\n[×] 部分测试失败")
