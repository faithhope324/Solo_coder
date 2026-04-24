#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据质量校验平台使用示例
"""

import os
import sqlite3
from datetime import datetime

from data_quality import (
    DataQualityEngine,
    CheckConfig,
    AlertConfig,
    ReportConfig,
    DataSourceConfig,
    AlertLevel,
)


def create_sample_database():
    """创建示例SQLite数据库"""
    db_path = "./sample_data.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            age INTEGER,
            created_at TEXT
        )
    """)

    cursor.execute("DELETE FROM users")

    sample_data = [
        (1, "张三", "zhangsan@example.com", 25, "2024-01-01"),
        (2, "李四", "lisi@example.com", None, "2024-01-02"),
        (3, "王五", None, 30, "2024-01-03"),
        (4, "赵六", "zhaoliu@example.com", 28, "2024-01-04"),
        (5, "钱七", "qianqi@example.com", 35, "2024-01-05"),
    ]

    cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?)", sample_data)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users_reference (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            age INTEGER,
            created_at TEXT
        )
    """)

    cursor.execute("DELETE FROM users_reference")
    cursor.executemany("INSERT INTO users_reference VALUES (?, ?, ?, ?, ?)", sample_data[:4])

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER,
            user_id INTEGER,
            amount REAL,
            status TEXT
        )
    """)

    cursor.execute("DELETE FROM orders")
    orders_data = [
        (1001, 1, 99.99, "paid"),
        (1002, 2, 199.99, "pending"),
        (1003, 1, 49.99, "paid"),
        (1001, 3, 299.99, "paid"),
        (1004, None, 150.00, "cancelled"),
    ]
    cursor.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", orders_data)

    conn.commit()
    conn.close()

    print(f"示例数据库已创建: {db_path}")
    return db_path


def run_data_quality_checks(db_path: str):
    """运行数据质量校验"""
    print("\n" + "=" * 60)
    print("开始运行数据质量校验")
    print("=" * 60)

    data_source = DataSourceConfig(
        name="main_db",
        connection_type="sqlite",
        connection_params={"db_path": db_path},
    )

    alert_config = AlertConfig(
        enabled=True,
        alert_channels=["console"],
    )

    report_config = ReportConfig(
        output_format="html",
        output_path="./reports",
        include_passed_checks=True,
        include_charts=True,
    )

    engine = DataQualityEngine(
        data_sources={"main_db": data_source},
        alert_config=alert_config,
        report_config=report_config,
    )

    check_configs = [
        CheckConfig(
            name="users_row_count_check",
            check_type="row_count",
            description="检查users表行数与参考表是否一致",
            data_source="main_db",
            table_name="users",
            reference_table="users_reference",
            threshold=0,
            alert_level=AlertLevel.HIGH,
        ),
        CheckConfig(
            name="email_null_rate_check",
            check_type="null_rate",
            description="检查email字段空值率",
            data_source="main_db",
            table_name="users",
            columns=["email"],
            threshold=10.0,
            alert_level=AlertLevel.MEDIUM,
        ),
        CheckConfig(
            name="age_null_rate_check",
            check_type="null_rate",
            description="检查age字段空值率",
            data_source="main_db",
            table_name="users",
            columns=["age"],
            threshold=20.0,
            alert_level=AlertLevel.MEDIUM,
        ),
        CheckConfig(
            name="orders_duplicate_key_check",
            check_type="duplicate_key",
            description="检查orders表order_id是否有重复",
            data_source="main_db",
            table_name="orders",
            primary_key="order_id",
            alert_level=AlertLevel.HIGH,
        ),
        CheckConfig(
            name="user_count_fluctuation_check",
            check_type="fluctuation",
            description="检查用户数量波动是否超过阈值",
            data_source="main_db",
            table_name="users",
            reference_value=10,
            fluctuation_percent=50.0,
            alert_level=AlertLevel.MEDIUM,
        ),
        CheckConfig(
            name="orders_user_id_null_check",
            check_type="null_rate",
            description="检查orders表user_id空值率",
            data_source="main_db",
            table_name="orders",
            columns=["user_id"],
            threshold=5.0,
            alert_level=AlertLevel.HIGH,
        ),
    ]

    print(f"\n共配置 {len(check_configs)} 个数据质量检查项")
    print("-" * 60)

    results = engine.run_checks(check_configs)

    print("\n" + "=" * 60)
    print("校验结果汇总")
    print("=" * 60)

    summary = engine.get_summary()

    print(f"\n总检查数: {summary['total_checks']}")
    print(f"通过数: {summary['passed_count']}")
    print(f"失败/警告数: {summary['failed_count']}")
    print(f"错误数: {summary['error_count']}")
    print(f"全部通过: {'是' if summary['all_passed'] else '否'}")

    print("\n" + "-" * 60)
    print("详细结果:")
    print("-" * 60)

    for result in results:
        status_icon = {
            "PASS": "[PASS]",
            "FAIL": "[FAIL]",
            "WARNING": "[WARN]",
            "ERROR": "[ERROR]",
        }.get(result.status.value, "[UNK]")

        print(f"\n{status_icon} {result.check_name}")
        print(f"   类型: {result.check_type}")
        print(f"   状态: {result.status.value}")
        print(f"   消息: {result.message}")
        print(f"   实际值: {result.actual_value}")
        print(f"   期望值: {result.expected_value}")
        print(f"   执行时间: {result.execution_time_ms:.2f}ms")

        if result.details:
            print(f"   详情: {result.details}")

    print("\n" + "=" * 60)
    print("生成质检报告")
    print("=" * 60)

    os.makedirs("./reports", exist_ok=True)
    report_path = engine.generate_report()
    print(f"\n报告已生成: {report_path}")

    return engine


def main():
    """主函数"""
    print("=" * 60)
    print("Python 数据质量校验平台演示")
    print("=" * 60)

    db_path = create_sample_database()
    engine = run_data_quality_checks(db_path)

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print(f"\n生成的文件:")
    print(f"  - 数据库: {db_path}")
    print(f"  - 报告: 请查看 ./reports 目录")


if __name__ == "__main__":
    main()
