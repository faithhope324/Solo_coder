import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("警告: matplotlib 或 seaborn 未安装，将跳过绘图功能")


EVENT_TYPES = ['启动', '浏览商品', '加入购物车', '支付', '退出']
SILENCE_THRESHOLD_DAYS = 30
ANALYSIS_WINDOW_DAYS = 7


class DataSimulator:
    """用户行为数据模拟器 - 模拟包含多ID问题的真实场景"""
    
    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date or datetime(2023, 1, 1)
        self.end_date = end_date or datetime(2024, 12, 31)
        self.user_id_counter = 0
        self.device_id_counter = 0
    
    def _generate_user_id(self):
        self.user_id_counter += 1
        return f'USER{str(self.user_id_counter).zfill(6)}'
    
    def _generate_device_id(self):
        self.device_id_counter += 1
        return f'DEV{str(self.device_id_counter).zfill(8)}'
    
    def _generate_user_events(self, user_id, device_id, start_time, end_time, 
                               behavior_pattern='normal', real_user_tag=None):
        """为单个用户生成一段时间内的行为事件"""
        events = []
        
        if behavior_pattern == 'churner':
            activity_days = random.randint(30, 90)
            actual_end = min(end_time, start_time + timedelta(days=activity_days))
        elif behavior_pattern == 'inactive':
            actual_end = start_time + timedelta(days=random.randint(7, 30))
        else:
            actual_end = end_time
        
        current_time = start_time
        while current_time < actual_end:
            if behavior_pattern == 'churner':
                elapsed = (current_time - start_time).days
                total = (actual_end - start_time).days
                if total > 0 and elapsed > total * 0.7:
                    break
            
            daily_activity = random.randint(1, 4) if behavior_pattern != 'inactive' else random.randint(0, 1)
            
            for _ in range(daily_activity):
                hour = random.randint(8, 22)
                minute = random.randint(0, 59)
                event_time = current_time.replace(hour=hour, minute=minute)
                
                if event_time > actual_end:
                    break
                
                event_weights = {
                    '启动': 0.35,
                    '浏览商品': 0.40,
                    '加入购物车': 0.15,
                    '支付': 0.05,
                    '退出': 0.05
                }
                
                event_name = random.choices(
                    list(event_weights.keys()),
                    weights=list(event_weights.values()),
                    k=1
                )[0]
                
                event_dict = {
                    'user_id': user_id,
                    'event_name': event_name,
                    'timestamp': event_time
                }
                
                if device_id:
                    event_dict['device_id'] = device_id
                if real_user_tag:
                    event_dict['real_user_tag'] = real_user_tag
                
                events.append(event_dict)
            
            interval_days = random.randint(1, 3) if behavior_pattern != 'inactive' else random.randint(7, 15)
            current_time += timedelta(days=interval_days)
        
        return events
    
    def generate_dataset(self, n_real_users=50, multi_id_ratio=0.4, 
                         include_device_id=True, seed=42):
        """
        生成包含多ID问题的完整数据集
        
        参数:
            n_real_users: 真实用户数量
            multi_id_ratio: 有多ID问题的用户比例
            include_device_id: 是否包含设备ID字段
            seed: 随机种子
        
        返回:
            DataFrame: 包含用户行为日志的数据框
        """
        random.seed(seed)
        np.random.seed(seed)
        
        all_events = []
        
        for real_user_idx in range(n_real_users):
            real_user_id = f'REAL{str(real_user_idx + 1).zfill(4)}'
            device_id = self._generate_device_id() if include_device_id else None
            
            has_multiple_ids = random.random() < multi_id_ratio
            
            if has_multiple_ids:
                n_ids = random.randint(2, 4)
                
                current_start = self.start_date
                
                for id_idx in range(n_ids):
                    user_id = self._generate_user_id()
                    
                    if id_idx < n_ids - 1:
                        active_days = random.randint(60, 180)
                        user_end = current_start + timedelta(days=active_days)
                        
                        silence_days = random.randint(35, 90)
                        next_start = user_end + timedelta(days=silence_days)
                    else:
                        user_end = self.end_date
                        next_start = None
                    
                    if id_idx == 0:
                        pattern = 'normal'
                    elif id_idx == n_ids - 1:
                        pattern = 'normal'
                    else:
                        pattern = 'churner'
                    
                    events = self._generate_user_events(
                        user_id, device_id, current_start, user_end, pattern, real_user_id
                    )
                    
                    all_events.extend(events)
                    
                    if next_start and next_start < self.end_date:
                        current_start = next_start
                    else:
                        break
            else:
                user_id = self._generate_user_id()
                pattern = random.choice(['normal', 'churner', 'inactive'])
                
                events = self._generate_user_events(
                    user_id, device_id, self.start_date, self.end_date, pattern, real_user_id
                )
                
                all_events.extend(events)
        
        df = pd.DataFrame(all_events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df


class MultiIDResolver:
    """
    多ID关联处理器 - 解决用户卸载重装导致的多ID问题
    
    核心逻辑:
    1. 基于设备ID的硬关联（最高置信度）
    2. 基于行为模式的软关联（中置信度）
    3. 无法关联的标记为独立用户（低置信度）
    """
    
    def __init__(self, time_gap_threshold_days=90, similarity_threshold=0.7):
        """
        初始化多ID关联处理器
        
        参数:
            time_gap_threshold_days: 两个ID活跃期之间的最大时间间隔（天）
            similarity_threshold: 行为相似度阈值（0-1）
        """
        self.time_gap_threshold = time_gap_threshold_days
        self.similarity_threshold = similarity_threshold
        self.virtual_user_mapping = {}
        self.next_virtual_id = 1
    
    def _calculate_behavior_similarity(self, events1, events2):
        """
        计算两个用户行为序列的相似度（基于事件分布的余弦相似度）
        
        参数:
            events1: 第一个用户的事件列表或DataFrame
            events2: 第二个用户的事件列表或DataFrame
        
        返回:
            float: 相似度分数（0-1）
        """
        def get_event_distribution(events):
            if isinstance(events, pd.DataFrame):
                event_names = events['event_name'].tolist()
            else:
                event_names = [e['event_name'] if isinstance(e, dict) else e for e in events]
            
            dist = {}
            total = len(event_names)
            for evt in event_names:
                dist[evt] = dist.get(evt, 0) + 1
            
            return {k: v/total for k, v in dist.items()} if total > 0 else {}
        
        dist1 = get_event_distribution(events1)
        dist2 = get_event_distribution(events2)
        
        if not dist1 or not dist2:
            return 0.0
        
        all_events = set(dist1.keys()) | set(dist2.keys())
        
        vec1 = np.array([dist1.get(e, 0) for e in all_events])
        vec2 = np.array([dist2.get(e, 0) for e in all_events])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cosine_sim = np.dot(vec1, vec2) / (norm1 * norm2)
        
        return float(cosine_sim)
    
    def _extract_user_features(self, user_df):
        """
        提取用户行为特征
        
        参数:
            user_df: 单个用户的事件DataFrame
        
        返回:
            dict: 用户特征字典
        """
        if len(user_df) == 0:
            return None
        
        user_df = user_df.sort_values('timestamp')
        
        first_event = user_df['timestamp'].min()
        last_event = user_df['timestamp'].max()
        active_days = (last_event - first_event).total_seconds() / (24 * 3600)
        
        event_counts = user_df['event_name'].value_counts().to_dict()
        total_events = len(user_df)
        
        avg_interval = 0
        if len(user_df) > 1:
            timestamps = user_df['timestamp'].sort_values()
            intervals = [(timestamps.iloc[i] - timestamps.iloc[i-1]).total_seconds() / 3600 
                        for i in range(1, len(timestamps))]
            avg_interval = np.mean(intervals) if intervals else 0
        
        return {
            'user_id': user_df['user_id'].iloc[0],
            'device_id': user_df['device_id'].iloc[0] if 'device_id' in user_df.columns else None,
            'first_event': first_event,
            'last_event': last_event,
            'active_days': active_days,
            'total_events': total_events,
            'event_distribution': event_counts,
            'avg_interval_hours': avg_interval,
            'events_df': user_df.copy()
        }
    
    def resolve_by_device_id(self, df):
        """
        基于设备ID进行硬关联（最高置信度）
        
        逻辑: 同一设备ID + 时间上不重叠的活跃期 = 可能是同一用户的不同注册ID
        
        参数:
            df: 事件数据框
        
        返回:
            dict: 用户ID映射关系 {原始user_id: {virtual_user_id, confidence, ...}}
        """
        if 'device_id' not in df.columns or df['device_id'].isna().all():
            print("警告: 未找到device_id字段，跳过设备ID关联")
            return {}
        
        mappings = {}
        
        device_groups = df.groupby('device_id')
        
        for device_id, group in device_groups:
            if pd.isna(device_id):
                continue
            
            user_ids = group['user_id'].unique()
            
            if len(user_ids) == 1:
                virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                self.next_virtual_id += 1
                
                user_df = group[group['user_id'] == user_ids[0]]
                features = self._extract_user_features(user_df)
                
                mappings[user_ids[0]] = {
                    'virtual_user_id': virtual_id,
                    'device_id': device_id,
                    'confidence': 'high',
                    'method': 'single_device_user',
                    'first_event': features['first_event'] if features else None,
                    'last_event': features['last_event'] if features else None
                }
            else:
                user_features = {}
                for user_id in user_ids:
                    user_df = group[group['user_id'] == user_id]
                    features = self._extract_user_features(user_df)
                    if features:
                        user_features[user_id] = features
                
                if not user_features:
                    continue
                
                sorted_users = sorted(
                    user_features.items(),
                    key=lambda x: x[1]['first_event']
                )
                
                i = 0
                while i < len(sorted_users):
                    user_id_1, features_1 = sorted_users[i]
                    
                    virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                    self.next_virtual_id += 1
                    
                    group_members = [(user_id_1, features_1, 1)]
                    
                    j = i + 1
                    while j < len(sorted_users):
                        user_id_j, features_j = sorted_users[j]
                        
                        time_gap = (features_j['first_event'] - features_1['last_event']).total_seconds() / (24 * 3600)
                        
                        if time_gap >= 0 and time_gap <= self.time_gap_threshold:
                            has_overlap = features_j['first_event'] <= features_1['last_event']
                            
                            if not has_overlap:
                                group_members.append((user_id_j, features_j, len(group_members) + 1))
                                j += 1
                                continue
                        
                        break
                    
                    for uid, feat, seq in group_members:
                        mappings[uid] = {
                            'virtual_user_id': virtual_id,
                            'device_id': device_id,
                            'confidence': 'high',
                            'method': 'device_based_merge',
                            'sequence': seq,
                            'first_event': feat['first_event'],
                            'last_event': feat['last_event'],
                            'group_size': len(group_members)
                        }
                    
                    i = j
        
        return mappings
    
    def resolve_by_behavior_pattern(self, df, existing_mappings=None):
        """
        基于行为模式进行软关联（针对无设备ID的情况）
        
        逻辑: 行为相似度高 + 时间上连续（前一个ID沉默，后一个ID激活）= 可能是同一用户
        
        参数:
            df: 事件数据框
            existing_mappings: 已有的映射关系（来自设备ID关联）
        
        返回:
            dict: 更新后的用户ID映射关系
        """
        existing_mappings = existing_mappings or {}
        all_user_ids = df['user_id'].unique()
        
        unmapped_users = [uid for uid in all_user_ids if uid not in existing_mappings]
        
        if len(unmapped_users) < 2:
            for user_id in unmapped_users:
                if user_id not in existing_mappings:
                    virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                    self.next_virtual_id += 1
                    existing_mappings[user_id] = {
                        'virtual_user_id': virtual_id,
                        'confidence': 'low',
                        'method': 'single_user_unmapped'
                    }
            return existing_mappings
        
        user_features = {}
        for user_id in unmapped_users:
            user_df = df[df['user_id'] == user_id]
            features = self._extract_user_features(user_df)
            if features and features['total_events'] >= 5:
                user_features[user_id] = features
        
        if len(user_features) < 2:
            for user_id in unmapped_users:
                if user_id not in existing_mappings:
                    virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                    self.next_virtual_id += 1
                    existing_mappings[user_id] = {
                        'virtual_user_id': virtual_id,
                        'confidence': 'low',
                        'method': 'single_user_insufficient_data'
                    }
            return existing_mappings
        
        sorted_users = sorted(
            user_features.items(),
            key=lambda x: x[1]['last_event']
        )
        
        i = 0
        while i < len(sorted_users) - 1:
            user_id_1, features_1 = sorted_users[i]
            user_id_2, features_2 = sorted_users[i + 1]
            
            time_gap = (features_2['first_event'] - features_1['last_event']).total_seconds() / (24 * 3600)
            
            if SILENCE_THRESHOLD_DAYS <= time_gap <= self.time_gap_threshold:
                similarity = self._calculate_behavior_similarity(
                    features_1['events_df'],
                    features_2['events_df']
                )
                
                if similarity >= self.similarity_threshold:
                    virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                    self.next_virtual_id += 1
                    
                    confidence = 'high' if similarity >= 0.9 else 'medium'
                    
                    existing_mappings[user_id_1] = {
                        'virtual_user_id': virtual_id,
                        'confidence': confidence,
                        'method': 'behavior_based_merge',
                        'similarity': similarity,
                        'time_gap_days': time_gap,
                        'sequence': 1
                    }
                    
                    existing_mappings[user_id_2] = {
                        'virtual_user_id': virtual_id,
                        'confidence': confidence,
                        'method': 'behavior_based_merge',
                        'similarity': similarity,
                        'time_gap_days': time_gap,
                        'sequence': 2
                    }
                    
                    i += 2
                    continue
            
            i += 1
        
        for user_id in unmapped_users:
            if user_id not in existing_mappings:
                virtual_id = f'V{str(self.next_virtual_id).zfill(6)}'
                self.next_virtual_id += 1
                existing_mappings[user_id] = {
                    'virtual_user_id': virtual_id,
                    'confidence': 'low',
                    'method': 'single_user_no_match'
                }
        
        return existing_mappings
    
    def resolve(self, df):
        """
        执行完整的多ID关联流程
        
        参数:
            df: 事件数据框
        
        返回:
            dict: 用户ID映射关系
        """
        print("\n" + "="*60)
        print("多ID关联处理")
        print("="*60)
        
        print(f"\n原始用户ID数: {df['user_id'].nunique()}")
        
        mappings = self.resolve_by_device_id(df)
        print(f"\n设备ID关联完成:")
        print(f"  - 已关联用户ID数: {len(mappings)}")
        
        if mappings:
            virtual_counts = {}
            for uid, info in mappings.items():
                vid = info['virtual_user_id']
                virtual_counts[vid] = virtual_counts.get(vid, 0) + 1
            
            multi_id_virtuals = {k: v for k, v in virtual_counts.items() if v > 1}
            print(f"  - 发现多ID虚拟用户数: {len(multi_id_virtuals)}")
        
        mappings = self.resolve_by_behavior_pattern(df, mappings)
        print(f"\n行为模式关联完成:")
        print(f"  - 总关联用户ID数: {len(mappings)}")
        
        virtual_counts = {}
        for uid, info in mappings.items():
            vid = info['virtual_user_id']
            virtual_counts[vid] = virtual_counts.get(vid, 0) + 1
        
        multi_id_virtuals = {k: v for k, v in virtual_counts.items() if v > 1}
        print(f"  - 最终多ID虚拟用户数: {len(multi_id_virtuals)}")
        print(f"  - 最终虚拟用户数: {len(virtual_counts)}")
        
        self.virtual_user_mapping = mappings
        return mappings
    
    def apply_mapping(self, df):
        """
        将虚拟用户ID应用到数据框
        
        参数:
            df: 原始事件数据框
        
        返回:
            DataFrame: 添加了虚拟用户ID列的数据框
        """
        if not self.virtual_user_mapping:
            print("警告: 尚未执行关联处理，请先调用 resolve() 方法")
            return df
        
        df = df.copy()
        
        df['virtual_user_id'] = df['user_id'].map(
            lambda x: self.virtual_user_mapping.get(x, {}).get('virtual_user_id', x)
        )
        
        df['merge_confidence'] = df['user_id'].map(
            lambda x: self.virtual_user_mapping.get(x, {}).get('confidence', 'unknown')
        )
        
        df['merge_method'] = df['user_id'].map(
            lambda x: self.virtual_user_mapping.get(x, {}).get('method', 'unknown')
        )
        
        return df
    
    def get_mapping_summary(self):
        """
        获取关联结果摘要
        
        返回:
            dict: 关联摘要信息
        """
        if not self.virtual_user_mapping:
            return {}
        
        virtual_counts = {}
        confidence_counts = {'high': 0, 'medium': 0, 'low': 0, 'unknown': 0}
        method_counts = {}
        
        for uid, info in self.virtual_user_mapping.items():
            vid = info['virtual_user_id']
            virtual_counts[vid] = virtual_counts.get(vid, 0) + 1
            
            conf = info.get('confidence', 'unknown')
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
            
            method = info.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        multi_id_virtuals = {k: v for k, v in virtual_counts.items() if v > 1}
        
        return {
            'total_original_ids': len(self.virtual_user_mapping),
            'total_virtual_users': len(virtual_counts),
            'multi_id_virtual_users': len(multi_id_virtuals),
            'max_ids_per_virtual': max(virtual_counts.values()) if virtual_counts else 0,
            'confidence_distribution': confidence_counts,
            'method_distribution': method_counts
        }


class SilenceWakeupDetector:
    """
    沉默期和唤醒事件检测器
    
    核心定义:
    - 沉默: 连续30天以上无任何事件记录
    - 唤醒: 沉默期后的第一个活跃事件
    
    支持的沉默类型:
    - short_history: 历史数据不足
    - long_term_silence: 长期沉默（>90天）
    - gradual_churn: 逐渐流失（行为频次逐渐下降）
    - abandon_churn: 突然流失
    """
    
    def __init__(self, silence_threshold_days=30):
        """
        初始化检测器
        
        参数:
            silence_threshold_days: 沉默判定阈值（天）
        """
        self.silence_threshold = silence_threshold_days
    
    def _classify_silence_type(self, events_before, silence_days):
        """
        分类沉默类型
        
        参数:
            events_before: 沉默前的事件DataFrame
            silence_days: 沉默时长（天）
        
        返回:
            str: 沉默类型
        """
        if len(events_before) < 5:
            return 'short_history'
        
        if silence_days > self.silence_threshold * 3:
            return 'long_term_silence'
        
        recent_events = events_before.tail(min(20, len(events_before)))
        if len(recent_events) >= 10:
            timestamps = recent_events['timestamp'].sort_values()
            recent_days = (timestamps.max() - timestamps.min()).total_seconds() / (24 * 3600)
            
            if recent_days > 0:
                recent_freq = len(recent_events) / recent_days
                
                earlier_events = events_before.head(len(events_before) - 10)
                if len(earlier_events) >= 10:
                    earlier_timestamps = earlier_events['timestamp'].sort_values()
                    earlier_days = (earlier_timestamps.max() - earlier_timestamps.min()).total_seconds() / (24 * 3600)
                    
                    if earlier_days > 0:
                        earlier_freq = len(earlier_events) / earlier_days
                        
                        if earlier_freq > 0 and recent_freq < earlier_freq * 0.3:
                            return 'gradual_churn'
        
        return 'abandon_churn'
    
    def _evaluate_wakeup_quality(self, wakeup_event_row, subsequent_events_df):
        """
        评估唤醒质量
        
        参数:
            wakeup_event_row: 唤醒事件的行数据
            subsequent_events_df: 唤醒后的事件DataFrame
        
        返回:
            str: 唤醒质量（weak/medium/strong）
        """
        wakeup_event = wakeup_event_row['event_name'] if isinstance(wakeup_event_row, pd.Series) else wakeup_event_row
        
        if wakeup_event != '启动':
            return 'weak'
        
        if len(subsequent_events_df) == 0:
            return 'weak'
        
        event_names = subsequent_events_df['event_name'].tolist()
        
        if '支付' in event_names:
            return 'strong'
        elif '加入购物车' in event_names or '浏览商品' in event_names:
            return 'medium'
        else:
            return 'weak'
    
    def detect_for_user(self, user_events_df):
        """
        为单个用户检测沉默期和唤醒事件
        
        参数:
            user_events_df: 按时间排序的用户事件DataFrame
        
        返回:
            tuple: (silent_periods列表, wakeup_events列表)
        """
        silent_periods = []
        wakeup_events = []
        
        if len(user_events_df) < 2:
            return silent_periods, wakeup_events
        
        user_events_df = user_events_df.sort_values('timestamp').reset_index(drop=True)
        
        for i in range(1, len(user_events_df)):
            prev_row = user_events_df.iloc[i-1]
            curr_row = user_events_df.iloc[i]
            
            time_gap = (curr_row['timestamp'] - prev_row['timestamp']).total_seconds() / (24 * 3600)
            
            if time_gap >= self.silence_threshold:
                silence_type = self._classify_silence_type(
                    user_events_df.iloc[:i], 
                    time_gap
                )
                
                silent_periods.append({
                    'silence_id': f'S{len(silent_periods)+1:04d}',
                    'silence_start': prev_row['timestamp'],
                    'silence_end': curr_row['timestamp'],
                    'silence_days': time_gap,
                    'silence_type': silence_type,
                    'last_event_before': prev_row['event_name'],
                    'first_event_after': curr_row['event_name'],
                    'events_before_count': i,
                    'events_after_count': len(user_events_df) - i
                })
                
                subsequent_events = user_events_df.iloc[i:min(i+20, len(user_events_df))]
                wakeup_quality = self._evaluate_wakeup_quality(curr_row, subsequent_events)
                
                wakeup_events.append({
                    'wakeup_id': f'W{len(wakeup_events)+1:04d}',
                    'wakeup_time': curr_row['timestamp'],
                    'wakeup_event': curr_row['event_name'],
                    'silence_days': time_gap,
                    'wakeup_quality': wakeup_quality,
                    'silence_type': silence_type,
                    'all_events_before': user_events_df.iloc[:i].copy(),
                    'all_events_after': user_events_df.iloc[i:].copy()
                })
        
        return silent_periods, wakeup_events
    
    def detect_all_users(self, df, user_id_col='virtual_user_id'):
        """
        检测所有用户的沉默期和唤醒事件
        
        参数:
            df: 事件数据框
            user_id_col: 用户ID列名（支持虚拟用户ID或原始user_id）
        
        返回:
            tuple: (silent_periods_df, wakeup_events_df, user_analysis_df)
        """
        print("\n" + "="*60)
        print("沉默期和唤醒事件检测")
        print("="*60)
        
        all_silent_periods = []
        all_wakeup_events = []
        user_analysis = {}
        
        users = df[user_id_col].unique()
        print(f"\n分析用户数: {len(users)}")
        
        for user_id in users:
            user_df = df[df[user_id_col] == user_id].copy()
            
            if len(user_df) < 2:
                user_analysis[user_id] = {
                    'user_id': user_id,
                    'event_count': len(user_df),
                    'has_silence': False,
                    'silence_count': 0,
                    'wakeup_count': 0
                }
                continue
            
            silent_periods, wakeup_events = self.detect_for_user(user_df)
            
            for sp in silent_periods:
                sp['user_id'] = user_id
                all_silent_periods.append(sp)
            
            for we in wakeup_events:
                we['user_id'] = user_id
                all_wakeup_events.append(we)
            
            user_analysis[user_id] = {
                'user_id': user_id,
                'event_count': len(user_df),
                'has_silence': len(silent_periods) > 0,
                'silence_count': len(silent_periods),
                'wakeup_count': len(wakeup_events),
                'avg_silence_days': np.mean([sp['silence_days'] for sp in silent_periods]) if silent_periods else 0,
                'max_silence_days': max([sp['silence_days'] for sp in silent_periods]) if silent_periods else 0
            }
        
        silent_periods_df = pd.DataFrame(all_silent_periods) if all_silent_periods else pd.DataFrame()
        wakeup_events_df = pd.DataFrame(all_wakeup_events) if all_wakeup_events else pd.DataFrame()
        user_analysis_df = pd.DataFrame(user_analysis.values())
        
        print(f"\n检测结果:")
        print(f"  - 总沉默期数: {len(all_silent_periods)}")
        print(f"  - 总唤醒事件数: {len(all_wakeup_events)}")
        
        users_with_silence = sum(1 for ua in user_analysis.values() if ua['has_silence'])
        print(f"  - 经历沉默-唤醒的用户数: {users_with_silence}")
        
        if not silent_periods_df.empty:
            print(f"\n沉默类型分布:")
            silence_type_counts = silent_periods_df['silence_type'].value_counts()
            for stype, count in silence_type_counts.items():
                print(f"    - {stype}: {count}")
        
        if not wakeup_events_df.empty:
            print(f"\n唤醒质量分布:")
            quality_counts = wakeup_events_df['wakeup_quality'].value_counts()
            for quality, count in quality_counts.items():
                print(f"    - {quality}: {count}")
        
        return silent_periods_df, wakeup_events_df, user_analysis_df


class BehaviorComparator:
    """
    行为对比分析器 - 分析唤醒前后的行为差异
    
    核心分析:
    1. 唤醒前后7天内的事件序列对比
    2. 各事件类型的变化量和变化率
    3. 支付转化情况分析
    4. 新增/消失的事件类型
    """
    
    def __init__(self, window_days=7):
        """
        初始化分析器
        
        参数:
            window_days: 分析窗口天数（默认7天）
        """
        self.window_days = window_days
    
    def extract_window_events(self, events_df, center_time, before=True):
        """
        提取时间窗口内的事件
        
        参数:
            events_df: 事件数据框
            center_time: 中心时间（唤醒时间）
            before: True=提取之前，False=提取之后
        
        返回:
            DataFrame: 窗口内的事件数据框
        """
        if len(events_df) == 0:
            return pd.DataFrame()
        
        if before:
            window_start = center_time - timedelta(days=self.window_days)
            window_end = center_time
            mask = (events_df['timestamp'] >= window_start) & (events_df['timestamp'] < window_end)
        else:
            window_start = center_time
            window_end = center_time + timedelta(days=self.window_days)
            mask = (events_df['timestamp'] > window_start) & (events_df['timestamp'] <= window_end)
        
        return events_df[mask].copy()
    
    def calculate_behavior_profile(self, events_df):
        """
        计算行为画像
        
        参数:
            events_df: 事件数据框
        
        返回:
            dict: 行为画像字典
        """
        if len(events_df) == 0:
            return {
                'event_count': 0,
                'event_types': set(),
                'event_distribution': {},
                'avg_interval_hours': None,
                'has_launch': False,
                'has_browse': False,
                'has_cart': False,
                'has_payment': False,
                'active_days': 0
            }
        
        event_counts = events_df['event_name'].value_counts()
        total_events = len(events_df)
        
        timestamps = events_df['timestamp'].sort_values()
        if len(timestamps) > 1:
            intervals = [(timestamps.iloc[i] - timestamps.iloc[i-1]).total_seconds() / 3600 
                        for i in range(1, len(timestamps))]
            avg_interval = np.mean(intervals)
        else:
            avg_interval = None
        
        event_names = set(events_df['event_name'].unique())
        active_dates = events_df['timestamp'].dt.date.nunique()
        
        return {
            'event_count': total_events,
            'event_types': event_names,
            'event_distribution': event_counts.to_dict(),
            'avg_interval_hours': avg_interval,
            'has_launch': '启动' in event_names,
            'has_browse': '浏览商品' in event_names,
            'has_cart': '加入购物车' in event_names,
            'has_payment': '支付' in event_names,
            'active_days': active_dates
        }
    
    def compare_single_wakeup(self, wakeup_event_dict):
        """
        对比单个唤醒事件前后的行为
        
        时间窗口定义:
        - 唤醒前7天: 沉默开始前的最后7天（以上次活跃期的最后一个事件时间为基准往前推）
        - 唤醒后7天: 唤醒事件及之后的7天（包含唤醒事件本身）
        
        参数:
            wakeup_event_dict: 唤醒事件字典（包含all_events_before和all_events_after）
        
        返回:
            tuple: (before_profile, after_profile, comparison_dict)
        """
        wakeup_time = wakeup_event_dict['wakeup_time']
        events_before_all = wakeup_event_dict['all_events_before']
        events_after_all = wakeup_event_dict['all_events_after']
        
        if len(events_before_all) > 0:
            last_event_before = events_before_all['timestamp'].max()
            before_window_end = last_event_before
            before_window_start = before_window_end - timedelta(days=self.window_days)
            mask_before = (events_before_all['timestamp'] >= before_window_start) & \
                         (events_before_all['timestamp'] <= before_window_end)
            events_before_window = events_before_all[mask_before].copy()
        else:
            events_before_window = pd.DataFrame()
        
        if len(events_after_all) > 0:
            after_window_start = wakeup_time
            after_window_end = wakeup_time + timedelta(days=self.window_days)
            mask_after = (events_after_all['timestamp'] >= after_window_start) & \
                        (events_after_all['timestamp'] <= after_window_end)
            events_after_window = events_after_all[mask_after].copy()
        else:
            events_after_window = pd.DataFrame()
        
        before_profile = self.calculate_behavior_profile(events_before_window)
        after_profile = self.calculate_behavior_profile(events_after_window)
        
        before_dist = before_profile['event_distribution']
        after_dist = after_profile['event_distribution']
        
        all_events = set(before_dist.keys()) | set(after_dist.keys())
        
        event_changes = {}
        for event in all_events:
            before_count = before_dist.get(event, 0)
            after_count = after_dist.get(event, 0)
            change = after_count - before_count
            
            if before_count > 0:
                change_pct = (change / before_count) * 100
            elif after_count > 0:
                change_pct = float('inf')
            else:
                change_pct = 0
            
            event_changes[event] = {
                'before': before_count,
                'after': after_count,
                'change': change,
                'change_pct': change_pct
            }
        
        comparison = {
            'wakeup_id': wakeup_event_dict.get('wakeup_id', 'unknown'),
            'user_id': wakeup_event_dict.get('user_id', 'unknown'),
            'wakeup_time': wakeup_time,
            'silence_days': wakeup_event_dict.get('silence_days', 0),
            'wakeup_quality': wakeup_event_dict.get('wakeup_quality', 'unknown'),
            'silence_type': wakeup_event_dict.get('silence_type', 'unknown'),
            'window_days': self.window_days,
            
            'before_event_count': before_profile['event_count'],
            'after_event_count': after_profile['event_count'],
            'event_count_change': after_profile['event_count'] - before_profile['event_count'],
            
            'before_active_days': before_profile['active_days'],
            'after_active_days': after_profile['active_days'],
            
            'before_has_payment': before_profile['has_payment'],
            'after_has_payment': after_profile['has_payment'],
            'converted_to_payment': not before_profile['has_payment'] and after_profile['has_payment'],
            
            'before_has_cart': before_profile['has_cart'],
            'after_has_cart': after_profile['has_cart'],
            
            'new_event_types': after_profile['event_types'] - before_profile['event_types'],
            'lost_event_types': before_profile['event_types'] - after_profile['event_types'],
            
            'event_changes': event_changes,
            
            'before_events_df': events_before_window,
            'after_events_df': events_after_window
        }
        
        return before_profile, after_profile, comparison
    
    def analyze_all_wakeups(self, wakeup_events_df):
        """
        分析所有唤醒事件的前后行为对比
        
        参数:
            wakeup_events_df: 唤醒事件数据框
        
        返回:
            tuple: (all_comparisons列表, summary_stats字典)
        """
        print("\n" + "="*60)
        print("唤醒前后行为对比分析")
        print("="*60)
        
        if len(wakeup_events_df) == 0:
            print("警告: 没有唤醒事件可分析")
            return [], {}
        
        all_comparisons = []
        
        print(f"\n分析唤醒事件数: {len(wakeup_events_df)}")
        
        for _, row in wakeup_events_df.iterrows():
            wakeup_event = row.to_dict()
            
            before_profile, after_profile, comparison = self.compare_single_wakeup(wakeup_event)
            all_comparisons.append(comparison)
        
        print(f"分析完成")
        
        summary_stats = self._generate_summary_stats(all_comparisons)
        
        print(f"\n汇总统计:")
        print(f"  - 平均事件数变化: {summary_stats.get('avg_event_count_change', 0):+.1f}")
        print(f"  - 支付转化率: {summary_stats.get('payment_conversion_rate_pct', 0):.1f}%")
        
        return all_comparisons, summary_stats
    
    def _generate_summary_stats(self, comparisons):
        """
        生成汇总统计
        
        参数:
            comparisons: 对比结果列表
        
        返回:
            dict: 汇总统计字典
        """
        if not comparisons:
            return {}
        
        total_wakeups = len(comparisons)
        
        event_count_changes = [c['event_count_change'] for c in comparisons]
        avg_event_change = np.mean(event_count_changes)
        
        converted_to_payment = sum(1 for c in comparisons if c['converted_to_payment'])
        payment_conversion_rate = (converted_to_payment / total_wakeups * 100) if total_wakeups > 0 else 0
        
        quality_dist = {}
        for c in comparisons:
            q = c['wakeup_quality']
            quality_dist[q] = quality_dist.get(q, 0) + 1
        
        silence_days = [c['silence_days'] for c in comparisons]
        avg_silence_days = np.mean(silence_days)
        
        all_event_changes = {}
        for c in comparisons:
            for event, changes in c['event_changes'].items():
                if event not in all_event_changes:
                    all_event_changes[event] = {'before': [], 'after': [], 'changes': []}
                all_event_changes[event]['before'].append(changes['before'])
                all_event_changes[event]['after'].append(changes['after'])
                all_event_changes[event]['changes'].append(changes['change'])
        
        event_change_summary = {}
        for event, data in all_event_changes.items():
            avg_before = np.mean(data['before'])
            avg_after = np.mean(data['after'])
            avg_change = np.mean(data['changes'])
            
            if avg_before > 0:
                pct_increase = (avg_change / avg_before) * 100
            elif avg_after > 0:
                pct_increase = float('inf')
            else:
                pct_increase = 0
            
            event_change_summary[event] = {
                'avg_before': avg_before,
                'avg_after': avg_after,
                'avg_change': avg_change,
                'pct_increase': pct_increase
            }
        
        return {
            'total_wakeups': total_wakeups,
            'avg_event_count_change': avg_event_change,
            'converted_to_payment_count': converted_to_payment,
            'payment_conversion_rate_pct': payment_conversion_rate,
            'wakeup_quality_distribution': quality_dist,
            'avg_silence_days': avg_silence_days,
            'event_type_changes': event_change_summary
        }


class ReportGenerator:
    """
    分析报告生成器
    
    功能:
    1. 生成详细的文本分析报告
    2. 生成可视化图表
    3. 导出关键数据
    """
    
    def __init__(self):
        pass
    
    def generate_text_report(self, 
                              user_analysis_df, 
                              silent_periods_df, 
                              wakeup_events_df,
                              comparisons,
                              summary_stats,
                              id_mappings=None,
                              id_mapping_summary=None):
        """
        生成文本报告
        
        参数:
            user_analysis_df: 用户分析数据框
            silent_periods_df: 沉默期数据框
            wakeup_events_df: 唤醒事件数据框
            comparisons: 对比结果列表
            summary_stats: 汇总统计
            id_mappings: ID映射关系
            id_mapping_summary: ID关联摘要
        
        返回:
            str: 完整的文本报告
        """
        report = []
        report.append("="*70)
        report.append("用户沉默与唤醒分析报告")
        report.append("="*70)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"参数配置:")
        report.append(f"  - 沉默阈值: {SILENCE_THRESHOLD_DAYS} 天")
        report.append(f"  - 分析窗口: {ANALYSIS_WINDOW_DAYS} 天")
        report.append("")
        
        report.append("-"*70)
        report.append("一、多ID关联分析结果")
        report.append("-"*70)
        
        if id_mapping_summary:
            report.append(f"总原始用户ID数: {id_mapping_summary.get('total_original_ids', 0)}")
            report.append(f"归并后虚拟用户数: {id_mapping_summary.get('total_virtual_users', 0)}")
            report.append(f"包含多ID的虚拟用户数: {id_mapping_summary.get('multi_id_virtual_users', 0)}")
            
            conf_dist = id_mapping_summary.get('confidence_distribution', {})
            if conf_dist:
                report.append("\n归并置信度分布:")
                for conf, count in conf_dist.items():
                    report.append(f"  - {conf}: {count}")
            
            method_dist = id_mapping_summary.get('method_distribution', {})
            if method_dist:
                report.append("\n归并方法分布:")
                for method, count in method_dist.items():
                    report.append(f"  - {method}: {count}")
        else:
            report.append("未执行多ID关联，使用原始user_id分析")
        report.append("")
        
        report.append("-"*70)
        report.append("二、沉默与唤醒总体统计")
        report.append("-"*70)
        
        if not user_analysis_df.empty:
            total_users = len(user_analysis_df)
            users_with_silence = len(user_analysis_df[user_analysis_df['has_silence']])
            
            report.append(f"总用户数: {total_users}")
            report.append(f"经历沉默-唤醒的用户数: {users_with_silence} "
                         f"({users_with_silence/total_users*100:.1f}%)")
        
        if not silent_periods_df.empty:
            report.append(f"\n沉默期统计:")
            report.append(f"  - 总沉默期数: {len(silent_periods_df)}")
            report.append(f"  - 平均沉默时长: {silent_periods_df['silence_days'].mean():.1f} 天")
            report.append(f"  - 最长沉默时长: {silent_periods_df['silence_days'].max():.1f} 天")
            report.append(f"  - 最短沉默时长: {silent_periods_df['silence_days'].min():.1f} 天")
            
            if 'silence_type' in silent_periods_df.columns:
                silence_type_dist = silent_periods_df['silence_type'].value_counts()
                report.append("\n沉默类型分布:")
                for stype, count in silence_type_dist.items():
                    report.append(f"  - {stype}: {count} ({count/len(silent_periods_df)*100:.1f}%)")
        
        if not wakeup_events_df.empty:
            report.append(f"\n唤醒事件统计:")
            report.append(f"  - 总唤醒事件数: {len(wakeup_events_df)}")
            
            if 'wakeup_quality' in wakeup_events_df.columns:
                quality_dist = wakeup_events_df['wakeup_quality'].value_counts()
                report.append("\n唤醒质量分布:")
                for quality, count in quality_dist.items():
                    report.append(f"  - {quality}: {count} ({count/len(wakeup_events_df)*100:.1f}%)")
        report.append("")
        
        report.append("-"*70)
        report.append("三、唤醒前后行为对比分析")
        report.append("-"*70)
        
        if summary_stats:
            report.append(f"分析的唤醒事件数: {summary_stats.get('total_wakeups', 0)}")
            report.append(f"平均沉默时长: {summary_stats.get('avg_silence_days', 0):.1f} 天")
            report.append(f"平均事件数变化: {summary_stats.get('avg_event_count_change', 0):+.1f}")
            report.append(f"转化为支付用户数: {summary_stats.get('converted_to_payment_count', 0)} "
                         f"({summary_stats.get('payment_conversion_rate_pct', 0):.1f}%)")
            
            event_changes = summary_stats.get('event_type_changes', {})
            if event_changes:
                report.append("\n各事件类型平均变化:")
                for event, stats in event_changes.items():
                    change_str = f"{stats['avg_change']:+.1f}"
                    if stats['pct_increase'] == float('inf'):
                        pct_str = "新增"
                    elif stats['pct_increase'] == float('-inf'):
                        pct_str = "消失"
                    else:
                        pct_str = f"{stats['pct_increase']:+.1f}%"
                    report.append(f"  {event}: {stats['avg_before']:.1f} -> {stats['avg_after']:.1f} "
                                 f"({change_str}, {pct_str})")
            
            quality_dist = summary_stats.get('wakeup_quality_distribution', {})
            if quality_dist:
                report.append("\n唤醒质量分布:")
                total = sum(quality_dist.values())
                for quality, count in quality_dist.items():
                    report.append(f"  {quality}: {count} ({count/total*100:.1f}%)")
        report.append("")
        
        report.append("-"*70)
        report.append("四、典型案例分析")
        report.append("-"*70)
        
        if comparisons:
            strong_wakeups = [c for c in comparisons if c.get('wakeup_quality') == 'strong']
            converted_wakeups = [c for c in comparisons if c.get('converted_to_payment')]
            long_silence_wakeups = sorted(
                [c for c in comparisons if c.get('silence_days', 0) > 60],
                key=lambda x: x.get('silence_days', 0),
                reverse=True
            )
            
            if strong_wakeups:
                case = strong_wakeups[0]
                report.append("\n【强唤醒案例】")
                report.append(f"  用户ID: {case.get('user_id', 'unknown')}")
                report.append(f"  沉默时长: {case.get('silence_days', 0):.1f} 天")
                report.append(f"  唤醒质量: {case.get('wakeup_quality', 'unknown')}")
                report.append(f"  事件数变化: {case.get('before_event_count', 0)} -> {case.get('after_event_count', 0)}")
                report.append(f"  转化为支付: {'是' if case.get('converted_to_payment') else '否'}")
                
                event_changes = case.get('event_changes', {})
                if event_changes:
                    report.append(f"  各事件变化:")
                    for evt, chg in event_changes.items():
                        report.append(f"    - {evt}: {chg['before']} -> {chg['after']} ({chg['change']:+d})")
            
            if converted_wakeups:
                case = converted_wakeups[0]
                report.append("\n【支付转化案例】")
                report.append(f"  用户ID: {case.get('user_id', 'unknown')}")
                report.append(f"  沉默时长: {case.get('silence_days', 0):.1f} 天")
                report.append(f"  唤醒前有支付: {'是' if case.get('before_has_payment') else '否'}")
                report.append(f"  唤醒后有支付: {'是' if case.get('after_has_payment') else '否'}")
                
                new_events = case.get('new_event_types', set())
                lost_events = case.get('lost_event_types', set())
                if new_events:
                    report.append(f"  新增事件类型: {', '.join(new_events)}")
                if lost_events:
                    report.append(f"  消失事件类型: {', '.join(lost_events)}")
            
            if long_silence_wakeups:
                case = long_silence_wakeups[0]
                report.append("\n【长期沉默后唤醒案例】")
                report.append(f"  用户ID: {case.get('user_id', 'unknown')}")
                report.append(f"  沉默时长: {case.get('silence_days', 0):.1f} 天")
                report.append(f"  沉默类型: {case.get('silence_type', 'unknown')}")
                report.append(f"  唤醒质量: {case.get('wakeup_quality', 'unknown')}")
        report.append("")
        
        report.append("-"*70)
        report.append("五、业务建议与洞察")
        report.append("-"*70)
        
        if summary_stats:
            payment_rate = summary_stats.get('payment_conversion_rate_pct', 0)
            if payment_rate > 15:
                report.append("✓ 唤醒用户支付转化率较高（>15%），说明唤醒策略效果良好")
            elif payment_rate > 5:
                report.append("△ 唤醒用户支付转化率中等（5%-15%），建议优化唤醒后的引导流程")
            else:
                report.append("⚠ 唤醒用户支付转化率较低（<5%），建议:")
                report.append("  - 分析唤醒渠道的精准度")
                report.append("  - 优化首屏展示内容")
                report.append("  - 设计针对性的回归激励活动")
            
            quality_dist = summary_stats.get('wakeup_quality_distribution', {})
            total = sum(quality_dist.values())
            strong_ratio = quality_dist.get('strong', 0) / total * 100 if total > 0 else 0
            
            if strong_ratio > 30:
                report.append(f"\n✓ 强唤醒用户占比高（{strong_ratio:.1f}%），用户回归质量较好")
            else:
                report.append(f"\n⚠ 弱唤醒用户较多（强唤醒占比 {strong_ratio:.1f}%），建议:")
                report.append("  - 关注唤醒后的首周留存")
                report.append("  - 设计渐进式的唤醒引导")
                report.append("  - 分析用户流失的具体原因")
        
        if id_mapping_summary:
            multi_id_count = id_mapping_summary.get('multi_id_virtual_users', 0)
            if multi_id_count > 0:
                report.append(f"\n⚠ 发现 {multi_id_count} 个用户存在多ID问题，建议:")
                report.append("  - 完善设备ID采集机制")
                report.append("  - 考虑引入账号绑定机制（手机号、第三方登录等）")
                report.append("  - 对高置信度归并的用户进行统一画像分析")
                report.append("  - 在分析时注意区分置信度等级")
        
        report.append("\n核心定义回顾:")
        report.append(f"  - 沉默: 连续 {SILENCE_THRESHOLD_DAYS} 天以上无任何事件记录")
        report.append(f"  - 唤醒: 沉默期后的第一个活跃事件")
        report.append(f"  - 分析窗口: 唤醒前后各 {ANALYSIS_WINDOW_DAYS} 天")
        report.append("")
        
        report.append("="*70)
        report.append("报告结束")
        report.append("="*70)
        
        return "\n".join(report)
    
    def plot_analysis_charts(self, 
                              silent_periods_df, 
                              wakeup_events_df, 
                              comparisons,
                              save_prefix='analysis'):
        """
        生成可视化图表
        
        参数:
            silent_periods_df: 沉默期数据框
            wakeup_events_df: 唤醒事件数据框
            comparisons: 对比结果列表
            save_prefix: 保存文件名前缀
        
        返回:
            dict: 图表对象字典 {name: matplotlib Figure}
        """
        if not PLOTTING_AVAILABLE:
            print("警告: 绘图库不可用，跳过图表生成")
            return {}
        
        figures = {}
        
        if not silent_periods_df.empty and 'silence_days' in silent_periods_df.columns:
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            ax1 = axes[0, 0]
            silent_periods_df['silence_days'].hist(bins=20, ax=ax1, edgecolor='black', alpha=0.7)
            ax1.axvline(x=SILENCE_THRESHOLD_DAYS, color='red', linestyle='--', 
                       label=f'沉默阈值 ({SILENCE_THRESHOLD_DAYS}天)')
            ax1.set_title('沉默时长分布', fontsize=12, fontweight='bold')
            ax1.set_xlabel('沉默天数')
            ax1.set_ylabel('频数')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            ax2 = axes[0, 1]
            if 'silence_type' in silent_periods_df.columns:
                silence_type_counts = silent_periods_df['silence_type'].value_counts()
                colors = plt.cm.Set3(np.linspace(0, 1, len(silence_type_counts)))
                silence_type_counts.plot(kind='bar', ax=ax2, color=colors, edgecolor='black')
                ax2.set_title('沉默类型分布', fontsize=12, fontweight='bold')
                ax2.set_xlabel('沉默类型')
                ax2.set_ylabel('数量')
                ax2.tick_params(axis='x', rotation=45)
                ax2.grid(True, alpha=0.3, axis='y')
            
            ax3 = axes[1, 0]
            if 'last_event_before' in silent_periods_df.columns:
                last_event_counts = silent_periods_df['last_event_before'].value_counts()
                colors = plt.cm.Pastel1(np.linspace(0, 1, len(last_event_counts)))
                last_event_counts.plot(kind='pie', ax=ax3, autopct='%1.1f%%', colors=colors,
                                      startangle=90, wedgeprops=dict(edgecolor='white'))
                ax3.set_title('沉默前最后事件类型', fontsize=12, fontweight='bold')
                ax3.set_ylabel('')
            
            ax4 = axes[1, 1]
            if 'first_event_after' in silent_periods_df.columns:
                first_event_counts = silent_periods_df['first_event_after'].value_counts()
                colors = plt.cm.Pastel2(np.linspace(0, 1, len(first_event_counts)))
                first_event_counts.plot(kind='pie', ax=ax4, autopct='%1.1f%%', colors=colors,
                                        startangle=90, wedgeprops=dict(edgecolor='white'))
                ax4.set_title('沉默后第一事件类型（唤醒事件）', fontsize=12, fontweight='bold')
                ax4.set_ylabel('')
            
            plt.tight_layout()
            figures['silence_analysis'] = fig
        
        if comparisons:
            fig2, axes = plt.subplots(1, 2, figsize=(14, 5))
            
            event_changes_data = []
            for c in comparisons:
                for event, changes in c.get('event_changes', {}).items():
                    event_changes_data.append({
                        'event': event,
                        'change': changes['change']
                    })
            
            if event_changes_data:
                changes_df = pd.DataFrame(event_changes_data)
                avg_changes = changes_df.groupby('event')['change'].mean().sort_values()
                
                ax1 = axes[0]
                colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in avg_changes.values]
                avg_changes.plot(kind='barh', ax=ax1, color=colors, edgecolor='black')
                ax1.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                ax1.set_title('各事件类型平均变化量（唤醒后-唤醒前）', fontsize=12, fontweight='bold')
                ax1.set_xlabel('平均变化量')
                ax1.set_ylabel('事件类型')
                ax1.grid(True, alpha=0.3, axis='x')
            
            quality_counts = {}
            for c in comparisons:
                q = c.get('wakeup_quality', 'unknown')
                quality_counts[q] = quality_counts.get(q, 0) + 1
            
            if quality_counts:
                ax2 = axes[1]
                quality_order = ['weak', 'medium', 'strong']
                counts = [quality_counts.get(q, 0) for q in quality_order]
                colors = ['#ff9999', '#ffcc99', '#99ff99']
                bars = ax2.bar(quality_order, counts, color=colors, edgecolor='black')
                ax2.set_title('唤醒质量分布', fontsize=12, fontweight='bold')
                ax2.set_xlabel('唤醒质量')
                ax2.set_ylabel('数量')
                ax2.grid(True, alpha=0.3, axis='y')
                
                for bar in bars:
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}',
                            ha='center', va='bottom')
            
            plt.tight_layout()
            figures['behavior_comparison'] = fig2
        
        return figures


def run_complete_analysis(n_real_users=100, multi_id_ratio=0.5, include_device_id=True, seed=42):
    """
    运行完整的分析流程
    
    参数:
        n_real_users: 模拟的真实用户数量
        multi_id_ratio: 有多ID问题的用户比例
        include_device_id: 是否包含设备ID字段
        seed: 随机种子
    
    返回:
        dict: 包含所有分析结果的字典
    """
    print("="*70)
    print("用户沉默与唤醒分析系统")
    print("="*70)
    
    print("\n[1/6] 生成模拟数据（包含多ID问题）...")
    simulator = DataSimulator()
    df = simulator.generate_dataset(
        n_real_users=n_real_users,
        multi_id_ratio=multi_id_ratio,
        include_device_id=include_device_id,
        seed=seed
    )
    
    print(f"\n数据生成完成:")
    print(f"  - 总事件数: {len(df)}")
    print(f"  - 原始用户ID数: {df['user_id'].nunique()}")
    if include_device_id:
        print(f"  - 设备ID数: {df['device_id'].nunique()}")
    if 'real_user_tag' in df.columns:
        print(f"  - 真实用户数: {df['real_user_tag'].nunique()}")
    print(f"  - 时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    print(f"\n事件类型分布:")
    print(df['event_name'].value_counts().to_string())
    
    print("\n[2/6] 多ID关联处理...")
    resolver = MultiIDResolver()
    id_mappings = resolver.resolve(df)
    df_with_virtual = resolver.apply_mapping(df)
    id_mapping_summary = resolver.get_mapping_summary()
    
    print(f"\n虚拟用户ID应用完成:")
    print(f"  - 虚拟用户数: {df_with_virtual['virtual_user_id'].nunique()}")
    print(f"\n归并置信度分布:")
    print(df_with_virtual['merge_confidence'].value_counts().to_string())
    
    print("\n[3/6] 沉默期和唤醒事件检测...")
    detector = SilenceWakeupDetector(silence_threshold_days=SILENCE_THRESHOLD_DAYS)
    
    silent_periods_df, wakeup_events_df, user_analysis_df = detector.detect_all_users(
        df_with_virtual, 
        user_id_col='virtual_user_id'
    )
    
    print("\n[4/6] 唤醒前后行为对比分析...")
    comparator = BehaviorComparator(window_days=ANALYSIS_WINDOW_DAYS)
    
    comparisons, summary_stats = comparator.analyze_all_wakeups(wakeup_events_df)
    
    print("\n[5/6] 生成分析报告...")
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
    
    print("\n[6/6] 生成可视化图表...")
    figures = reporter.plot_analysis_charts(
        silent_periods_df,
        wakeup_events_df,
        comparisons
    )
    
    print("\n" + "="*70)
    print("分析完成！")
    print("="*70)
    
    print("\n" + "-"*70)
    print("分析报告预览（前100行）")
    print("-"*70)
    report_lines = report.split('\n')
    print('\n'.join(report_lines[:100]))
    if len(report_lines) > 100:
        print(f"\n... 报告共 {len(report_lines)} 行，剩余部分已省略")
    
    output_data = {
        'original_data': df,
        'data_with_virtual_id': df_with_virtual,
        'id_mappings': id_mappings,
        'id_mapping_summary': id_mapping_summary,
        'silent_periods': silent_periods_df,
        'wakeup_events': wakeup_events_df,
        'user_analysis': user_analysis_df,
        'comparisons': comparisons,
        'summary_stats': summary_stats,
        'report': report,
        'figures': figures
    }
    
    return output_data


def analyze_real_data(df, user_id_col='user_id', device_id_col='device_id',
                       silence_threshold_days=30, analysis_window_days=7):
    """
    分析真实数据的便捷接口
    
    参数:
        df: 真实的用户行为日志数据框，需包含:
            - user_id: 用户ID
            - event_name: 事件名称
            - timestamp: 时间戳
            - device_id (可选): 设备ID（用于多ID关联）
        user_id_col: 用户ID列名
        device_id_col: 设备ID列名
        silence_threshold_days: 沉默阈值天数
        analysis_window_days: 分析窗口天数
    
    返回:
        dict: 包含所有分析结果的字典
    """
    global SILENCE_THRESHOLD_DAYS, ANALYSIS_WINDOW_DAYS
    SILENCE_THRESHOLD_DAYS = silence_threshold_days
    ANALYSIS_WINDOW_DAYS = analysis_window_days
    
    required_cols = [user_id_col, 'event_name', 'timestamp']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"缺少必需的列: {col}")
    
    df = df.copy()
    df.rename(columns={user_id_col: 'user_id'}, inplace=True)
    if device_id_col in df.columns:
        df.rename(columns={device_id_col: 'device_id'}, inplace=True)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print("="*70)
    print("真实数据 - 用户沉默与唤醒分析")
    print("="*70)
    
    print(f"\n数据概况:")
    print(f"  - 总事件数: {len(df)}")
    print(f"  - 用户ID数: {df['user_id'].nunique()}")
    if 'device_id' in df.columns:
        print(f"  - 设备ID数: {df['device_id'].nunique()}")
    print(f"  - 时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    
    print("\n[1/5] 多ID关联处理...")
    resolver = MultiIDResolver()
    id_mappings = resolver.resolve(df)
    df_with_virtual = resolver.apply_mapping(df)
    id_mapping_summary = resolver.get_mapping_summary()
    
    print("\n[2/5] 沉默期和唤醒事件检测...")
    detector = SilenceWakeupDetector(silence_threshold_days=silence_threshold_days)
    
    silent_periods_df, wakeup_events_df, user_analysis_df = detector.detect_all_users(
        df_with_virtual, 
        user_id_col='virtual_user_id'
    )
    
    print("\n[3/5] 唤醒前后行为对比分析...")
    comparator = BehaviorComparator(window_days=analysis_window_days)
    
    comparisons, summary_stats = comparator.analyze_all_wakeups(wakeup_events_df)
    
    print("\n[4/5] 生成分析报告...")
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
    
    print("\n[5/5] 生成可视化图表...")
    figures = reporter.plot_analysis_charts(
        silent_periods_df,
        wakeup_events_df,
        comparisons
    )
    
    print("\n" + "="*70)
    print("分析完成！")
    print("="*70)
    
    output_data = {
        'original_data': df,
        'data_with_virtual_id': df_with_virtual,
        'id_mappings': id_mappings,
        'id_mapping_summary': id_mapping_summary,
        'silent_periods': silent_periods_df,
        'wakeup_events': wakeup_events_df,
        'user_analysis': user_analysis_df,
        'comparisons': comparisons,
        'summary_stats': summary_stats,
        'report': report,
        'figures': figures
    }
    
    return output_data


if __name__ == "__main__":
    results = run_complete_analysis(
        n_real_users=100,
        multi_id_ratio=0.5,
        include_device_id=True,
        seed=42
    )
    
    print("\n" + "="*70)
    print("使用示例")
    print("="*70)
    print("""
# 方式一：使用模拟数据运行完整分析
from user_behavior_analyzer import run_complete_analysis
results = run_complete_analysis(n_real_users=100, multi_id_ratio=0.5)

# 访问结果
print(results['report'])                    # 完整文本报告
print(results['silent_periods'])            # 沉默期数据框
print(results['wakeup_events'])             # 唤醒事件数据框
print(results['summary_stats'])             # 汇总统计
print(results['comparisons'])               # 所有对比结果

# 方式二：使用真实数据
import pandas as pd
from user_behavior_analyzer import analyze_real_data

# 加载你的真实数据
df = pd.read_csv('your_log_data.csv')

# 运行分析
results = analyze_real_data(
    df,
    user_id_col='user_id',
    device_id_col='device_id',  # 可选
    silence_threshold_days=30,
    analysis_window_days=7
)

# 方式三：单独使用各个组件
from user_behavior_analyzer import MultiIDResolver, SilenceDetector, BehaviorComparator

# 1. 多ID关联
resolver = MultiIDResolver()
id_mappings = resolver.resolve(df)
df_with_virtual = resolver.apply_mapping(df)

# 2. 沉默期检测
detector = SilenceDetector(silence_threshold_days=30)
silent_df, wakeup_df, user_analysis = detector.detect_all_users(
    df_with_virtual, 
    user_id_col='virtual_user_id'
)

# 3. 行为对比分析
comparator = BehaviorComparator(window_days=7)
comparisons, summary = comparator.analyze_all_wakeups(wakeup_df)
""")