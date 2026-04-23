"""
日志模块 - 支持日志落地、控制台输出、日志轮转
"""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


def get_logger(name: str, log_dir: str = None, level: str = 'INFO') -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录，如果为None则仅输出到控制台
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'{name}_{today}.log')
        
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_execution_time(logger: logging.Logger = None):
    """
    记录函数执行时间的装饰器
    
    Args:
        logger: 日志记录器，如果为None则使用print输出
    """
    def decorator(func):
        from functools import wraps
        import time
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            
            message = f"函数 {func.__name__} 执行完成，耗时: {execution_time:.2f} 秒"
            
            if logger:
                logger.info(message)
            else:
                print(message)
            
            return result
        return wrapper
    return decorator
