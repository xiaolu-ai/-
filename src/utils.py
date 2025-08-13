# -*- coding: utf-8 -*-
"""
工具函数模块
包含时间格式化、文件处理等通用工具函数
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class SaveImageThread(QThread):
    """保存图像的后台线程"""
    
    finished = Signal(bool, str)  # 保存完成信号 (成功状态, 文件路径)
    error = Signal(str, str)     # 错误信号 (错误信息, 文件路径)
    
    def __init__(self, image: QImage, file_path: str, parent=None):
        super().__init__(parent)
        self.image = image
        self.file_path = file_path
        
    def run(self):
        """线程执行体"""
        try:
            # 确保保存目录存在
            save_dir = Path(self.file_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            success = self.image.save(self.file_path, "PNG")
            
            if success:
                self.finished.emit(True, self.file_path)
            else:
                self.error.emit(f"QImage::save() 返回 false", self.file_path)
                
        except Exception as e:
            self.error.emit(f"保存图像时发生异常: {str(e)}", self.file_path)


class ErrorHandler:
    """错误处理工具类"""
    
    @staticmethod
    def show_message(title: str, message: str, icon: QMessageBox.Icon = QMessageBox.Information, parent=None):
        """
        显示一个通用的消息框
        
        Args:
            title: 消息框标题
            message: 消息内容
            icon: 消息框图标
            parent: 父窗口
        """
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    @staticmethod
    def show_info(title: str, message: str, parent=None):
        """显示信息消息框"""
        ErrorHandler.show_message(title, message, QMessageBox.Information, parent)

    @staticmethod
    def show_warning(title: str, message: str, parent=None):
        """显示警告消息框"""
        ErrorHandler.show_message(title, message, QMessageBox.Warning, parent)

    @staticmethod
    def show_critical(title: str, message: str, parent=None):
        """显示严重错误消息框"""
        ErrorHandler.show_message(title, message, QMessageBox.Critical, parent)


class TimeFormatter:
    """时间格式化工具类"""
    
    @staticmethod
    def ms_to_time_string(milliseconds: int) -> str:
        """
        将毫秒转换为时间字符串格式 HH:MM:SS
        
        Args:
            milliseconds: 毫秒数
            
        Returns:
            格式化的时间字符串
        """
        if milliseconds < 0:
            return "00:00:00"
        
        seconds = milliseconds // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def time_string_to_ms(time_string: str) -> int:
        """
        将时间字符串转换为毫秒
        
        Args:
            time_string: 时间字符串，格式为 HH:MM:SS 或 MM:SS
            
        Returns:
            毫秒数
        """
        try:
            parts = time_string.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                hours = 0
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
            else:
                return 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds * 1000
        except (ValueError, IndexError):
            return 0
    
    @staticmethod
    def get_current_timestamp() -> str:
        """
        获取当前时间戳字符串
        
        Returns:
            当前时间戳字符串，格式为 YYYY-MM-DD_HH-MM-SS
        """
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


class FileManager:
    """文件管理工具类"""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> bool:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            目录是否存在或创建成功
        """
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except OSError as e:
            print(f"创建目录失败: {e}")
            return False
    
    @staticmethod
    def get_safe_filename(filename: str) -> str:
        """
        获取安全的文件名，移除或替换不安全的字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        # 定义不安全的字符
        unsafe_chars = '<>:"/\\|?*'
        safe_filename = filename
        
        # 替换不安全的字符
        for char in unsafe_chars:
            safe_filename = safe_filename.replace(char, '_')
        
        # 移除前后空格和点号
        safe_filename = safe_filename.strip(' .')
        
        # 如果文件名为空，使用默认名称
        if not safe_filename:
            safe_filename = "untitled"
        
        return safe_filename
    
    @staticmethod
    def get_video_filename_without_extension(file_path: str) -> str:
        """
        获取视频文件名（不包含扩展名）
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            不包含扩展名的文件名
        """
        return Path(file_path).stem
    
    @staticmethod
    def get_unique_filename(directory: str, base_name: str, extension: str) -> str:
        """
        获取唯一的文件名，如果文件已存在则添加数字后缀
        
        Args:
            directory: 目录路径
            base_name: 基础文件名
            extension: 文件扩展名
            
        Returns:
            唯一的文件路径
        """
        directory_path = Path(directory)
        counter = 1
        
        # 构建初始文件路径
        file_path = directory_path / f"{base_name}.{extension}"
        
        # 如果文件不存在，直接返回
        if not file_path.exists():
            return str(file_path)
        
        # 文件存在，添加数字后缀
        while file_path.exists():
            file_path = directory_path / f"{base_name}_{counter}.{extension}"
            counter += 1
        
        return str(file_path)
    
    @staticmethod
    def is_video_file(file_path: str) -> bool:
        """
        检查文件是否为支持的视频格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为支持的视频文件
        """
        video_extensions = {
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', 
            '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts'
        }
        
        extension = Path(file_path).suffix.lower()
        return extension in video_extensions
    
    @staticmethod
    def get_file_size_string(file_path: str) -> str:
        """
        获取文件大小的字符串表示
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小字符串，如 "1.5 MB"
        """
        try:
            size_bytes = os.path.getsize(file_path)
            
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
        except OSError:
            return "未知大小"


class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def get_image_info(image_path: str) -> Optional[Tuple[int, int]]:
        """
        获取图像信息
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            图像尺寸元组 (width, height)，如果失败返回 None
        """
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            print(f"获取图像信息失败: {e}")
            return None
    
    @staticmethod
    def create_thumbnail(image_path: str, thumbnail_path: str, size: Tuple[int, int] = (200, 150)) -> bool:
        """
        创建图像缩略图
        
        Args:
            image_path: 原始图像路径
            thumbnail_path: 缩略图保存路径
            size: 缩略图尺寸
            
        Returns:
            是否创建成功
        """
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "PNG")
            return True
        except Exception as e:
            print(f"创建缩略图失败: {e}")
            return False