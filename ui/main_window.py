# -*- coding: utf-8 -*-
"""
主窗口模块
应用程序的主界面窗口
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QMenuBar, QStatusBar, QSplitter, QFrame, QPushButton,
                               QSlider, QLabel, QStyle, QFileDialog, QGroupBox,
                               QSpinBox, QComboBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtMultimedia import QMediaPlayer

from src.config import config_manager
from src.player import PlayerManager
from src.screenshot import ScreenshotManager
from src.utils import TimeFormatter
from pathlib import Path
import os


class MainWindow(QMainWindow):
    """
    主窗口类
    
    负责构建应用程序的主界面，并连接UI控件与后端的管理器。
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        self.setWindowTitle("视频播放器 - 支持截图和标注")
        self.setMinimumSize(QSize(1000, 700))
        
        # 从配置加载窗口几何信息
        geometry = config_manager.get("ui.window_geometry", [100, 100, 1200, 800])
        self.setGeometry(*geometry)

        # 初始化管理器
        self.player_manager = PlayerManager()
        self.screenshot_manager = ScreenshotManager(self.player_manager)
        
        # 初始化界面
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_connections()

        # 初始化UI状态
        self.update_volume_icon(self.player_manager.get_volume(), self.player_manager.is_muted())
        
        # 设置快捷键（空格: 播放/暂停，z: 倍速切换，x: 截图，c: 标注截图）
        self._install_shortcuts()
    
    def setup_ui(self):
        """设置用户界面布局"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # 确保主窗口可接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 创建分割器用于调整布局
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 视频播放区域（占主要空间）
        self.video_frame = QFrame()
        self.video_frame.setFrameStyle(QFrame.StyledPanel)
        self.video_frame.setMinimumHeight(400)
        self.video_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 2px solid #333333;
                border-radius: 5px;
            }
        """)
        self.video_layout = QVBoxLayout(self.video_frame)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_frame.setLayout(self.video_layout)
        
        # 将播放器的 video_widget 添加到布局
        self.video_layout.addWidget(self.player_manager.video_widget)

        splitter.addWidget(self.video_frame)
        
        # 控制面板区域
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 设置分割器比例（视频区域占大部分空间）
        splitter.setStretchFactor(0, 3)  # 视频区域
        splitter.setStretchFactor(1, 1)  # 控制面板
    
    def create_control_panel(self) -> QWidget:
        """创建包含所有控制控件的底部面板"""
        panel = QWidget()
        panel.setMaximumHeight(200)
        panel.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 播放控制栏
        playback_controls = self.create_playback_controls()
        layout.addWidget(playback_controls)
        
        # 功能控制区域
        function_layout = QHBoxLayout()
        
        # 截图控制栏
        screenshot_controls = self.create_screenshot_controls()
        function_layout.addWidget(screenshot_controls)
        
        # 标注工具栏
        annotation_toolbar = self.create_annotation_toolbar()
        function_layout.addWidget(annotation_toolbar)
        
        layout.addLayout(function_layout)
        
        return panel

    def create_screenshot_controls(self) -> QWidget:
        """创建截图控制栏UI"""
        group_box = QGroupBox("截图")
        layout = QHBoxLayout(group_box)
        
        self.screenshot_button = QPushButton("立即截图")
        self.screenshot_button.setToolTip("截取当前画面")
        layout.addWidget(self.screenshot_button)
        
        self.annotate_button = QPushButton("标注截图")
        self.annotate_button.setToolTip("对上一张截图进行标注")
        layout.addWidget(self.annotate_button)
        
        layout.addSpacing(20)

        self.batch_screenshot_button = QPushButton("开始批量截图")
        self.batch_screenshot_button.setCheckable(True)
        layout.addWidget(self.batch_screenshot_button)
        
        layout.addWidget(QLabel("间隔(秒):"))
        self.batch_interval_spinbox = QSpinBox()
        self.batch_interval_spinbox.setRange(1, 60)
        self.batch_interval_spinbox.setValue(self.screenshot_manager.batch_interval)
        layout.addWidget(self.batch_interval_spinbox)
        
        return group_box

    def create_annotation_toolbar(self) -> QWidget:
        """创建文本标注工具栏UI"""
        group_box = QGroupBox("文本标注设置")
        layout = QHBoxLayout(group_box)
        
        # 字体大小
        layout.addWidget(QLabel("字号:"))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(12, 48)
        self.font_size_spinbox.setValue(self.screenshot_manager.get_font_size())
        layout.addWidget(self.font_size_spinbox)
        
        # 字体颜色
        layout.addWidget(QLabel("颜色:"))
        self.font_color_combo = QComboBox()
        available_colors = self.screenshot_manager.annotation_manager.get_available_colors()
        for name, color in available_colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(color)
            self.font_color_combo.addItem(QIcon(pixmap), name, color)
        
        current_color = self.screenshot_manager.annotation_manager.font_color
        for i in range(self.font_color_combo.count()):
            if self.font_color_combo.itemData(i) == current_color:
                self.font_color_combo.setCurrentIndex(i)
                break
                
        layout.addWidget(self.font_color_combo)
        
        return group_box

    def create_playback_controls(self) -> QWidget:
        """创建播放控制栏UI"""
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)

        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        layout.addWidget(self.progress_slider)

        # 控制按钮和时间标签
        controls_layout = QHBoxLayout()
        
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        controls_layout.addWidget(self.play_pause_button)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        controls_layout.addWidget(self.stop_button)

        self.rewind_button = QPushButton()
        self.rewind_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        controls_layout.addWidget(self.rewind_button)

        self.forward_button = QPushButton()
        self.forward_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        controls_layout.addWidget(self.forward_button)

        controls_layout.addStretch()

        # 音量控制
        self.mute_button = QPushButton()
        self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.mute_button.setCheckable(True)
        controls_layout.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setValue(self.player_manager.get_volume())
        controls_layout.addWidget(self.volume_slider)

        controls_layout.addSpacing(10)

        self.time_label = QLabel("00:00:00 / 00:00:00")
        controls_layout.addWidget(self.time_label)
        
        layout.addLayout(controls_layout)
        
        return widget

    def _install_shortcuts(self):
        """安装全局快捷键：空格用 QAction，其余用 QShortcut（单一序列，避免歧义）"""
        try:
            from PySide6.QtGui import QAction, QKeySequence, QShortcut
            # 空格：播放/暂停（QAction 方式工作正常）
            self.action_play_pause = QAction(self)
            self.action_play_pause.setShortcut(QKeySequence(Qt.Key_Space))
            self.action_play_pause.setShortcutContext(Qt.ApplicationShortcut)
            self.action_play_pause.triggered.connect(self.player_manager.toggle_playback)
            self.addAction(self.action_play_pause)

            # z：在 1x 与 2x 间切换（使用 QShortcut，避免多个序列导致的歧义）
            self.shortcut_toggle_speed = QShortcut(QKeySequence(Qt.Key_Z), self)
            self.shortcut_toggle_speed.setContext(Qt.ApplicationShortcut)
            self.shortcut_toggle_speed.activated.connect(self.player_manager.toggle_speed)

            # x：立即截图
            self.shortcut_take_screenshot = QShortcut(QKeySequence(Qt.Key_X), self)
            self.shortcut_take_screenshot.setContext(Qt.ApplicationShortcut)
            self.shortcut_take_screenshot.activated.connect(self.screenshot_manager.take_screenshot)

            # c：标注截图
            self.shortcut_annotate_screenshot = QShortcut(QKeySequence(Qt.Key_C), self)
            self.shortcut_annotate_screenshot.setContext(Qt.ApplicationShortcut)
            self.shortcut_annotate_screenshot.activated.connect(self.screenshot_manager.annotate_current_frame)
        except Exception as e:
            print(f"安装快捷键失败: {e}")

    def keyPressEvent(self, event):
        """键盘事件兜底处理，保证快捷键在部分控件抢焦点时依然可用"""
        try:
            key = event.key()
            if key == Qt.Key_Space:
                self.player_manager.toggle_playback()
                event.accept()
                return
            if key in (Qt.Key_Z,):
                self.player_manager.toggle_speed()
                event.accept()
                return
            if key in (Qt.Key_X,):
                self.screenshot_manager.take_screenshot()
                event.accept()
                return
            if key in (Qt.Key_C,):
                self.screenshot_manager.annotate_current_frame()
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)
    
    def setup_menu_bar(self):
        """设置顶部菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 打开视频文件
        open_action = QAction("打开视频文件(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("打开本地视频文件")
        open_action.triggered.connect(self.open_video_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # 退出应用
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        # 截图设置
        screenshot_settings_action = QAction("截图设置(&S)", self)
        screenshot_settings_action.setStatusTip("配置截图相关设置")
        tools_menu.addAction(screenshot_settings_action)
        
        # 标注设置
        annotation_settings_action = QAction("标注设置(&A)", self)
        annotation_settings_action.setStatusTip("配置标注工具设置")
        tools_menu.addAction(annotation_settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        # 关于
        about_action = QAction("关于(&A)", self)
        about_action.setStatusTip("关于本应用程序")
        help_menu.addAction(about_action)
        
        # 新增“打开文件夹”和“选集/下一集”菜单
        open_dir_action = QAction("打开文件夹(&D)", self)
        open_dir_action.setStatusTip("选择一个包含视频的文件夹")
        open_dir_action.triggered.connect(self.open_video_directory)
        file_menu.addAction(open_dir_action)
        
        next_action = QAction("下一集(&N)", self)
        next_action.setShortcut("Ctrl+N")
        next_action.setStatusTip("播放下一个视频")
        next_action.triggered.connect(self.play_next_in_playlist)
        file_menu.addAction(next_action)
        
        choose_action = QAction("选集(&S)", self)
        choose_action.setStatusTip("从播放列表选择视频")
        choose_action.triggered.connect(self.choose_from_playlist)
        file_menu.addAction(choose_action)
    
    def setup_status_bar(self):
        """设置底部状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 显示就绪状态
        self.status_bar.showMessage("就绪", 2000)

    def open_video_file(self):
        """
        处理“打开文件”操作，显示文件对话框并加载选定的视频。
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            config_manager.get("path.last_video_dir", str(Path.home())),
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv *.wmv)"
        )
        if file_path:
            self.player_manager.load_video(file_path)
            # 清空播放列表上下文（单视频模式）
            self.player_manager.playlist = []
            self.player_manager.playlist_index = -1
            self.player_manager.playlist_dir = None

    def open_video_directory(self):
        """选择一个包含视频的文件夹并载入为播放列表"""
        directory = QFileDialog.getExistingDirectory(self, "选择视频文件夹", config_manager.get("path.last_video_dir", str(Path.home())))
        if directory:
            # 扫描视频文件
            exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.mts'}
            files = sorted([str(Path(directory) / f) for f in os.listdir(directory) if Path(f).suffix.lower() in exts])
            if not files:
                self.status_bar.showMessage("所选文件夹中没有视频文件", 3000)
                return
            self.player_manager.playlist = files
            self.player_manager.playlist_index = 0
            self.player_manager.playlist_dir = directory
            config_manager.set("path.last_video_dir", directory)
            self.player_manager.load_video(self.player_manager.playlist[0])
            self.status_bar.showMessage(f"已加载播放列表，共 {len(files)} 个视频", 3000)

    def play_next_in_playlist(self):
        """播放播放列表中的下一集"""
        if getattr(self.player_manager, 'playlist', None):
            if self.player_manager.playlist_index + 1 < len(self.player_manager.playlist):
                self.player_manager.playlist_index += 1
                next_path = self.player_manager.playlist[self.player_manager.playlist_index]
                self.player_manager.load_video(next_path)
                self.status_bar.showMessage(f"下一集: {Path(next_path).name}", 2000)
            else:
                self.status_bar.showMessage("已经是最后一集", 2000)
        else:
            self.status_bar.showMessage("未加载播放列表", 2000)

    def choose_from_playlist(self):
        """从播放列表中选择视频播放（简单文件对话框选择）"""
        if not getattr(self.player_manager, 'playlist', None):
            self.status_bar.showMessage("未加载播放列表", 2000)
            return
        # 使用文件选择对话框，默认到播放列表目录
        directory = getattr(self.player_manager, 'playlist_dir', config_manager.get("path.last_video_dir", str(Path.home())))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "从播放列表选择视频",
            directory,
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.flv *.wmv *.webm *.m4v *.3gp *.ogv *.ts *.mts)"
        )
        if file_path:
            try:
                idx = self.player_manager.playlist.index(file_path)
                self.player_manager.playlist_index = idx
            except ValueError:
                # 不在当前列表，则直接播放并重置列表上下文
                self.player_manager.playlist = []
                self.player_manager.playlist_index = -1
                self.player_manager.playlist_dir = None
            self.player_manager.load_video(file_path)

    def setup_connections(self):
        """
        设置所有UI控件的信号槽连接。
        将UI事件连接到管理器中的相应方法。
        """
        # 播放器控制
        self.play_pause_button.clicked.connect(self.player_manager.toggle_playback)
        self.stop_button.clicked.connect(self.player_manager.stop)
        self.rewind_button.clicked.connect(self.player_manager.rewind)
        self.forward_button.clicked.connect(self.player_manager.forward)
        
        # 进度条
        self.progress_slider.sliderMoved.connect(self.player_manager.set_position)

        # 播放器信号
        self.player_manager.error_occurred.connect(self.show_error_message)
        # 状态消息提示（包括倍速切换等）
        self.player_manager.status_message.connect(lambda m: self.status_bar.showMessage(m, 2000))

        # 播放器核心信号
        self.player_manager.player.positionChanged.connect(self.update_progress_slider)
        self.player_manager.player.durationChanged.connect(self.update_duration)
        self.player_manager.player.playbackStateChanged.connect(self.update_play_pause_button)
        
        # 音频输出信号
        self.player_manager.audio_output.volumeChanged.connect(
            lambda v: self.volume_slider.setValue(int(v * 100))
        )
        self.player_manager.audio_output.mutedChanged.connect(
            lambda m: self.update_volume_icon(self.player_manager.get_volume(), m)
        )

        # 音量控制
        self.volume_slider.valueChanged.connect(self.player_manager.set_volume)
        self.mute_button.toggled.connect(self.on_mute_toggled)

        # 截图控制
        self.screenshot_button.clicked.connect(self.screenshot_manager.take_screenshot)
        self.annotate_button.clicked.connect(self.screenshot_manager.annotate_current_frame)
        self.batch_screenshot_button.toggled.connect(self.toggle_batch_screenshot)
        self.batch_interval_spinbox.valueChanged.connect(self.screenshot_manager.set_batch_interval)
        
        # 标注工具栏
        self.font_size_spinbox.valueChanged.connect(self.screenshot_manager.set_font_size)
        self.font_color_combo.currentIndexChanged.connect(self.on_font_color_changed)

        # 截图管理器信号
        self.screenshot_manager.status_message.connect(lambda m: self.status_bar.showMessage(m, 2000))

    def toggle_batch_screenshot(self, checked: bool):
        """
        处理批量截图按钮的点击事件。
        
        Args:
            checked: 按钮是否被选中
        """
        if checked:
            interval = self.batch_interval_spinbox.value()
            if self.screenshot_manager.start_batch_screenshot(interval):
                self.batch_screenshot_button.setText("停止批量截图")
            else:
                self.batch_screenshot_button.setChecked(False) # 启动失败
        else:
            self.screenshot_manager.stop_batch_screenshot()
            self.batch_screenshot_button.setText("开始批量截图")

    def on_font_color_changed(self, index: int):
        """
        处理字体颜色组合框的选择变化事件。
        
        Args:
            index: 新选中的索引
        """
        color = self.font_color_combo.itemData(index)
        if color:
            self.screenshot_manager.annotation_manager.set_font_color(color)

    def update_progress_slider(self, position: int):
        """
        根据播放器位置更新进度条滑块和时间标签。
        由 player_manager 的 position_changed 信号触发。
        """
        self.progress_slider.setValue(position)
        duration = self.player_manager.get_duration()
        self.time_label.setText(
            f"{TimeFormatter.ms_to_time_string(position)} / {TimeFormatter.ms_to_time_string(duration)}"
        )

    def update_duration(self, duration: int):
        """
        当视频加载完成时，更新进度条的最大值。
        由 player_manager 的 duration_changed 信号触发。
        """
        self.progress_slider.setRange(0, duration)
        self.update_progress_slider(0)

    def update_play_pause_button(self, state: QMediaPlayer.PlaybackState):
        """
        根据播放状态更新播放/暂停按钮的图标。
        由 player_manager 的 playback_state_changed 信号触发。
        """
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
    
    def on_volume_changed(self, volume: int):
        """处理音量滑块变化"""
        self.player_manager.set_volume(volume)
        self.update_volume_icon(volume, self.player_manager.is_muted())
    
    def on_mute_toggled(self, muted: bool):
        """处理静音按钮切换"""
        self.player_manager.set_muted(muted)
        self.update_volume_icon(self.player_manager.get_volume(), muted)
    
    def update_volume_icon(self, volume: int, muted: bool):
        """
        根据音量大小和静音状态更新音量图标。
        由 player_manager 的 volume_changed 和 muted_changed 信号触发。
        """
        if muted or volume == 0:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        else:
            self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        
        # 同步静音按钮状态
        self.mute_button.setChecked(muted)
        # 更新滑块显示
        self.volume_slider.setValue(volume)

    def show_error_message(self, message: str):
        """
        在状态栏显示错误消息。
        由各个管理器的错误信号触发。
        """
        self.status_bar.showMessage(f"错误: {message}", 5000)

    def closeEvent(self, event):
        """
        窗口关闭事件处理
        
        Args:
            event: 关闭事件
        """
        # 保存窗口几何信息到配置
        geometry = self.geometry()
        config_manager.set("ui.window_geometry", [
            geometry.x(), geometry.y(), 
            geometry.width(), geometry.height()
        ])
        
        # 保存配置
        config_manager.save_config()
        
        # 清理管理器
        self.player_manager.cleanup()
        self.screenshot_manager.cleanup()

        # 接受关闭事件
        event.accept()
        
        print("应用程序已关闭，配置已保存")