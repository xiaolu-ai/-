# -*- coding: utf-8 -*-
"""
文本叠加集成测试
测试截图管理器与标注管理器的集成
"""

import unittest
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 检查 PySide6 是否可用
try:
    from PySide6.QtCore import QObject, Signal
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
    
    class QImage:
        def __init__(self, width=100, height=100):
            self.width_val = width
            self.height_val = height
            
        def copy(self):
            return QImage(self.width_val, self.height_val)
            
        def save(self, path, format):
            return True
            
        def width(self):
            return self.width_val
            
        def height(self):
            return self.height_val


class TestTextOverlayIntegration(unittest.TestCase):
    """文本叠加集成测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟播放器管理器
        self.mock_player = Mock()
        self.mock_player.has_video.return_value = True
        
        # 创建正确的 QImage 对象
        if PYSIDE6_AVAILABLE:
            from PySide6.QtCore import QSize
            test_image = QImage(QSize(800, 600), QImage.Format_RGB32)
        else:
            test_image = QImage(800, 600)
        
        self.mock_player.get_current_frame.return_value = test_image
        self.mock_player.get_current_video_info.return_value = {
            "file_name": "test_video",
            "position": 125000  # 2分5秒
        }
    
    def tearDown(self):
        """测试后清理"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass
    
    @patch('src.screenshot.config_manager')
    def test_screenshot_with_auto_annotation_enabled(self, mock_config):
        """测试启用自动标注的截图功能"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.batch_interval": 5,
            "screenshot.auto_annotation": True,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 验证自动标注已启用
        self.assertTrue(screenshot_manager.auto_annotation)
        
        # 截图
        result_path = screenshot_manager.take_screenshot()
        
        # 验证截图成功
        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.endswith('.png'))
    
    @patch('src.screenshot.config_manager')
    def test_screenshot_with_auto_annotation_disabled(self, mock_config):
        """测试禁用自动标注的截图功能"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.batch_interval": 5,
            "screenshot.auto_annotation": False,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 验证自动标注已禁用
        self.assertFalse(screenshot_manager.auto_annotation)
        
        # 截图
        result_path = screenshot_manager.take_screenshot()
        
        # 验证截图成功
        self.assertIsNotNone(result_path)
        self.assertTrue(result_path.endswith('.png'))
    
    @patch('src.screenshot.config_manager')
    def test_process_screenshot_image_with_annotation(self, mock_config):
        """测试带标注的截图图像处理"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.auto_annotation": True,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 创建测试图像
        test_image = QImage(800, 600)
        
        # 处理图像
        processed_image = screenshot_manager.process_screenshot_image(
            test_image, "test_video", "00:02:05"
        )
        
        # 验证返回了处理后的图像
        self.assertIsNotNone(processed_image)
        if not PYSIDE6_AVAILABLE:
            self.assertEqual(processed_image.width(), 800)
            self.assertEqual(processed_image.height(), 600)
    
    @patch('src.screenshot.config_manager')
    def test_process_screenshot_image_without_annotation(self, mock_config):
        """测试不带标注的截图图像处理"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.auto_annotation": False,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 创建测试图像
        test_image = QImage(800, 600)
        
        # 处理图像
        processed_image = screenshot_manager.process_screenshot_image(
            test_image, "test_video", "00:02:05"
        )
        
        # 验证返回了原始图像（因为自动标注被禁用）
        self.assertEqual(processed_image, test_image)
    
    @patch('src.screenshot.config_manager')
    def test_set_auto_annotation(self, mock_config):
        """测试设置自动标注开关"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.auto_annotation": True,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 初始状态应该是启用的
        self.assertTrue(screenshot_manager.auto_annotation)
        
        # 禁用自动标注
        screenshot_manager.set_auto_annotation(False)
        self.assertFalse(screenshot_manager.auto_annotation)
        mock_config.set.assert_called_with("screenshot.auto_annotation", False)
        
        # 启用自动标注
        screenshot_manager.set_auto_annotation(True)
        self.assertTrue(screenshot_manager.auto_annotation)
        mock_config.set.assert_called_with("screenshot.auto_annotation", True)
    
    @patch('src.screenshot.config_manager')
    def test_set_font_size(self, mock_config):
        """测试设置字体大小"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.auto_annotation": True,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 设置字体大小
        screenshot_manager.set_font_size(24)
        self.assertEqual(screenshot_manager.get_font_size(), 24)
        
        # 测试字体大小范围限制
        screenshot_manager.set_font_size(5)  # 小于最小值
        self.assertEqual(screenshot_manager.get_font_size(), 12)
        
        screenshot_manager.set_font_size(100)  # 大于最大值
        self.assertEqual(screenshot_manager.get_font_size(), 48)
    
    @patch('src.screenshot.config_manager')
    def test_annotation_manager_integration(self, mock_config):
        """测试标注管理器集成"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.save_directory": self.temp_dir,
            "screenshot.auto_annotation": True,
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        mock_config.set = Mock()
        
        from src.screenshot import ScreenshotManager
        screenshot_manager = ScreenshotManager(self.mock_player)
        
        # 验证标注管理器已创建
        self.assertIsNotNone(screenshot_manager.annotation_manager)
        
        # 验证可以获取标注信息
        annotation_info = screenshot_manager.annotation_manager.get_annotation_info()
        self.assertIsInstance(annotation_info, dict)
        self.assertIn("font_size", annotation_info)
        self.assertIn("available_colors", annotation_info)


def run_text_overlay_integration_tests():
    """运行文本叠加集成测试"""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestTextOverlayIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("文本叠加集成测试")
    if not PYSIDE6_AVAILABLE:
        print("注意: PySide6 未安装，使用模拟环境进行测试")
    print("=" * 60)
    
    success = run_text_overlay_integration_tests()
    
    if success:
        print("\n🎉 所有文本叠加集成测试通过！")
    else:
        print("\n❌ 部分文本叠加集成测试失败")
    
    exit(0 if success else 1)