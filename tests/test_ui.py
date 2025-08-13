import unittest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

class TestUI(unittest.TestCase):
    """UI组件冒烟测试"""
    
    @classmethod
    def setUpClass(cls):
        """为所有测试创建一个 QApplication 实例"""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])
            
    def test_main_window_creation(self):
        """测试 MainWindow 是否可以被成功创建"""
        from ui.main_window import MainWindow
        try:
            window = MainWindow()
            window.close() # 立即关闭以避免挂起
            self.assertIsNotNone(window)
        except Exception as e:
            self.fail(f"创建 MainWindow 失败，错误: {e}")

    def test_annotation_dialog_creation(self):
        """测试 AnnotationDialog 是否可以被成功创建"""
        from src.annotation import AnnotationDialog
        try:
            # 创建一个模拟图像
            image = QImage(100, 100, QImage.Format_RGB32)
            dialog = AnnotationDialog(image)
            dialog.close()
            self.assertIsNotNone(dialog)
        except Exception as e:
            self.fail(f"创建 AnnotationDialog 失败，错误: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
