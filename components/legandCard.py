import random
from qfluentwidgets import HeaderCardWidget, ListWidget,LineEdit,RoundMenu,Action,BodyLabel,ColorPickerButton
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout,QListWidgetItem
from PyQt5.QtCore import Qt,pyqtSignal
from PyQt5.QtGui import QColor
# from common.settings_manager import SettingsManager
from common.config import cfg

class EditableLabel(QWidget):
    # 信号，用于发射修改后的类别名称
    categoryNameChanged = pyqtSignal(str,str)
    def __init__(self, text, parent=None):
        super().__init__(parent)
        # 创建 QLabel 和 QLineEdit
        self.label = BodyLabel(text, self)
        self.line_edit = LineEdit(self)
        self.line_edit.setText(text)
        self.line_edit.hide()  # 初始隐藏 QLineEdit
        
        # 布局
        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # 连接信号槽
        self.line_edit.editingFinished.connect(self.finish_editing)

    def mouseDoubleClickEvent(self, event):
        """双击 QLabel 时，切换为 QLineEdit"""
        if event.button() == Qt.LeftButton:
            self.label.hide()
            self.line_edit.show()
            self.line_edit.setFocus()

    def finish_editing(self):
        """完成编辑后，保存新文本并切换回 QLabel"""
        # editingFinished执行两次的bug解决方案
        if not self.line_edit.hasFocus():
            return
        old_text=self.label.text()
        new_text = self.line_edit.text()
        color_map = cfg.get(cfg.color_map)
        # 不允许类别重名
        if new_text in color_map:
            self.label.setText(old_text)
            self.line_edit.setText(old_text)
        else:
            self.categoryNameChanged.emit(old_text,new_text)
            self.label.setText(new_text)
        self.line_edit.hide()
        self.label.show()

class ColorItemWidget(QWidget):

    colorChanged = pyqtSignal(str, QColor)  # 信号，发射类别名称和新颜色
    categoryNameChanged = pyqtSignal(str,str)
    def __init__(self, category_name, color, parent=None):
        super().__init__(parent)

        # 类别名称
        self.category_label = EditableLabel(category_name)
        # self.category_label.setFixedWidth(80)
        # 颜色色块按钮
        self.color_button = ColorPickerButton(QColor(color), 'Background Color', enableAlpha=False)
        self.color_button.setFixedSize(32,32)
        # 水平布局：左边是类别名称，右边是颜色色块
        layout = QHBoxLayout()
        layout.addWidget(self.category_label)
        layout.addStretch()
        layout.addWidget(self.color_button)
        layout.setContentsMargins(4, 0, 4, 0)

        self.setLayout(layout)

        # 监听类别名称修改
        self.category_label.categoryNameChanged.connect(self.category_name_changed)
        self.color_button.colorChanged.connect(self.change_color)

    def category_name_changed(self,old_name, new_name):
        """处理类别名称修改"""
        # 获取旧的类别名称并发射信号
        self.categoryNameChanged.emit(old_name,new_name)

    def change_color(self,color):
        # 发射颜色变化信号
        category_name = self.category_label.label.text()
        self.colorChanged.emit(category_name, color)

class LegandCard(HeaderCardWidget):
    categorySelected = pyqtSignal(str, QColor)
    categoryRenamed = pyqtSignal(str, str)  # 信号，发射旧类别名和新类别名
    colorChanged = pyqtSignal(str, QColor)  # 信号，发射类别名和新颜色
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTitle("图例")
        self.setBorderRadius(8)
        self.vBoxLayout=QVBoxLayout()
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.list_widget=ListWidget()
        self.legandInput=LineEdit(self)
        self.legandInput.setPlaceholderText('新增类别')
        self.vBoxLayout.addWidget(self.legandInput)
        self.vBoxLayout.addWidget(self.list_widget)

        # 初始化数据
        self.load_categories_from_settings()
        # 连接信号到自定义的槽函数 item_selected
        self.list_widget.currentItemChanged.connect(self.item_selected)
        # 恢复上次的选择
        # cur_category = self.settings_manager.get_setting('category.cur_category')
        cur_category=cfg.get(cfg.cur_category)
        self.select_category(cur_category)
        # 允许右键点击操作
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.viewLayout.addLayout(self.vBoxLayout)

        self.setMinimumWidth(200)

    

    def show_context_menu(self, position):
        """显示右键菜单"""
        # 获取当前选中的项
        current_item = self.list_widget.itemAt(position)
        if current_item:
            context_menu = RoundMenu(parent=self)
            delete_action = Action(FIF.DELETE, '删除')
            context_menu.addAction(delete_action)
            rename_action = Action(FIF.EDIT,'重命名')
            context_menu.addAction(rename_action)
            # 绑定删除操作
            delete_action.triggered.connect(lambda: self.delete_category(current_item))
            rename_action.triggered.connect(lambda: self.rename_(current_item))
            # 显示菜单
            context_menu.exec_(self.list_widget.viewport().mapToGlobal(position))

    def rename_(self,item):
        widget = self.list_widget.itemWidget(item)
        widget.category_label.label.hide()
        widget.category_label.line_edit.show()

    
    # 删除类别
    def delete_category(self, item):
        widget = self.list_widget.itemWidget(item)
        category_name = widget.category_label.label.text()
        # 从 QListWidget 中删除项目
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        color_map = cfg.get(cfg.color_map)
        if category_name in color_map:
            del color_map[category_name]
            cfg.set(cfg.color_map,color_map)
            cfg.save()
            # 下面这两行代码我也不知道为啥要这样，反正逻辑正确
            cur_category=cfg.get(cfg.cur_category)
            self.select_category(cur_category)

    def load_categories_from_settings(self):
        """从 config 中读取类别和颜色"""
        color_map = cfg.get(cfg.color_map)
        if not color_map:  # 如果 color_map 为空，使用默认类别
            # 初始化默认类别和颜色
            self.add_item("Class 1", QColor(255, 0, 0))  # 红色
            self.add_item("Class 2", QColor(0, 255, 0))  # 绿色
            self.add_item("Class 3", QColor(0, 0, 255))  # 蓝色
        else:
            # 遍历 color_map 并根据存储的颜色初始化类别
            for category, color_value in color_map.items():
                color = QColor(color_value)
                self.add_item(category, color)

    def select_category(self, category_name):
        """根据类别名称选择当前项"""
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            widget = self.list_widget.itemWidget(item)
            if widget.category_label.label.text() == category_name:
                self.list_widget.setCurrentRow(index)
                break


    def add_item(self, category_name, color):
        """向列表中添加一个带颜色的类别项"""
        # 创建自定义的 item widget
        item_widget = ColorItemWidget(category_name, color)
        # 监听类别名称修改
        item_widget.category_label.categoryNameChanged.connect(self.rename_category)
        # 监听颜色修改
        item_widget.colorChanged.connect(self.update_color)
        # 创建 QListWidgetItem 并将其绑定到自定义 widget
        list_item = QListWidgetItem(self.list_widget)
        list_item.setSizeHint(item_widget.sizeHint())
        # 将自定义 widget 设置为 QListWidget 的 item
        self.list_widget.setItemWidget(list_item, item_widget)



    def generate_random_color(self):
        """生成一个随机颜色"""
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        return QColor(r, g, b)
    
    def rename_category(self, old_name, new_name):
        """处理类别名称修改并发射信号"""
        self.categoryRenamed.emit(old_name, new_name)

    def update_color(self, category_name, new_color):
        """处理颜色变化并发射信号"""
        self.colorChanged.emit(category_name, new_color)
        
    
    def item_selected(self, current, previous):
        """当列表中的项被选中时，发射信号"""
        # 获取当前选中的 widget（自定义的 ColorItemWidget）
        if current is not None:
            widget = self.list_widget.itemWidget(current)
            category_name = widget.category_label.label.text()
            color = widget.color_button.palette().color(widget.color_button.backgroundRole())
            # 发射自定义信号，将选中的类别和颜色发送出去
            self.categorySelected.emit(category_name, color)