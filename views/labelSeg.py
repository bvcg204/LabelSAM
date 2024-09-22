from PyQt5.QtWidgets import  QHBoxLayout, QWidget,QHBoxLayout, QVBoxLayout,QFileDialog,QListWidgetItem
from components import FileListCard,LegandCard,GraphicsCard
from common.config import cfg
import os
class LabelSeg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("labelSeg")
        self.hBox=QHBoxLayout()
        self.graphicsCard=GraphicsCard()
        self.fileListCard=FileListCard()
        self.legandCard=LegandCard()


        self.hBox.addWidget(self.fileListCard)
        self.hBox.addWidget(self.graphicsCard)
        self.hBox.addWidget(self.legandCard)
        self.hBox.setStretch(0,1)
        self.hBox.setStretch(1,5)
        self.hBox.setStretch(2,1)
        self.setLayout(self.hBox)

        self.fileListCard.hide()

        self.fileListCard.file_list_widget.itemClicked.connect(self.on_item_clicked)

        self.legandCard.legandInput.returnPressed.connect(self.add_category)
        self.legandCard.categorySelected.connect(self.update_selected_category)
        # 连接类别名称修改信号
        self.legandCard.categoryRenamed.connect(self.update_category_name)
        # 连接颜色修改信号
        self.legandCard.colorChanged.connect(self.update_category_color)

    # 用户点击列表项时，重新加载新的图片
    def on_item_clicked(self, item):
        cur_index=self.fileListCard.file_list_widget.currentRow()
        image_path=self.graphicsCard.image_files[cur_index]
        self.graphicsCard.load_new_image(image_path)
        image_name=os.path.basename(image_path)
        self.graphicsCard.graphicsView.show_annotation(image_name)
        self.graphicsCard.current_index=cur_index#更新当前索引

    # 添加一个新的类别
    def add_category(self):
        category_name = self.legandCard.legandInput.text()
        color_map = cfg.get(cfg.color_map)
        if category_name and category_name not in color_map:  # 确保输入不为空并且不重复
            random_color = self.legandCard.generate_random_color()  # 生成随机颜色
            self.legandCard.add_item(category_name, random_color)  # 添加到 SegmentationLegend
            # 更新字典，保存类别和颜色的映射关系
            
            color_map[category_name]=random_color.name()
            cfg.set(cfg.color_map,color_map)
            cfg.set(cfg.cur_category,category_name)
            # 清空输入框
            self.legandCard.legandInput.clear()
            self.legandCard.select_category(category_name)
    
    # 更新类别名称
    def update_category_name(self, old_name, new_name):
        color_map = cfg.get(cfg.color_map)
        if old_name in color_map:
            color_map[new_name] = color_map.pop(old_name)
            cfg.set(cfg.color_map,color_map)
            cfg.set(cfg.cur_category,new_name)
            cfg.save()
            self.graphicsCard.graphicsView.update_mask_category(old_name, new_name)
            print(f"Updated category name from {old_name} to {new_name}")
        else:
            print(f"Category {old_name} not found.")

    # 更新类别颜色
    def update_category_color(self, category_name, new_color):
        color_map = cfg.get(cfg.color_map)
        if category_name in color_map:
            color_map[category_name]=new_color.name()
            cfg.set(cfg.color_map,color_map)
            cfg.save()
            self.legandCard.select_category(category_name)
            self.graphicsCard.graphicsView.update_mask_color(category_name,new_color.name())

    # 更新当前选中的类别
    def update_selected_category(self, category_name, color):
        cfg.set(cfg.cur_category,category_name)
        

    # 向父组件传递像素坐标
    def update_status(self, x, y):
        # 如果坐标为有效值，更新状态标签
        if x >= 0 and y >= 0:
            self.statusLabel.setText(f"像素坐标: ({x}, {y})")
        else:
            self.statusLabel.setText("")