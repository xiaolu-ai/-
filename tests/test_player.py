# -*- coding: utf-8 -*-
"""
播放器管理器单元测试
测试播放器基础功能和状态管理
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 模拟 PySide6 模块（用于没有安装 PySide6 的环境）
try:
    from PySide6.QtCore import QObject, Signal, QUrl, QTimer
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    
    # 创建模拟类
    class QObject:
        pass
    
    class Signal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass
        def connect(self, *args):
            pass
    
    class QMediaPlayer:
        StoppedState = 0
        PlayingState = 1
        PausedState = 2
        
        NoMedia = 0
        LoadedMedia = 1
        InvalidMedia = 2
        
        NoError = 0
        
        def __init__(self):
            self.position_val = 0
            self.duration_val = 0
            self.state_val = self.StoppedState
            self.status_val = self.NoMedia
            
        def position(self):
            return self.position_val
            
        def duration(self):
            return self.duration_val
            
        def playbackState(self):
            return self.state_val
            
        def mediaStatus(self):
            return self.status_val
            
        def setSource(self, url):
            pass
            
        def play(self):
            self.state_val = self.PlayingState
            
        def pause(self):
            self.state_val = self.PausedState
            
        def stop(self):
            self.state_val = self.StoppedState
            
        def setPosition(self, pos):
            self.position_val = pos
            
        def setPlaybackRate(self, rate):
            pass
            
        def setAudioOutput(self, output):
            pass
            
        def setVideoOutput(self, output):
            pass
            
        def isSeekable(self):
            return True
    
    class QAudioOutput:
        def setVolume(self, volume):
            pass
        def setMuted(self, muted):
            pass
    
    class QVideoWidget:
        pass


class TestPlayerManager(unittest.TestCase):
    """播放器管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            self.app = QApplication([])
    
    @patch('src.player.config_manager')
    def test_player_initialization(self, mock_config):
        """测试播放器初始化"""
        # 设置模拟配置
        mock_config.get.side_effect = lambda key, default: {
            "player.volume": 80,
            "player.muted": False,
            "player.playback_rate": 1.0
        }.get(key, default)
        
        # 导入并创建播放器管理器
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 验证初始化
        self.assertEqual(player.get_volume(), 80)
        self.assertEqual(player.get_playback_rate(), 1.0)
        self.assertFalse(player.is_muted())
        self.assertEqual(player.current_video_path, "")
        player.cleanup()
    
    @patch('src.player.ErrorHandler')
    @patch('src.player.config_manager')
    @patch('src.player.Path.exists')
    def test_load_video_success(self, mock_exists, mock_config, mock_error_handler):
        """测试成功加载视频"""
        # 设置模拟
        mock_exists.return_value = True
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 测试加载视频
        test_path = "/path/to/test_video.mp4"
        player.load_video(test_path)
        
        self.assertEqual(player.current_video_path, test_path)
        self.assertEqual(Path(player.player.source().path()).name, "test_video.mp4")
        mock_error_handler.show_critical.assert_not_called()
        player.cleanup()

    @patch('src.player.ErrorHandler')
    @patch('src.player.config_manager')
    @patch('src.player.Path.exists')
    def test_load_video_file_not_exists(self, mock_exists, mock_config, mock_error_handler):
        """测试加载不存在的视频文件"""
        # 设置模拟
        mock_exists.return_value = False
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 测试加载不存在的文件
        player.load_video("/path/to/nonexistent.mp4")
        
        self.assertEqual(player.current_video_path, "")
        mock_error_handler.show_critical.assert_called_once()
        player.cleanup()
    
    @patch('src.player.config_manager')
    def test_playback_controls(self, mock_config):
        """测试播放控制功能"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 使用spy来监视方法调用
        play_spy = Mock(wraps=player.player.play)
        pause_spy = Mock(wraps=player.player.pause)
        stop_spy = Mock(wraps=player.player.stop)
        
        player.player.play = play_spy
        player.player.pause = pause_spy
        player.player.stop = stop_spy
        
        player.play()
        play_spy.assert_called_once()
        
        player.pause()
        pause_spy.assert_called_once()
        
        player.stop()
        stop_spy.assert_called_once()
        player.cleanup()

    @patch('src.player.config_manager')
    def test_seek_operations(self, mock_config):
        """测试跳转操作"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 模拟视频已加载且可跳转
        player.player.setSource(QUrl.fromLocalFile("/fake.mp4"))
        player.player.isSeekable = Mock(return_value=True)

        set_position_spy = Mock(wraps=player.player.setPosition)
        player.player.setPosition = set_position_spy

        # 测试 forward
        player.player.setPosition(10000)
        player.forward() # 默认10秒
        set_position_spy.assert_called_with(20000)

        # 测试 rewind
        player.player.setPosition(20000)
        player.rewind() # 默认10秒
        set_position_spy.assert_called_with(10000)
        
        # 测试 set_position
        player.set_position(50000)
        set_position_spy.assert_called_with(50000)
        player.cleanup()

    @patch('src.player.config_manager')
    def test_volume_control(self, mock_config):
        """测试音量控制"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 测试设置音量
        player.set_volume(75)
        self.assertEqual(player.get_volume(), 75)
        
        # 测试音量范围限制
        player.set_volume(150)
        self.assertEqual(player.get_volume(), 100)
        
        player.set_volume(-10)
        self.assertEqual(player.get_volume(), 0)
        player.cleanup()
    
    @patch('src.player.config_manager')
    def test_mute_control(self, mock_config):
        """测试静音控制"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 测试静音
        self.assertFalse(player.is_muted())
        player.set_muted(True)
        self.assertTrue(player.is_muted())
        
        # 测试切换静音
        player.set_muted(False)
        self.assertFalse(player.is_muted())
        player.cleanup()
    
    @patch('src.player.config_manager')
    def test_playback_rate_control(self, mock_config):
        """测试播放速度控制"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 测试设置播放速度
        player.set_playback_rate(1.5)
        self.assertEqual(player.get_playback_rate(), 1.5)
        
        # 测试速度范围限制 (根据代码实现调整)
        player.set_playback_rate(5.0)
        self.assertEqual(player.get_playback_rate(), 2.0)
        
        player.set_playback_rate(0.1)
        self.assertEqual(player.get_playback_rate(), 0.5)
        player.cleanup()
    
    @patch('src.player.config_manager')
    def test_video_info_methods(self, mock_config):
        """测试视频信息获取方法"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager()
        
        # 设置一些测试数据
        player.current_video_path = "/test/video.mp4"
        
        # 模拟播放器状态
        player.player.setPosition(5000)
        player.player.setDuration(60000)
        player.player.setPlaybackState(QMediaPlayer.PlaybackState.PlayingState)
        
        # 测试获取视频信息
        info = player.get_current_video_info()
        self.assertIsInstance(info, dict)
        self.assertEqual(info["file_path"], "/test/video.mp4")
        self.assertEqual(info["file_name"], "video")
        self.assertEqual(info["position"], 5000)
        self.assertEqual(info["duration"], 60000)
        self.assertEqual(info["state"], QMediaPlayer.PlaybackState.PlayingState)
        
        player.cleanup()

if __name__ == "__main__":
    unittest.main(verbosity=2)