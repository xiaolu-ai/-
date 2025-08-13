# -*- coding: utf-8 -*-
"""
标注管理器简化测试
避免复杂的 Qt 图像操作，专注于逻辑测试
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAnnotationManagerSimple(unittest.TestCase):
    """标注管理器简化测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 信号接收器
        self.received_signals = {
            "annotation_added": [],
            "annotation_saved": [],
            "annotation_failed": []
        }
    
    def connect_signals(self, annotation_manager):
        """连接信号到接收器"""
        annotation_manager.annotation_added.connect(
            lambda tool: self.received_signals["annotation_added"].append(tool)
        )
        annotation_manager.annotation_saved.connect(
            lambda path: self.received_signals["annotation_saved"].append(path)
        )
        annotation_manager.annotation_failed.connect(
            lambda msg: self.received_signals["annotation_failed"].append(msg)
        )
    
    @patch('src.annotation.config_manager')
    def test_annotation_manager_initialization(self, mock_config):
        """测试标注管理器初始化"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.font_size": 16,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        
        from src.annotation import AnnotationManager
        annotation_manager = AnnotationManager()
        
        # 验证初始化
        self.assertEqual(annotation_manager.font_size, 16)
        self.assertEqual(annotation_manager.line_width, 3)
        self.assertEqual(annotation_manager.arrow_size, 10)
        
        # 验证可用颜色
        colors = annotation_manager.get_available_colors()
        self.assertIn("红色", colors)
        self.assertIn("绿色", colors)
        self.assertIn("蓝色", colors)
    
    @patch('src.annotation.config_manager')
    def test_set_font_size(self, mock_config):
        """测试设置字体大小"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.annotation import AnnotationManager
        annotation_manager = AnnotationManager()
        
        # 测试设置有效字体大小
        annotation_manager.set_font_size(20)
        self.assertEqual(annotation_manager.font_size, 20)
        mock_config.set.assert_called_with("screenshot.font_size", 20)
        
        # 测试字体大小范围限制
        annotation_manager.set_font_size(5)  # 小于最小值
        self.assertEqual(annotation_manager.font_size, 12)
        
        annotation_manager.set_font_size(100)  # 大于最大值
        self.assertEqual(annotation_manager.font_size, 48)
    
    @patch('src.annotation.config_manager')
    def test_set_line_width(self, mock_config):
        """测试设置线条宽度"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.annotation import AnnotationManager
        annotation_manager = AnnotationManager()
        
        # 测试设置有效线条宽度
        annotation_manager.set_line_width(5)
        self.assertEqual(annotation_manager.line_width, 5)
        mock_config.set.assert_called_with("annotation.line_width", 5)
        
        # 测试线条宽度范围限制
        annotation_manager.set_line_width(0)  # 小于最小值
        self.assertEqual(annotation_manager.line_width, 1)
        
        annotation_manager.set_line_width(20)  # 大于最大值
        self.assertEqual(annotation_manager.line_width, 10)
    
    @patch('src.annotation.config_manager')
    def test_get_annotation_info(self, mock_config):
        """测试获取标注信息"""
        mock_config.get.side_effect = lambda key, default: {
            "screenshot.font_size": 18,
            "screenshot.font_color": "#FFFFFF",
            "annotation.default_color": "#FF0000",
            "annotation.line_width": 3,
            "annotation.arrow_size": 10
        }.get(key, default)
        
        from src.annotation import AnnotationManager
        annotation_manager = AnnotationManager()
        
        info = annotation_manager.get_annotation_info()
        
        self.assertIsInstance(info, dict)
        self.assertEqual(info["font_size"], 18)
        self.assertEqual(info["line_width"], 3)
        self.assertEqual(info["arrow_size"], 10)
        self.assertIn("available_colors", info)
    
    @patch('src.annotation.config_manager')
    def test_annotation_tools_enum(self, mock_config):
        """测试标注工具枚举"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.annotation import AnnotationTool
        
        # 验证枚举值
        self.assertEqual(AnnotationTool.NONE.value, "none")
        self.assertEqual(AnnotationTool.ARROW.value, "arrow")
        self.assertEqual(AnnotationTool.RECTANGLE.value, "rectangle")
        self.assertEqual(AnnotationTool.FREEHAND.value, "freehand")
    
    @patch('src.annotation.config_manager')
    def test_annotation_data_class(self, mock_config):
        """测试标注数据类"""
        mock_config.get.side_effect = lambda key, default: default
        
        from src.annotation import AnnotationData, AnnotationTool
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QColor
        
        # 创建标注数据
        points = [QPoint(10, 10), QPoint(20, 20)]
        color = QColor("#FF0000")
        
        annotation = AnnotationData(
            tool=AnnotationTool.ARROW,
            points=points,
            color=color,
            line_width=3
        )
        
        # 验证数据
        self.assertEqual(annotation.tool, AnnotationTool.ARROW)
        self.assertEqual(len(annotation.points), 2)
        self.assertEqual(annotation.line_width, 3)
        self.assertIsInstance(annotation.color, QColor)
    
    @patch('src.annotation.config_manager')
    def test_color_handling(self, mock_config):
        """测试颜色处理"""
        mock_config.get.side_effect = lambda key, default: default
        mock_config.set = Mock()
        
        from src.annotation import AnnotationManager
        from PySide6.QtGui import QColor
        
        annotation_manager = AnnotationManager()
        
        # 测试设置字体颜色
        test_color = QColor("#00FF00")
        annotation_manager.set_font_color(test_color)
        
        # 测试设置标注颜色
        annotation_color = QColor("#0000FF")
        annotation_manager.set_annotation_color(annotation_color)
        
        # 验证配置保存被调用
        self.assertTrue(mock_config.set.called)


def run_annotation_simple_tests():
    """运行简化标注测试"""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTests(loader.loadTestsFromTestCase(TestAnnotationManagerSimple))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("标注管理器简化测试")
    print("=" * 60)
    
    success = run_annotation_simple_tests()
    
    if success:
        print("\n🎉 所有简化标注测试通过！")
    else:
        print("\n❌ 部分简化标注测试失败")
    
    exit(0 if success else 1)