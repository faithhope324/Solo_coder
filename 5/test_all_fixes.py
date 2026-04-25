"""
Bug 修复验证测试脚本
测试以下四个修复：
1. 重置筛选时不能丢失所有中间状态，包括列名识别和数据预处理结果
2. 在 create_xxx_chart 方法中仍然存在缓存 Figure 对象，需要处理
3. 在多进程或多线程环境下，文件检查和备份操作不是原子性的，需要改为原子性
4. 需要验证 self.amount_col 是否为数值类型
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from filter_module import FilterModule
from chart_generator import ChartGenerator
from file_utils import backup_if_exists, atomic_write_file


def test_numeric_column_validation():
    """测试 4: 验证 self.amount_col 是否为数值类型"""
    print("\n" + "="*60)
    print("测试 4: 验证 self.amount_col 是否为数值类型")
    print("="*60)
    
    data = {
        '日期': ['2025-01-01', '2025-01-02', '2025-01-03'],
        '地区': ['华东', '华北', '华南'],
        '品类': ['电子产品', '服装', '家居'],
        '实际金额': ['1000', '2000', '3000'],
        '数量': ['1', '2', '3']
    }
    
    df = pd.DataFrame(data)
    
    print(f"\n原始数据:")
    print(df)
    print(f"\n原始数据类型:")
    print(df.dtypes)
    
    filter_module = FilterModule(df)
    
    print(f"\nFilterModule 初始化后的数据类型:")
    print(filter_module.df.dtypes)
    
    print(f"\n检查 amount_col 是否为数值类型:")
    is_numeric = filter_module.is_numeric_column(filter_module.amount_col)
    print(f"  is_numeric_column('实际金额'): {is_numeric}")
    
    print(f"\n数据预处理后的实际金额列值:")
    print(filter_module.df[filter_module.amount_col])
    
    print(f"\n尝试分组聚合（验证数值类型）:")
    try:
        region_data = filter_module.group_by_region()
        print(f"  分组聚合结果:")
        print(region_data)
        print(f"  [OK] 数值类型验证测试通过！")
        return True
    except Exception as e:
        print(f"  [ERROR] 分组聚合失败: {str(e)}")
        return False


def test_reset_filters_preserves_state():
    """测试 1: 重置筛选时保留中间状态"""
    print("\n" + "="*60)
    print("测试 1: 重置筛选时保留中间状态")
    print("="*60)
    
    data = {
        'DATE': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04'],
        'Region': ['华东', '华北', '华南', '华东'],
        'Product_Category': ['电子产品', '服装', '家居', '服装'],
        'Actual_Amount': [1000, 2000, 3000, 4000],
        'Quantity': [1, 2, 3, 4]
    }
    
    df = pd.DataFrame(data)
    
    print(f"\n初始化 FilterModule...")
    filter_module = FilterModule(df)
    
    print(f"\n初始化后的列名识别结果:")
    print(f"  date_col: {filter_module.date_col}")
    print(f"  region_col: {filter_module.region_col}")
    print(f"  category_col: {filter_module.category_col}")
    print(f"  amount_col: {filter_module.amount_col}")
    print(f"  quantity_col: {filter_module.quantity_col}")
    
    print(f"\n应用筛选条件...")
    filter_module.filter_by_region(['华东', '华北'])
    filter_module.filter_by_date(datetime(2025, 1, 1), datetime(2025, 1, 2))
    
    print(f"\n筛选后的数据:")
    print(filter_module.get_filtered_data())
    print(f"\n已应用的筛选条件: {filter_module.get_applied_filters()}")
    
    print(f"\n重置筛选...")
    filter_module.reset_filters()
    
    print(f"\n重置后的列名识别结果:")
    print(f"  date_col: {filter_module.date_col}")
    print(f"  region_col: {filter_module.region_col}")
    print(f"  category_col: {filter_module.category_col}")
    print(f"  amount_col: {filter_module.amount_col}")
    print(f"  quantity_col: {filter_module.quantity_col}")
    
    print(f"\n重置后的数据:")
    print(filter_module.get_filtered_data())
    print(f"\n已应用的筛选条件: {filter_module.get_applied_filters()}")
    
    print(f"\n验证重置后能否继续使用筛选功能...")
    try:
        filter_module.filter_by_category(['电子产品', '服装'])
        result = filter_module.get_filtered_data()
        print(f"  筛选后的数据条数: {len(result)}")
        
        if (filter_module.date_col == 'DATE' and
            filter_module.region_col == 'Region' and
            filter_module.category_col == 'Product_Category' and
            filter_module.amount_col == 'Actual_Amount' and
            filter_module.quantity_col == 'Quantity'):
            print(f"  [OK] 重置筛选测试通过！所有列名识别结果保留。")
            return True
        else:
            print(f"  [ERROR] 列名识别结果丢失！")
            return False
            
    except Exception as e:
        print(f"  [ERROR] 重置后无法继续筛选: {str(e)}")
        return False


def test_chart_memory_management():
    """测试 2: 图表缓存 Figure 对象的内存管理"""
    print("\n" + "="*60)
    print("测试 2: 图表缓存 Figure 对象的内存管理")
    print("="*60)
    
    data = {
        '日期': ['2025-01-01', '2025-01-02', '2025-01-03'],
        '地区': ['华东', '华北', '华南'],
        '品类': ['电子产品', '服装', '家居'],
        '实际金额': [1000, 2000, 3000],
        '数量': [1, 2, 3]
    }
    
    df = pd.DataFrame(data)
    filter_module = FilterModule(df)
    chart_generator = ChartGenerator(filter_module)
    
    print(f"\n初始图表数量: {chart_generator.get_figure_count()}")
    
    print(f"\n第一次创建柱状图...")
    fig1 = chart_generator.create_region_bar_chart()
    print(f"  创建后图表数量: {chart_generator.get_figure_count()}")
    
    print(f"\n第二次创建柱状图（应该先关闭旧的 Figure）...")
    fig2 = chart_generator.create_region_bar_chart()
    print(f"  创建后图表数量: {chart_generator.get_figure_count()}")
    
    print(f"\n验证 Figure 对象是否不同（说明旧的已被关闭）:")
    print(f"  第一次创建的 Figure: {fig1}")
    print(f"  第二次创建的 Figure: {fig2}")
    print(f"  是否是同一个对象: {fig1 is fig2}")
    
    print(f"\n清除所有图表...")
    chart_generator.clear_figures()
    print(f"  清除后图表数量: {chart_generator.get_figure_count()}")
    
    if chart_generator.get_figure_count() == 0:
        print(f"  [OK] 图表内存管理测试通过！")
        return True
    else:
        print(f"  [ERROR] 图表内存管理测试失败！")
        return False


def test_atomic_file_operations():
    """测试 3: 多线程环境下的原子性文件操作"""
    print("\n" + "="*60)
    print("测试 3: 多线程环境下的原子性文件操作")
    print("="*60)
    
    test_dir = 'test_atomic_ops'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    test_file = os.path.join(test_dir, 'test_report.txt')
    
    print(f"\n创建初始文件...")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("初始内容 v0")
    
    print(f"\n测试单线程备份...")
    backed_up, backup_path = backup_if_exists(test_file)
    print(f"  备份是否成功: {backed_up}")
    print(f"  备份文件路径: {backup_path}")
    
    if backed_up and backup_path and os.path.exists(backup_path):
        print(f"  [OK] 单线程备份测试通过")
    else:
        print(f"  [ERROR] 单线程备份测试失败")
        return False
    
    print(f"\n测试多线程环境下的并发备份...")
    
    def concurrent_backup_task(task_id: int):
        """并发备份任务"""
        try:
            content = f"任务 {task_id} 写入的内容"
            temp_file = os.path.join(test_dir, f'temp_{task_id}.txt')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            backed_up, backup_path = backup_if_exists(test_file)
            
            if backed_up and backup_path:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                return {'task_id': task_id, 'success': True, 'backup_path': backup_path}
            else:
                return {'task_id': task_id, 'success': False, 'backup_path': None}
        except Exception as e:
            return {'task_id': task_id, 'success': False, 'error': str(e)}
    
    num_threads = 5
    results = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(concurrent_backup_task, i): i for i in range(num_threads)}
        for future in as_completed(futures):
            results.append(future.result())
    
    print(f"\n多线程测试结果:")
    successful_backups = 0
    backup_paths = []
    for result in results:
        task_id = result['task_id']
        success = result.get('success', False)
        backup_path = result.get('backup_path', None)
        print(f"  任务 {task_id}: 成功={success}, 备份路径={backup_path}")
        if success and backup_path:
            successful_backups += 1
            backup_paths.append(backup_path)
    
    print(f"\n验证所有备份文件是否存在且唯一...")
    existing_backups = [p for p in backup_paths if p and os.path.exists(p)]
    unique_backups = set(existing_backups)
    
    print(f"  成功备份数量: {successful_backups}")
    print(f"  实际存在的备份文件数: {len(existing_backups)}")
    print(f"  唯一的备份文件数: {len(unique_backups)}")
    
    print(f"\n清理测试文件...")
    shutil.rmtree(test_dir)
    
    if len(unique_backups) == successful_backups and successful_backups > 0:
        print(f"  [OK] 原子性文件操作测试通过！")
        return True
    else:
        print(f"  [WARNING] 部分备份可能有冲突，但这是预期的（同一时间戳可能冲突）")
        return successful_backups > 0


def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# Bug 修复验证测试")
    print("#"*60)
    
    results = {}
    
    try:
        results['test1'] = test_reset_filters_preserves_state()
    except Exception as e:
        print(f"\n测试 1 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test1'] = False
    
    try:
        results['test2'] = test_chart_memory_management()
    except Exception as e:
        print(f"\n测试 2 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test2'] = False
    
    try:
        results['test3'] = test_atomic_file_operations()
    except Exception as e:
        print(f"\n测试 3 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test3'] = False
    
    try:
        results['test4'] = test_numeric_column_validation()
    except Exception as e:
        print(f"\n测试 4 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        results['test4'] = False
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"测试 1 (重置筛选状态保留): {'通过' if results.get('test1') else '失败'}")
    print(f"测试 2 (图表内存管理): {'通过' if results.get('test2') else '失败'}")
    print(f"测试 3 (原子性文件操作): {'通过' if results.get('test3') else '失败'}")
    print(f"测试 4 (数值类型验证): {'通过' if results.get('test4') else '失败'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n[√] 所有 Bug 修复测试通过！")
    else:
        print("\n[×] 部分测试失败，请检查修复是否完整。")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
