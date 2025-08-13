# -*- coding: utf-8 -*-
"""
播放器管理模块
负责视频播放逻辑和状态管理
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaFormat, QVideoSink, QVideoFrame
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtGui import QImage

from .config import config_manager
from .utils import FileManager, TimeFormatter, ErrorHandler


class PlayerManager(QObject):
    """
    播放器管理器
    封装了 QMediaPlayer 的核心功能，提供视频播放、控制和状态管理。
    """
    
    # 定义自定义信号，用于向UI层传递更简洁的信息
    status_message = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, video_widget: Optional[QVideoWidget] = None):
        """初始化播放器管理器"""
        super().__init__()
        
        # 创建核心组件
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.video_widget = video_widget if video_widget is not None else QVideoWidget()
        self.video_sink: Optional[QVideoSink] = None
        self.current_frame: Optional[QImage] = None

        self.player.setAudioOutput(self.audio_output)
        # 仅将视频输出绑定到 QVideoWidget 的 videoSink，符合 Qt6 API
        sink = self.video_widget.videoSink()
        self.player.setVideoOutput(sink)
        # 连接视频帧信号以捕获真实帧，避免 QWidget.grab 导致的灰屏
        if isinstance(sink, QVideoSink):
            self.video_sink = sink
            self.video_sink.videoFrameChanged.connect(self._on_video_frame_changed)
        
        # 加载配置
        self.audio_output.setVolume(config_manager.get("player.volume", 80) / 100)
        self.audio_output.setMuted(config_manager.get("player.muted", False))
        self.player.setPlaybackRate(config_manager.get("player.playback_rate", 1.0))
        
        # 初始状态
        self.current_video_path = ""
        # 播放列表上下文（可选）
        self.playlist = []
        self.playlist_index = -1
        self.playlist_dir = None
        
        print("播放器管理器初始化完成")
    

    
    def load_video(self, file_path: str) -> bool:
        """
        加载视频文件
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 检查文件是否存在
            video_path = Path(file_path)
            if not video_path.exists():
                error_msg = f"文件不存在: {file_path}"
                print(error_msg)
                self.error_occurred.emit(error_msg)
                ErrorHandler.show_critical("加载失败", error_msg)
                return False
            
            # 检查是否为支持的视频格式
            if not FileManager.is_video_file(file_path):
                self.error_occurred.emit(f"不支持的视频格式: {file_path}")
                return False
            
            # 保存当前视频信息
            self.current_video_path = file_path
            
            # 创建媒体源
            media_url = QUrl.fromLocalFile(file_path)
            self.player.setSource(media_url)
            
            # 记住上次打开的目录
            config_manager.set("path.last_video_dir", str(video_path.parent))
            
            print(f"视频已加载: {file_path}")
            self.status_message.emit(f"加载完成: {FileManager.get_video_filename_without_extension(file_path)}")
            return True
            
        except Exception as e:
            error_msg = f"加载视频时发生未知错误: {str(e)}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            ErrorHandler.show_critical("加载失败", error_msg)
            return False
    
    def play(self):
        """开始播放"""
        self.player.play()
        print("开始播放")
    
    def pause(self):
        """暂停播放"""
        self.player.pause()
        print("暂停播放")
    
    def stop(self):
        """停止播放"""
        self.player.stop()
        print("停止播放")
    
    def toggle_playback(self):
        """切换播放/暂停状态"""
        if self.is_playing():
            self.pause()
        else:
            self.play()
    
    def set_position(self, position: int):
        """设置播放位置（用于进度条）"""
        self.player.setPosition(position)
    
    def rewind(self, seconds: int = 10):
        """后退指定秒数"""
        new_pos = max(0, self.player.position() - seconds * 1000)
        self.player.setPosition(new_pos)
    
    def forward(self, seconds: int = 10):
        """快进指定秒数"""
        new_pos = self.player.position() + seconds * 1000
        if self.player.duration() > 0:
            new_pos = min(new_pos, self.player.duration())
        self.player.setPosition(new_pos)
    
    def set_volume(self, volume: int):
        """
        设置音量

        Args:
            volume: 音量大小 (0-100)
        """
        self.audio_output.setVolume(volume / 100)
        print(f"音量设置为: {volume}%")

    def get_volume(self) -> int:
        """获取当前音量 (0-100)"""
        return int(self.audio_output.volume() * 100)
        
    def set_muted(self, muted: bool):
        """设置静音状态"""
        self.audio_output.setMuted(muted)
        status = "静音" if muted else "取消静音"
        print(f"音频状态: {status}")

    def is_muted(self) -> bool:
        """获取静音状态"""
        return self.audio_output.isMuted()

    def set_playback_rate(self, rate: float):
        """
        设置播放速度

        Args:
            rate: 播放速度 (0.5-2.0)
        """
        # 限制播放速度范围
        rate = max(0.5, min(2.0, rate))
        
        self.player.setPlaybackRate(rate)
        print(f"播放速度设置为: {rate}x")

    def get_playback_rate(self) -> float:
        """获取当前播放速度"""
        return self.player.playbackRate()
    
    def toggle_speed(self):
        """在 1.0x、1.5x、2.0x 间循环切换播放速度"""
        try:
            speeds = [1.0, 1.5, 2.0]
            current = self.get_playback_rate()
            # 找到当前最接近的速度索引
            idx = min(range(len(speeds)), key=lambda i: abs(speeds[i] - current))
            next_idx = (idx + 1) % len(speeds)
            next_speed = speeds[next_idx]
            self.set_playback_rate(next_speed)
            self.status_message.emit(f"速度: {next_speed:.1f}x")
        except Exception as e:
            print(f"切换倍速失败: {e}")
    
    def get_current_frame(self) -> Optional[QImage]:
        """
        获取当前播放帧的图像
        
        Returns:
            当前帧的 QImage 对象，如果获取失败返回 None
        """
        try:
            # 检查是否有视频在播放
            if not self.has_video():
                print("当前没有加载视频")
                return None
            
            # 优先返回通过 QVideoSink 捕获的最新帧
            if self.current_frame is not None and not self.current_frame.isNull():
                return self.current_frame
            
            # 回退：尝试从控件抓取（在部分平台可能为灰屏，仅作兜底）
            widget_size = self.video_widget.size()
            if widget_size.width() <= 0 or widget_size.height() <= 0:
                print("视频控件尺寸无效")
                return None
            pixmap = self.video_widget.grab()
            if pixmap.isNull():
                print("无法从视频控件获取内容")
                return None
            image = pixmap.toImage()
            if not image.isNull():
                return image
            return None
                
        except Exception as e:
            print(f"获取当前帧时发生错误: {e}")
            # 不在这里显示弹窗，过于频繁
            # ErrorHandler.show_warning("帧捕获失败", f"获取当前帧失败: {str(e)}")
            return None
    
    def capture_frame_alternative(self) -> Optional[QImage]:
        """
        备用帧捕获方法
        使用定时器在播放时定期捕获帧
        
        Returns:
            捕获的帧图像
        """
        # 这个方法可以在未来实现更高级的帧捕获逻辑
        return self.get_current_frame()

    def _on_video_frame_changed(self, frame: QVideoFrame):
        """接收视频帧并缓存为 QImage 以供截图使用"""
        try:
            if not frame.isValid():
                return
            image = frame.toImage()
            if image.isNull():
                return
            # 复制一份，避免后续帧覆盖共享缓冲
            self.current_frame = image.copy()
        except Exception as e:
            # 捕获异常但不打断播放
            print(f"处理视频帧时出错: {e}")
    
    # 信号槽处理方法
    def on_position_changed(self, position: int):
        """
        播放位置变化处理
        
        Args:
            position: 当前播放位置（毫秒）
        """
        self.position_changed.emit(position)
    
    def on_duration_changed(self, duration: int):
        """
        视频时长变化处理
        
        Args:
            duration: 视频总时长（毫秒）
        """
        self.duration_changed.emit(duration)
        print(f"视频时长: {TimeFormatter.ms_to_time_string(duration)}")
    
    def on_state_changed(self, state: QMediaPlayer.PlaybackState):
        """
        播放状态变化处理
        
        Args:
            state: 新的播放状态
        """
        self.state_changed.emit(state)
        
        state_names = {
            QMediaPlayer.StoppedState: "停止",
            QMediaPlayer.PlayingState: "播放中",
            QMediaPlayer.PausedState: "暂停"
        }
        
        state_name = state_names.get(state, "未知状态")
        print(f"播放状态变化: {state_name}")
    
    def on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        """
        媒体状态变化处理
        
        Args:
            status: 新的媒体状态
        """
        self.media_status_changed.emit(status)
        
        if status == QMediaPlayer.LoadedMedia:
            self.video_loaded.emit(self.current_video_path)
            print(f"视频加载完成: {self.current_video_name}")
        elif status == QMediaPlayer.InvalidMedia:
            self.error_occurred.emit("无效的媒体文件")
    
    def _handle_player_error(self, error: QMediaPlayer.Error):
        """处理播放器内部错误"""
        if error != QMediaPlayer.Error.NoError:
            error_string = self.player.errorString()
            print(f"播放器错误: {error_string}")
            self.error_occurred.emit(error_string)
            ErrorHandler.show_critical("播放器错误", f"发生了一个播放器错误:\n\n{error_string}")
    
    def _handle_media_status(self, status: QMediaPlayer.MediaStatus):
        """处理媒体状态变化"""
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            video_name = Path(self.current_video_path).name
            print(f"视频加载完成: {video_name}")
            self.status_message.emit(f"加载完成: {video_name}")
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            error_msg = "无效或不支持的媒体文件"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            ErrorHandler.show_critical("加载失败", error_msg)
    
    # 属性获取方法
    def get_current_position(self) -> int:
        """获取当前播放位置（毫秒）"""
        return self.player.position()
    
    def get_duration(self) -> int:
        """获取视频总时长（毫秒）"""
        return self.player.duration()
    
    def get_playback_state(self) -> QMediaPlayer.PlaybackState:
        """获取当前播放状态"""
        return self.player.playbackState()
    
    def get_media_status(self) -> QMediaPlayer.MediaStatus:
        """获取当前媒体状态"""
        return self.player.mediaStatus()
    
    def get_current_video_info(self) -> dict:
        """获取当前视频的各类信息"""
        return {
            "file_path": self.current_video_path,
            "file_name": Path(self.current_video_path).stem,
            "duration": self.get_duration(),
            "position": self.player.position(),
            "playback_rate": self.get_playback_rate(),
            "volume": self.get_volume(),
            "is_muted": self.is_muted(),
            "state": self.player.playbackState(),
        }

    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
    
    def is_paused(self) -> bool:
        """检查是否已暂停"""
        return self.player.playbackState() == QMediaPlayer.PausedState
    
    def is_stopped(self) -> bool:
        """检查是否已停止"""
        return self.player.playbackState() == QMediaPlayer.StoppedState
    
    def has_video(self) -> bool:
        """检查是否已加载视频"""
        return self.player.source().isValid() and self.player.mediaStatus() != QMediaPlayer.MediaStatus.NoMedia

    def cleanup(self):
        """清理资源"""
        
        # 保存音量和静音状态
        if self.audio_output:
            config_manager.set("player.volume", self.get_volume())
            config_manager.set("player.muted", self.is_muted())

        # 停止播放器
        if self.player:
            self.player.stop()
        
        # 断开视频帧信号，释放引用
        if self.video_sink:
            try:
                self.video_sink.videoFrameChanged.disconnect(self._on_video_frame_changed)
            except Exception:
                pass
        self.current_frame = None
        print("播放器管理器资源已清理")