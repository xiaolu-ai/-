# -*- coding: utf-8 -*-
"""
截图管理器单元测试
测试截图功能，包括单次截图和批量截图
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 检查 PySide6 是否可用
try:
    from PySide6.QtCore import QObject, Signal, QTimer
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
    
    class QTimer:
        def __init__(self):
            self.timeout = Signal()
            self.active = False
            
        def start(self, interval):
            self.active = True
            
        def stop(self):
            self.active = False
            
        def setInterval(self, interval):
            pass
    
    class QImage:
        def __init__(self):
            pass
            
        def save(self, path, format):
            return True


class TestScreenshotManager(unittest.TestCase):
    """截图管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟的播放器管理器
        self.mock_player = Mock()
        self.mock_player.has_video.return_value = True
        self.mock_player.get_current_frame.return_value = QImage(10, 10, QImage.Format_RGB32)
        self.mock_player.get_current_video_info.return_value = {
            "file_name": "test_video",
            "position": 125000,  # 2分5秒
            "duration": 300000   # 5分钟
        }
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    @patch('src.screenshot.config_manager')
    def test_screenshot_manager_initialization(self, mock_config):
        """测试截图管理器初始化"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.batch_interval": 5,
            "screenshot.auto_annotation": True
        }.get(key, default)
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 验证初始化
        self.assertEqual(screenshot_manager.save_directory, self.temp_dir)
        self.assertEqual(screenshot_manager.batch_interval, 5)
        self.assertTrue(screenshot_manager.auto_annotation)
        self.assertFalse(screenshot_manager.is_batch_active)
        self.assertEqual(screenshot_manager.batch_count, 0)
    
    @patch('src.screenshot.config_manager')
    def test_set_save_directory(self, mock_config):
        """测试设置保存目录"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试设置有效目录
        new_dir = Path(self.temp_dir) / "screenshots"
        result = screenshot_manager.set_save_directory(str(new_dir))
        
        self.assertTrue(result)
        self.assertEqual(screenshot_manager.save_directory, str(new_dir))
        mock_config.set.assert_called_with("screenshot.save_directory", str(new_dir))
    
    @patch('src.screenshot.config_manager')
    def test_generate_filename(self, mock_config):
        """测试文件名生成"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试正常文件名生成
        filename = screenshot_manager.generate_filename("test_video", "00:02:05")
        expected_path = Path(self.temp_dir) / "test_video_00-02-05.png"
        self.assertEqual(filename, str(expected_path))
        
        # 测试不安全字符处理
        filename = screenshot_manager.generate_filename("test<>video", "01:30:45")
        self.assertNotIn("<", filename)
        self.assertNotIn(">", filename)
    
    @patch('src.screenshot.SaveImageThread')
    @patch('src.screenshot.config_manager')
    def test_take_screenshot_starts_thread(self, mock_config, mock_save_thread):
        """测试截图是否启动了保存线程"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else True
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 执行截图
        result_path = screenshot_manager.take_screenshot()
        
        # 验证返回了预期的路径
        self.assertIn("test_video_02-05-00.png", result_path)
        
        # 验证 SaveImageThread 被实例化并启动
        mock_save_thread.assert_called_once()
        mock_save_thread.return_value.start.assert_called_once()

    @patch('src.screenshot.config_manager')
    def test_take_screenshot_no_video(self, mock_config):
        """测试没有视频时截图"""
        mock_config.get.side_effect = lambda key, default: default
        
        # 设置播放器没有视频
        self.mock_player.has_video.return_value = False
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        result = screenshot_manager.take_screenshot()
        self.assertIsNone(result)
    
    @patch('src.screenshot.config_manager')
    def test_take_screenshot_no_frame(self, mock_config):
        """测试无法获取帧时截图"""
        mock_config.get.side_effect = lambda key, default: default
        
        # 设置播放器无法获取帧
        self.mock_player.get_current_frame.return_value = None
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        result = screenshot_manager.take_screenshot()
        self.assertIsNone(result)
    
    @patch('src.screenshot.config_manager')
    def test_save_screenshot_image(self, mock_config):
        """测试保存截图图像"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 创建测试图像
        test_image = QImage()
        test_path = Path(self.temp_dir) / "test_screenshot.png"
        
        # 这个方法现在是异步的，我们可以测试它是否正确启动线程
        with patch('src.screenshot.SaveImageThread') as mock_thread:
            result = screenshot_manager.save_screenshot_image(test_image, str(test_path))
            self.assertTrue(result) # 启动线程应该返回 True
            mock_thread.assert_called_once_with(test_image, str(test_path))
            mock_thread.return_value.start.assert_called_once()
    
    @patch('src.screenshot.config_manager')
    def test_start_batch_screenshot(self, mock_config):
        """测试开始批量截图"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 模拟成功的截图
        with patch.object(screenshot_manager, 'take_screenshot', return_value="test.png"):
            result = screenshot_manager.start_batch_screenshot(3)
            
            self.assertTrue(result)
            self.assertTrue(screenshot_manager.is_batch_active)
            self.assertIsNotNone(screenshot_manager.batch_timer)
            self.assertEqual(screenshot_manager.batch_interval, 3)
            
            screenshot_manager.cleanup()
    
    @patch('src.screenshot.config_manager')
    def test_start_batch_screenshot_no_video(self, mock_config):
        """测试没有视频时开始批量截图"""
        mock_config.get.side_effect = lambda key, default: default
        
        # 设置播放器没有视频
        self.mock_player.has_video.return_value = False
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        result = screenshot_manager.start_batch_screenshot()
        self.assertFalse(result)
        self.assertFalse(screenshot_manager.is_batch_active)
    
    @patch('src.screenshot.config_manager')
    def test_stop_batch_screenshot(self, mock_config):
        """测试停止批量截图"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 先启动批量截图
        with patch.object(screenshot_manager, 'take_screenshot', return_value="test.png"):
            screenshot_manager.start_batch_screenshot()
            self.assertTrue(screenshot_manager.is_batch_active)
            
            # 停止批量截图
            screenshot_manager.stop_batch_screenshot()
            self.assertFalse(screenshot_manager.is_batch_active)
            self.assertIsNone(screenshot_manager.batch_timer)
    
    @patch('src.screenshot.config_manager')
    def test_set_batch_interval(self, mock_config):
        """测试设置批量截图间隔"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试设置有效间隔
        screenshot_manager.set_batch_interval(10)
        self.assertEqual(screenshot_manager.batch_interval, 10)
        mock_config.set.assert_called_with("screenshot.batch_interval", 10)
        
        # 测试间隔范围限制
        screenshot_manager.set_batch_interval(0)  # 小于最小值
        self.assertEqual(screenshot_manager.batch_interval, 1)
        
        screenshot_manager.set_batch_interval(100)  # 大于最大值
        self.assertEqual(screenshot_manager.batch_interval, 60)
    
    @patch('src.screenshot.config_manager')
    def test_on_batch_timer_timeout(self, mock_config):
        """测试批量截图定时器超时处理"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 设置批量截图状态
        screenshot_manager.is_batch_active = True
        screenshot_manager.batch_count = 0
        
        # 模拟成功截图
        with patch.object(screenshot_manager, 'take_screenshot', return_value="test.png"):
            screenshot_manager.on_batch_timer_timeout()
            
            self.assertEqual(screenshot_manager.batch_count, 1)
    
    @patch('src.screenshot.config_manager')
    def test_on_batch_timer_timeout_no_video(self, mock_config):
        """测试批量截图时视频停止的处理"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 设置批量截图状态
        screenshot_manager.is_batch_active = True
        
        # 设置播放器没有视频
        self.mock_player.has_video.return_value = False
        
        # 模拟定时器超时
        with patch.object(screenshot_manager, 'stop_batch_screenshot') as mock_stop:
            screenshot_manager.on_batch_timer_timeout()
            mock_stop.assert_called_once()
    
    @patch('src.screenshot.config_manager')
    def test_get_screenshot_info(self, mock_config):
        """测试获取截图信息"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.batch_interval": 5,
            "screenshot.auto_annotation": True
        }.get(key, default)
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        info = screenshot_manager.get_screenshot_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["save_directory"], self.temp_dir)
        self.assertEqual(info["batch_interval"], 5)
        self.assertTrue(info["auto_annotation"])
        self.assertFalse(info["is_batch_active"])
        self.assertEqual(info["batch_count"], 0)
    
    @patch('src.screenshot.config_manager')
    def test_get_supported_formats(self, mock_config):
        """测试获取支持的格式"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        formats = screenshot_manager.get_supported_formats()
        
        self.assertIsInstance(formats, list)
        self.assertIn("PNG", formats)
        self.assertIn("JPG", formats)
    
    @patch('src.screenshot.config_manager')
    def test_cleanup(self, mock_config):
        """测试资源清理"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 启动批量截图
        with patch.object(screenshot_manager, 'take_screenshot', return_value="test.png"):
            screenshot_manager.start_batch_screenshot()
            self.assertTrue(screenshot_manager.is_batch_active)
            
            # 清理资源
            screenshot_manager.cleanup()
            self.assertFalse(screenshot_manager.is_batch_active)


if __name__ == "__main__":
    unittest.main(verbosity=2)