"""
异常重试装饰器模块 - 支持指数退避、可配置的重试策略
"""
import time
import logging
from typing import Type, Tuple, Optional, Callable, Any
from functools import wraps


class RetryExhaustedError(Exception):
    """重试耗尽异常"""
    pass


def retry(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exponential_backoff: bool = True,
    max_wait_seconds: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        wait_seconds: 初始等待时间(秒)
        exponential_backoff: 是否使用指数退避
        max_wait_seconds: 最大等待时间(秒)
        retry_exceptions: 需要重试的异常类型元组
        logger: 日志记录器
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_wait = wait_seconds
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        actual_wait = min(current_wait, max_wait_seconds)
                        
                        log_msg = (
                            f"函数 {func.__name__} 第 {attempt} 次执行失败: {type(e).__name__}: {e}. "
                            f"等待 {actual_wait} 秒后重试 (剩余 {max_attempts - attempt} 次)"
                        )
                        
                        if logger:
                            logger.warning(log_msg)
                        else:
                            print(log_msg)
                        
                        time.sleep(actual_wait)
                        
                        if exponential_backoff:
                            current_wait *= 2
                    else:
                        log_msg = (
                            f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败: "
                            f"{type(e).__name__}: {e}"
                        )
                        
                        if logger:
                            logger.error(log_msg)
                        else:
                            print(log_msg)
            
            raise RetryExhaustedError(
                f"重试 {max_attempts} 次后仍然失败"
            ) from last_exception
        
        return wrapper
    return decorator


def mysql_retry(
    max_attempts: int = 5,
    wait_seconds: float = 2.0,
    logger: Optional[logging.Logger] = None
):
    """
    MySQL专用重试装饰器 - 针对MySQL常见异常进行重试
    
    Args:
        max_attempts: 最大重试次数
        wait_seconds: 初始等待时间
        logger: 日志记录器
        
    Returns:
        装饰器函数
    """
    import pymysql
    
    mysql_retry_exceptions = (
        pymysql.OperationalError,
        pymysql.InterfaceError,
        pymysql.InternalError,
        TimeoutError,
        ConnectionResetError,
    )
    
    return retry(
        max_attempts=max_attempts,
        wait_seconds=wait_seconds,
        exponential_backoff=True,
        max_wait_seconds=30.0,
        retry_exceptions=mysql_retry_exceptions,
        logger=logger
    )
