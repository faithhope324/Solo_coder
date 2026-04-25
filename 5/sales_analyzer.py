import pandas as pd
from datetime import datetime
import os
import sys

from data_loader import DataLoader
from filter_module import FilterModule
from chart_generator import ChartGenerator
from excel_generator import ExcelGenerator


class SalesAnalyzer:
    """销售数据多维分析工具主类"""
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.filter_module = None
        self.chart_generator = None
        self.excel_generator = None
        self.data_loaded = False
    
    def load_data(self, file_path: str = None, use_sample: bool = False, sample_size: int = 1000) -> bool:
        """加载数据
        
        Args:
            file_path: 数据文件路径（CSV 或 Excel）
            use_sample: 是否使用示例数据
            sample_size: 示例数据大小
        
        Returns:
            是否加载成功
        """
        try:
            if use_sample:
                print(f"正在生成 {sample_size} 条示例销售数据...")
                self.data_loader.load_sample_data(n_records=sample_size)
                print("示例数据生成成功！")
            else:
                if not file_path or not os.path.exists(file_path):
                    print(f"错误：文件不存在 - {file_path}")
                    return False
                
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == '.csv':
                    print(f"正在从 CSV 文件加载数据: {file_path}")
                    self.data_loader.load_from_csv(file_path)
                elif ext in ['.xlsx', '.xls']:
                    print(f"正在从 Excel 文件加载数据: {file_path}")
                    self.data_loader.load_from_excel(file_path)
                else:
                    print(f"错误：不支持的文件格式 - {ext}")
                    return False
                
                print("数据加载成功！")
            
            self.filter_module = FilterModule(self.data_loader.get_data())
            self.chart_generator = ChartGenerator(self.filter_module)
            self.excel_generator = ExcelGenerator(self.filter_module)
            self.data_loaded = True
            
            return True
            
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            return False
    
    def show_data_info(self):
        """显示数据基本信息"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        df = self.data_loader.get_data()
        filter_options = self.data_loader.get_filter_options()
        
        print("\n" + "="*60)
        print("数据基本信息")
        print("="*60)
        
        print(f"\n数据总行数: {len(df):,}")
        print(f"数据总列数: {len(df.columns)}")
        
        print(f"\n列名:")
        for col in df.columns:
            print(f"  - {col}")
        
        print(f"\n可用筛选选项:")
        if filter_options['regions']:
            print(f"  地区 ({len(filter_options['regions'])} 个):")
            for region in filter_options['regions']:
                print(f"    - {region}")
        
        if filter_options['categories']:
            print(f"\n  品类 ({len(filter_options['categories'])} 个):")
            for category in filter_options['categories']:
                print(f"    - {category}")
        
        if filter_options['date_range'][0] and filter_options['date_range'][1]:
            print(f"\n  日期范围:")
            print(f"    开始: {filter_options['date_range'][0].strftime('%Y-%m-%d')}")
            print(f"    结束: {filter_options['date_range'][1].strftime('%Y-%m-%d')}")
        
        print("\n" + "="*60)
    
    def filter_by_region(self, regions: list):
        """按地区筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        self.filter_module.filter_by_region(regions)
        print(f"已应用地区筛选: {', '.join(regions)}")
    
    def filter_by_category(self, categories: list):
        """按品类筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        self.filter_module.filter_by_category(categories)
        print(f"已应用品类筛选: {', '.join(categories)}")
    
    def filter_by_date_range(self, start_date: str, end_date: str):
        """按日期范围筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            self.filter_module.filter_by_date(start, end)
            print(f"已应用日期筛选: {start_date} 至 {end_date}")
        except ValueError as e:
            print(f"日期格式错误: {str(e)}")
            print("请使用格式: YYYY-MM-DD")
    
    def filter_by_month(self, year: int, month: int):
        """按月份筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        self.filter_module.filter_by_month(year, month)
        print(f"已应用月份筛选: {year}年{month}月")
    
    def filter_by_quarter(self, year: int, quarter: int):
        """按季度筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        self.filter_module.filter_by_quarter(year, quarter)
        print(f"已应用季度筛选: {year}年第{quarter}季度")
    
    def reset_filters(self):
        """重置所有筛选"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        self.filter_module.reset_filters()
        print("已重置所有筛选条件")
    
    def show_current_filters(self):
        """显示当前筛选条件"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        filters = self.filter_module.get_applied_filters()
        
        print("\n" + "-"*50)
        print("当前筛选条件:")
        print("-"*50)
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    print(f"  {key}: {', '.join(map(str, value))}")
                else:
                    print(f"  {key}: {value}")
        else:
            print("  未应用任何筛选条件")
        
        print("-"*50)
    
    def show_summary_statistics(self):
        """显示汇总统计信息"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        summary = self.filter_module.get_summary_statistics()
        
        print("\n" + "="*60)
        print("销售数据汇总统计")
        print("="*60)
        
        print(f"\n  总记录数: {summary['总记录数']:,}")
        print(f"  总销售金额: ¥{summary['总销售金额']:,.2f}")
        print(f"  平均客单价: ¥{summary['平均客单价']:,.2f}")
        print(f"  总销售数量: {summary['总销售数量']:,}")
        print(f"  涉及地区数: {summary['涉及地区数']}")
        print(f"  涉及品类数: {summary['涉及品类数']}")
        
        print("\n" + "="*60)
    
    def generate_charts(
        self,
        output_dir: str = None,
        show: bool = False,
        auto_clear_memory: bool = True,
        backup: bool = True,
        backup_dir: str = None
    ):
        """生成图表
        
        Args:
            output_dir: 输出目录（如果不提供则不保存）
            show: 是否显示图表
            auto_clear_memory: 生成完成后是否自动释放内存
            backup: 是否在文件已存在时进行备份
            backup_dir: 备份文件存放目录（可选）
        """
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        try:
            print("\n正在生成图表...")
            
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"创建输出目录: {output_dir}")
            
            if backup and output_dir:
                try:
                    from file_utils import backup_if_exists
                except ImportError:
                    backup = False
            
            def get_save_path(filename: str) -> Optional[str]:
                if not output_dir:
                    return None
                
                full_path = os.path.join(output_dir, filename)
                
                if backup and os.path.exists(full_path):
                    try:
                        backed_up, backup_path = backup_if_exists(full_path, backup_dir)
                        if backed_up and backup_path:
                            print(f"  [备份] 原文件已备份到: {os.path.basename(backup_path)}")
                    except:
                        pass
                
                return full_path
            
            # 生成地区销售对比图
            try:
                region_path = get_save_path('地区销售对比.png')
                self.chart_generator.create_region_bar_chart(output_path=region_path)
                if region_path:
                    print(f"  [OK] 地区销售对比图已保存: {region_path}")
            except Exception as e:
                print(f"  [ERROR] 地区销售对比图生成失败: {str(e)}")
            
            # 生成品类销售占比图
            try:
                category_pie_path = get_save_path('品类销售占比.png')
                self.chart_generator.create_category_pie_chart(output_path=category_pie_path)
                if category_pie_path:
                    print(f"  [OK] 品类销售占比图已保存: {category_pie_path}")
            except Exception as e:
                print(f"  [ERROR] 品类销售占比图生成失败: {str(e)}")
            
            # 生成月度销售趋势图
            try:
                monthly_path = get_save_path('月度销售趋势.png')
                self.chart_generator.create_monthly_trend_chart(output_path=monthly_path)
                if monthly_path:
                    print(f"  [OK] 月度销售趋势图已保存: {monthly_path}")
            except Exception as e:
                print(f"  [ERROR] 月度销售趋势图生成失败: {str(e)}")
            
            # 生成地区品类热力图
            try:
                heatmap_path = get_save_path('地区品类热力图.png')
                self.chart_generator.create_region_category_heatmap(output_path=heatmap_path)
                if heatmap_path:
                    print(f"  [OK] 地区品类热力图已保存: {heatmap_path}")
            except Exception as e:
                print(f"  [ERROR] 地区品类热力图生成失败: {str(e)}")
            
            # 生成品类销售排行图
            try:
                category_bar_path = get_save_path('品类销售排行.png')
                self.chart_generator.create_category_bar_chart(output_path=category_bar_path)
                if category_bar_path:
                    print(f"  [OK] 品类销售排行图已保存: {category_bar_path}")
            except Exception as e:
                print(f"  [ERROR] 品类销售排行图生成失败: {str(e)}")
            
            # 生成综合分析仪表板
            try:
                dashboard_path = get_save_path('综合分析仪表板.png')
                self.chart_generator.create_combined_dashboard(output_path=dashboard_path)
                if dashboard_path:
                    print(f"  [OK] 综合分析仪表板已保存: {dashboard_path}")
            except Exception as e:
                print(f"  [ERROR] 综合分析仪表板生成失败: {str(e)}")
            
            print("\n图表生成完成！")
            
            if show:
                self.chart_generator.show_all_charts()
            
            if auto_clear_memory:
                self.chart_generator.clear_figures()
                print(f"已释放图表内存，当前图表数量: {self.chart_generator.get_figure_count()}")
                
        except Exception as e:
            print(f"图表生成失败: {str(e)}")
    
    def generate_excel_report(
        self,
        output_path: str,
        include_raw_data: bool = True,
        comparison_type: str = None,
        backup: bool = True,
        backup_dir: str = None
    ):
        """生成 Excel 汇总报告（支持自动备份）
        
        Args:
            output_path: 输出文件路径
            include_raw_data: 是否包含原始数据
            comparison_type: 对比类型（'region' 或 'category'，可选）
            backup: 是否在文件已存在时进行备份
            backup_dir: 备份文件存放目录（可选）
        """
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        try:
            print(f"\n正在生成 Excel 报告: {output_path}")
            
            if backup and os.path.exists(output_path):
                try:
                    from file_utils import backup_if_exists
                    backed_up, backup_path = backup_if_exists(output_path, backup_dir)
                    if backed_up and backup_path:
                        print(f"  [备份] 原文件已备份到: {os.path.basename(backup_path)}")
                except ImportError:
                    pass
                except Exception:
                    pass
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 生成主报告
            actual_path = self.excel_generator.generate_summary_excel(
                output_path=output_path,
                include_raw_data=include_raw_data,
                backup=backup,
                backup_dir=backup_dir
            )
            
            last_backup = self.excel_generator.get_last_backup_path()
            if last_backup:
                print(f"  [OK] 主报告已生成，原文件已备份")
            else:
                print(f"  [OK] 主报告已生成")
            
            # 如果指定了对比类型，生成对比报告
            if comparison_type in ['region', 'category']:
                base_name, ext = os.path.splitext(output_path)
                comparison_path = f"{base_name}_对比分析{ext}"
                
                self.excel_generator.generate_comparison_report(
                    output_path=comparison_path,
                    comparison_type=comparison_type,
                    backup=backup,
                    backup_dir=backup_dir
                )
                
                print(f"  [OK] 对比分析报告已生成: {comparison_path}")
            
            print("\nExcel 报告生成完成！")
            
        except Exception as e:
            print(f"Excel 报告生成失败: {str(e)}")
    
    def export_filtered_data(
        self,
        output_path: str,
        backup: bool = True,
        backup_dir: str = None
    ):
        """导出筛选后的数据（支持自动备份）
        
        Args:
            output_path: 输出文件路径
            backup: 是否在文件已存在时进行备份
            backup_dir: 备份文件存放目录（可选）
        """
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        try:
            df = self.filter_module.get_filtered_data()
            
            if df.empty:
                print("错误：筛选后的数据为空")
                return
            
            ext = os.path.splitext(output_path)[1].lower()
            
            # 备份已存在的文件
            if backup and os.path.exists(output_path):
                try:
                    from file_utils import backup_if_exists
                    backed_up, backup_path = backup_if_exists(output_path, backup_dir)
                    if backed_up and backup_path:
                        print(f"  [备份] 原文件已备份到: {os.path.basename(backup_path)}")
                except ImportError:
                    pass
                except Exception:
                    pass
            
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            if ext == '.csv':
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
            elif ext in ['.xlsx', '.xls']:
                df.to_excel(output_path, index=False)
            else:
                print(f"错误：不支持的导出格式 - {ext}")
                return
            
            print(f"[OK] 数据已成功导出到: {output_path}")
            print(f"     共导出 {len(df):,} 条记录")
            
        except Exception as e:
            print(f"数据导出失败: {str(e)}")
    
    def run_interactive_mode(self):
        """运行交互模式"""
        print("\n" + "="*60)
        print("欢迎使用销售数据多维分析工具")
        print("="*60)
        
        while True:
            print("\n" + "-"*60)
            print("主菜单:")
            print("-"*60)
            print("  1. 加载数据")
            print("  2. 查看数据信息")
            print("  3. 设置筛选条件")
            print("  4. 查看当前筛选条件")
            print("  5. 重置筛选条件")
            print("  6. 查看汇总统计")
            print("  7. 生成图表")
            print("  8. 生成 Excel 报告")
            print("  9. 导出筛选后的数据")
            print("  0. 退出")
            print("-"*60)
            
            choice = input("\n请选择操作 (0-9): ").strip()
            
            if choice == '0':
                print("\n感谢使用，再见！")
                break
            
            elif choice == '1':
                self._interactive_load_data()
            
            elif choice == '2':
                self.show_data_info()
            
            elif choice == '3':
                self._interactive_set_filters()
            
            elif choice == '4':
                self.show_current_filters()
            
            elif choice == '5':
                self.reset_filters()
            
            elif choice == '6':
                self.show_summary_statistics()
            
            elif choice == '7':
                self._interactive_generate_charts()
            
            elif choice == '8':
                self._interactive_generate_excel()
            
            elif choice == '9':
                self._interactive_export_data()
            
            else:
                print("无效的选择，请重新输入")
    
    def _interactive_load_data(self):
        """交互模式加载数据"""
        print("\n数据加载选项:")
        print("  1. 使用示例数据")
        print("  2. 从文件加载 (CSV/Excel)")
        
        sub_choice = input("请选择 (1-2): ").strip()
        
        if sub_choice == '1':
            try:
                size_input = input("请输入示例数据大小 (默认 1000): ").strip()
                size = int(size_input) if size_input else 1000
                self.load_data(use_sample=True, sample_size=size)
            except ValueError:
                print("无效的数值，使用默认大小 1000")
                self.load_data(use_sample=True)
        
        elif sub_choice == '2':
            file_path = input("请输入文件路径: ").strip()
            if file_path:
                self.load_data(file_path=file_path)
        else:
            print("无效的选择")
    
    def _interactive_set_filters(self):
        """交互模式设置筛选条件"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        print("\n筛选条件设置:")
        print("  1. 按地区筛选")
        print("  2. 按品类筛选")
        print("  3. 按日期范围筛选")
        print("  4. 按月份筛选")
        print("  5. 按季度筛选")
        
        sub_choice = input("请选择 (1-5): ").strip()
        
        filter_options = self.data_loader.get_filter_options()
        
        if sub_choice == '1':
            print(f"\n可用地区: {', '.join(filter_options['regions'])}")
            regions_input = input("请输入要筛选的地区（多个用逗号分隔）: ").strip()
            if regions_input:
                regions = [r.strip() for r in regions_input.split(',')]
                self.filter_by_region(regions)
        
        elif sub_choice == '2':
            print(f"\n可用品类: {', '.join(filter_options['categories'])}")
            categories_input = input("请输入要筛选的品类（多个用逗号分隔）: ").strip()
            if categories_input:
                categories = [c.strip() for c in categories_input.split(',')]
                self.filter_by_category(categories)
        
        elif sub_choice == '3':
            start_date = input("请输入开始日期 (YYYY-MM-DD): ").strip()
            end_date = input("请输入结束日期 (YYYY-MM-DD): ").strip()
            if start_date and end_date:
                self.filter_by_date_range(start_date, end_date)
        
        elif sub_choice == '4':
            try:
                year = int(input("请输入年份: ").strip())
                month = int(input("请输入月份 (1-12): ").strip())
                self.filter_by_month(year, month)
            except ValueError:
                print("无效的输入")
        
        elif sub_choice == '5':
            try:
                year = int(input("请输入年份: ").strip())
                quarter = int(input("请输入季度 (1-4): ").strip())
                self.filter_by_quarter(year, quarter)
            except ValueError:
                print("无效的输入")
        
        else:
            print("无效的选择")
    
    def _interactive_generate_charts(self):
        """交互模式生成图表"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        print("\n图表生成选项:")
        print("  1. 仅显示图表")
        print("  2. 仅保存图表到文件")
        print("  3. 显示并保存图表")
        
        sub_choice = input("请选择 (1-3): ").strip()
        
        show = False
        save = False
        output_dir = None
        
        if sub_choice in ['1', '3']:
            show = True
        
        if sub_choice in ['2', '3']:
            save = True
            output_dir = input("请输入输出目录 (默认 charts): ").strip()
            if not output_dir:
                output_dir = 'charts'
        
        self.generate_charts(output_dir=output_dir if save else None, show=show)
    
    def _interactive_generate_excel(self):
        """交互模式生成 Excel 报告"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        output_path = input("请输入输出文件路径 (默认 output/sales_report.xlsx): ").strip()
        if not output_path:
            output_path = 'output/sales_report.xlsx'
        
        include_raw = input("是否包含原始数据? (y/n, 默认 y): ").strip().lower()
        include_raw_data = include_raw != 'n'
        
        print("\n对比分析选项:")
        print("  1. 不生成对比分析")
        print("  2. 按地区对比")
        print("  3. 按品类对比")
        
        comp_choice = input("请选择 (1-3, 默认 1): ").strip()
        
        comparison_type = None
        if comp_choice == '2':
            comparison_type = 'region'
        elif comp_choice == '3':
            comparison_type = 'category'
        
        self.generate_excel_report(
            output_path=output_path,
            include_raw_data=include_raw_data,
            comparison_type=comparison_type
        )
    
    def _interactive_export_data(self):
        """交互模式导出数据"""
        if not self.data_loaded:
            print("错误：数据尚未加载")
            return
        
        output_path = input("请输入输出文件路径 (默认 output/filtered_data.xlsx): ").strip()
        if not output_path:
            output_path = 'output/filtered_data.xlsx'
        
        self.export_filtered_data(output_path)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='销售数据多维分析工具 - 支持按地区/品类/时间筛选，自动生成图表与汇总 Excel'
    )
    
    parser.add_argument('-i', '--interactive', action='store_true', help='运行交互模式')
    parser.add_argument('-f', '--file', type=str, help='数据文件路径 (CSV 或 Excel)')
    parser.add_argument('-s', '--sample', action='store_true', help='使用示例数据')
    parser.add_argument('-n', '--sample-size', type=int, default=1000, help='示例数据大小 (默认 1000)')
    parser.add_argument('-r', '--regions', type=str, help='地区筛选（多个用逗号分隔）')
    parser.add_argument('-c', '--categories', type=str, help='品类筛选（多个用逗号分隔）')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--month', type=str, help='月份筛选 (格式: YYYY-MM，如 2025-01)')
    parser.add_argument('--quarter', type=str, help='季度筛选 (格式: YYYY-QN，如 2025-Q1)')
    parser.add_argument('--charts', type=str, help='图表输出目录')
    parser.add_argument('--excel', type=str, help='Excel 报告输出路径')
    parser.add_argument('--no-raw-data', action='store_true', help='Excel 报告不包含原始数据')
    parser.add_argument('--export', type=str, help='导出筛选后的数据路径')
    
    args = parser.parse_args()
    
    analyzer = SalesAnalyzer()
    
    # 交互模式
    if args.interactive or len(sys.argv) == 1:
        analyzer.run_interactive_mode()
        return
    
    # 命令行模式
    # 1. 加载数据
    loaded = False
    if args.sample:
        loaded = analyzer.load_data(use_sample=True, sample_size=args.sample_size)
    elif args.file:
        loaded = analyzer.load_data(file_path=args.file)
    else:
        print("错误：请指定数据来源 (-s 使用示例数据 或 -f 指定文件)")
        parser.print_help()
        return
    
    if not loaded:
        return
    
    # 2. 应用筛选条件
    if args.regions:
        regions = [r.strip() for r in args.regions.split(',')]
        analyzer.filter_by_region(regions)
    
    if args.categories:
        categories = [c.strip() for c in args.categories.split(',')]
        analyzer.filter_by_category(categories)
    
    if args.start_date and args.end_date:
        analyzer.filter_by_date_range(args.start_date, args.end_date)
    
    if args.month:
        try:
            year, month = map(int, args.month.split('-'))
            analyzer.filter_by_month(year, month)
        except ValueError:
            print(f"错误：无效的月份格式 {args.month}，请使用格式 YYYY-MM")
    
    if args.quarter:
        try:
            parts = args.quarter.split('-')
            year = int(parts[0])
            quarter = int(parts[1].upper().replace('Q', ''))
            analyzer.filter_by_quarter(year, quarter)
        except (ValueError, IndexError):
            print(f"错误：无效的季度格式 {args.quarter}，请使用格式 YYYY-QN")
    
    # 3. 显示信息
    analyzer.show_data_info()
    analyzer.show_current_filters()
    analyzer.show_summary_statistics()
    
    # 4. 生成图表
    if args.charts:
        analyzer.generate_charts(output_dir=args.charts)
    
    # 5. 生成 Excel 报告
    if args.excel:
        analyzer.generate_excel_report(
            output_path=args.excel,
            include_raw_data=not args.no_raw_data
        )
    
    # 6. 导出数据
    if args.export:
        analyzer.export_filtered_data(args.export)


if __name__ == '__main__':
    main()
