"""
配置模块 - 支持YAML/JSON配置文件读取
"""
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load_yaml(config_path: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if not HAS_YAML:
            raise ImportError("PyYAML模块未安装，请运行: pip install pyyaml")
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    @staticmethod
    def load_json(config_path: str) -> Dict[str, Any]:
        """
        加载JSON配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config
    
    @classmethod
    def load(cls, config_path: str) -> Dict[str, Any]:
        """
        自动识别配置文件格式并加载
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        config_path = Path(config_path)
        suffix = config_path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            return cls.load_yaml(str(config_path))
        elif suffix == '.json':
            return cls.load_json(str(config_path))
        else:
            raise ValueError(f"不支持的配置文件格式: {suffix}")


class SyncConfig:
    """同步配置"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        初始化同步配置
        
        Args:
            config_dict: 配置字典
        """
        self._config = config_dict
    
    @property
    def mysql_config(self) -> Dict[str, Any]:
        """获取MySQL配置"""
        return self._config.get('mysql', {})
    
    @property
    def tables(self) -> List[Dict[str, Any]]:
        """获取表配置列表"""
        return self._config.get('tables', [])
    
    @property
    def output_dir(self) -> str:
        """获取输出目录"""
        return self._config.get('output', {}).get('dir', './output')
    
    @property
    def watermark_dir(self) -> str:
        """获取水印目录"""
        return self._config.get('output', {}).get('watermark_dir', './watermark')
    
    @property
    def log_dir(self) -> str:
        """获取日志目录"""
        return self._config.get('log', {}).get('dir', './logs')
    
    @property
    def log_level(self) -> str:
        """获取日志级别"""
        return self._config.get('log', {}).get('level', 'INFO')
    
    @property
    def batch_size(self) -> int:
        """获取批处理大小"""
        return self._config.get('extract', {}).get('batch_size', 10000)
    
    def get_table_config(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定表的配置
        
        Args:
            table_name: 表名
            
        Returns:
            表配置字典，不存在则返回None
        """
        for table in self.tables:
            if table.get('name') == table_name:
                return table
        return None
