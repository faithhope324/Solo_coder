import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("用户沉默与唤醒分析 - 简化测试版")
print("="*70)

EVENT_TYPES = ['启动', '浏览商品', '加入购物车', '支付', '退出']
SILENCE_THRESHOLD_DAYS = 30

print("\n[1] 生成测试数据...")

def generate_test_data():
    """生成包含沉默-唤醒场景的测试数据"""
    np.random.seed(42)
    random.seed(42)
    
    events = []
    
    user_id_1 = 'USER001'
    device_id_1 = 'DEV001'
    
    start_date = datetime(2023, 1, 1)
    
    for day in range(60):
        current_date = start_date + timedelta(days=day)
        for _ in range(random.randint(1, 3)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_name = random.choices(
                EVENT_TYPES,
                weights=[0.35, 0.40, 0.15, 0.05, 0.05],
                k=1
            )[0]
            events.append({
                'user_id': user_id_1,
                'device_id': device_id_1,
                'event_name': event_name,
                'timestamp': event_time,
                'real_user_tag': 'REAL001'
            })
    
    user_id_2 = 'USER002'
    reactivate_date = start_date + timedelta(days=120)
    
    for day in range(60):
        current_date = reactivate_date + timedelta(days=day)
        for _ in range(random.randint(1, 3)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_name = random.choices(
                EVENT_TYPES,
                weights=[0.35, 0.40, 0.15, 0.05, 0.05],
                k=1
            )[0]
            events.append({
                'user_id': user_id_2,
                'device_id': device_id_1,
                'event_name': event_name,
                'timestamp': event_time,
                'real_user_tag': 'REAL001'
            })
    
    user_id_3 = 'USER003'
    device_id_2 = 'DEV002'
    
    for day in range(30):
        current_date = start_date + timedelta(days=day)
        for _ in range(random.randint(0, 2)):
            hour = random.randint(8, 22)
            event_time = current_date.replace(hour=hour, minute=random.randint(0, 59))
            event_name = random.choices(
                EVENT_TYPES,
                weights=[0.35, 0.40, 0.15, 0.05, 0.05],
                k=1
            )[0]
            events.append({
                'user_id': user_id_3,
                'device_id': device_id_2,
                'event_name': event_name,
                'timestamp': event_time,
                'real_user_tag': 'REAL002'
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

print("\n[2] 多ID关联处理（基于设备ID）...")

def resolve_by_device_id(df):
    """基于设备ID进行硬关联"""
    if 'device_id' not in df.columns:
        return {}
    
    device_groups = df.groupby('device_id')
    mappings = {}
    next_virtual_id = 1
    
    for device_id, group in device_groups:
        user_ids = group['user_id'].unique()
        
        virtual_id = f'V{str(next_virtual_id).zfill(6)}'
        next_virtual_id += 1
        
        user_features = {}
        for user_id in user_ids:
            user_df = group[group['user_id'] == user_id]
            if len(user_df) > 0:
                user_features[user_id] = {
                    'first_event': user_df['timestamp'].min(),
                    'last_event': user_df['timestamp'].max()
                }
        
        sorted_users = sorted(
            user_features.items(),
            key=lambda x: x[1]['first_event']
        )
        
        for i, (user_id, features) in enumerate(sorted_users):
            mappings[user_id] = {
                'virtual_user_id': virtual_id,
                'device_id': device_id,
                'confidence': 'high',
                'sequence': i + 1,
                'first_event': features['first_event'],
                'last_event': features['last_event']
            }
    
    return mappings

id_mappings = resolve_by_device_id(df)

print(f"\n关联结果:")
for uid, info in id_mappings.items():
    print(f"  {uid} -> {info['virtual_user_id']} "
          f"(设备: {info['device_id']}, 置信度: {info['confidence']})")

df['virtual_user_id'] = df['user_id'].map(
    lambda x: id_mappings.get(x, {}).get('virtual_user_id', x)
)

print(f"\n虚拟用户统计:")
for vid in df['virtual_user_id'].unique():
    vid_df = df[df['virtual_user_id'] == vid]
    original_ids = vid_df['user_id'].unique()
    print(f"  {vid}: 包含 {len(original_ids)} 个原始ID ({', '.join(original_ids)}), "
          f"共 {len(vid_df)} 个事件")

print("\n[3] 沉默期和唤醒事件检测...")

def detect_silent_periods(user_events, silence_threshold_days=30):
    """检测用户的沉默期"""
    silent_periods = []
    wakeup_events = []
    
    if len(user_events) < 2:
        return silent_periods, wakeup_events
    
    user_events = user_events.sort_values('timestamp').reset_index(drop=True)
    
    for i in range(1, len(user_events)):
        prev_row = user_events.iloc[i-1]
        curr_row = user_events.iloc[i]
        
        time_gap = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / (24 * 3600)
        
        if time_gap >= silence_threshold_days:
            silent_periods.append({
                'silence_id': f'S{len(silent_periods)+1:04d}',
                'silence_start': prev_row['timestamp'],
                'silence_end': curr_row['timestamp'],
                'silence_days': time_gap,
                'last_event_before': prev_row['event_name'],
                'first_event_after': curr_row['event_name']
            })
            
            wakeup_events.append({
                'wakeup_id': f'W{len(wakeup_events)+1:04d}',
                'wakeup_time': curr_row['timestamp'],
                'wakeup_event': curr_row['event_name'],
                'silence_days': time_gap,
                'events_before': user_events.iloc[:i].copy(),
                'events_after': user_events.iloc[i:].copy()
            })
    
    return silent_periods, wakeup_events

all_silent_periods = []
all_wakeup_events = []

for vid in df['virtual_user_id'].unique():
    vid_df = df[df['virtual_user_id'] == vid].copy()
    
    print(f"\n分析虚拟用户 {vid}...")
    print(f"  事件数: {len(vid_df)}")
    
    silent_periods, wakeup_events = detect_silent_periods(vid_df, SILENCE_THRESHOLD_DAYS)
    
    for sp in silent_periods:
        sp['virtual_user_id'] = vid
        all_silent_periods.append(sp)
    
    for we in wakeup_events:
        we['virtual_user_id'] = vid
        all_wakeup_events.append(we)
    
    if silent_periods:
        print(f"  发现 {len(silent_periods)} 个沉默期")
        for sp in silent_periods:
            print(f"    - 沉默 {sp['silence_days']:.1f} 天: "
                  f"{sp['silence_start'].strftime('%Y-%m-%d')} ~ "
                  f"{sp['silence_end'].strftime('%Y-%m-%d')}")
    else:
        print(f"  未发现沉默期")

print(f"\n检测结果汇总:")
print(f"  - 总沉默期数: {len(all_silent_periods)}")
print(f"  - 总唤醒事件数: {len(all_wakeup_events)}")

if all_silent_periods:
    silent_df = pd.DataFrame(all_silent_periods)
    print(f"\n沉默期详情:")
    print(silent_df[['virtual_user_id', 'silence_days', 'last_event_before', 'first_event_after']].to_string())

print("\n[4] 唤醒前后行为对比分析...")

def analyze_behavior_changes(wakeup_event, window_days=7):
    """分析唤醒前后的行为变化"""
    wakeup_time = wakeup_event['wakeup_time']
    
    events_before = wakeup_event['events_before']
    events_after = wakeup_event['events_after']
    
    before_window_start = wakeup_time - timedelta(days=window_days)
    after_window_end = wakeup_time + timedelta(days=window_days)
    
    events_before_window = events_before[
        (events_before['timestamp'] >= before_window_start) & 
        (events_before['timestamp'] < wakeup_time)
    ].copy()
    
    events_after_window = events_after[
        (events_after['timestamp'] > wakeup_time) & 
        (events_after['timestamp'] <= after_window_end)
    ].copy()
    
    def get_stats(events_df):
        if len(events_df) == 0:
            return {
                'count': 0,
                'event_types': set(),
                'distribution': {}
            }
        
        dist = events_df['event_name'].value_counts().to_dict()
        return {
            'count': len(events_df),
            'event_types': set(events_df['event_name'].unique()),
            'distribution': dist
        }
    
    before_stats = get_stats(events_before_window)
    after_stats = get_stats(events_after_window)
    
    all_events = set(before_stats['distribution'].keys()) | set(after_stats['distribution'].keys())
    
    changes = {}
    for event in all_events:
        before_count = before_stats['distribution'].get(event, 0)
        after_count = after_stats['distribution'].get(event, 0)
        changes[event] = {
            'before': before_count,
            'after': after_count,
            'change': after_count - before_count
        }
    
    return {
        'wakeup_id': wakeup_event['wakeup_id'],
        'virtual_user_id': wakeup_event['virtual_user_id'],
        'wakeup_time': wakeup_time,
        'silence_days': wakeup_event['silence_days'],
        'window_days': window_days,
        'before_count': before_stats['count'],
        'after_count': after_stats['count'],
        'before_events': events_before_window,
        'after_events': events_after_window,
        'event_changes': changes
    }

if all_wakeup_events:
    print(f"\n分析 {len(all_wakeup_events)} 个唤醒事件...")
    
    for i, wakeup_event in enumerate(all_wakeup_events):
        comparison = analyze_behavior_changes(wakeup_event, window_days=7)
        
        print(f"\n--- 唤醒事件 {comparison['wakeup_id']} ---")
        print(f"用户: {comparison['virtual_user_id']}")
        print(f"沉默时长: {comparison['silence_days']:.1f} 天")
        print(f"唤醒时间: {comparison['wakeup_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"\n行为对比 (前后{comparison['window_days']}天):")
        print(f"  唤醒前事件数: {comparison['before_count']}")
        print(f"  唤醒后事件数: {comparison['after_count']}")
        print(f"  变化: {comparison['after_count'] - comparison['before_count']:+d}")
        
        print(f"\n各事件类型变化:")
        for event, change_data in comparison['event_changes'].items():
            change_str = f"{change_data['change']:+d}"
            print(f"  {event}: {change_data['before']} -> {change_data['after']} ({change_str})")

print("\n" + "="*70)
print("分析完成！")
print("="*70)

print("\n关键结论:")
print("1. 多ID关联: 相同设备ID + 时间上不重叠的活跃期 = 可能是同一用户")
print("2. 沉默定义: 连续30天以上无任何事件记录")
print("3. 唤醒定义: 沉默期后的第一个活跃事件")
print("4. 行为对比: 分析唤醒前后7天内的事件序列差异")

print("\n输出数据结构:")
print("- 原始事件数据: DataFrame (包含 user_id, device_id, event_name, timestamp)")
print("- ID映射关系: Dict (原始ID -> 虚拟用户ID + 置信度)")
print("- 沉默期数据: DataFrame (包含沉默开始/结束时间、时长、前后事件)")
print("- 唤醒事件数据: List (包含唤醒时间、沉默时长、前后事件序列)")
print("- 行为对比结果: Dict (包含前后事件数、各事件类型变化)")
