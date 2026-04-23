"""
MySQL客户端模块 - 支持连接池、查询操作、元数据获取
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import List, Dict, Any, Optional, Tuple
import logging


class MySQLClient:
    """MySQL客户端类"""
    
    def __init__(self, host: str, port: int, user: str, password: str, 
                 database: str, charset: str = 'utf8mb4', 
                 connect_timeout: int = 30, logger: logging.Logger = None):
        """
        初始化MySQL客户端
        
        Args:
            host: MySQL主机地址
            port: MySQL端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            connect_timeout: 连接超时时间(秒)
            logger: 日志记录器
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.connect_timeout = connect_timeout
        self.logger = logger or logging.getLogger(__name__)
        self._connection = None
    
    def _ping_connection(self, conn: pymysql.connections.Connection) -> bool:
        """
        检测连接是否真正可用（心跳检测）
        
        Args:
            conn: 连接对象
            
        Returns:
            True: 连接可用, False: 连接已失效
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False
    
    def _get_connection(self) -> pymysql.connections.Connection:
        """
        获取数据库连接（包含假连接检测）
        
        Returns:
            pymysql连接对象
        """
        need_reconnect = True
        
        if self._connection is not None and self._connection.open:
            if self._ping_connection(self._connection):
                need_reconnect = False
            else:
                self.logger.warning("检测到假连接，尝试重新连接...")
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None
        
        if need_reconnect:
            self.logger.info(f"连接到MySQL: {self.host}:{self.port}/{self.database}")
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                connect_timeout=self.connect_timeout,
                cursorclass=DictCursor
            )
        
        return self._connection
    
    def close(self):
        """关闭数据库连接"""
        if self._connection and self._connection.open:
            self._connection.close()
            self.logger.info("数据库连接已关闭")
            self._connection = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数列表
            
        Returns:
            查询结果列表，每行为字典
        """
        conn = self._get_connection()
        with conn.cursor() as cursor:
            self.logger.debug(f"执行SQL: {sql}")
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            result = cursor.fetchall()
            return result
    
    def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        执行更新SQL (INSERT/UPDATE/DELETE)
        
        Args:
            sql: SQL语句
            params: 参数列表
            
        Returns:
            受影响的行数
        """
        conn = self._get_connection()
        with conn.cursor() as cursor:
            self.logger.debug(f"执行SQL: {sql}")
            if params:
                affected_rows = cursor.execute(sql, params)
            else:
                affected_rows = cursor.execute(sql)
            conn.commit()
            return affected_rows
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Args:
            table_name: 表名
            
        Returns:
            列信息列表
        """
        sql = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE,
            IS_NULLABLE,
            COLUMN_KEY,
            COLUMN_DEFAULT,
            EXTRA
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
        """
        return self.execute_query(sql, (self.database, table_name))
    
    def get_primary_keys(self, table_name: str) -> List[str]:
        """
        获取表的主键列名
        
        Args:
            table_name: 表名
            
        Returns:
            主键列名列表
        """
        sql = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s 
          AND TABLE_NAME = %s 
          AND CONSTRAINT_NAME = 'PRIMARY'
        ORDER BY ORDINAL_POSITION
        """
        result = self.execute_query(sql, (self.database, table_name))
        return [row['COLUMN_NAME'] for row in result]
    
    def get_table_count(self, table_name: str, condition: str = None) -> int:
        """
        获取表的记录数
        
        Args:
            table_name: 表名
            condition: 可选的WHERE条件
            
        Returns:
            记录数
        """
        sql = f"SELECT COUNT(*) as cnt FROM `{table_name}`"
        if condition:
            sql += f" WHERE {condition}"
        result = self.execute_query(sql)
        return result[0]['cnt'] if result else 0
    
    def get_min_max_value(self, table_name: str, column_name: str, 
                          condition: str = None) -> Tuple[Optional[Any], Optional[Any]]:
        """
        获取列的最小和最大值
        
        Args:
            table_name: 表名
            column_name: 列名
            condition: 可选的WHERE条件
            
        Returns:
            (最小值, 最大值)元组
        """
        sql = f"SELECT MIN(`{column_name}`) as min_val, MAX(`{column_name}`) as max_val FROM `{table_name}`"
        if condition:
            sql += f" WHERE {condition}"
        result = self.execute_query(sql)
        if result:
            return result[0]['min_val'], result[0]['max_val']
        return None, None
