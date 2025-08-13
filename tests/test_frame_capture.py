# -*- coding: utf-8 -*-
"""
视频帧捕获功能测试
测试视频帧的捕获和转换功能
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 检查 PySide6 是否可用
try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtGui import QImage
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
    
    class QVideoFrame:
        def __init__(self):
            self.valid = True
            
        def toImage(self):
            # 模拟返回一个有效的图像
            mock_image = Mock()
            mock_image.isNull.return_value = False
            mock_image.width.return_value = 1920
            mock_image.height.return_value = 1080
            return mock_image
    
    class QVideoSink:
        def __init__(self):
            self.videoFrameChanged = Signal()
    
    class QMediaPlayer:
        StoppedState = 0
        PlayingState = 1
        PausedState = 2
        
        NoMedia = 0
        LoadedMedia = 1
        InvalidMedia = 2
        
        def __init__(self):
            self.position_val = 0
            self.duration_val = 0
            self.state_val = self.StoppedState
            self.status_val = self.NoMedia
            
        def setVideoOutput(self, outputs):
            pass
            
        def setAudioOutput(self, output):
            pass
            
        def position(self):
            return self.position_val
            
        def duration(self):
            return self.duration_val
            
        def playbackState(self):
            return self.state_val
            
        def mediaStatus(self):
            return self.status_val
    
    class QAudioOutput:
        def setVolume(self, volume):
            pass
        def setMuted(self, muted):
            pass
    
    class QVideoWidget:
        pass


class TestFrameCapture(unittest.TestCase):
    """视频帧捕获测试类"""
    
    def setUp(self):
        """测试前准备"""
        if PYSIDE6_AVAILABLE:
            # 真实环境下需要 QApplication
            from PySide6.QtWidgets import QApplication
            if not QApplication.instance():
                self.app = QApplication([])
            self.video_widget = QVideoWidget()
        else:
            self.video_widget = QVideoWidget()
    
    @patch('src.player.config_manager')
    def test_frame_capture_initialization(self, mock_config):
        """测试帧捕获初始化"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 验证帧捕获相关属性已初始化
        self.assertIsNotNone(player.video_sink)
        self.assertIsNone(player.current_frame)  # 初始时没有帧
    
    @patch('src.player.config_manager')
    def test_get_current_frame_no_frame(self, mock_config):
        """测试没有帧时获取当前帧"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 没有帧时应该返回 None
        frame_image = player.get_current_frame()
        self.assertIsNone(frame_image)
    
    @patch('src.player.config_manager')
    def test_get_current_frame_with_video(self, mock_config):
        """测试有视频时获取当前帧"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 模拟有视频加载
        player.current_video_path = "/test/video.mp4"
        
        # 模拟视频控件有内容
        if PYSIDE6_AVAILABLE:
            # 在真实环境中，需要视频控件有实际内容才能捕获
            pass
        else:
            # 在模拟环境中，模拟 grab 方法
            mock_pixmap = Mock()
            mock_pixmap.isNull.return_value = False
            mock_pixmap.toImage.return_value = Mock()
            mock_pixmap.toImage.return_value.isNull.return_value = False
            mock_pixmap.toImage.return_value.width.return_value = 1920
            mock_pixmap.toImage.return_value.height.return_value = 1080
            
            self.video_widget.grab = Mock(return_value=mock_pixmap)
            self.video_widget.size = Mock()
            self.video_widget.size.return_value.width.return_value = 800
            self.video_widget.size.return_value.height.return_value = 600
            
            # 获取当前帧
            frame_image = player.get_current_frame()
            self.assertIsNotNone(frame_image)
    
    @patch('src.player.config_manager')
    def test_capture_frame_alternative(self, mock_config):
        """测试备用帧捕获方法"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 测试备用捕获方法
        result = player.capture_frame_alternative()
        
        # 在没有视频的情况下应该返回 None
        self.assertIsNone(result)
    
    @patch('src.player.config_manager')
    def test_frame_capture_error_handling(self, mock_config):
        """测试帧捕获错误处理"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 模拟视频控件抛出异常
        if not PYSIDE6_AVAILABLE:
            self.video_widget.grab = Mock(side_effect=Exception("截取失败"))
            self.video_widget.size = Mock()
            self.video_widget.size.return_value.width.return_value = 800
            self.video_widget.size.return_value.height.return_value = 600
            
            # 设置有视频
            player.current_video_path = "/test/video.mp4"
            
            # 获取当前帧应该返回 None 而不是抛出异常
            frame_image = player.get_current_frame()
            self.assertIsNone(frame_image)


class TestFrameCaptureIntegration(unittest.TestCase):
    """帧捕获集成测试"""
    
    def setUp(self):
        """测试前准备"""
        if PYSIDE6_AVAILABLE:
            from PySide6.QtWidgets import QApplication
            if not QApplication.instance():
                self.app = QApplication([])
            self.video_widget = QVideoWidget()
        else:
            self.video_widget = QVideoWidget()
    
    @patch('src.player.config_manager')
    def test_frame_capture_workflow(self, mock_config):
        """测试帧捕获完整工作流"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 1. 初始状态：没有视频，无法获取帧
        self.assertIsNone(player.get_current_frame())
        
        # 2. 模拟加载视频
        player.current_video_path = "/test/video.mp4"
        
        if not PYSIDE6_AVAILABLE:
            # 3. 模拟视频控件有内容
            mock_pixmap = Mock()
            mock_pixmap.isNull.return_value = False
            mock_image = Mock()
            mock_image.isNull.return_value = False
            mock_image.width.return_value = 1920
            mock_image.height.return_value = 1080
            mock_pixmap.toImage.return_value = mock_image
            
            self.video_widget.grab = Mock(return_value=mock_pixmap)
            self.video_widget.size = Mock()
            self.video_widget.size.return_value.width.return_value = 800
            self.video_widget.size.return_value.height.return_value = 600
            
            # 4. 验证可以获取到帧
            captured_image = player.get_current_frame()
            self.assertIsNotNone(captured_image)
            
            # 5. 测试备用捕获方法
            alt_image = player.capture_frame_alternative()
            self.assertIsNotNone(alt_image)
    
    @patch('src.player.config_manager')
    def test_frame_capture_with_video_loading(self, mock_config):
        """测试视频加载时的帧捕获"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.player import PlayerManager
        player = PlayerManager(self.video_widget)
        
        # 模拟视频加载过程中的帧捕获
        if not PYSIDE6_AVAILABLE:
            # 1. 加载视频前没有帧
            self.assertIsNone(player.get_current_frame())
            
            # 2. 模拟视频加载
            player.current_video_path = "/test/video.mp4"
            
            # 3. 模拟视频控件准备就绪
            mock_pixmap = Mock()
            mock_pixmap.isNull.return_value = False
            mock_image = Mock()
            mock_image.isNull.return_value = False
            mock_image.width.return_value = 1920
            mock_image.height.return_value = 1080
            mock_pixmap.toImage.return_value = mock_image
            
            self.video_widget.grab = Mock(return_value=mock_pixmap)
            self.video_widget.size = Mock()
            self.video_widget.size.return_value.width.return_value = 800
            self.video_widget.size.return_value.height.return_value = 600
            
            # 4. 验证可以捕获帧
            captured_image = player.get_current_frame()
            self.assertIsNotNone(captured_image)
            
            # 5. 模拟多次捕获
            for i in range(3):
                latest_image = player.get_current_frame()
                self.assertIsNotNone(latest_image)


def run_frame_capture_tests():
    """运行帧捕获测试"""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestFrameCapture))
    test_suite.addTests(loader.loadTestsFromTestCase(TestFrameCaptureIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("视频帧捕获功能测试")
    if not PYSIDE6_AVAILABLE:
        print("注意: PySide6 未安装，使用模拟环境进行测试")
    print("=" * 60)
    
    success = run_frame_capture_tests()
    
    if success:
        print("\n🎉 所有帧捕获测试通过！")
    else:
        print("\n❌ 部分帧捕获测试失败")
    
    exit(0 if success else 1)