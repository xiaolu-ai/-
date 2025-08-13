# -*- coding: utf-8 -*-
"""
标注管理模块
负责图像标注功能，包括文本叠加和绘制工具
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QObject, Signal, QPoint, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QFont, QColor, QPen, QBrush, QPixmap, QIcon, QGuiApplication
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QColorDialog, QSpinBox, QComboBox, QScrollArea, QWidget,
                               QButtonGroup, QToolButton, QSlider, QGroupBox, QGridLayout)

from .config import config_manager
from .utils import TimeFormatter, SaveImageThread, ErrorHandler


class AnnotationTool(Enum):
    """标注工具枚举"""
    NONE = "none"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    FREEHAND = "freehand"


@dataclass
class AnnotationData:
    """标注数据类"""
    tool: AnnotationTool
    points: List[QPoint]
    color: QColor
    line_width: int
    
    def __post_init__(self):
        """确保颜色是 QColor 对象"""
        if isinstance(self.color, str):
            self.color = QColor(self.color)


class AnnotationManager(QObject):
    """标注管理器类"""
    
    # 信号定义
    annotation_added = Signal(str)  # 标注添加完成信号 (标注类型)
    annotation_saved = Signal(str)  # 标注保存完成信号 (文件路径)
    annotation_failed = Signal(str)  # 标注失败信号 (错误信息)
    
    def __init__(self):
        """初始化标注管理器"""
        super().__init__()
        
        # 标注配置
        self.font_size = config_manager.get("screenshot.font_size", 16)
        self.font_color = QColor(config_manager.get("screenshot.font_color", "#FFFFFF"))
        self.default_annotation_color = QColor(config_manager.get("annotation.default_color", "#FF0000"))
        self.line_width = config_manager.get("annotation.line_width", 3)
        self.arrow_size = config_manager.get("annotation.arrow_size", 10)
        
        # 跟踪活动的保存线程
        self.active_save_threads = []

        # 支持的颜色
        self.available_colors = {
            "红色": QColor("#FF0000"),
            "绿色": QColor("#00FF00"),
            "蓝色": QColor("#0000FF"),
            "黄色": QColor("#FFFF00"),
            "黑色": QColor("#000000"),
            "白色": QColor("#FFFFFF"),
            "橙色": QColor("#FFA500"),
            "紫色": QColor("#800080")
        }
        
        print("标注管理器初始化完成")
    
    def add_text_overlay(self, image: QImage, text_lines: List[str], font_size: int = None) -> QImage:
        """
        在图像上添加文本叠加
        
        Args:
            image: 原始图像
            text_lines: 文本行列表
            font_size: 字体大小，如果为 None 则使用配置中的值
            
        Returns:
            添加了文本的图像
        """
        try:
            if font_size is None:
                font_size = self.font_size
            
            # 创建图像副本
            result_image = image.copy()
            
            # 创建画笔
            painter = QPainter(result_image)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置字体
            font = QFont("Arial", font_size, QFont.Bold)
            painter.setFont(font)
            
            # 设置文本颜色和背景
            text_color = self.font_color
            background_color = QColor(0, 0, 0, 128)  # 半透明黑色背景
            
            # 计算文本位置（左上角，留一些边距）
            margin = 10
            line_height = font_size + 5
            
            for i, text_line in enumerate(text_lines):
                if not text_line.strip():
                    continue
                
                # 计算文本位置
                y_position = margin + (i + 1) * line_height
                
                # 获取文本尺寸
                text_rect = painter.fontMetrics().boundingRect(text_line)
                
                # 绘制背景矩形
                background_rect = QRect(
                    margin - 5,
                    y_position - text_rect.height(),
                    text_rect.width() + 10,
                    text_rect.height() + 5
                )
                painter.fillRect(background_rect, background_color)
                
                # 绘制文本
                painter.setPen(text_color)
                painter.drawText(margin, y_position, text_line)
            
            painter.end()
            
            print(f"成功添加文本叠加，共 {len(text_lines)} 行")
            return result_image
            
        except Exception as e:
            error_msg = f"添加文本叠加失败: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            return image
    
    def create_screenshot_with_info(self, image: QImage, video_name: str, timestamp: str) -> QImage:
        """
        创建带有视频信息的截图
        
        Args:
            image: 原始截图图像
            video_name: 视频文件名
            timestamp: 时间戳字符串
            
        Returns:
            添加了信息的截图
        """
        try:
            # 准备文本行
            text_lines = [
                f"文件: {video_name}",
                f"时间: {timestamp}"
            ]
            
            # 添加文本叠加
            result_image = self.add_text_overlay(image, text_lines)
            
            print(f"成功创建带信息的截图: {video_name} @ {timestamp}")
            return result_image
            
        except Exception as e:
            error_msg = f"创建带信息截图失败: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            return image
    
    def draw_arrow(self, image: QImage, start_point: QPoint, end_point: QPoint, 
                   color: QColor = None, line_width: int = None) -> QImage:
        """
        在图像上绘制箭头
        
        Args:
            image: 原始图像
            start_point: 起始点
            end_point: 结束点
            color: 箭头颜色
            line_width: 线条宽度
            
        Returns:
            绘制了箭头的图像
        """
        try:
            if color is None:
                color = self.default_annotation_color
            if line_width is None:
                line_width = self.line_width
            
            # 创建图像副本
            result_image = image.copy()
            
            # 创建画笔
            painter = QPainter(result_image)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置画笔
            pen = QPen(color, line_width)
            painter.setPen(pen)
            
            # 绘制主线
            painter.drawLine(start_point, end_point)
            
            # 计算箭头头部
            import math
            
            # 计算角度
            dx = end_point.x() - start_point.x()
            dy = end_point.y() - start_point.y()
            angle = math.atan2(dy, dx)
            
            # 箭头头部长度
            arrow_length = self.arrow_size
            arrow_angle = math.pi / 6  # 30度
            
            # 计算箭头头部的两个点
            arrow_point1 = QPoint(
                int(end_point.x() - arrow_length * math.cos(angle - arrow_angle)),
                int(end_point.y() - arrow_length * math.sin(angle - arrow_angle))
            )
            arrow_point2 = QPoint(
                int(end_point.x() - arrow_length * math.cos(angle + arrow_angle)),
                int(end_point.y() - arrow_length * math.sin(angle + arrow_angle))
            )
            
            # 绘制箭头头部
            painter.drawLine(end_point, arrow_point1)
            painter.drawLine(end_point, arrow_point2)
            
            painter.end()
            
            print(f"成功绘制箭头: ({start_point.x()}, {start_point.y()}) -> ({end_point.x()}, {end_point.y()})")
            self.annotation_added.emit("arrow")
            return result_image
            
        except Exception as e:
            error_msg = f"绘制箭头失败: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            return image
    
    def draw_rectangle(self, image: QImage, start_point: QPoint, end_point: QPoint,
                      color: QColor = None, line_width: int = None, filled: bool = False) -> QImage:
        """
        在图像上绘制矩形
        
        Args:
            image: 原始图像
            start_point: 起始点
            end_point: 结束点
            color: 矩形颜色
            line_width: 线条宽度
            filled: 是否填充
            
        Returns:
            绘制了矩形的图像
        """
        try:
            if color is None:
                color = self.default_annotation_color
            if line_width is None:
                line_width = self.line_width
            
            # 创建图像副本
            result_image = image.copy()
            
            # 创建画笔
            painter = QPainter(result_image)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 创建矩形
            rect = QRect(start_point, end_point)
            
            if filled:
                # 填充矩形
                brush = QBrush(color)
                painter.fillRect(rect, brush)
            else:
                # 绘制矩形边框
                pen = QPen(color, line_width)
                painter.setPen(pen)
                painter.drawRect(rect)
            
            painter.end()
            
            print(f"成功绘制矩形: ({start_point.x()}, {start_point.y()}) -> ({end_point.x()}, {end_point.y()})")
            self.annotation_added.emit("rectangle")
            return result_image
            
        except Exception as e:
            error_msg = f"绘制矩形失败: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            return image
    
    def draw_freehand(self, image: QImage, points: List[QPoint], 
                     color: QColor = None, line_width: int = None) -> QImage:
        """
        在图像上绘制自由线条
        
        Args:
            image: 原始图像
            points: 点列表
            color: 线条颜色
            line_width: 线条宽度
            
        Returns:
            绘制了线条的图像
        """
        try:
            if not points or len(points) < 2:
                return image
            
            if color is None:
                color = self.default_annotation_color
            if line_width is None:
                line_width = self.line_width
            
            # 创建图像副本
            result_image = image.copy()
            
            # 创建画笔
            painter = QPainter(result_image)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置画笔
            pen = QPen(color, line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            
            # 绘制连续线条
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
            
            painter.end()
            
            print(f"成功绘制自由线条，共 {len(points)} 个点")
            self.annotation_added.emit("freehand")
            return result_image
            
        except Exception as e:
            error_msg = f"绘制自由线条失败: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            return image
    
    def save_annotated_image(self, image: QImage, file_path: str) -> bool:
        """
        保存标注后的图像
        
        Args:
            image: 要保存的图像
            file_path: 保存路径
            
        Returns:
            保存是否成功
        """
        try:
            thread = SaveImageThread(image, file_path)
            thread.finished.connect(self._on_save_finished)
            thread.error.connect(self._on_save_error)
            thread.start()
            
            self.active_save_threads.append(thread)
            return True

        except Exception as e:
            error_msg = f"保存标注图像时发生错误: {str(e)}"
            print(error_msg)
            self.annotation_failed.emit(error_msg)
            ErrorHandler.show_critical("保存失败", error_msg)
            return False

    def _on_save_finished(self, success: bool, file_path: str):
        """图像保存完成处理"""
        if success:
            print(f"标注图像保存成功: {file_path}")
            self.annotation_saved.emit(file_path)
        
        # 清理完成的线程
        self.active_save_threads = [t for t in self.active_save_threads if not t.isFinished()]

    def _on_save_error(self, error_msg: str, file_path: str):
        """图像保存错误处理"""
        full_error = f"保存标注图像失败: {Path(file_path).name}\n原因: {error_msg}"
        print(full_error)
        self.annotation_failed.emit(full_error)
        ErrorHandler.show_critical("保存失败", full_error)
        
        # 清理完成的线程
        self.active_save_threads = [t for t in self.active_save_threads if not t.isFinished()]

    def set_font_size(self, size: int):
        """
        设置字体大小
        
        Args:
            size: 字体大小 (12-48)
        """
        size = max(12, min(48, size))
        self.font_size = size
        config_manager.set("screenshot.font_size", size)
        print(f"字体大小设置为: {size}")
    
    def set_font_color(self, color: QColor):
        """
        设置字体颜色
        
        Args:
            color: 字体颜色
        """
        self.font_color = color
        config_manager.set("screenshot.font_color", color.name())
        print(f"字体颜色设置为: {color.name()}")
    
    def set_annotation_color(self, color: QColor):
        """
        设置标注颜色
        
        Args:
            color: 标注颜色
        """
        self.default_annotation_color = color
        config_manager.set("annotation.default_color", color.name())
        print(f"标注颜色设置为: {color.name()}")
    
    def set_line_width(self, width: int):
        """
        设置线条宽度
        
        Args:
            width: 线条宽度 (1-10)
        """
        width = max(1, min(10, width))
        self.line_width = width
        config_manager.set("annotation.line_width", width)
        print(f"线条宽度设置为: {width}")
    
    def get_annotation_info(self) -> dict:
        """
        获取标注相关信息
        
        Returns:
            包含标注信息的字典
        """
        return {
            "font_size": self.font_size,
            "font_color": self.font_color.name(),
            "annotation_color": self.default_annotation_color.name(),
            "line_width": self.line_width,
            "arrow_size": self.arrow_size,
            "available_colors": {name: color.name() for name, color in self.available_colors.items()}
        }
    
    def get_available_colors(self) -> dict:
        """
        获取可用颜色
        
        Returns:
            颜色名称到 QColor 的映射
        """
        return self.available_colors.copy()
    
    def cleanup(self):
        """清理资源"""
        # 等待所有保存线程完成
        for thread in self.active_save_threads:
            thread.wait()

        print("标注管理器资源已清理")


class AnnotationWidget(QWidget):
    """标注绘制组件"""
    
    # 信号定义
    tool_changed = Signal(AnnotationTool)  # 工具切换信号
    color_changed = Signal(QColor)  # 颜色切换信号
    line_width_changed = Signal(int)  # 线宽切换信号
    drawing_completed = Signal()  # 绘制完成信号
    
    def __init__(self, image: QImage, parent: Optional[QWidget] = None):
        """
        初始化标注绘制组件
        
        Args:
            image: 要标注的原始图像
            parent: 父组件
        """
        super().__init__(parent)
        
        self.image = image.copy()
        self.original_image = image.copy()
        self.scale_factor: float = 1.0
        
        # 绘制状态
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_shape = None
        self.shapes: List[AnnotationData] = []
        
        # 绘制工具配置
        self.current_tool = AnnotationTool.NONE
        self.current_color = QColor(config_manager.get("annotation.default_color", "#FF0000"))
        self.line_width = config_manager.get("annotation.line_width", 3)
        
        # 设置基础属性（尺寸由 scale_factor 控制）
        self._apply_scale()
        self.setMouseTracking(True)

    def _apply_scale(self):
        """根据当前 scale_factor 应用小部件尺寸"""
        scaled_width = max(1, int(self.original_image.width() * self.scale_factor))
        scaled_height = max(1, int(self.original_image.height() * self.scale_factor))
        self.setFixedSize(scaled_width, scaled_height)

    def set_scale_factor(self, factor: float):
        """设置缩放比例并更新组件尺寸"""
        factor = max(0.05, min(8.0, factor))
        if abs(self.scale_factor - factor) > 1e-3:
            self.scale_factor = factor
            self._apply_scale()
            self.update()

    def fit_to_size(self, max_width: int, max_height: int):
        """根据给定的最大宽高进行自适应缩放（只缩小，不放大）"""
        if self.original_image.isNull():
            return
        iw = self.original_image.width()
        ih = self.original_image.height()
        if iw == 0 or ih == 0:
            return
        scale_w = max_width / iw
        scale_h = max_height / ih
        scale = min(scale_w, scale_h)
        # 仅缩小，避免小图放大变糊
        scale = min(1.0, scale)
        if scale <= 0:
            scale = 0.1
        self.set_scale_factor(scale)
    
    def set_tool(self, tool: AnnotationTool):
        """设置当前使用的工具"""
        if self.current_tool != tool:
            self.current_tool = tool
            print(f"标注工具切换为: {tool.value}")
            self.tool_changed.emit(tool)
    
    def set_color(self, color: QColor):
        """设置当前颜色"""
        if self.current_color != color:
            self.current_color = color
            print(f"标注颜色切换为: {color.name()}")
            self.color_changed.emit(color)
            
    def set_line_width(self, width: int):
        """设置当前线宽"""
        width = max(1, min(10, width))
        if self.line_width != width:
            self.line_width = width
            print(f"标注线宽切换为: {width}")
            self.line_width_changed.emit(width)
            
    def get_annotated_image(self) -> QImage:
        """获取包含所有标注的最终图像"""
        return self.image.copy()

    def mousePressEvent(self, event: "QMouseEvent"):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton and self.current_tool != AnnotationTool.NONE:
            self.drawing = True
            # 将坐标从显示坐标转换为原始图像坐标
            self.start_point = QPoint(int(event.pos().x() / self.scale_factor), int(event.pos().y() / self.scale_factor))
            self.end_point = QPoint(int(event.pos().x() / self.scale_factor), int(event.pos().y() / self.scale_factor))
            
            # 初始化当前绘制的形状
            self.current_shape = AnnotationData(
                tool=self.current_tool,
                points=[self.start_point],
                color=self.current_color,
                line_width=self.line_width
            )
            print(f"开始绘制: {self.current_tool.value} at ({self.start_point.x()}, {self.start_point.y()})")
            
    def mouseMoveEvent(self, event: "QMouseEvent"):
        """鼠标移动事件"""
        if self.drawing and self.current_tool != AnnotationTool.NONE:
            self.end_point = QPoint(int(event.pos().x() / self.scale_factor), int(event.pos().y() / self.scale_factor))
            
            # 更新当前形状的点
            if self.current_tool == AnnotationTool.FREEHAND:
                self.current_shape.points.append(self.end_point)
            
            # 触发重绘
            self.update()
            
    def mouseReleaseEvent(self, event: "QMouseEvent"):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_point = QPoint(int(event.pos().x() / self.scale_factor), int(event.pos().y() / self.scale_factor))
            
            # 更新最终点
            if self.current_tool in [AnnotationTool.ARROW, AnnotationTool.RECTANGLE]:
                self.current_shape.points.append(self.end_point)

            # 保存当前形状
            if self.current_shape:
                self.shapes.append(self.current_shape)
                print(f"完成绘制: {self.current_tool.value}, 共 {len(self.shapes)} 个标注")
            
            self.current_shape = None
            self.drawing_completed.emit()
            self.update()
            
    def paintEvent(self, event: "QPaintEvent"):
        """绘制事件"""
        painter = QPainter(self)
        # 按缩放比例绘制图像与向量标注（标注数据以原始坐标存储）
        painter.scale(self.scale_factor, self.scale_factor)
        painter.drawImage(QPoint(0, 0), self.original_image)
        for shape in self.shapes:
            self._draw_shape(painter, shape)
        if self.drawing and self.current_shape:
            preview_shape = AnnotationData(
                tool=self.current_shape.tool,
                points=self.current_shape.points + ([self.end_point] if self.current_shape.tool != AnnotationTool.FREEHAND else []),
                color=self.current_shape.color,
                line_width=self.current_shape.line_width
            )
            self._draw_shape(painter, preview_shape)
    
    def _draw_shape(self, painter: QPainter, shape_data: AnnotationData):
        """根据 AnnotationData 绘制单个形状"""
        
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(shape_data.color, shape_data.line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        
        if shape_data.tool == AnnotationTool.ARROW and len(shape_data.points) >= 2:
            self._draw_arrow_on_painter(painter, shape_data.points[0], shape_data.points[1])
        elif shape_data.tool == AnnotationTool.RECTANGLE and len(shape_data.points) >= 2:
            rect = QRect(shape_data.points[0], shape_data.points[1])
            painter.drawRect(rect)
        elif shape_data.tool == AnnotationTool.FREEHAND and len(shape_data.points) >= 2:
            painter.drawPolyline(shape_data.points)
            
    def _draw_arrow_on_painter(self, painter: QPainter, start_point: QPoint, end_point: QPoint):
        """在指定的 painter 上绘制箭头"""
        
        import math
        
        # 绘制主线
        painter.drawLine(start_point, end_point)
        
        # 计算角度
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        angle = math.atan2(dy, dx)
        
        # 箭头配置
        arrow_size = config_manager.get("annotation.arrow_size", 10)
        arrow_angle = math.pi / 6  # 30度
        
        # 计算箭头头部的两个点
        p1 = QPoint(
            int(end_point.x() - arrow_size * math.cos(angle - arrow_angle)),
            int(end_point.y() - arrow_size * math.sin(angle - arrow_angle))
        )
        p2 = QPoint(
            int(end_point.x() - arrow_size * math.cos(angle + arrow_angle)),
            int(end_point.y() - arrow_size * math.sin(angle + arrow_angle))
        )
        
        # 绘制箭头头部
        painter.drawLine(end_point, p1)
        painter.drawLine(end_point, p2)


class AnnotationDialog(QDialog):
    """标注对话框"""
    
    # 信号定义
    annotation_completed = Signal(QImage)  # 标注完成信号
    
    def __init__(self, image: QImage, parent: Optional[QWidget] = None):
        """
        初始化标注对话框
        
        Args:
            image: 要标注的图像
            parent: 父组件
        """
        super().__init__(parent)
        self.setWindowTitle("图像标注")
        self.setModal(True)
        
        # 创建 AnnotationManager 实例
        self.annotation_manager = AnnotationManager()
        
        # 创建 AnnotationWidget
        self.annotation_widget = AnnotationWidget(image, self)
        self._image_size = image.size()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar_layout = self._create_toolbar()
        main_layout.addLayout(toolbar_layout)
        
        # 滚动区域用于显示图像
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.annotation_widget)
        scroll_area.setWidgetResizable(True)
        self.scroll_area = scroll_area
        main_layout.addWidget(scroll_area)
        
        # 操作按钮
        button_layout = self._create_action_buttons()
        main_layout.addLayout(button_layout)
        
        # 设置窗口初始大小（将于显示时根据图像与屏幕尺寸自适应调整）
        self.resize(800, 600)

        # 初始拟合：将图像适配到默认窗口工作区
        self._fit_image_to_default_window()

    def showEvent(self, event):
        """显示事件：根据图像与屏幕可用空间调整对话框大小"""
        try:
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry()
                # 目标尺寸：不超过屏幕 90%，同时尽量容纳完整图像
                target_w = min(self._image_size.width() + 200, int(avail.width() * 0.9))
                target_h = min(self._image_size.height() + 200, int(avail.height() * 0.9))
                self.resize(target_w, target_h)
                # 依据新尺寸重新拟合缩放
                self._fit_image_to_current_window()
                # 确保滚动区域布局刷新
                if hasattr(self, 'scroll_area'):
                    self.scroll_area.updateGeometry()
                    self.scroll_area.ensureVisible(0, 0, 10, 10)
        except Exception:
            pass
        super().showEvent(event)

    def _fit_image_to_default_window(self):
        """在构造后先按默认窗口大小对图像进行缩放适配"""
        try:
            # 预估内容区域：窗口宽高扣除左右/上下面板与边距，给予约 200px 的工具与边距空间
            max_w = max(100, self.width() - 200)
            max_h = max(100, self.height() - 200)
            self.annotation_widget.fit_to_size(max_w, max_h)
        except Exception:
            pass

    def _fit_image_to_current_window(self):
        """在窗口 resize/show 之后按当前实际可用区域自适应缩放图像"""
        try:
            # 估算滚动区域的可用空间
            if hasattr(self, 'scroll_area') and self.scroll_area is not None:
                viewport = self.scroll_area.viewport()
                max_w = max(100, viewport.width() - 20)
                max_h = max(100, viewport.height() - 20)
            else:
                max_w = max(100, self.width() - 200)
                max_h = max(100, self.height() - 200)
            self.annotation_widget.fit_to_size(max_w, max_h)
        except Exception:
            pass
        
    def _create_toolbar(self) -> QGridLayout:
        """创建工具栏布局"""
        layout = QGridLayout()
        
        # 工具选择
        tool_group_box = QGroupBox("工具")
        tool_layout = QHBoxLayout()
        self.tool_button_group = QButtonGroup(self)
        self._id_to_tool = {}
        
        tools = {
            "arrow": ("绘制箭头", AnnotationTool.ARROW),
            "rectangle": ("绘制矩形", AnnotationTool.RECTANGLE),
            "freehand": ("自由绘制", AnnotationTool.FREEHAND),
        }
        
        for tool_id, (name, (tooltip, tool_enum)) in enumerate(tools.items(), start=1):
            button = QToolButton()
            # 这里可以设置图标
            # icon_path = f":/icons/{name}.png"
            # button.setIcon(QIcon(icon_path))
            button.setText(name.capitalize())
            button.setToolTip(tooltip)
            button.setCheckable(True)
            self.tool_button_group.addButton(button, tool_id)
            self._id_to_tool[tool_id] = tool_enum
            tool_layout.addWidget(button)
            
        self.tool_button_group.buttonClicked.connect(self._on_tool_selected)
        tool_group_box.setLayout(tool_layout)
        layout.addWidget(tool_group_box, 0, 0)
        
        # 颜色选择
        color_group_box = QGroupBox("颜色")
        color_layout = QHBoxLayout()
        self.color_combo = QComboBox()
        available_colors = self.annotation_manager.get_available_colors()
        for name, color in available_colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(color)
            self.color_combo.addItem(QIcon(pixmap), name, color)
        
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)
        color_layout.addWidget(self.color_combo)
        color_group_box.setLayout(color_layout)
        layout.addWidget(color_group_box, 0, 1)
        
        # 线宽选择
        width_group_box = QGroupBox("线宽")
        width_layout = QHBoxLayout()
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 10)
        self.width_slider.setValue(self.annotation_widget.line_width)
        self.width_slider.valueChanged.connect(self._on_line_width_changed)
        width_layout.addWidget(self.width_slider)
        width_group_box.setLayout(width_layout)
        layout.addWidget(width_group_box, 0, 2)
        
        layout.setColumnStretch(3, 1) # 占位
        
        return layout

    def _create_action_buttons(self) -> QHBoxLayout:
        """创建操作按钮布局"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # 撤销按钮
        self.undo_button = QPushButton("撤销")
        self.undo_button.clicked.connect(self._on_undo)
        layout.addWidget(self.undo_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        return layout
        
    def _on_tool_selected(self, button):
        """工具选择处理"""
        tool_id = self.tool_button_group.id(button)
        tool = self._id_to_tool.get(tool_id)
        if tool is not None:
            self.annotation_widget.set_tool(tool)

    def _on_color_changed(self, index: int):
        """颜色选择处理"""
        color = self.color_combo.itemData(index)
        if color:
            self.annotation_widget.set_color(color)
    
    def _on_line_width_changed(self, width: int):
        """线宽变化处理"""
        self.annotation_widget.set_line_width(width)
        
    def get_annotated_image(self) -> QImage:
        """获取最终标注的图像"""
        # 重新绘制最终图像
        final_image = self.annotation_widget.original_image.copy()
        painter = QPainter(final_image)
        for shape in self.annotation_widget.shapes:
            self.annotation_widget._draw_shape(painter, shape)
        painter.end()
        return final_image

    def _on_undo(self):
        """撤销上一步标注"""
        if self.annotation_widget.shapes:
            self.annotation_widget.shapes.pop()
            self.annotation_widget.update()

    def accept(self):
        """确认操作，发送信号并关闭对话框"""
        try:
            final_image = self.get_annotated_image()
            # 复制一份，确保离开对话框后图像仍然有效
            final_image_copy = final_image.copy()
            self.annotation_completed.emit(final_image_copy)
        except Exception as e:
            print(f"生成最终标注图像失败: {e}")
        finally:
            super().accept()

    def reject(self):
        """取消操作"""
        super().reject()