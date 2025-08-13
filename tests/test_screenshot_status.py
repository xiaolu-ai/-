# -*- coding: utf-8 -*-
"""
截图状态反馈功能测试
测试截图状态消息、进度跟踪和信息获取功能
"""

import unittest
import tempfile
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

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
            self.connected_slots = []
            
        def emit(self, *args):
            for slot in self.connected_slots:
                slot(*args)
                
        def connect(self, slot):
            self.connected_slots.append(slot)
    
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
        def save(self, path, format):
            return True


class TestScreenshotStatus(unittest.TestCase):
    """截图状态反馈测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟的播放器管理器
        self.mock_player = Mock()
        self.mock_player.has_video.return_value = True
        self.mock_player.get_current_frame.return_value = QImage()
        self.mock_player.get_current_video_info.return_value = {
            "file_name": "test_video",
            "position": 125000,  # 2分5秒
            "duration": 300000   # 5分钟
        }
        
        # 信号接收器
        self.received_signals = {
            "screenshot_saved": [],
            "screenshot_failed": [],
            "batch_started": [],
            "batch_stopped": [],
            "batch_progress": [],
            "status_message": []
        }
    
    def tearDown(self):
        """测试后清理"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    def connect_signals(self, screenshot_manager):
        """连接信号到接收器"""
        screenshot_manager.screenshot_saved.connect(
            lambda path: self.received_signals["screenshot_saved"].append(path)
        )
        screenshot_manager.screenshot_failed.connect(
            lambda msg: self.received_signals["screenshot_failed"].append(msg)
        )
        screenshot_manager.batch_screenshot_started.connect(
            lambda interval: self.received_signals["batch_started"].append(interval)
        )
        screenshot_manager.batch_screenshot_stopped.connect(
            lambda count: self.received_signals["batch_stopped"].append(count)
        )
        screenshot_manager.batch_screenshot_progress.connect(
            lambda count, path: self.received_signals["batch_progress"].append((count, path))
        )
        screenshot_manager.status_message.connect(
            lambda msg: self.received_signals["status_message"].append(msg)
        )
    
    @patch('src.screenshot.config_manager')
    def test_screenshot_success_signals(self, mock_config):
        """测试成功截图的信号发射"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        self.connect_signals(screenshot_manager)
        
        # 模拟成功的截图保存
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            result = screenshot_manager.take_screenshot()
            
            # 验证信号发射
            self.assertEqual(len(self.received_signals["screenshot_saved"]), 1)
            self.assertEqual(len(self.received_signals["status_message"]), 1)
            self.assertIn("截图保存成功", self.received_signals["status_message"][0])
    
    @patch('src.screenshot.config_manager')
    def test_screenshot_failure_signals(self, mock_config):
        """测试截图失败的信号发射"""
        mock_config.get.side_effect = lambda key, default: default
        
        # 设置播放器没有视频
        self.mock_player.has_video.return_value = False
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        self.connect_signals(screenshot_manager)
        
        result = screenshot_manager.take_screenshot()
        
        # 验证失败信号发射
        self.assertEqual(len(self.received_signals["screenshot_failed"]), 1)
        self.assertEqual(len(self.received_signals["status_message"]), 1)
        self.assertIn("没有加载视频", self.received_signals["screenshot_failed"][0])
    
    @patch('src.screenshot.config_manager')
    def test_batch_screenshot_signals(self, mock_config):
        """测试批量截图信号发射"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        self.connect_signals(screenshot_manager)
        
        # 模拟成功的截图
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            # 启动批量截图
            result = screenshot_manager.start_batch_screenshot(3)
            
            # 验证启动信号
            self.assertTrue(result)
            self.assertEqual(len(self.received_signals["batch_started"]), 1)
            self.assertEqual(self.received_signals["batch_started"][0], 3)
            self.assertTrue(any("批量截图已启动" in msg for msg in self.received_signals["status_message"]))
            
            # 验证进度信号（第一张截图）
            self.assertEqual(len(self.received_signals["batch_progress"]), 1)
            count, path = self.received_signals["batch_progress"][0]
            self.assertEqual(count, 1)
            
            # 停止批量截图
            screenshot_manager.stop_batch_screenshot()
            
            # 验证停止信号
            self.assertEqual(len(self.received_signals["batch_stopped"]), 1)
            self.assertEqual(self.received_signals["batch_stopped"][0], 1)  # 截取了1张
    
    @patch('src.screenshot.config_manager')
    def test_batch_timer_timeout_signals(self, mock_config):
        """测试批量截图定时器信号"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        self.connect_signals(screenshot_manager)
        
        # 设置批量截图状态
        screenshot_manager.is_batch_active = True
        screenshot_manager.batch_count = 2
        
        # 模拟成功截图
        with patch.object(screenshot_manager, 'take_screenshot', return_value="test.png"):
            screenshot_manager.on_batch_timer_timeout()
            
            # 验证进度信号
            self.assertEqual(len(self.received_signals["batch_progress"]), 1)
            count, path = self.received_signals["batch_progress"][0]
            self.assertEqual(count, 3)  # 从2增加到3
            self.assertEqual(path, "test.png")
    
    @patch('src.screenshot.config_manager')
    def test_get_screenshot_info_detailed(self, mock_config):
        """测试获取详细截图信息"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.batch_interval": 5,
            "screenshot.auto_annotation": True
        }.get(key, default)
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试初始状态
        info = screenshot_manager.get_screenshot_info()
        self.assertEqual(info["batch_count"], 0)
        self.assertEqual(info["batch_duration"], 0)
        self.assertFalse(info["is_batch_active"])
        self.assertEqual(info["last_screenshot_path"], "")
        
        # 模拟启动批量截图
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            screenshot_manager.start_batch_screenshot()
            
            # 测试活动状态
            info = screenshot_manager.get_screenshot_info()
            self.assertTrue(info["is_batch_active"])
            self.assertEqual(info["batch_count"], 1)  # 启动时截取了第一张
            self.assertIsNotNone(info["batch_start_time"])
            self.assertNotEqual(info["last_screenshot_path"], "")
    
    @patch('src.screenshot.config_manager')
    def test_get_batch_status_message(self, mock_config):
        """测试获取批量截图状态消息"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试未启动状态
        status = screenshot_manager.get_batch_status_message()
        self.assertEqual(status, "批量截图未启动")
        
        # 模拟启动批量截图
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            screenshot_manager.start_batch_screenshot()
            
            # 测试运行状态
            status = screenshot_manager.get_batch_status_message()
            self.assertIn("批量截图进行中", status)
            self.assertIn("已截取 1 张", status)
            self.assertIn("运行", status)
    
    @patch('src.screenshot.config_manager')
    def test_get_last_screenshot_info(self, mock_config):
        """测试获取最后截图信息"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 测试没有截图时
        info = screenshot_manager.get_last_screenshot_info()
        self.assertFalse(info["exists"])
        
        # 创建一个测试文件
        test_file = Path(self.temp_dir) / "test_screenshot.png"
        test_file.write_text("test image data")
        screenshot_manager.last_screenshot_path = str(test_file)
        
        # 测试有截图时
        info = screenshot_manager.get_last_screenshot_info()
        self.assertTrue(info["exists"])
        self.assertEqual(info["name"], "test_screenshot.png")
        self.assertIn("size", info)
        self.assertIn("created_time", info)
        self.assertIn("size_string", info)
    
    @patch('src.screenshot.config_manager')
    def test_status_message_content(self, mock_config):
        """测试状态消息内容"""
        mock_config.get.side_effect = lambda key, default: self.temp_dir if "directory" in key else default
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        self.connect_signals(screenshot_manager)
        
        # 测试成功截图消息
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            screenshot_manager.take_screenshot()
            
            messages = self.received_signals["status_message"]
            self.assertTrue(any("截图保存成功" in msg for msg in messages))
            self.assertTrue(any("test_video_00-02-05.png" in msg for msg in messages))
        
        # 清空消息
        self.received_signals["status_message"].clear()
        
        # 测试批量截图消息
        with patch.object(screenshot_manager, 'save_screenshot_image', return_value=True):
            screenshot_manager.start_batch_screenshot(2)
            screenshot_manager.stop_batch_screenshot()
            
            messages = self.received_signals["status_message"]
            self.assertTrue(any("批量截图已启动，间隔: 2秒" in msg for msg in messages))
            self.assertTrue(any("批量截图已停止" in msg for msg in messages))
            self.assertTrue(any("共截取 1 张图片" in msg for msg in messages))


def run_screenshot_status_tests():
    """运行截图状态测试"""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestScreenshotStatus))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("截图状态反馈功能测试")
    if not PYSIDE6_AVAILABLE:
        print("注意: PySide6 未安装，使用模拟环境进行测试")
    print("=" * 60)
    
    success = run_screenshot_status_tests()
    
    if success:
        print("\n🎉 所有截图状态测试通过！")
    else:
        print("\n❌ 部分截图状态测试失败")
    
    exit(0 if success else 1)