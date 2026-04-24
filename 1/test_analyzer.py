import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

print("="*70)
print("用户行为分析器 - 功能测试")
print("="*70)

np.random.seed(42)
random.seed(42)

print("\n[测试1] 生成模拟测试数据...")

def generate_test_data():
    """生成包含多ID和沉默-唤醒场景的测试数据"""
    events = []
    
    user_id_1 = 'USER001'
    user_id_2 = 'USER002'
    user_id_3 = 'USER003'
    device_id_1 = 'DEV001'
    device_id_2 = 'DEV002'
    
    start_date = datetime(2023, 1, 1)
    
    for day in range(60):
        current_date = start_date + timedelta(days=day)
        for _ in range(random.randint(1, 3)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_weights = [0.35, 0.40, 0.15, 0.05, 0.05]
            event_name = random.choices(
                ['启动', '浏览商品', '加入购物车', '支付', '退出'],
                weights=event_weights,
                k=1
            )[0]
            events.append({
                'user_id': user_id_1,
                'device_id': device_id_1,
                'event_name': event_name,
                'timestamp': event_time
            })
    
    reactivate_date = start_date + timedelta(days=120)
    for day in range(60):
        current_date = reactivate_date + timedelta(days=day)
        for _ in range(random.randint(1, 4)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_weights = [0.35, 0.40, 0.15, 0.05, 0.05]
            event_name = random.choices(
                ['启动', '浏览商品', '加入购物车', '支付', '退出'],
                weights=event_weights,
                k=1
            )[0]
            events.append({
                'user_id': user_id_2,
                'device_id': device_id_1,
                'event_name': event_name,
                'timestamp': event_time
            })
    
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        for _ in range(random.randint(0, 2)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_weights = [0.35, 0.40, 0.15, 0.05, 0.05]
            event_name = random.choices(
                ['启动', '浏览商品', '加入购物车', '支付', '退出'],
                weights=event_weights,
                k=1
            )[0]
            events.append({
                'user_id': user_id_3,
                'device_id': device_id_2,
                'event_name': event_name,
                'timestamp': event_time
            })
    
    df = pd.DataFrame(events)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df

df = generate_test_data()

print(f"\n数据生成完成:")
print(f"  - 总事件数: {len(df)}")
print(f"  - 原始用户ID数: {df['user_id'].nunique()}")
print(f"  - 设备ID数: {df['device_id'].nunique()}")
print(f"  - 时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")

print("\n各用户事件统计:")
for user_id in df['user_id'].unique():
    user_df = df[df['user_id'] == user_id]
    print(f"  {user_id}: {len(user_df)} 个事件, "
          f"时间范围: {user_df['timestamp'].min().strftime('%Y-%m-%d')} ~ "
          f"{user_df['timestamp'].max().strftime('%Y-%m-%d')}")

print("\n[测试2] 多ID关联处理...")

from user_behavior_analyzer import MultiIDResolver

resolver = MultiIDResolver()
id_mappings = resolver.resolve(df)
df_with_virtual = resolver.apply_mapping(df)
id_mapping_summary = resolver.get_mapping_summary()

print(f"\n关联结果:")
for uid, info in id_mappings.items():
    print(f"  {uid} -> {info['virtual_user_id']} "
          f"(置信度: {info['confidence']}, 方法: {info['method']})")

print(f"\n虚拟用户统计:")
for vid in df_with_virtual['virtual_user_id'].unique():
    vid_df = df_with_virtual[df_with_virtual['virtual_user_id'] == vid]
    original_ids = vid_df['user_id'].unique()
    print(f"  {vid}: 包含 {len(original_ids)} 个原始ID ({', '.join(original_ids)}), "
          f"共 {len(vid_df)} 个事件")

print(f"\n关联摘要:")
print(f"  - 总原始ID数: {id_mapping_summary.get('total_original_ids', 0)}")
print(f"  - 虚拟用户数: {id_mapping_summary.get('total_virtual_users', 0)}")
print(f"  - 多ID虚拟用户数: {id_mapping_summary.get('multi_id_virtual_users', 0)}")

print("\n[测试3] 沉默期和唤醒事件检测...")

from user_behavior_analyzer import SilenceWakeupDetector

detector = SilenceWakeupDetector(silence_threshold_days=30)
silent_periods_df, wakeup_events_df, user_analysis_df = detector.detect_all_users(
    df_with_virtual, 
    user_id_col='virtual_user_id'
)

print(f"\n检测结果:")
print(f"  - 总沉默期数: {len(silent_periods_df)}")
print(f"  - 总唤醒事件数: {len(wakeup_events_df)}")

if not silent_periods_df.empty:
    print(f"\n沉默期详情:")
    print(silent_periods_df[['user_id', 'silence_days', 'silence_type', 
                             'last_event_before', 'first_event_after']].to_string())

if not wakeup_events_df.empty:
    print(f"\n唤醒事件详情:")
    print(wakeup_events_df[['user_id', 'wakeup_time', 'wakeup_event', 
                            'silence_days', 'wakeup_quality', 'silence_type']].to_string())

print("\n[测试4] 唤醒前后行为对比分析...")

from user_behavior_analyzer import BehaviorComparator

comparator = BehaviorComparator(window_days=7)
comparisons, summary_stats = comparator.analyze_all_wakeups(wakeup_events_df)

if comparisons:
    for i, comp in enumerate(comparisons):
        print(f"\n--- 唤醒事件 {i+1} ---")
        print(f"用户: {comp['user_id']}")
        print(f"沉默时长: {comp['silence_days']:.1f} 天")
        print(f"唤醒质量: {comp['wakeup_quality']}")
        print(f"沉默类型: {comp['silence_type']}")
        print(f"\n行为对比 (前后7天):")
        print(f"  唤醒前事件数: {comp['before_event_count']}")
        print(f"  唤醒后事件数: {comp['after_event_count']}")
        print(f"  变化: {comp['event_count_change']:+d}")
        print(f"  转化为支付: {'是' if comp['converted_to_payment'] else '否'}")
        
        if comp['event_changes']:
            print(f"\n各事件类型变化:")
            for event, chg in comp['event_changes'].items():
                print(f"  {event}: {chg['before']} -> {chg['after']} ({chg['change']:+d})")

if summary_stats:
    print(f"\n汇总统计:")
    print(f"  - 分析的唤醒事件数: {summary_stats.get('total_wakeups', 0)}")
    print(f"  - 平均沉默时长: {summary_stats.get('avg_silence_days', 0):.1f} 天")
    print(f"  - 平均事件数变化: {summary_stats.get('avg_event_count_change', 0):+.1f}")
    print(f"  - 支付转化率: {summary_stats.get('payment_conversion_rate_pct', 0):.1f}%")

print("\n[测试5] 报告生成...")

from user_behavior_analyzer import ReportGenerator

reporter = ReportGenerator()

report = reporter.generate_text_report(
    user_analysis_df,
    silent_periods_df,
    wakeup_events_df,
    comparisons,
    summary_stats,
    id_mappings,
    id_mapping_summary
)

print("\n" + "-"*70)
print("报告预览（前50行）")
print("-"*70)
report_lines = report.split('\n')
print('\n'.join(report_lines[:50]))

print("\n" + "="*70)
print("所有测试完成！")
print("="*70)

print("\n核心逻辑定义:")
print("  - 沉默: 连续30天以上无任何事件记录")
print("  - 唤醒: 沉默期后的第一个活跃事件")
print("  - 多ID关联策略:")
print("    1. 设备ID硬关联（高置信度）: 同一设备 + 时间不重叠")
print("    2. 行为模式软关联（中置信度）: 行为相似度高 + 时间连续")
print("    3. 无法关联（低置信度）: 标记为独立用户")

print("\n输出数据结构:")
print("  - id_mappings: 原始ID -> 虚拟用户ID映射")
print("  - silent_periods_df: 沉默期数据框")
print("  - wakeup_events_df: 唤醒事件数据框")
print("  - comparisons: 每个唤醒事件的前后对比")
print("  - summary_stats: 汇总统计")
print("  - report: 完整文本报告")
