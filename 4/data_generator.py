import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple

from logger_setup import get_logger


class ECommerceDataGenerator:
    """电商用户行为数据生成器"""

    def __init__(self, num_users: int = 10000, num_products: int = 5000, 
                 num_events: int = 100000, start_date: str = '2024-01-01',
                 end_date: str = '2024-03-31', random_seed: int = 42):
        """
        初始化数据生成器
        
        Args:
            num_users: 用户数量
            num_products: 商品数量
            num_events: 行为事件数量
            start_date: 数据开始日期
            end_date: 数据结束日期
            random_seed: 随机种子
        """
        self.logger = get_logger('DataGenerator')
        self.num_users = num_users
        self.num_products = num_products
        self.num_events = num_events
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.random_seed = random_seed
        
        self.logger.info(f"初始化数据生成器: 用户={num_users:,}, 商品={num_products:,}, 事件={num_events:,}")
        self.logger.info(f"数据时间范围: {start_date} 至 {end_date}")
        
        np.random.seed(random_seed)
        random.seed(random_seed)
        
        # 定义行为类型及其转化概率
        self.event_types = ['view', 'click', 'add_to_cart', 'purchase', 'remove_from_cart', 'search']
        self.event_conversion_probs = {
            'view': 1.0,
            'click': 0.3,
            'add_to_cart': 0.15,
            'remove_from_cart': 0.05,
            'purchase': 0.08,
            'search': 0.4
        }
        
        # 商品类别
        self.product_categories = ['电子产品', '服装', '家居用品', '食品', '美妆', '运动器材', '图书', '玩具']
        
    def _generate_random_timestamp(self) -> datetime:
        """生成指定时间范围内的随机时间戳"""
        time_span = (self.end_date - self.start_date).total_seconds()
        random_seconds = np.random.randint(0, int(time_span))
        return self.start_date + timedelta(seconds=random_seconds)
    
    def _generate_user_ids(self) -> np.ndarray:
        """生成用户ID"""
        return np.arange(1, self.num_users + 1).astype(int)
    
    def _generate_product_data(self) -> pd.DataFrame:
        """生成商品数据"""
        product_data = {
            'product_id': np.arange(1, self.num_products + 1),
            'product_name': [f'商品_{i}' for i in range(1, self.num_products + 1)],
            'category': np.random.choice(self.product_categories, size=self.num_products),
            'price': np.round(np.random.uniform(10, 5000, size=self.num_products), 2)
        }
        return pd.DataFrame(product_data)
    
    def _generate_user_sessions(self, user_ids: np.ndarray) -> pd.DataFrame:
        """生成用户会话数据"""
        num_sessions = int(self.num_events * 0.3)
        session_data = {
            'session_id': np.arange(1, num_sessions + 1),
            'user_id': np.random.choice(user_ids, size=num_sessions),
            'start_time': [self._generate_random_timestamp() for _ in range(num_sessions)]
        }
        return pd.DataFrame(session_data)
    
    def _generate_event_data(self, user_ids: np.ndarray, product_data: pd.DataFrame, 
                            session_data: pd.DataFrame) -> pd.DataFrame:
        """生成用户行为事件数据（列级生成，更高效）"""
        
        # 预生成事件时间戳并排序
        event_timestamps = sorted([self._generate_random_timestamp() for _ in range(self.num_events)])
        
        # 列级生成：一次性生成所有列的数据
        n = self.num_events
        
        # 生成 event_id
        event_ids = np.arange(1, n + 1)
        
        # 生成 user_id
        user_ids_array = np.random.choice(user_ids, size=n)
        
        # 从 product_data 中随机采样商品
        product_indices = np.random.choice(len(product_data), size=n)
        product_ids = product_data['product_id'].values[product_indices]
        categories = product_data['category'].values[product_indices]
        prices = product_data['price'].values[product_indices]
        
        # 生成事件类型
        event_types = np.array([self._generate_event_type() for _ in range(n)])
        
        # 从 session_data 中随机采样会话
        session_indices = np.random.choice(len(session_data), size=n)
        session_ids = session_data['session_id'].values[session_indices]
        
        # 生成设备类型
        device_types = np.random.choice(['mobile', 'desktop', 'tablet'], size=n)
        
        # 生成 page_url
        page_urls = [f'/product/{pid}' for pid in product_ids]
        
        # 生成来源渠道
        referrers = np.random.choice(['google', 'baidu', 'direct', 'social_media', 'email'], size=n)
        
        # 创建 DataFrame（列级方式，更高效）
        event_data = {
            'event_id': event_ids,
            'user_id': user_ids_array,
            'session_id': session_ids,
            'product_id': product_ids,
            'category': categories,
            'price': prices,
            'event_type': event_types,
            'timestamp': event_timestamps,
            'device_type': device_types,
            'page_url': page_urls,
            'referrer': referrers
        }
        
        return pd.DataFrame(event_data)
    
    def _generate_event_type(self) -> str:
        """根据转化概率生成行为类型"""
        types = list(self.event_conversion_probs.keys())
        probs = list(self.event_conversion_probs.values())
        probs = np.array(probs) / sum(probs)  # 归一化
        return np.random.choice(types, p=probs)
    
    def _add_dirty_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加脏数据（缺失值、异常值、格式错误）用于测试数据清洗"""
        df = df.copy()
        
        # 添加缺失值
        missing_rate = 0.05  # 5% 的缺失值
        for col in ['product_id', 'category', 'price', 'device_type']:
            df.loc[np.random.choice(df.index, size=int(len(df) * missing_rate)), col] = np.nan
        
        # 添加时间戳格式错误
        if 'timestamp' in df.columns:
            # 先将 timestamp 列转换为 object 类型，以便添加字符串格式的错误值
            df['timestamp'] = df['timestamp'].astype(object)
            bad_indices = np.random.choice(df.index, size=int(len(df) * 0.02))
            for idx in bad_indices:
                df.loc[idx, 'timestamp'] = 'invalid_date_format'
        
        # 添加异常价格值
        if 'price' in df.columns:
            bad_indices = np.random.choice(df.index, size=int(len(df) * 0.03))
            for idx in bad_indices:
                df.loc[idx, 'price'] = np.random.choice([-100, 0, 999999, np.inf])
        
        # 添加重复行
        duplicates = df.sample(n=int(len(df) * 0.02))
        df = pd.concat([df, duplicates], ignore_index=True)
        
        return df
    
    def generate(self, add_dirty_data: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        生成完整的电商数据
        
        Args:
            add_dirty_data: 是否添加脏数据用于测试
        
        Returns:
            包含 (事件数据, 商品数据, 会话数据) 的元组
        """
        self.logger.info("开始生成电商用户行为数据...")
        print("正在生成电商用户行为数据...")
        
        user_ids = self._generate_user_ids()
        product_data = self._generate_product_data()
        session_data = self._generate_user_sessions(user_ids)
        
        event_data = self._generate_event_data(user_ids, product_data, session_data)
        
        if add_dirty_data:
            self.logger.info("正在添加脏数据用于测试数据清洗...")
            print("正在添加脏数据用于测试数据清洗...")
            event_data = self._add_dirty_data(event_data)
        
        self.logger.info(f"数据生成完成: 事件={len(event_data):,}, 商品={len(product_data):,}, 会话={len(session_data):,}")
        print(f"生成完成：")
        print(f"  - 用户行为事件: {len(event_data)} 条")
        print(f"  - 商品: {len(product_data)} 件")
        print(f"  - 会话: {len(session_data)} 个")
        
        return event_data, product_data, session_data
    
    def save_to_csv(self, event_data: pd.DataFrame, product_data: pd.DataFrame, 
                   session_data: pd.DataFrame, output_dir: str = './data') -> None:
        """
        保存数据到 CSV 文件
        
        Args:
            event_data: 事件数据
            product_data: 商品数据
            session_data: 会话数据
            output_dir: 输出目录
        """
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        event_path = os.path.join(output_dir, 'user_events.csv')
        event_data.to_csv(event_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"事件数据已保存到: {event_path}")
        print(f"事件数据已保存到: {event_path}")
        
        product_path = os.path.join(output_dir, 'products.csv')
        product_data.to_csv(product_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"商品数据已保存到: {product_path}")
        print(f"商品数据已保存到: {product_path}")
        
        session_path = os.path.join(output_dir, 'sessions.csv')
        session_data.to_csv(session_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"会话数据已保存到: {session_path}")
        print(f"会话数据已保存到: {session_path}")


if __name__ == '__main__':
    # 示例用法
    generator = ECommerceDataGenerator(
        num_users=10000,
        num_products=5000,
        num_events=100000,
        start_date='2024-01-01',
        end_date='2024-03-31'
    )
    
    events, products, sessions = generator.generate(add_dirty_data=True)
    generator.save_to_csv(events, products, sessions)
