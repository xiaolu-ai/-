# -*- coding: utf-8 -*-
"""
截图管理模块
负责视频截图功能，包括单次截图和批量截图
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QDialog

from .config import config_manager
from .utils import FileManager, TimeFormatter, ErrorHandler, SaveImageThread
from .player import PlayerManager
from .annotation import AnnotationManager, AnnotationDialog


class ScreenshotManager(QObject):
    """截图管理器类"""
    
    # 信号定义
    screenshot_saved = Signal(str)  # 截图保存完成信号 (文件路径)
    screenshot_failed = Signal(str)  # 截图失败信号 (错误信息)
    batch_screenshot_started = Signal(int)  # 批量截图开始信号 (间隔秒数)
    batch_screenshot_stopped = Signal(int)  # 批量截图停止信号 (总截图数量)
    batch_screenshot_progress = Signal(int, str)  # 批量截图进度信号 (已截图数量, 最新文件路径)
    status_message = Signal(str)  # 状态消息信号 (用于状态栏显示)
    
    def __init__(self, player_manager: PlayerManager):
        """
        初始化截图管理器
        
        Args:
            player_manager: 播放器管理器实例
        """
        super().__init__()
        
        # 保存播放器管理器引用
        self.player_manager = player_manager
        
        # 初始化标注管理器
        self.annotation_manager = AnnotationManager()
        
        # 截图配置
        self.save_directory = config_manager.get(
            "screenshot.save_directory", 
            str(Path.home() / "Desktop" / "Screenshots")
        )
        self.batch_interval = config_manager.get("screenshot.batch_interval", 5)
        self.auto_annotation = config_manager.get("screenshot.auto_annotation", True)
        
        # 批量截图状态
        self.batch_timer = None
        self.is_batch_active = False
        self.batch_count = 0
        self.batch_start_time = None
        self.last_screenshot_path = ""
        self.active_save_threads = []
        
        # 确保保存目录存在
        if not FileManager.ensure_directory_exists(self.save_directory):
            ErrorHandler.show_warning(
                "目录创建失败",
                f"无法创建截图保存目录:\n{self.save_directory}\n请检查权限或配置。"
            )

        print("截图管理器初始化完成")
    
    def annotate_last_screenshot(self) -> Optional[str]:
        """
        对最后一张截图进行标注
        
        Returns:
            标注后保存的文件路径，如果失败或取消则返回 None
        """
        last_screenshot_info = self.get_last_screenshot_info()
        if not last_screenshot_info["exists"]:
            error_msg = "没有可用的截图进行标注"
            print(error_msg)
            self.status_message.emit(error_msg)
            ErrorHandler.show_info("标注提示", error_msg)
            return None
            
        try:
            image = QImage(last_screenshot_info["path"])
            if image.isNull():
                error_msg = f"无法加载图像: {last_screenshot_info['path']}"
                print(error_msg)
                self.status_message.emit(error_msg)
                ErrorHandler.show_warning("加载图像失败", error_msg)
                return None
            
            # 创建并显示标注对话框
            dialog = AnnotationDialog(image)
            if dialog.exec() == QDialog.Accepted:
                # 获取标注后的图像
                annotated_image = dialog.get_annotated_image()
                
                # 保存标注后的图像
                save_path = last_screenshot_info["path"] # 覆盖原图
                if self.save_screenshot_image(annotated_image, save_path):
                    success_msg = f"标注已保存: {Path(save_path).name}"
                    print(success_msg)
                    self.status_message.emit(success_msg)
                    return save_path
                else:
                    # 错误已在 save_screenshot_image 中处理
                    return None
            else:
                print("标注操作被取消")
                self.status_message.emit("标注已取消")
                return None

        except Exception as e:
            error_msg = f"标注过程中发生错误: {str(e)}"
            print(error_msg)
            self.status_message.emit(error_msg)
            ErrorHandler.show_critical("标注错误", error_msg)
            return None

    def annotate_current_frame(self) -> Optional[str]:
        """
        暂停视频，基于当前帧进行标注并自动保存
        
        Returns:
            保存的文件路径，失败返回 None
        """
        try:
            # 检查视频
            if not self.player_manager.has_video():
                msg = "没有加载视频，无法标注"
                print(msg)
                self.status_message.emit(msg)
                ErrorHandler.show_warning("标注失败", msg)
                return None
            
            # 暂停播放以冻结画面
            self.player_manager.pause()
            
            # 获取当前帧
            current_frame = self.player_manager.get_current_frame()
            if current_frame is None or current_frame.isNull():
                msg = "无法获取当前视频帧用于标注"
                print(msg)
                self.status_message.emit(msg)
                ErrorHandler.show_warning("标注失败", msg)
                return None
            
            # 视频信息与时间戳
            video_info = self.player_manager.get_current_video_info()
            video_name = video_info["file_name"]
            position_ms = video_info["position"]
            timestamp = TimeFormatter.ms_to_time_string(position_ms)
            
            # 打开标注对话框
            dialog = AnnotationDialog(current_frame)
            if dialog.exec() == QDialog.Accepted:
                annotated_image = dialog.get_annotated_image()
                # 叠加左上角文件名与时间点
                annotated_image = self.annotation_manager.create_screenshot_with_info(
                    annotated_image, video_name, timestamp
                )
                # 生成路径并保存
                file_path = self.generate_filename(video_name, timestamp)
                if self.save_screenshot_image(annotated_image, file_path):
                    self.last_screenshot_path = file_path
                    success_msg = f"标注截图已保存: {Path(file_path).name}"
                    print(success_msg)
                    self.status_message.emit(success_msg)
                    return file_path
                else:
                    return None
            else:
                print("标注操作被取消")
                self.status_message.emit("标注已取消")
                return None
        except Exception as e:
            error_msg = f"标注当前帧时发生错误: {str(e)}"
            print(error_msg)
            self.status_message.emit(error_msg)
            ErrorHandler.show_critical("标注错误", error_msg)
            return None
    
    def set_save_directory(self, directory: str) -> bool:
        """
        设置截图保存目录
        
        Args:
            directory: 目录路径
            
        Returns:
            设置是否成功
        """
        try:
            # 确保目录存在
            if FileManager.ensure_directory_exists(directory):
                self.save_directory = directory
                config_manager.set("screenshot.save_directory", directory)
                print(f"截图保存目录设置为: {directory}")
                return True
            else:
                error_msg = f"无法创建或访问目录: {directory}"
                print(error_msg)
                ErrorHandler.show_warning("设置目录失败", error_msg)
                return False
        except Exception as e:
            error_msg = f"设置保存目录时出错: {e}"
            print(error_msg)
            ErrorHandler.show_critical("设置目录失败", error_msg)
            return False
    
    def generate_filename(self, video_name: str, timestamp: str) -> str:
        """
        生成截图文件名
        
        Args:
            video_name: 视频文件名（不含扩展名）
            timestamp: 时间点字符串 (HH:MM:SS)
            
        Returns:
            生成的文件名
        """
        # 清理文件名中的不安全字符
        safe_video_name = FileManager.get_safe_filename(video_name)
        safe_timestamp = timestamp.replace(":", "-")  # 替换冒号为横线
        
        # 生成基础文件名
        base_name = f"{safe_video_name}_{safe_timestamp}"
        
        # 生成唯一文件名（如果文件已存在则添加数字后缀）
        unique_path = FileManager.get_unique_filename(
            self._resolve_output_directory(), base_name, "png"
        )
        
        return unique_path

    def _resolve_output_directory(self) -> str:
        """
        解析截图保存目录：始终输出到桌面（而非原文件夹）
        路径：~/Desktop/原文件名-审核反馈截图
        """
        try:
            from pathlib import Path as _P
            desktop = _P.home() / "Desktop"
            current_path = getattr(self.player_manager, 'current_video_path', '')
            video_stem = _P(current_path).stem if current_path else "截图"
            output_dir = desktop / f"{video_stem}-审核反馈截图"
            FileManager.ensure_directory_exists(str(output_dir))
            return str(output_dir)
        except Exception:
            return self.save_directory
    
    def take_screenshot(self) -> Optional[str]:
        """
        立即截图
        
        Returns:
            截图文件路径，失败返回 None
        """
        try:
            # 检查是否有视频在播放
            if not self.player_manager.has_video():
                error_msg = "没有加载视频，无法截图"
                print(error_msg)
                self.screenshot_failed.emit(error_msg)
                self.status_message.emit(error_msg)
                ErrorHandler.show_warning("截图失败", error_msg)
                return None
            
            # 获取当前帧
            current_frame = self.player_manager.get_current_frame()
            if current_frame is None:
                error_msg = "无法获取当前视频帧"
                print(error_msg)
                self.screenshot_failed.emit(error_msg)
                self.status_message.emit(error_msg)
                # 不显示弹窗，因为状态栏已经提示
                return None
            
            # 获取视频信息
            video_info = self.player_manager.get_current_video_info()
            video_name = video_info["file_name"]
            position_ms = video_info["position"]
            
            # 生成时间戳
            timestamp = TimeFormatter.ms_to_time_string(position_ms)
            
            # 生成文件名
            file_path = self.generate_filename(video_name, timestamp)
            
            # 处理图像（添加文本叠加）
            processed_image = self.process_screenshot_image(current_frame, video_name, timestamp)
            
            # 保存截图
            self.save_screenshot_image(processed_image, file_path)
            return file_path # 立即返回，不等待保存完成
                
        except Exception as e:
            error_msg = f"截图过程中发生错误: {str(e)}"
            print(error_msg)
            self.screenshot_failed.emit(error_msg)
            self.status_message.emit(error_msg)
            ErrorHandler.show_critical("截图错误", error_msg)
            return None
    
    def process_screenshot_image(self, image: QImage, video_name: str, timestamp: str) -> QImage:
        """
        处理截图图像，根据配置添加文本叠加
        
        Args:
            image: 原始截图图像
            video_name: 视频文件名
            timestamp: 时间戳字符串
            
        Returns:
            处理后的图像
        """
        try:
            # 如果启用了自动标注，添加文本叠加
            if self.auto_annotation:
                processed_image = self.annotation_manager.create_screenshot_with_info(
                    image, video_name, timestamp
                )
                print(f"已为截图添加文本叠加: {video_name} @ {timestamp}")
                return processed_image
            else:
                print("自动标注已禁用，返回原始截图")
                return image
                
        except Exception as e:
            error_msg = f"处理截图图像时发生错误: {str(e)}"
            print(error_msg)
            # 在这种情况下，只在控制台打印错误，然后返回原始图像，避免中断流程
            return image
    
    def save_screenshot_image(self, image: QImage, file_path: str) -> bool:
        """
        保存截图图像到文件
        
        Args:
            image: 要保存的图像
            file_path: 保存路径
            
        Returns:
            保存是否成功
        """
        try:
            # 确保保存目录存在
            FileManager.ensure_directory_exists(Path(file_path).parent)
            
            # 拷贝一份图像，避免原图在其他线程/组件中被修改导致崩溃
            safe_image = image.copy()
            
            thread = SaveImageThread(safe_image, file_path)
            thread.finished.connect(self._on_save_finished)
            thread.error.connect(self._on_save_error)
            thread.start()
            
            # 保持对线程的引用，以防被垃圾回收
            self.active_save_threads.append(thread)
            
            return True
        except Exception as e:
            error_msg = f"启动图像保存线程失败: {e}"
            print(error_msg)
            ErrorHandler.show_critical("保存失败", error_msg)
            return False

    def _on_save_finished(self, success: bool, file_path: str):
        """图像保存完成处理"""
        if success:
            success_msg = f"截图保存成功: {Path(file_path).name}"
            print(f"截图保存成功: {file_path}")
            self.screenshot_saved.emit(file_path)
            self.status_message.emit(success_msg)
            self.last_screenshot_path = file_path
        
        # 清理完成的线程
        self.active_save_threads = [t for t in self.active_save_threads if not t.isFinished()]

    def _on_save_error(self, error_msg: str, file_path: str):
        """图像保存错误处理"""
        full_error = f"保存截图失败: {Path(file_path).name}\n原因: {error_msg}"
        print(full_error)
        self.screenshot_failed.emit(file_path)
        self.status_message.emit(f"保存失败: {Path(file_path).name}")
        ErrorHandler.show_critical("保存失败", full_error)

        # 清理完成的线程
        self.active_save_threads = [t for t in self.active_save_threads if not t.isFinished()]

    def start_batch_screenshot(self, interval: int = None) -> bool:
        """
        开始批量截图
        
        Args:
            interval: 截图间隔（秒），如果为 None 则使用配置中的值
            
        Returns:
            启动是否成功
        """
        try:
            # 检查是否已经在批量截图
            if self.is_batch_active:
                print("批量截图已在进行中")
                return False
            
            # 检查是否有视频
            if not self.player_manager.has_video():
                error_msg = "没有加载视频，无法开始批量截图"
                print(error_msg)
                self.screenshot_failed.emit(error_msg)
                self.status_message.emit(error_msg)
                ErrorHandler.show_warning("批量截图失败", error_msg)
                return False
            
            # 设置截图间隔
            if interval is not None:
                self.batch_interval = max(1, min(60, interval))  # 限制在1-60秒之间
                config_manager.set("screenshot.batch_interval", self.batch_interval)
            
            # 创建定时器
            self.batch_timer = QTimer()
            self.batch_timer.timeout.connect(self.on_batch_timer_timeout)
            
            # 重置计数器和状态
            self.batch_count = 0
            self.batch_start_time = datetime.now()
            
            # 启动定时器
            self.batch_timer.start(self.batch_interval * 1000)  # 转换为毫秒
            self.is_batch_active = True
            
            start_msg = f"批量截图已启动，间隔: {self.batch_interval}秒"
            print(start_msg)
            self.batch_screenshot_started.emit(self.batch_interval)
            self.status_message.emit(start_msg)
            
            # 立即截取第一张
            first_screenshot = self.take_screenshot()
            if first_screenshot:
                self.batch_count = 1
                self.batch_screenshot_progress.emit(self.batch_count, first_screenshot)
            
            return True
            
        except Exception as e:
            error_msg = f"启动批量截图失败: {str(e)}"
            print(error_msg)
            self.screenshot_failed.emit(error_msg)
            self.status_message.emit(error_msg)
            ErrorHandler.show_critical("批量截图错误", error_msg)
            return False
    
    def stop_batch_screenshot(self):
        """停止批量截图"""
        if self.batch_timer is not None:
            self.batch_timer.stop()
            self.batch_timer = None
        
        if self.is_batch_active:
            self.is_batch_active = False
            
            # 计算批量截图持续时间
            duration_msg = ""
            if self.batch_start_time:
                duration = datetime.now() - self.batch_start_time
                duration_seconds = int(duration.total_seconds())
                duration_msg = f"，耗时: {duration_seconds}秒"
            
            stop_msg = f"批量截图已停止，共截取 {self.batch_count} 张图片{duration_msg}"
            print(stop_msg)
            self.batch_screenshot_stopped.emit(self.batch_count)
            self.status_message.emit(stop_msg)
    
    def on_batch_timer_timeout(self):
        """批量截图定时器超时处理"""
        if self.is_batch_active:
            # 检查视频是否还在播放
            if not self.player_manager.has_video():
                print("视频已停止，自动停止批量截图")
                self.stop_batch_screenshot()
                return
            
            # 截图
            screenshot_path = self.take_screenshot()
            if screenshot_path:
                self.batch_count += 1
                progress_msg = f"批量截图进行中... ({self.batch_count} 张)"
                self.batch_screenshot_progress.emit(self.batch_count, screenshot_path)
                self.status_message.emit(progress_msg)
    
    def set_batch_interval(self, interval: int):
        """
        设置批量截图间隔
        
        Args:
            interval: 间隔时间（秒）
        """
        # 限制间隔范围
        interval = max(1, min(60, interval))
        self.batch_interval = interval
        
        # 保存到配置
        config_manager.set("screenshot.batch_interval", interval)
        
        # 如果正在批量截图，更新定时器
        if self.is_batch_active and self.batch_timer is not None:
            self.batch_timer.setInterval(interval * 1000)
        
        print(f"批量截图间隔设置为: {interval}秒")
    
    def set_auto_annotation(self, enabled: bool):
        """
        设置是否启用自动标注
        
        Args:
            enabled: 是否启用自动标注
        """
        self.auto_annotation = enabled
        config_manager.set("screenshot.auto_annotation", enabled)
        status = "启用" if enabled else "禁用"
        print(f"自动标注已{status}")
    
    def set_font_size(self, size: int):
        """
        设置文本叠加字体大小
        
        Args:
            size: 字体大小 (12-48)
        """
        self.annotation_manager.set_font_size(size)
        print(f"文本叠加字体大小设置为: {size}")
    
    def get_font_size(self) -> int:
        """
        获取当前字体大小
        
        Returns:
            当前字体大小
        """
        return self.annotation_manager.font_size
    
    def get_screenshot_info(self) -> dict:
        """
        获取截图相关信息
        
        Returns:
            包含截图信息的字典
        """
        # 计算批量截图运行时间
        batch_duration = 0
        if self.is_batch_active and self.batch_start_time:
            duration = datetime.now() - self.batch_start_time
            batch_duration = int(duration.total_seconds())
        
        return {
            "save_directory": self.save_directory,
            "batch_interval": self.batch_interval,
            "auto_annotation": self.auto_annotation,
            "is_batch_active": self.is_batch_active,
            "batch_count": self.batch_count,
            "batch_duration": batch_duration,
            "last_screenshot_path": self.last_screenshot_path,
            "batch_start_time": self.batch_start_time.isoformat() if self.batch_start_time else None
        }
    
    def get_batch_status_message(self) -> str:
        """
        获取批量截图状态消息
        
        Returns:
            状态消息字符串
        """
        if not self.is_batch_active:
            return "批量截图未启动"
        
        duration = 0
        if self.batch_start_time:
            duration = int((datetime.now() - self.batch_start_time).total_seconds())
        
        return f"批量截图进行中 - 已截取 {self.batch_count} 张，运行 {duration} 秒"
    
    def get_last_screenshot_info(self) -> dict:
        """
        获取最后一张截图的信息
        
        Returns:
            包含最后截图信息的字典
        """
        if not self.last_screenshot_path:
            return {"exists": False}
        
        try:
            file_path = Path(self.last_screenshot_path)
            if file_path.exists():
                stat = file_path.stat()
                return {
                    "exists": True,
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "size_string": FileManager.get_file_size_string(str(file_path))
                }
            else:
                return {"exists": False, "path": str(file_path)}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def get_supported_formats(self) -> list:
        """
        获取支持的截图格式
        
        Returns:
            支持的格式列表
        """
        return ["PNG", "JPG", "JPEG", "BMP"]
    
    def cleanup(self):
        """清理资源"""
        if self.is_batch_active:
            self.stop_batch_screenshot()
        
        # 清理标注管理器
        if hasattr(self, 'annotation_manager'):
            self.annotation_manager.cleanup()
        
        # 等待所有保存线程完成
        for thread in self.active_save_threads:
            thread.wait()

        print("截图管理器资源已清理")