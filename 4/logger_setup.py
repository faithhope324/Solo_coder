#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志系统模块
- 支持同时输出到控制台和文件
- 支持日志级别（DEBUG, INFO, WARNING, ERROR）
- 自动创建日志目录
- 按日期轮转日志文件
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Optional


class LoggerSetup:
    """日志系统设置器"""
    
    _instance = None
    _logger = None
    _log_dir = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志系统"""
        if self._logger is not None:
            return
        
        self._setup_default_logger()
    
    def _setup_default_logger(self):
        """设置默认日志配置"""
        log_dir = self._get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'ecommerce_analysis.log')
        
        logger = logging.getLogger('ecommerce_analysis')
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        
        if logger.handlers:
            logger.handlers.clear()
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        self._logger = logger
        self._log_dir = log_dir
        
        logger.info("=" * 70)
        logger.info("电商用户行为分析系统 - 日志系统启动")
        logger.info(f"日志目录: {log_dir}")
        logger.info("=" * 70)
    
    def _get_log_dir(self) -> str:
        """获取日志目录"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'logs')
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 子模块名称，如果为None则返回根日志记录器
        
        Returns:
            配置好的日志记录器
        """
        if name is None:
            return self._logger
        
        child_logger = self._logger.getChild(name)
        child_logger.setLevel(self._logger.level)
        return child_logger
    
    def set_level(self, level: str):
        """
        设置日志级别
        
        Args:
            level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = level_map.get(level.upper(), logging.INFO)
        self._logger.setLevel(log_level)
        
        for handler in self._logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(max(log_level, logging.INFO))
            else:
                handler.setLevel(log_level)
        
        self._logger.info(f"日志级别已设置为: {level}")
    
    def get_log_dir(self) -> str:
        """获取日志目录路径"""
        return self._log_dir


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    便捷函数：获取日志记录器
    
    Args:
        name: 子模块名称
    
    Returns:
        配置好的日志记录器
    """
    setup = LoggerSetup()
    return setup.get_logger(name)


def set_log_level(level: str):
    """
    便捷函数：设置日志级别
    
    Args:
        level: 日志级别
    """
    setup = LoggerSetup()
    setup.set_level(level)


def get_log_dir() -> str:
    """
    便捷函数：获取日志目录
    
    Returns:
        日志目录路径
    """
    setup = LoggerSetup()
    return setup.get_log_dir()
