from qfluentwidgets import (InfoBar,RangeSettingCard,ComboBoxSettingCard,SwitchSettingCard,ScrollArea,ExpandLayout,SettingCardGroup,PushSettingCard,
                            isDarkTheme,Theme,setTheme,OptionsSettingCard,CustomColorSettingCard,setThemeColor)
from PyQt5.QtWidgets import QHBoxLayout,QWidget,QLabel,QFileDialog,QFrame
from qfluentwidgets import FluentIcon as FIF
from common.config import cfg
from PyQt5.QtCore import Qt
class SettingInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # setting label
        self.settingLabel = QLabel('设置', self)
        self.modelGroup=SettingCardGroup('SAM2',self.scrollWidget)
        self.sam2_tinyFolderCard=PushSettingCard(
            '更改',
            FIF.DOWNLOAD,
            'SAM2_tiny',
            cfg.get(cfg.sam2_tiny),
            self.modelGroup
        )
        self.sam2_smallFolderCard=PushSettingCard(
            '更改',
            FIF.DOWNLOAD,
            'SAM2_small',
            cfg.get(cfg.sam2_small),
            self.modelGroup
        )
        self.sam2_base_plusFolderCard=PushSettingCard(
            '更改',
            FIF.DOWNLOAD,
            'SAM2_base+',
            cfg.get(cfg.sam2_base_plus),
            self.modelGroup
        )
        self.sam2_largeFolderCard=PushSettingCard(
            '更改',
            FIF.DOWNLOAD,
            'SAM2_large',
            cfg.get(cfg.sam2_large),
            self.modelGroup
        )
        self.segmantationGroup=SettingCardGroup('分割配置',self.scrollWidget)
        self.autoSaveCard = SwitchSettingCard(
            FIF.QUICK_NOTE,
            '自动保存分割结果',
            '当切换到其他图片时，上一张图片的分割结果将自动保存到指定目录',
            configItem=cfg.auto_save,
            parent=self.segmantationGroup
        )
        self.saveFolderCard=PushSettingCard(
            '打开文件夹',
            FIF.SAVE,
            '标注结果保存位置',
            cfg.get(cfg.save_path),
            self.segmantationGroup
        )
        self.opacityCard = RangeSettingCard(
            cfg.opacity,
            FIF.HIGHTLIGHT,
            '掩膜透明度',
            '修改标注掩码的透明度',
            parent=self.segmantationGroup
        )


        self.personalGroup = SettingCardGroup('个性化', self.scrollWidget)
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr('Application theme'),
            self.tr("Change the appearance of your application"),
            texts=[
                self.tr('Light'), self.tr('Dark'),
                self.tr('Use system setting')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard=CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('Theme color'),
            self.tr('Change the theme color of you application'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("Interface zoom"),
            self.tr("Change the size of widgets and fonts"),
            texts=[
                "100%", "125%", "150%", "175%", "200%",
                self.tr("Use system setting")
            ],
            parent=self.personalGroup
        )
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr('Language'),
            self.tr('Set your preferred language for UI'),
            texts=['简体中文', '繁體中文', 'English', self.tr('Use system setting')],
            parent=self.personalGroup
        )

        self.__initWidget()

    def __initWidget(self):
        # self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        # initialize style sheet
        self.__setQss()

        # initialize layout
        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(23, 23)
        self.modelGroup.addSettingCards([self.sam2_tinyFolderCard,self.sam2_smallFolderCard,self.sam2_base_plusFolderCard,self.sam2_largeFolderCard])
        self.segmantationGroup.addSettingCards([self.autoSaveCard,self.saveFolderCard,self.opacityCard])
        self.personalGroup.addSettingCards([self.themeCard,self.themeColorCard,self.zoomCard,self.languageCard])
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(30, 10, 30, 0)
        self.expandLayout.addWidget(self.modelGroup)
        self.expandLayout.addWidget(self.segmantationGroup)
        self.expandLayout.addWidget(self.personalGroup)

    def __setQss(self):
        """ set style sheet """
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')

        theme = 'dark' if isDarkTheme() else 'light'
        with open(f'resource/qss/{theme}/setting_interface.qss', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        cfg.themeChanged.connect(self.__onThemeChanged)
        self.themeColorCard.colorChanged.connect(setThemeColor)

        self.saveFolderCard.clicked.connect(
            self.saveFolderCardClicked)
        
        self.sam2_tinyFolderCard.clicked.connect(
            self.SAM2_tinyCardClicked)
        
        self.sam2_smallFolderCard.clicked.connect(
            self.SAM2_samllCardClicked)
        
        self.sam2_base_plusFolderCard.clicked.connect(
            self.SAM2_base_plusCardClicked)
        
        self.sam2_largeFolderCard.clicked.connect(
            self.SAM2_largeCardClicked)
        
    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            '',
            self.tr('Configuration takes effect after restart'),
            parent=self.window()
        )

    def saveFolderCardClicked(self):
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Choose folder"), "./")
        if not folder or cfg.get(cfg.save_path) == folder:
            return
        cfg.set(cfg.save_path, folder)
        self.saveFolderCard.setContent(folder)
    
    def SAM2_tinyCardClicked(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型权重文件", "", "pth Files (*.pt);;All Files (*)", options=options)
        if not file_path or cfg.get(cfg.sam2_tiny) == file_path:
            return
        cfg.set(cfg.sam2_tiny, file_path)
        self.sam2_tinyFolderCard.setContent(file_path)
    

    def SAM2_samllCardClicked(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型权重文件", "", "pth Files (*.pt);;All Files (*)", options=options)
        if not file_path or cfg.get(cfg.sam2_small) == file_path:
            return
        cfg.set(cfg.sam2_small, file_path)
        self.sam2_smallFolderCard.setContent(file_path)

    def SAM2_base_plusCardClicked(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型权重文件", "", "pth Files (*.pt);;All Files (*)", options=options)
        if not file_path or cfg.get(cfg.sam2_base_plus) == file_path:
            return
        cfg.set(cfg.sam2_base_plus, file_path)
        self.sam2_base_plusFolderCard.setContent(file_path)

    def SAM2_largeCardClicked(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型权重文件", "", "pth Files (*.pt);;All Files (*)", options=options)
        if not file_path or cfg.get(cfg.sam2_large) == file_path:
            return
        cfg.set(cfg.sam2_large, file_path)
        self.sam2_largeFolderCard.setContent(file_path)


    def __onThemeChanged(self, theme: Theme):
        """ theme changed slot """
        # change the theme of qfluentwidgets
        setTheme(theme)

        # chang the theme of setting interface
        self.__setQss()

class Setting(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)
        self.settingInterface = SettingInterface(self)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.settingInterface)
        self.setObjectName('setting')