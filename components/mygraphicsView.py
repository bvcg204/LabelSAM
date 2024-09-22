from PyQt5.QtWidgets import  QFrame, QFileDialog, QGraphicsPolygonItem, QGraphicsScene, QGraphicsPixmapItem,  QGraphicsView,QGraphicsEllipseItem
from PyQt5.QtGui import QPixmap, QImage, QPen, QColor,QMouseEvent,QPolygonF,QBrush
from PyQt5.QtCore import pyqtSignal,QRectF,Qt
from qfluentwidgets import RoundMenu,Action,SmoothScrollArea,InfoBar,InfoBarPosition
from qfluentwidgets import FluentIcon as FIF
import math
import numpy as np
import pycocotools.mask as mask
import json
import cv2
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
import torch
import os
from typing import List, Dict, Any
# from common.settings_manager import SettingsManager
from common.config import cfg
def show_mask(mask,color, opacity=0.6, borders = False):

    color = np.concatenate([color, np.array([opacity])], axis=0)

    h, w = mask.shape[-2:]
    mask = mask.astype(np.uint8)
    mask_image =  mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    if borders:
        import cv2
        contours, _ = cv2.findContours(mask,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) 
        contours = [cv2.approxPolyDP(contour, epsilon=0.01, closed=True) for contour in contours]
        mask_image = cv2.drawContours(mask_image, contours, -1, (1, 1, 1, 0.5), thickness=1) 
    return np.uint8(mask_image*255)

def Hex_to_RGB(hex):
    r = int(hex[1:3],16)
    g = int(hex[3:5],16)
    b = int(hex[5:7], 16)
    return np.array([r/255,g/255,b/255])

def Hex_to_RGBA_QColor(hex,opacity=0.6):
    r = int(hex[1:3],16)
    g = int(hex[3:5],16)
    b = int(hex[5:7], 16)
    return QColor(r,g,b,int(255*opacity))

# 编码函数：将二值掩码转换为 RLE 编码
# def encode_binary_mask(binary_mask):
#     rle = mask.encode(np.asfortranarray(binary_mask))  # 编码为 RLE
#     rle['counts'] = rle['counts'].decode('ascii')  # 将 counts 转换为字符串（COCO 格式需要）
#     return rle

# 解码函数：将 RLE 编码解码回二值掩码
# def decode_rle_to_binary_mask(rle):
#     binary_mask = mask.decode(rle)
#     return binary_mask

def mask_to_rle(mask: np.ndarray) -> Dict[str, List[int]]:
    """
    Encodes a binary mask to an uncompressed RLE (Run-Length Encoding).
    Parameters:
        mask (np.ndarray): A binary mask of shape (height, width), 
                           where 1 represents the object and 0 represents the background.   
    Returns:
        Dict: A dictionary containing the RLE 'counts' and 'size' (height, width) of the mask.
    """
    # Get the height and width of the mask
    h, w = mask.shape
    # Flatten the mask in Fortran (column-major) order (equivalent to Tensor permute)
    flattened_mask = mask.T.flatten()
    # Identify where changes occur (find the indices where the value changes)
    changes = np.diff(flattened_mask).nonzero()[0] + 1
    # Add the start and end points to the change indices
    rle = np.concatenate([[0], changes, [h * w]])
    # Calculate the lengths of runs (differences between consecutive indices)
    counts = np.diff(rle)
    # Handle masks that start with a foreground pixel
    if flattened_mask[0] == 1:
        counts = np.concatenate([[0], counts])
    
    return {"size": [h, w], "counts": counts.tolist()}


def rle_to_mask(rle: Dict[str, Any]) -> np.ndarray:
    """Compute a binary mask from an uncompressed RLE."""
    h, w = rle["size"]
    mask = np.empty(h * w, dtype=bool)
    idx = 0
    parity = False
    for count in rle["counts"]:
        mask[idx : idx + count] = parity
        idx += count
        parity ^= True
    mask = mask.reshape(w, h)
    return mask.transpose().copy()  # Put in C order

class PolygonItem(QGraphicsPolygonItem):
    def __init__(self,polygon, mask_id=None, category=None, color="#FF0000", parent=None):
        super().__init__(polygon,parent)
        self._id = mask_id
        self._confirm = False
        self._category = category  # 新增类别属性
        self._color = color        # 新增颜色属性
        self.height=0
        self.width=0
        self.setOpacity(1)
        self.setZValue(1)
        # 设置边框的画笔（例如白色边框）
        self.pen = QPen(QColor(255, 255, 255), 1)
        # 半透明掩膜颜色
        self.mask_color = Hex_to_RGBA_QColor(color,opacity=cfg.get(cfg.opacity)/10)  # 半透明黑色

    def get_polygon_points(self):
        """从QPolygonF中提取点，转换为OpenCV的格式"""
        polygon = self.polygon()  # QPolygonF
        points = []
        for i in range(polygon.count()):
            point = polygon.at(i)
            points.append([int(point.x()), int(point.y())])

        # OpenCV需要点坐标是一个Nx1x2的形状
        return np.array([points], dtype=np.int32)

    def generate_binary_mask(self, points):
        """根据多边形点生成二值化掩码"""
        # 创建一个全零的二值掩码图像，大小与原始图像相同
        binary_mask = np.zeros((self.height, self.width), dtype=np.uint8)

        # 使用OpenCV的fillPoly函数填充多边形区域
        cv2.fillPoly(binary_mask, points, 1)

        return binary_mask

    def update_mask_visual(self):
        self.mask_color=Hex_to_RGBA_QColor(self._color)
        self.setPen(self.pen)
        self.setBrush(QBrush(self.mask_color))
        

    def confirm(self, mask_obj):
        self._confirm = True
        self._id = mask_obj['id']
        self._category=mask_obj['category']
        self._color=mask_obj['color']
        self.height=mask_obj['height']
        self.width=mask_obj['width']
        self.update_mask_visual()

    def status(self):
        return self._confirm

    def get_id(self):
        return self._id if self._confirm else -1

    def set_category(self, category):
        self._category = category

    def get_category(self):
        return self._category

    def set_color(self, color):
        self._color = color
        self.update_mask_visual()

    def get_color(self):
        return self._color

    def to_dict(self):
        # 获取多边形的点
        points = self.get_polygon_points()
        # 生成二值掩码
        binary_mask = self.generate_binary_mask(points)
        return {
            'id':self._id,
            'category':self._category,
            'color':self._color,
            'mask':mask_to_rle(binary_mask)
        }


class MaskItem(QGraphicsPixmapItem):
    def __init__(self, binary_mask, mask_id=None, category=None, color="#FF0000", parent=None):
        super().__init__( parent)
        self._id = mask_id
        self._confirm = False
        self._category = category  # 新增类别属性
        self._color = color        # 新增颜色属性
        self.mask=binary_mask      # 新增mask属性
        self.update_mask_visual()  # 更新掩码可视化
        self.setOpacity(1)
        self.setZValue(1)

    def update_mask_visual(self):
        """接受一个二值掩码，并在MaskItem中可视化"""
        color=Hex_to_RGB(self._color)
        mask_image =  show_mask(self.mask,color=color,borders=True,opacity=cfg.get(cfg.opacity)/10)
        height, width, channels = mask_image.shape
        bytes_per_line = channels * width
        qimage_mask = QImage(mask_image.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        # 将 QImage 转换为 QPixmap
        mask_pixmap = QPixmap.fromImage(qimage_mask)
        # 将QImage转换为QPixmap并设置到MaskItem
        self.setPixmap(mask_pixmap)

    def confirm(self, mask_obj):
        self._confirm = True
        self._id = mask_obj['id']
        self._category=mask_obj['category']
        self._color=mask_obj['color']
        self.update_mask_visual()

    def status(self):
        return self._confirm

    def get_id(self):
        return self._id if self._confirm else -1

    def set_category(self, category):
        self._category = category

    def get_category(self):
        return self._category

    def set_color(self, color):
        self._color = color
        self.update_mask_visual()

    def get_color(self):
        return self._color

    def to_dict(self):
        return {
            'id':self._id,
            'category':self._category,
            'color':self._color,
            'mask':mask_to_rle(self.mask.astype(np.uint8))
        }

class MyGraphicsView(QGraphicsView,SmoothScrollArea):

    # 定义一个信号，参数为两个整数，分别表示 x 和 y 坐标
    mouseMoved = pyqtSignal(int, int)

    def __init__(self,parent=None):
        super().__init__(parent)

        self.setMouseTracking(True)  # 启用鼠标追踪

        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)
        # 设置场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.image_width = 0
        self.image_height = 0
        
        self.point_type = "foreground"  # 默认点的类型为前景点
        self.is_drawing = False # 初始化鼠标状态
        self.mode='sam' # 当前掩膜的生成模式
        

        self.mask_items = {}  # 存储所有 mask_items 的字典，键为 mask_id
        self.polygon_items={} #存储所有的 polygon_item 的字典，键为 mask_id

        self.sam_points = []  # 存储sam的提示点
        self.polygon_points = [] # 当前的多边形点列表
        
        self.pixmap_item = None  # 用于存储加载的图片
        self.mask_item=None # 当前sam分割的mask对象
        self.polygon_item = None #当前人工分割的多边形对象

        self.last_hovered_item = None  # 保存上次悬停的项

        self.image=None # 当前正在处理的np图片

        self.obj_ids=[] #当前图像的所有分割对象id列表
        self.cur_obj={ #当前图像当前的分割对象
            'id':'',
            'input_points':[],
            'input_labels':[],
            'mask':'',
            'category':'',
            'color':''
        }

        # 获取 SettingsManager 的实例
        # self.settings_manager = SettingsManager()
        self.model_cfg ={
            'sam2_tiny':'sam2_hiera_t.yaml',
            'sam2_small':'sam2_hiera_s.yaml',
            'sam2_base_plus':'sam2_hiera_b+.yaml',
            'sam2_large':'sam2_hiera_l.yaml',
        }

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")
        
        # 模型初始化
        self.get_preditor(cfg.get(cfg.cur_model)) 
        
    # 获取模型预测器
    # 切换模型后，应该先将图片加载到模型中
    def get_preditor(self,model_name):
        # model_name=cfg.get(cfg.cur_model)
        model_weight=cfg.get(getattr(cfg, model_name, None))
        model_cfg=self.model_cfg[model_name]
        try:
            self.sam2_model=build_sam2(model_cfg,model_weight,device=self.device)
            self.predictor = SAM2ImagePredictor(self.sam2_model)
            cfg.set(cfg.cur_model,model_name)#只有在加载成功后才会更新配置
            InfoBar.success(
                title='模型载入成功',
                content=f"当前模型:{model_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_LEFT,
                duration=1000,
                parent=self
            )
        except:
            InfoBar.error(
                title='模型加载失败',
                content="请检查模型权重路径是否正确",
                orient=Qt.Vertical,  # 内容太长时可使用垂直布局
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,#永久显示
                parent=self.parent()
            )
            # 从配置中重新读取之前的model
            cur_model=cfg.get(cfg.cur_model)
            self.parent().select_model()#选中之前的模型
            self.get_preditor(cur_model)
        if self.image is not None:
            self.predictor.set_image(self.image)
            self.reset_points()
    
    # 加载一张新图片，并送进SAM进行初始化
    def load_image(self, image_path):
        # 清空场景，加载并显示图片
        
        self.mask_items.clear()
        self.polygon_items.clear()
        self.obj_ids.clear()
        self.reset_points()
        self.scene.clear()
        self.last_hovered_item=None
        pixmap = QPixmap(image_path)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        # 记录图片的尺寸
        self.image_width = pixmap.width()
        self.image_height = pixmap.height()
        # 自适应图片大小
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

        # 加载图片为np
        image = Image.open(image_path)
        image = np.array(image.convert("RGB"))
        self.image=image
        # 加载模型
        if self.predictor:#模型已经加载好了则直接输入图片
            self.predictor.set_image(self.image)
        else:#否则先加载模型再输入图片
            self.get_preditor(cfg.get(cfg.cur_model))
        
    # 设置当前绘制的点类型
    def set_point_type(self, point_type):
        self.point_type = point_type

    # 绘制一个点
    def draw_point(self, x, y):
        """在指定的场景坐标 (x, y) 处绘制一个小圆点"""
        radius = 4  # 圆点的半径
        # 根据当前点类型设置颜色
        if self.point_type == "foreground":
            pen = QPen(QColor("red"))
            brush = QColor("yellow")
        else:  # 背景点
            pen = QPen(QColor("blue"))
            brush = QColor("green")

        pen.setWidth(1)
        ellipse = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        ellipse.setZValue(999)#最高层级
        ellipse.setPen(pen)
        ellipse.setBrush(brush)
        self.sam_points.append(ellipse)
        # 将点添加到场景中
        self.scene.addItem(ellipse)
        
        # 记录已绘制的点
        self.cur_obj['input_points'].append([int(x),int(y)])
        if self.point_type == "foreground":
            self.cur_obj['input_labels'].append(1)
        else:
            self.cur_obj['input_labels'].append(0)

        input_point = np.array(self.cur_obj['input_points'])
        input_label = np.array(self.cur_obj['input_labels'])
        masks, _, _ = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=False,
        )

        # 检查是否已经有一个未确认的掩码存在，若存在则移除
        if self.mask_item and not self.mask_item.status():
            self.scene.removeItem(self.mask_item)
            del self.mask_item #防止内存泄漏
        cur_category=cfg.get(cfg.cur_category)
        color_map=cfg.get(cfg.color_map)
        cur_color=color_map[cur_category]
        # 将掩码添加到场景
        self.mask_item=MaskItem(masks[0],color=cur_color)
        self.scene.addItem(self.mask_item)
        # 记录当前Mask的颜色参数
        self.cur_obj['category']=cur_category
        self.cur_obj['color']=cur_color

    # 重置当前所有提示点，同时清除当前mask
    def reset_points(self):
        for point in self.sam_points:
            self.scene.removeItem(point)
        self.sam_points.clear()
        self.cur_obj['input_points'].clear()
        self.cur_obj['input_labels'].clear()
        if self.mask_item and not self.mask_item.status():
            self.scene.removeItem(self.mask_item)
            del self.mask_item #防止内存泄漏
            self.mask_item=None

    # 获取下一个分割对象的id
    def get_next_id(self):
        if len(self.obj_ids)==0:
            return 'obj_1'  # 如果当前没有对象，则 id 从 'obj_1' 开始
        else:
            # 提取已有 id 中最大的数字部分，并自增
            max_id = max(int(obj_id.split('_')[1]) for obj_id in self.obj_ids)
            return f'obj_{max_id + 1}'

    # 完成当前Mask的编辑
    def confirm_mask(self):
        if self.mask_item and not self.mask_item.status():
            obj_id = self.get_next_id()
            self.cur_obj['id'] = obj_id  # 将生成的 id 赋值给对象
            self.obj_ids.append(obj_id)
            self.mask_item.confirm(self.cur_obj)
            self.mask_items[obj_id] = self.mask_item
            self.reset_points()
            self.cur_obj={ 
                'id':'',
                'input_points':[],
                'input_labels':[],
                'mask':'',
                'category':'',
                'color':''
            }
            
    # 完成当前多边形掩膜的编辑
    def confirm_polygon(self):
       if self.polygon_item and not self.polygon_item.status():
            obj_id = self.get_next_id()
            self.cur_obj['id']=obj_id
            self.obj_ids.append(obj_id)
            cur_category=cfg.get(cfg.cur_category)
            color_map=cfg.get(cfg.color_map)
            cur_color=color_map[cur_category]
            self.cur_obj['color']=cur_color
            self.cur_obj['category']=cur_category
            self.cur_obj['height']=self.image_height
            self.cur_obj['width']=self.image_width
            self.polygon_item.confirm(self.cur_obj)
            self.polygon_items[obj_id] = self.polygon_item
            self.cur_obj={
                'id':'',
                'input_points':[],
                'input_labels':[],
                'mask':'',
                'category':'',
                'color':''
            }

    # 滚轮事件
    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:#检查是否同时按下了ctrl键
            self.scaleView(math.pow(2.0, event.angleDelta().y() / 240.0))
        super().wheelEvent(event)
    # 视图放大缩小
    def scaleView(self, scaleFactor):
        factor = self.transform().scale(scaleFactor, scaleFactor).mapRect(QRectF(0, 0, 1, 1)).width()
        if factor < 0.07 or factor > 100:
            return
        self.scale(scaleFactor, scaleFactor)
    # 鼠标点击事件
    def mousePressEvent(self, event: QMouseEvent):
        # 将点击点转换为场景坐标
        point = self.mapToScene(event.pos())
        # 检查点击是否在图片区域内
        if 0 <= point.x() < self.image_width and 0 <= point.y() < self.image_height:
            # 手动绘制多边形
            if self.mode=='draw':
                if event.button() == Qt.LeftButton:
                    # 如果是第一次点击，初始化多边形
                    if not self.is_drawing:
                        self.polygon_points = [point]
                        self.is_drawing = True
                    else:
                        # 如果正在绘制，添加点到多边形
                        self.polygon_points.append(point)

                    # 如果存在未编辑好的多边形项，则删除
                    if self.polygon_item and not self.polygon_item.status():
                        self.scene.removeItem(self.polygon_item)

                    # 创建新的多边形项
                    polygon = QPolygonF(self.polygon_points)
                    cur_category=cfg.get(cfg.cur_category)
                    color_map=cfg.get(cfg.color_map)
                    cur_color=color_map[cur_category]
                    self.polygon_item = PolygonItem(polygon,color=cur_color)
                    self.polygon_item.update_mask_visual()
                    
                    # 将多边形添加到场景中
                    self.scene.addItem(self.polygon_item)
                    
                # 在绘制过程中点击右键
                elif event.button() == Qt.RightButton and self.is_drawing:
                    # 右键点击结束多边形绘制
                    self.is_drawing = False
                    # 如果存在polygon_item且它属于当前场景，移除它
                    if self.polygon_item and self.polygon_item in self.scene.items():
                        self.scene.removeItem(self.polygon_item)
                    # 创建最终的多边形
                    # 小于三个点，本次操作全部取消
                    if len(self.polygon_points)<3:
                        # 清空点列表
                        self.polygon_points = []
                        self.polygon_item = None  # 清空polygon_item引用
                    else:
                        polygon = QPolygonF(self.polygon_points)
                        self.polygon_item = PolygonItem(polygon)
                        # 将多边形添加到场景中
                        self.scene.addItem(self.polygon_item)
                        # 清空点列表
                        self.polygon_points = []
                        # 保存当前多边形
                        self.confirm_polygon()

                # 在绘制结束点击右键，弹出菜单
                elif event.button() == Qt.RightButton and not self.is_drawing:
                    items_under_mouse = self.scene.items(point)
                    if items_under_mouse:
                        current_selected_item = items_under_mouse[0]
                        if isinstance(current_selected_item, (MaskItem,PolygonItem)):
                            # 弹出右键菜单
                            self.showContextMenu(current_selected_item, event.globalPos())

            else:# sam分割得到掩膜
                if event.button() == Qt.LeftButton:
                    # 绘制一个可视化点，同时送进SAM进行提示
                    self.draw_point(point.x(), point.y())
                elif event.button() == Qt.RightButton:  # 右键点击
                    # 右键单击确认掩膜分割完毕
                    if self.mask_item and not self.mask_item.status():
                        self.confirm_mask()
                    # 如果已经分割完毕，则弹出菜单
                    else:
                        items_under_mouse = self.scene.items(point)
                        if items_under_mouse:
                            current_selected_item = items_under_mouse[0]
                            if isinstance(current_selected_item, (MaskItem,PolygonItem)):
                                # 弹出右键菜单
                                self.showContextMenu(current_selected_item, event.globalPos())
    # 鼠标移动事件
    def mouseMoveEvent(self, event):
        # 首先，调用父类的 mouseMoveEvent 以确保默认行为正常
        super().mouseMoveEvent(event)
        # 将鼠标视图坐标转换为场景坐标
        scene_pos = self.mapToScene(event.pos())
        # 检查鼠标是否在图片区域内
        if self.pixmap_item and 0 <= scene_pos.x() < self.image_width and 0 <= scene_pos.y() < self.image_height:
            # 将场景坐标转换为图片中的像素坐标
            pixel_x = int(scene_pos.x())
            pixel_y = int(scene_pos.y())
            # 发射信号，将坐标传递给父类
            self.mouseMoved.emit(pixel_x, pixel_y)
            # 获取鼠标下的所有场景项
            items_under_mouse = self.scene.items(scene_pos)
            if self.last_hovered_item and isinstance(self.last_hovered_item, (MaskItem,PolygonItem)):
                self.last_hovered_item.setOpacity(1.0)  # 恢复上次悬停的项的透明度
            # 如果鼠标悬停在某个 QGraphicsPixmapItem 上，设置其透明度为 0.5
            if items_under_mouse:
                current_hovered_item = items_under_mouse[0]
                if isinstance(current_hovered_item, (MaskItem,PolygonItem)):
                    current_hovered_item.setOpacity(0.5)
                    self.last_hovered_item = current_hovered_item

            # 实时绘制多边形
            if self.mode=='draw' and self.is_drawing:

                # 绘制临时多边形，包括鼠标的当前点
                temp_points = self.polygon_points + [scene_pos]
                polygon = QPolygonF(temp_points)

                # 删除之前的多边形项
                if self.polygon_item:
                    self.scene.removeItem(self.polygon_item)

                # 创建新的多边形项
                cur_category=cfg.get(cfg.cur_category)
                color_map=cfg.get(cfg.color_map)
                cur_color=color_map[cur_category]
                self.polygon_item = PolygonItem(polygon,color=cur_color)
                self.polygon_item.update_mask_visual()

                # 将多边形添加到场景中
                self.scene.addItem(self.polygon_item)
        else:
            # 发射空坐标信号，用于清除父类中的显示
            self.mouseMoved.emit(-1, -1)

    
    # 更新掩码颜色
    def update_mask_color(self, category, new_color):
        # 遍历并更新所有类别匹配的 mask_items
        for mask_item in self.mask_items.values():
            if mask_item.get_category() == category:
                mask_item.set_color(new_color)

        # 遍历并更新所有类别匹配的 polygon_items
        for mask_item in self.polygon_items.values():
            if mask_item.get_category() == category:
                mask_item.set_color(new_color)

    # 更新掩码类别
    def update_mask_category(self, old_category, new_category):
        # 遍历并更新所有类别匹配的 mask_items
        for mask_item in self.mask_items.values():
            if mask_item.get_category() == old_category:
                mask_item.set_category(new_category)

        # 遍历并更新所有类别匹配的 polygon_items
        for mask_item in self.polygon_items.values():
            if mask_item.get_category() == old_category:
                mask_item.set_category(new_category)
        
    # 显示右键菜单
    def showContextMenu(self, item, global_pos):
        menu = RoundMenu(self)
        delete_action = Action(FIF.DELETE, '删除')
        menu.addAction(delete_action)
        # 绑定删除操作
        delete_action.triggered.connect(lambda: self.deleteMaskItem(item))
        # 在鼠标位置显示菜单
        menu.exec_(global_pos)

    # 删除已经编辑好的mask item
    def deleteMaskItem(self, item):
        if item:
            self.scene.removeItem(item)
            mask_id = item.get_id()
            if mask_id != -1:
                if isinstance(item,MaskItem):
                    del self.mask_items[mask_id]
                elif isinstance(item,PolygonItem):
                    del self.polygon_items[mask_id]
                for obj_id in self.obj_ids:
                    if mask_id==obj_id:
                        self.obj_ids.remove(obj_id)
            del item  # 确保对象被释放

    # 从文件中读取标注文件
    def show_annotation(self,file_name):
        filepath=os.path.join(cfg.get(cfg.save_path),file_name.split('.')[0]+'.json')
        if not os.path.exists(filepath):
            return 
        with open(filepath, 'r') as file:
            objs = json.load(file)
        for obj_key,mask_obj in objs.items():
            mask=rle_to_mask(mask_obj['mask']) 
            color=mask_obj['color']
            id=mask_obj['id']
            self.mask_item=MaskItem(mask,color)
            self.obj_ids.append(id)
            self.mask_item.confirm(mask_obj)
            self.mask_items[id] = self.mask_item
            self.scene.addItem(self.mask_item)
        

    # 导出所有的Obj
    def export_obj(self):
        objs={}
        for mask_item in self.mask_items.values():
            objs[mask_item.get_id()]=mask_item.to_dict()
        for mask_item in self.polygon_items.values():
            objs[mask_item.get_id()]=mask_item.to_dict()
        return objs
    
    # 保存到指定文件夹
    def save_to(self):
        objs=self.export_obj()
        if objs:
            filepath,type = QFileDialog.getSaveFileName(self,'文件保存','/','json(*.json)')
            if filepath:
                with open(filepath,'w') as file_obj:
                    json.dump(objs,file_obj, ensure_ascii=False, indent=4)

    # 自动保存
    def auto_save(self,filename):
        save_path=cfg.get(cfg.save_path)
        filepath=os.path.join(save_path,filename.split('.')[0]+'.json')
        objs=self.export_obj()
        if objs:
            with open(filepath,'w') as file_obj:
                json.dump(objs,file_obj, ensure_ascii=False, indent=4)

    
