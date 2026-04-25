"""
示例数据生成脚本
用于生成测试用的销售数据
"""

from data_loader import DataLoader
import os


def generate_sample_files(output_dir: str = 'data', sample_size: int = 2000):
    """生成示例数据文件
    
    Args:
        output_dir: 输出目录
        sample_size: 数据量大小
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    loader = DataLoader()
    
    print(f"正在生成 {sample_size} 条示例销售数据...")
    df = loader.load_sample_data(n_records=sample_size)
    
    # 保存为 CSV
    csv_path = os.path.join(output_dir, 'sales_data.csv')
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"CSV 文件已保存: {csv_path}")
    
    # 保存为 Excel
    excel_path = os.path.join(output_dir, 'sales_data.xlsx')
    df.to_excel(excel_path, index=False, sheet_name='销售数据')
    print(f"Excel 文件已保存: {excel_path}")
    
    # 显示数据信息
    print("\n" + "="*60)
    print("示例数据信息")
    print("="*60)
    print(f"数据总行数: {len(df):,}")
    print(f"数据总列数: {len(df.columns)}")
    
    print(f"\n列名:")
    for col in df.columns:
        print(f"  - {col}")
    
    print(f"\n数据预览 (前 5 行):")
    print(df.head())
    
    print(f"\n数据统计:")
    print(df.describe())
    
    print("\n" + "="*60)
    print("示例数据生成完成！")
    print("="*60)
    
    return df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='生成示例销售数据')
    parser.add_argument('-n', '--size', type=int, default=2000, help='数据量大小 (默认 2000)')
    parser.add_argument('-o', '--output', type=str, default='data', help='输出目录 (默认 data)')
    
    args = parser.parse_args()
    
    generate_sample_files(output_dir=args.output, sample_size=args.size)
