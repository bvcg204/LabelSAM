
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            ColorConfigItem, OptionsValidator, RangeConfigItem, RangeValidator,
                            FolderListValidator, EnumSerializer, FolderValidator, ConfigSerializer, __version__)
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QGuiApplication, QFont
from enum import Enum

class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()


class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO

class MyConfig(QConfig):
    sam2_tiny=ConfigItem('Model','sam2_tiny',r'D:\code\pyqt_progrem\segment-anything-2-main\checkpoints\sam2_hiera_tiny.pt')
    sam2_small=ConfigItem('Model','sam2_small',r'D:\code\pyqt_progrem\segment-anything-2-main\checkpoints\sam2_hiera_small.pt')
    sam2_base_plus=ConfigItem('Model','sam2_base_plus',r'D:\code\pyqt_progrem\segment-anything-2-main\checkpoints\sam2_hiera_tiny.pt')
    sam2_large=ConfigItem('Model','sam2_large',r'D:')
    auto_save=ConfigItem('Segmentation','auto_save',True,BoolValidator())
    opacity=RangeConfigItem('Segmentation','opacity',6,RangeValidator(3,10))
    save_path=ConfigItem('Segmentation','save_path','',FolderValidator())
    cur_model=ConfigItem('Segmentation','cur_model','sam2_tiny')
    cur_category=ConfigItem('Segmentation','cur_category','Class 1')
    color_map=ConfigItem('Segmentation','color_map',{
        "Class 1": "#ff0000",
        "Class 2": "#00ff00",
        "Class 3": "#0000ff"
    })


    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.AUTO, OptionsValidator(Language), LanguageSerializer(), restart=True)


cfg = MyConfig()
qconfig.load(r'D:\code\pyqt_progrem\labelSAM\config\config.json', cfg)


