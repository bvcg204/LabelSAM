import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QMovie

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint)
        self.setModal(True)

        # 设置布局
        layout = QVBoxLayout()

        # 创建加载动画标签
        self.loading_label = QLabel(self)
        self.loading_label.setAlignment(Qt.AlignCenter)

        # 创建文字标签
        self.text_label = QLabel("加载中", self)
        self.text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.loading_label)
        layout.addWidget(self.text_label)
        self.setLayout(layout)

        # 启动加载动画
        self.start_loading_animation()

        # 调整弹窗大小和位置
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def start_loading_animation(self):
        # 设置加载动画
        self.movie = QMovie(r"D:\code\pyqt_progrem\assets\loading.gif")  # 使用一个gif动画
        self.loading_label.setMovie(self.movie)
        self.movie.start()

    def stop_loading_animation(self):
        # 停止加载动画
        self.movie.stop()
        self.loading_label.clear()

    def show_loading_completed(self):
        # 停止动画并显示“加载完成”的文本
        self.stop_loading_animation()
        self.text_label.setText("加载完成")