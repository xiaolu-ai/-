#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频播放器应用主入口文件
支持视频播放、截图和标注功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """应用程序主函数"""
    # 创建 QApplication 实例
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("视频播放器")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VideoPlayer")
    
    # 设置高 DPI 支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建主窗口
    main_window = MainWindow()
    main_window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()