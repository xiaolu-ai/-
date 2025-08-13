# -*- coding: utf-8 -*-
"""
配置管理模块
负责应用配置的加载、保存和管理
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: str = "settings.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件名，默认为 settings.json
        """
        self.config_file = Path(config_file)
        self.config_data = {}
        self.load_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            "screenshot": {
                "save_directory": str(Path.home() / "Desktop" / "Screenshots"),
                "batch_interval": 5,
                "auto_annotation": True,
                "font_size": 16,
                "font_color": "#FFFFFF"
            },
            "player": {
                "default_volume": 80,
                "remember_position": True,
                "default_playback_rate": 1.0
            },
            "annotation": {
                "default_color": "#FF0000",
                "line_width": 3,
                "arrow_size": 10
            },
            "ui": {
                "window_geometry": [100, 100, 1200, 800],
                "last_video_directory": str(Path.home() / "Videos")
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置
        
        Returns:
            配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                    print(f"配置已从 {self.config_file} 加载")
            else:
                # 配置文件不存在，使用默认配置
                self.config_data = self.get_default_config()
                self.save_config(self.config_data)
                print(f"使用默认配置并创建 {self.config_file}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载配置文件失败: {e}")
            print("使用默认配置")
            self.config_data = self.get_default_config()
            self.save_config(self.config_data)
        
        return self.config_data
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典，如果为 None 则保存当前配置
            
        Returns:
            保存是否成功
        """
        try:
            if config is not None:
                self.config_data = config
            
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            
            print(f"配置已保存到 {self.config_file}")
            return True
        except IOError as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项值
        
        Args:
            key: 配置项键，支持点号分隔的嵌套键如 'player.volume'
            default: 默认值
            
        Returns:
            配置项值
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项值
        
        Args:
            key: 配置项键，支持点号分隔的嵌套键如 'player.volume'
            value: 配置项值
        """
        keys = key.split('.')
        config = self.config_data
        
        # 导航到最后一级的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置最后一级的值
        config[keys[-1]] = value
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        批量更新配置项
        
        Args:
            updates: 要更新的配置项字典
        """
        def deep_update(base_dict: Dict, update_dict: Dict) -> None:
            """递归更新字典"""
            for key, value in update_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self.config_data, updates)


# 全局配置管理器实例
config_manager = ConfigManager()