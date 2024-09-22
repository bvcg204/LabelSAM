from .mygraphicsView import MyGraphicsView
from qfluentwidgets import CardWidget,CommandBar,Action,FluentIcon,ComboBox,TransparentDropDownPushButton,setFont,RoundMenu,InfoBar,InfoBarPosition,ProgressBar,PushButton
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtWidgets import QVBoxLayout,QHBoxLayout,QFileDialog,QListWidgetItem,QDialog
from PyQt5.QtGui import QIcon,QPixmap,QImageReader
from PyQt5.QtCore import Qt,QThread, pyqtSignal
from common.config import cfg
from .loadingDialog import LoadingDialog
import os


class ImageLoaderThread(QThread):
    max_len=pyqtSignal(int) #计算文件最大长度
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)  # 完成时发送总共加载的文件数
    canceled = pyqtSignal()
    paused = pyqtSignal() #暂停

    def __init__(self, folder_path, image_extensions):
        super().__init__()
        self.folder_path = folder_path
        self.image_extensions = image_extensions
        self._is_canceled = False
        self.image_files = []

    def run(self):
        # 预先遍历计算总文件数
        for root, dirs, files in os.walk(self.folder_path):
            for filename in files:
                if filename.lower().endswith(tuple(self.image_extensions)) :
                    file_path = os.path.join(root, filename)
                    self.image_files.append(file_path)
        # 更新进度条的最大值
        self.max_len.emit(len(self.image_files))

        # 继续文件加载
        for i,file_path in enumerate(self.image_files):
            if self._is_canceled:
                    self.canceled.emit()
                    return
            else:
                self.progress.emit(i+1, file_path)
        
        self.finished.emit(self.image_files)
    def cancel(self):
        """设置取消标志为 True"""
        self._is_canceled = True


# 自定义的进度对话框
class ProgressDialog(QDialog):
    cancel_clicked = pyqtSignal()  # 定义一个取消按钮点击信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("加载图片")
        self.setFixedSize(400, 150)

        # 创建布局
        layout = QVBoxLayout(self)

        # 创建进度条
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.resume()
        layout.addWidget(self.progress_bar)

        # 创建标签用于显示加载状态
        # self.label = QLabel("读取中...", self)
        # layout.addWidget(self.label)

        # 创建取消按钮
        self.cancel_button = PushButton(FIF.CANCEL, "取消", self)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)  # 绑定取消按钮的点击事件
        layout.addWidget(self.cancel_button,0, Qt.AlignHCenter)
        layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(layout)

    def on_cancel_clicked(self):
        """点击取消按钮的处理"""
        self.cancel_clicked.emit()  # 发送取消信号
        self.close()  # 点击取消时直接关闭对话框

    def update_progress(self, current_count, file_name):
        self.progress_bar.setValue(current_count)
        # self.label.setText(f"加载: {os.path.basename(file_name)}")
        

    def set_max_progress(self, max_value):
        # self.progress_bar.setMaximum(max_value)
        self.progress_bar.setRange(0,max_value)

class GraphicsCard(CardWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setBorderRadius(8)
        self.vBoxLayout=QVBoxLayout()
        self.hBoxLayout = QHBoxLayout()

        # 核心组件，绘制面板
        self.graphicsView=MyGraphicsView(self)
        self.graphicsView.setStyleSheet("background: transparent;border:0px")
        # self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 菜单
        self.commandBar = CommandBar(self)
        self.hBoxLayout.addStretch(3)
        self.hBoxLayout.addWidget(self.commandBar,10)
        self.hBoxLayout.addStretch(2)
        self.commandBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # 模型选择下拉框
        self.modelSelectButton=ComboBox()
        self.modelSelectButton.setPlaceholderText('选择模型')
        modellist=['sam2_tiny','sam2_small','sam2_base_plus','sam2_large']
        self.modelSelectButton.addItems(modellist)
        self.modelSelectButton.currentTextChanged.connect(self.model_select)
        self.commandBar.addWidget(self.modelSelectButton)
        # 点绘制按钮
        self.addPointButton=self.createAddPointButton()
        self.commandBar.addWidget(self.addPointButton)

        self.commandBar.addAction(Action(FluentIcon.SYNC,'重置',triggered=self.reset_points,shortcut='Ctrl+R'))
        self.commandBar.addSeparator()
        
        self.commandBar.addAction(Action(FluentIcon.PHOTO,'图片',triggered=self.open_image,shortcut='Ctrl+P'))
        self.commandBar.addAction(Action(FluentIcon.FOLDER,'文件夹',triggered=self.open_folder,shortcut='Ctrl+D'))
        self.commandBar.addAction(Action(FluentIcon.LEFT_ARROW,'上一张',triggered=self.preImage,shortcut='A'))
        self.commandBar.addAction(Action(FluentIcon.RIGHT_ARROW,'下一张',triggered=self.nextImage,shortcut='D'))
        self.commandBar.addAction(Action(FluentIcon.SAVE_AS,'导出',triggered=self.save,shortcut='Ctrl+S'))

        self.commandBar.addHiddenAction(Action(FluentIcon.SCROLL, 'Sort', triggered=self.pp))
        self.commandBar.addHiddenAction(Action(FluentIcon.SETTING, 'Settings', ))

        self.vBoxLayout.addLayout(self.hBoxLayout)
        self.vBoxLayout.addWidget(self.graphicsView)
        self.setLayout(self.vBoxLayout)

        self.select_model()#选中上次用的模型

        self.image_files = []  # 存储所有图片文件路径
        self.current_index = -1  # 当前图片的索引
        self.progress_dialog = ProgressDialog(self)



    def select_model(self):
        cur_model=cfg.get(cfg.cur_model)
        self.modelSelectButton.setCurrentText(cur_model)

    def createAddPointButton(self):
        button = TransparentDropDownPushButton('添加', self, FluentIcon.ADD)
        button.setFixedHeight(34)
        setFont(button, 12)
        menu = RoundMenu(parent=self)
        menu.addActions([
            Action(FluentIcon.ADD_TO, '前景点',triggered=self.select_foreground_point,shortcut='Shift+A'),
            Action(FluentIcon.REMOVE_FROM, '背景点',triggered=self.select_background_point,shortcut='Shift+Z'),
            Action(FluentIcon.IOT, '多边形',triggered=self.set_draw,shortcut='Tab'),
            
        ])
        button.setMenu(menu)
        return button
    
    def pp(self):
        print('Z')

    def preImage(self):
        if self.current_index > 0:
            self.current_index -= 1
            image_path=self.image_files[self.current_index]
            self.load_new_image(image_path)
            image_name=os.path.basename(image_path)
            self.graphicsView.show_annotation(image_name)
            self.parent().fileListCard.file_list_widget.setCurrentRow(self.current_index)

    def nextImage(self):
        if self.current_index < len(self.image_files) - 1:
            if cfg.get(cfg.auto_save):
                filename=(os.path.basename(self.image_files[self.current_index]))
                self.graphicsView.auto_save(filename)
            else:
                self.graphicsView.save_to()
            self.current_index += 1
            image_path=self.image_files[self.current_index]
            self.load_new_image(self.image_files[self.current_index])
            image_name=os.path.basename(image_path)
            self.graphicsView.show_annotation(image_name)
            self.parent().fileListCard.file_list_widget.setCurrentRow(self.current_index)

    

    # 读取文件夹中的图片文件并在 QListWidget 中显示(旧版本，没有进度条显示)
    # def load_images_from_folder(self, folder_path):
    #     # 支持的图片扩展名
    #     image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
    #     # 清空之前的图片列表
    #     self.parent().fileListCard.file_list_widget.clear()
    #     self.image_files.clear()
    #     self.current_index=-1
    #     # 遍历文件夹下的所有文件
    #     for root, dirs, files in os.walk(folder_path):
    #         for filename in files:
    #             if filename.lower().endswith(tuple(image_extensions)):
    #                 # 构建图片的完整路径
    #                 file_path = os.path.join(root, filename)
    #                 # 创建 QListWidgetItem
    #                 # item = QListWidgetItem(QIcon(file_path),filename)
    #                 item = QListWidgetItem(filename)
    #                 # item.setData(1, file_path)  # 额外存储图片路径
    #                 self.image_files.append(file_path)
    #                 # 将项添加到 QListWidget
    #                 self.parent().fileListCard.file_list_widget.addItem(item)

    #     if len(self.image_files)>0:
    #         self.parent().fileListCard.show()

    def load_images_from_folder(self, folder_path):
        image_extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        self.progress_dialog.show()
        self.thread = ImageLoaderThread(folder_path, image_extensions)
        self.thread.max_len.connect(self.progress_dialog.set_max_progress)
        # self.thread.progress.connect(self.update_ui) #更新图片列表ui
        self.thread.progress.connect(self.progress_dialog.update_progress) #更新对话框里面的ui

        self.thread.finished.connect(self.finishLoad)

        self.thread.canceled.connect(self.on_cancel)
        self.progress_dialog.cancel_clicked.connect(self.thread.cancel)

        # 开始线程
        self.thread.start()

    def finishLoad(self,image_files):
        self.progress_dialog.close()
        if len(image_files)>0:
            self.parent().fileListCard.file_list_widget.clear()
            self.image_files.clear()
            self.current_index=-1
            self.image_files=image_files
            for file_path in image_files:
                item = QListWidgetItem(os.path.basename(file_path))
                self.parent().fileListCard.file_list_widget.addItem(item)
            self.parent().fileListCard.show()
        

    def update_ui(self, index, file_path):
        """更新 QListWidget，加载的图像不会清除"""
        # item = QListWidgetItem(QIcon(file_path),os.path.basename(file_path))
        item = QListWidgetItem(os.path.basename(file_path))
        self.parent().fileListCard.file_list_widget.addItem(item)


    def on_cancel(self):
        """当加载被取消时，显示取消状态"""
        print("Loading was canceled!")

    # 载入一张新的图片
    def load_new_image(self,image_path):
        if image_path:
            # 创建并显示加载弹窗
            self.setEnabled(False)
            self.loading_dialog = LoadingDialog(self)
            self.loading_dialog.start_loading_animation()
            self.graphicsView.load_image(image_path)
            self.loading_dialog.accept()
            self.setEnabled(True)
            InfoBar.success(
                title='图片载入成功',
                content="可以开始进行分割了",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_LEFT,
                duration=1000,
                parent=self
            )



    # 模型选择
    def model_select(self,model):
        self.graphicsView.get_preditor(model)
        

    # 点击手动绘制点
    def set_draw(self):
        self.graphicsView.mode='draw'

    # 点击前景点
    def select_foreground_point(self):
        self.graphicsView.mode='sam'
        self.graphicsView.set_point_type("foreground")

    # 点击背景点
    def select_background_point(self):
        self.graphicsView.mode='sam'
        self.graphicsView.set_point_type("background")

    # 重置点
    def reset_points(self):
        self.graphicsView.reset_points()
        self.select_foreground_point()#重置后默认选择前景点
        

    # 手动保存所有分割对象
    def save(self):
        self.graphicsView.save_to()

    
            
    # 弹出选择文件夹对话框
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            # 读取文件夹下所有的图片文件
            self.load_images_from_folder(folder_path)

    # 打开一张图片
    def open_image(self):
        image_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Image Files (*.png *.jpg *.bmp)")
        self.load_new_image(image_path)
