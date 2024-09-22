from qfluentwidgets import HeaderCardWidget,ListWidget
from PyQt5.QtWidgets import QVBoxLayout,QListWidget
from PyQt5.QtCore import QSize
class FileListCard(HeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("文件列表")
        self.setBorderRadius(8)
        self.vBoxLayout=QVBoxLayout()
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.file_list_widget=ListWidget(self)
        self.file_list_widget.setIconSize(QSize(20, 20))
        self.vBoxLayout.addWidget(self.file_list_widget)
        self.viewLayout.addLayout(self.vBoxLayout)
        self.setMinimumWidth(200)

        
        # self.file_list_widget.setViewMode(QListWidget.IconMode)