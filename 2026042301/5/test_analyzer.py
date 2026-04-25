"""
销售数据多维分析工具测试脚本
测试核心功能：数据加载、筛选、Excel 生成
"""

import os
import sys
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from filter_module import FilterModule
from excel_generator import ExcelGenerator


def test_data_loader():
    """测试数据加载模块"""
    print("\n" + "="*60)
    print("测试数据加载模块")
    print("="*60)
    
    loader = DataLoader()
    
    # 测试生成示例数据
    print("\n1. 测试生成示例数据...")
    df = loader.load_sample_data(n_records=500)
    print(f"   [OK] 成功生成 {len(df)} 条数据")
    
    # 测试获取筛选选项
    print("\n2. 测试获取筛选选项...")
    filter_options = loader.get_filter_options()
    print(f"   [OK] 可用地区: {filter_options['regions']}")
    print(f"   [OK] 可用品类: {filter_options['categories']}")
    print(f"   [OK] 日期范围: {filter_options['date_range']}")
    
    # 测试数据列
    print("\n3. 测试数据列...")
    print(f"   [OK] 列名: {list(df.columns)}")
    print(f"   [OK] 数据类型:\n{df.dtypes}")
    
    return loader


def test_filter_module(loader):
    """测试筛选模块"""
    print("\n" + "="*60)
    print("测试筛选模块")
    print("="*60)
    
    df = loader.get_data()
    filter_module = FilterModule(df)
    
    # 测试初始状态
    print("\n1. 测试初始数据...")
    filtered_df = filter_module.get_filtered_data()
    print(f"   [OK] 初始数据条数: {len(filtered_df)}")
    
    # 测试按地区筛选
    print("\n2. 测试按地区筛选...")
    filter_module.filter_by_region(['华东', '华北'])
    filtered_df = filter_module.get_filtered_data()
    print(f"   [OK] 筛选后数据条数: {len(filtered_df)}")
    
    filters = filter_module.get_applied_filters()
    print(f"   [OK] 应用的筛选: {filters}")
    
    # 测试按品类筛选
    print("\n3. 测试按品类筛选...")
    filter_module.filter_by_category(['电子产品', '服装'])
    filtered_df = filter_module.get_filtered_data()
    print(f"   [OK] 筛选后数据条数: {len(filtered_df)}")
    
    filters = filter_module.get_applied_filters()
    print(f"   [OK] 应用的筛选: {filters}")
    
    # 测试重置筛选
    print("\n4. 测试重置筛选...")
    filter_module.reset_filters()
    filtered_df = filter_module.get_filtered_data()
    print(f"   [OK] 重置后数据条数: {len(filtered_df)}")
    
    # 测试分组功能
    print("\n5. 测试分组汇总...")
    
    region_summary = filter_module.group_by_region()
    if not region_summary.empty:
        print(f"   [OK] 地区分组结果:\n{region_summary}")
    
    category_summary = filter_module.group_by_category()
    if not category_summary.empty:
        print(f"\n   [OK] 品类分组结果:\n{category_summary}")
    
    monthly_summary = filter_module.group_by_month()
    if not monthly_summary.empty:
        print(f"\n   [OK] 月度分组结果 (前5行):\n{monthly_summary.head()}")
    
    cross_summary = filter_module.group_by_region_category()
    if not cross_summary.empty:
        print(f"\n   [OK] 交叉分组结果 (前5行):\n{cross_summary.head()}")
    
    # 测试汇总统计
    print("\n6. 测试汇总统计...")
    summary = filter_module.get_summary_statistics()
    print(f"   [OK] 汇总统计:")
    for key, value in summary.items():
        if isinstance(value, (int, float)):
            print(f"      {key}: {value:,.2f}" if isinstance(value, float) else f"      {key}: {value:,}")
        else:
            print(f"      {key}: {value}")
    
    return filter_module


def test_excel_generator(filter_module):
    """测试 Excel 生成模块"""
    print("\n" + "="*60)
    print("测试 Excel 生成模块")
    print("="*60)
    
    excel_gen = ExcelGenerator(filter_module)
    
    # 创建输出目录
    output_dir = 'test_output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 测试生成汇总 Excel
    print("\n1. 测试生成汇总 Excel...")
    output_path = os.path.join(output_dir, 'test_sales_report.xlsx')
    
    try:
        excel_gen.generate_summary_excel(
            output_path=output_path,
            include_raw_data=True
        )
        print(f"   [OK] Excel 报告已生成: {output_path}")
        print(f"   [OK] 文件大小: {os.path.getsize(output_path):,} 字节")
    except Exception as e:
        print(f"   [ERROR] 生成失败: {str(e)}")
    
    # 测试生成对比报告
    print("\n2. 测试生成地区对比报告...")
    comparison_path = os.path.join(output_dir, 'test_region_comparison.xlsx')
    
    try:
        excel_gen.generate_comparison_report(
            output_path=comparison_path,
            comparison_type='region'
        )
        print(f"   [OK] 地区对比报告已生成: {comparison_path}")
        print(f"   [OK] 文件大小: {os.path.getsize(comparison_path):,} 字节")
    except Exception as e:
        print(f"   [ERROR] 生成失败: {str(e)}")
    
    print("\n3. 测试生成品类对比报告...")
    comparison_path = os.path.join(output_dir, 'test_category_comparison.xlsx')
    
    try:
        excel_gen.generate_comparison_report(
            output_path=comparison_path,
            comparison_type='category'
        )
        print(f"   [OK] 品类对比报告已生成: {comparison_path}")
        print(f"   [OK] 文件大小: {os.path.getsize(comparison_path):,} 字节")
    except Exception as e:
        print(f"   [ERROR] 生成失败: {str(e)}")


def test_data_export(loader):
    """测试数据导出"""
    print("\n" + "="*60)
    print("测试数据导出")
    print("="*60)
    
    df = loader.get_data()
    
    output_dir = 'test_output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 测试导出 CSV
    print("\n1. 测试导出 CSV...")
    csv_path = os.path.join(output_dir, 'test_export.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"   [OK] CSV 文件已导出: {csv_path}")
    print(f"   [OK] 文件大小: {os.path.getsize(csv_path):,} 字节")
    
    # 测试导出 Excel
    print("\n2. 测试导出 Excel...")
    excel_path = os.path.join(output_dir, 'test_export.xlsx')
    df.to_excel(excel_path, index=False, sheet_name='销售数据')
    print(f"   [OK] Excel 文件已导出: {excel_path}")
    print(f"   [OK] 文件大小: {os.path.getsize(excel_path):,} 字节")


def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# 销售数据多维分析工具 - 功能测试")
    print("#"*60)
    
    try:
        # 测试数据加载
        loader = test_data_loader()
        
        # 测试筛选模块
        filter_module = test_filter_module(loader)
        
        # 测试 Excel 生成
        test_excel_generator(filter_module)
        
        # 测试数据导出
        test_data_export(loader)
        
        print("\n" + "="*60)
        print("所有测试完成！")
        print("="*60)
        print("\n生成的文件位于: test_output/ 目录")
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
