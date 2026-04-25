#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试会话漏斗分析的严格版逻辑
- 时间顺序检查
- 时间窗口检查
- 阶段完整性检查
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from funnel_analysis import FunnelAnalyzer


def create_test_data():
    """创建测试数据，包含各种边界情况"""
    
    data = []
    
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    # 测试用例1: 完美转化路径
    # view -> search -> click -> add_to_cart -> purchase
    # 时间顺序正确，间隔在30分钟内，没有跳阶段
    session_1_events = [
        {'session_id': 'session_001', 'user_id': 'user_001', 'event_type': 'view', 'timestamp': base_time},
        {'session_id': 'session_001', 'user_id': 'user_001', 'event_type': 'search', 'timestamp': base_time + timedelta(minutes=2)},
        {'session_id': 'session_001', 'user_id': 'user_001', 'event_type': 'click', 'timestamp': base_time + timedelta(minutes=5)},
        {'session_id': 'session_001', 'user_id': 'user_001', 'event_type': 'add_to_cart', 'timestamp': base_time + timedelta(minutes=10)},
        {'session_id': 'session_001', 'user_id': 'user_001', 'event_type': 'purchase', 'timestamp': base_time + timedelta(minutes=15)},
    ]
    data.extend(session_1_events)
    
    # 测试用例2: 时间顺序错误（purchase 在 click 之前）
    session_2_events = [
        {'session_id': 'session_002', 'user_id': 'user_002', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=1)},
        {'session_id': 'session_002', 'user_id': 'user_002', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=1, minutes=2)},
        {'session_id': 'session_002', 'user_id': 'user_002', 'event_type': 'purchase', 'timestamp': base_time + timedelta(hours=1, minutes=3)},
        {'session_id': 'session_002', 'user_id': 'user_002', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=1, minutes=5)},
    ]
    data.extend(session_2_events)
    
    # 测试用例3: 时间窗口超过（search 和 click 之间间隔45分钟，超过30分钟阈值）
    session_3_events = [
        {'session_id': 'session_003', 'user_id': 'user_003', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=2)},
        {'session_id': 'session_003', 'user_id': 'user_003', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=2, minutes=5)},
        {'session_id': 'session_003', 'user_id': 'user_003', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=2, minutes=50)},
        {'session_id': 'session_003', 'user_id': 'user_003', 'event_type': 'add_to_cart', 'timestamp': base_time + timedelta(hours=2, minutes=55)},
    ]
    data.extend(session_3_events)
    
    # 测试用例4: 跳阶段（直接从 view 到 click，跳过 search）
    session_4_events = [
        {'session_id': 'session_004', 'user_id': 'user_004', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=3)},
        {'session_id': 'session_004', 'user_id': 'user_004', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=3, minutes=5)},
        {'session_id': 'session_004', 'user_id': 'user_004', 'event_type': 'add_to_cart', 'timestamp': base_time + timedelta(hours=3, minutes=10)},
    ]
    data.extend(session_4_events)
    
    # 测试用例5: 只有部分阶段
    session_5_events = [
        {'session_id': 'session_005', 'user_id': 'user_005', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=4)},
        {'session_id': 'session_005', 'user_id': 'user_005', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=4, minutes=2)},
    ]
    data.extend(session_5_events)
    
    # 测试用例6: 重复同一阶段
    session_6_events = [
        {'session_id': 'session_006', 'user_id': 'user_006', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=5)},
        {'session_id': 'session_006', 'user_id': 'user_006', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=5, minutes=2)},
        {'session_id': 'session_006', 'user_id': 'user_006', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=5, minutes=3)},
        {'session_id': 'session_006', 'user_id': 'user_006', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=5, minutes=5)},
    ]
    data.extend(session_6_events)
    
    # 测试用例7: 允许跳阶段（宽松模式）
    session_7_events = [
        {'session_id': 'session_007', 'user_id': 'user_007', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=6)},
        {'session_id': 'session_007', 'user_id': 'user_007', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=6, minutes=5)},
        {'session_id': 'session_007', 'user_id': 'user_007', 'event_type': 'add_to_cart', 'timestamp': base_time + timedelta(hours=6, minutes=10)},
    ]
    data.extend(session_7_events)
    
    # 测试用例8: 时间刚好在窗口内（29分钟）
    session_8_events = [
        {'session_id': 'session_008', 'user_id': 'user_008', 'event_type': 'view', 'timestamp': base_time + timedelta(hours=7)},
        {'session_id': 'session_008', 'user_id': 'user_008', 'event_type': 'search', 'timestamp': base_time + timedelta(hours=7, minutes=29)},
        {'session_id': 'session_008', 'user_id': 'user_008', 'event_type': 'click', 'timestamp': base_time + timedelta(hours=7, minutes=35)},
    ]
    data.extend(session_8_events)
    
    return pd.DataFrame(data)


def test_session_funnel():
    """测试会话漏斗分析的严格版逻辑"""
    
    print("=" * 80)
    print("测试会话漏斗分析的严格版逻辑")
    print("=" * 80)
    
    df = create_test_data()
    
    print("\n测试数据概览:")
    print(f"  总行数: {len(df)}")
    print(f"  会话数: {df['session_id'].nunique()}")
    print(f"  用户数: {df['user_id'].nunique()}")
    
    print("\n测试数据详情（按会话分组）:")
    for session_id in sorted(df['session_id'].unique()):
        session_events = df[df['session_id'] == session_id].sort_values('timestamp')
        print(f"\n  {session_id}:")
        for _, row in session_events.iterrows():
            time_str = row['timestamp'].strftime('%H:%M:%S')
            print(f"    {time_str} - {row['event_type']}")
    
    analyzer = FunnelAnalyzer()
    
    print("\n" + "=" * 80)
    print("测试1: 严格模式（默认）- 不允许跳阶段，时间窗口30分钟")
    print("=" * 80)
    
    result_strict = analyzer.analyze_session_funnel(
        df,
        max_time_window_minutes=30,
        allow_skipped_stages=False,
        use_strict_check=True
    )
    
    print("\n会话分析结果:")
    session_analysis = result_strict['session_analysis']
    for _, row in session_analysis.iterrows():
        stages = row['stages_reached']
        max_stage = row['max_stage_reached']
        duration = row.get('total_duration_minutes', 'N/A')
        valid = row.get('valid_conversion_path', 'N/A')
        break_reason = row.get('break_reason', 'N/A')
        
        print(f"\n  {row['session_id']}:")
        print(f"    到达阶段: {stages}")
        print(f"    最大阶段: {max_stage}")
        print(f"    转化时长: {duration} 分钟")
        print(f"    有效路径: {valid}")
        print(f"    中断原因: {break_reason}")
    
    print("\n" + "=" * 80)
    print("测试2: 宽松模式 - 允许跳阶段，时间窗口30分钟")
    print("=" * 80)
    
    result_loose = analyzer.analyze_session_funnel(
        df,
        max_time_window_minutes=30,
        allow_skipped_stages=True,
        use_strict_check=True
    )
    
    print("\n会话分析结果（宽松模式）:")
    session_analysis_loose = result_loose['session_analysis']
    for _, row in session_analysis_loose.iterrows():
        stages = row['stages_reached']
        max_stage = row['max_stage_reached']
        print(f"\n  {row['session_id']}: {stages} (max: {max_stage})")
    
    print("\n" + "=" * 80)
    print("测试3: 简化模式 - 不检查时间顺序和时间窗口（旧版行为）")
    print("=" * 80)
    
    result_simple = analyzer.analyze_session_funnel(
        df,
        use_strict_check=False
    )
    
    print("\n会话分析结果（简化模式）:")
    session_analysis_simple = result_simple['session_analysis']
    for _, row in session_analysis_simple.iterrows():
        stages = row['stages_reached']
        max_stage = row['max_stage_reached']
        print(f"\n  {row['session_id']}: {stages} (max: {max_stage})")
    
    print("\n" + "=" * 80)
    print("测试结果对比")
    print("=" * 80)
    
    comparison_data = []
    for session_id in sorted(df['session_id'].unique()):
        strict_row = session_analysis[session_analysis['session_id'] == session_id].iloc[0]
        loose_row = session_analysis_loose[session_analysis_loose['session_id'] == session_id].iloc[0]
        simple_row = session_analysis_simple[session_analysis_simple['session_id'] == session_id].iloc[0]
        
        comparison_data.append({
            'session_id': session_id,
            '严格模式': strict_row['stages_reached'],
            '宽松模式': loose_row['stages_reached'],
            '简化模式': simple_row['stages_reached'],
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("关键测试用例验证")
    print("=" * 80)
    
    test_cases = {
        'session_001': {
            'name': '完美转化路径',
            'expected_strict': ['view', 'search', 'click', 'add_to_cart', 'purchase'],
            'expected_loose': ['view', 'search', 'click', 'add_to_cart', 'purchase'],
            'expected_simple': ['view', 'search', 'click', 'add_to_cart', 'purchase'],
        },
        'session_002': {
            'name': '时间顺序错误（purchase在click之前）',
            'expected_strict': ['view', 'search'],
            'expected_loose': ['view', 'search', 'purchase'],
            'expected_simple': ['view', 'search', 'click', 'purchase'],
        },
        'session_003': {
            'name': '时间窗口超过（45分钟>30分钟）',
            'expected_strict': ['view', 'search'],
            'expected_loose': ['view', 'search'],
            'expected_simple': ['view', 'search', 'click', 'add_to_cart'],
        },
        'session_004': {
            'name': '跳阶段（view直接到click）',
            'expected_strict': ['view'],
            'expected_loose': ['view', 'click', 'add_to_cart'],
            'expected_simple': ['view', 'click', 'add_to_cart'],
        },
        'session_008': {
            'name': '时间刚好在窗口内（29分钟）',
            'expected_strict': ['view', 'search', 'click'],
            'expected_loose': ['view', 'search', 'click'],
            'expected_simple': ['view', 'search', 'click'],
        },
    }
    
    all_passed = True
    for session_id, expected in test_cases.items():
        print(f"\n测试用例: {expected['name']} ({session_id})")
        
        strict_row = session_analysis[session_analysis['session_id'] == session_id].iloc[0]
        loose_row = session_analysis_loose[session_analysis_loose['session_id'] == session_id].iloc[0]
        simple_row = session_analysis_simple[session_analysis_simple['session_id'] == session_id].iloc[0]
        
        strict_match = strict_row['stages_reached'] == expected['expected_strict']
        loose_match = loose_row['stages_reached'] == expected['expected_loose']
        simple_match = simple_row['stages_reached'] == expected['expected_simple']
        
        print(f"  严格模式: {strict_row['stages_reached']} (预期: {expected['expected_strict']}) {'✓' if strict_match else '✗'}")
        print(f"  宽松模式: {loose_row['stages_reached']} (预期: {expected['expected_loose']}) {'✓' if loose_match else '✗'}")
        print(f"  简化模式: {simple_row['stages_reached']} (预期: {expected['expected_simple']}) {'✓' if simple_match else '✗'}")
        
        if not (strict_match and loose_match and simple_match):
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ 所有关键测试用例通过！")
    else:
        print("✗ 部分测试用例失败，请检查逻辑")
    print("=" * 80)
    
    return all_passed


if __name__ == '__main__':
    test_session_funnel()
