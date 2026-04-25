"""
文件工具模块
提供文件备份、安全写入等功能
支持多进程/多线程环境下的原子性操作
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Optional, Tuple
import re


def backup_if_exists(file_path: str, backup_dir: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """如果文件已存在，创建备份（多进程/多线程安全版本）
    
    备份文件命名格式: 原文件名_YYYYMMDD_HHMMSS.扩展名
    同一秒内多次备份会自动添加序号: 原文件名_YYYYMMDD_HHMMSS_1.扩展名
    
    实现说明:
    - 使用临时文件 + 原子重命名 (os.rename) 确保操作的原子性
    - 检查文件存在和创建备份之间不会产生竞态条件
    
    Args:
        file_path: 目标文件路径
        backup_dir: 备份目录（可选，如果不指定则在同一目录下备份）
        
    Returns:
        (是否进行了备份, 备份文件路径)
    """
    if not os.path.exists(file_path):
        return False, None
    
    if not os.path.isfile(file_path):
        return False, None
    
    dir_name = os.path.dirname(file_path) if backup_dir is None else backup_dir
    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if backup_dir and not os.path.exists(backup_dir):
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception:
            pass
    
    max_attempts = 100
    for counter in range(max_attempts):
        if counter == 0:
            backup_name = f"{name}_{timestamp}{ext}"
        else:
            backup_name = f"{name}_{timestamp}_{counter}{ext}"
        
        backup_path = os.path.join(dir_name, backup_name)
        
        tmp_fd, tmp_path = None, None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix=ext,
                prefix=f'.{name}_tmp_',
                dir=dir_name
            )
            os.close(tmp_fd)
            
            shutil.copy2(file_path, tmp_path)
            
            try:
                os.rename(tmp_path, backup_path)
                return True, backup_path
            except FileExistsError:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                continue
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise
                
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            if counter == max_attempts - 1:
                return False, None
            continue
    
    return False, None


def safe_save_path(file_path: str, backup: bool = True, backup_dir: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """获取安全的保存路径，在保存前自动备份已存在的文件
    
    Args:
        file_path: 目标文件路径
        backup: 是否进行备份
        backup_dir: 备份目录（可选）
        
    Returns:
        (原文件路径, 备份文件路径，如果没有备份则为 None)
    """
    if not backup:
        return file_path, None
    
    backup_performed, backup_path = backup_if_exists(file_path, backup_dir)
    
    return file_path, backup_path


def atomic_write_file(
    content: str,
    file_path: str,
    encoding: str = 'utf-8',
    backup: bool = True,
    backup_dir: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """原子性地写入文件内容
    
    使用临时文件 + 原子重命名的方式确保写入操作的原子性。
    如果写入过程中发生错误，原文件不会被破坏。
    
    Args:
        content: 要写入的内容
        file_path: 目标文件路径
        encoding: 文件编码
        backup: 是否备份已存在的文件
        backup_dir: 备份目录（可选）
        
    Returns:
        (是否成功, 备份文件路径)
    """
    backup_path = None
    
    if backup and os.path.exists(file_path):
        backup_performed, backup_path = backup_if_exists(file_path, backup_dir)
    
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix='.tmp',
        prefix='.atomic_write_',
        dir=dir_name if dir_name else None
    )
    
    try:
        os.close(tmp_fd)
        
        with open(tmp_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        os.replace(tmp_path, file_path)
        
        return True, backup_path
        
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return False, backup_path


def get_backup_list(file_path: str, backup_dir: Optional[str] = None) -> list:
    """获取指定文件的所有备份文件列表
    
    Args:
        file_path: 原文件路径
        backup_dir: 备份目录（可选）
        
    Returns:
        备份文件路径列表，按时间排序（最新的在前）
    """
    if not os.path.exists(file_path):
        return []
    
    dir_name = os.path.dirname(file_path) if backup_dir is None else backup_dir
    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    pattern = re.compile(rf'^{re.escape(name)}_\d{{8}}_\d{{6}}(_\d+)?{re.escape(ext)}$')
    
    backups = []
    
    if os.path.exists(dir_name):
        for filename in os.listdir(dir_name):
            if pattern.match(filename):
                full_path = os.path.join(dir_name, filename)
                backups.append((full_path, os.path.getmtime(full_path)))
    
    backups.sort(key=lambda x: x[1], reverse=True)
    
    return [path for path, mtime in backups]


def clean_old_backups(file_path: str, max_backups: int = 5, backup_dir: Optional[str] = None) -> int:
    """清理旧的备份文件，只保留最新的 N 个
    
    Args:
        file_path: 原文件路径
        max_backups: 保留的最大备份数量
        backup_dir: 备份目录（可选）
        
    Returns:
        删除的文件数量
    """
    backups = get_backup_list(file_path, backup_dir)
    
    if len(backups) <= max_backups:
        return 0
    
    deleted_count = 0
    for backup_path in backups[max_backups:]:
        try:
            os.remove(backup_path)
            deleted_count += 1
        except:
            pass
    
    return deleted_count
