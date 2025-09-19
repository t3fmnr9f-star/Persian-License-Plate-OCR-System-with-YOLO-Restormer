import sys , os
import re
import cv2
import pathlib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QHBoxLayout, QVBoxLayout, QMenuBar,
    QMenu, QAction, QFileDialog,QFrame,QMainWindow, QScrollArea, QListWidget,QDialog,QSplitter, QSlider, QLineEdit, QSizePolicy, QTextEdit
)
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont, QCursor, QFontDatabase, QPixmap, QImage, QDragEnterEvent, QDropEvent
from PyQt5.QtCore import Qt, QUrl

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PlakNet")
        self.setWindowIcon(QIcon("icon.png")) 

        self.resize(600, 400)
        self.setFixedSize(600, 400)  
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)  
        self.move_to_center()

        # رنگ پس‌زمینه
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#181818"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # ساخت دکمه‌ها
        self.init_ui()

    def move_to_center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.primaryScreen().geometry()
        centerPoint = screen.center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def init_ui(self):
        button_style = """
            QPushButton {
                background-color: #1F1F1F;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 40px 50px;
                font-size: 25px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
        """

        # فونت
        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "Arial"
        
        btn_video = QPushButton("فیلم")
        btn_video.setStyleSheet(button_style)
        btn_video.clicked.connect(self.open_video_page)
        btn_video.setMinimumWidth(200)

        btn_image = QPushButton("عکس")
        btn_image.setStyleSheet(button_style)
        btn_image.clicked.connect(self.open_image_page)
        btn_image.setMinimumWidth(200)


        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(btn_video)
        hbox.addSpacing(40)
        hbox.addWidget(btn_image)
        hbox.addStretch(1)


        # نوشته کوچک پایین راست
        footer_label = QLabel("وارد کردن پلاک با فاصله خیلی نزدیک")
        footer_label.setStyleSheet("color: #0C9EF7;")
        footer_label.setFont(QFont(family, 10, QFont.Bold))  # سایز ۱۰ بولد
        footer_label.setCursor(QCursor(Qt.PointingHandCursor))
        footer_label.mousePressEvent = self.open_another_page

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        footer_layout.addWidget(footer_label)

        vbox = QVBoxLayout()
        vbox.addStretch(2)
        vbox.addLayout(hbox)
        vbox.addStretch(3)
        vbox.addLayout(footer_layout)

        self.setLayout(vbox)

    def open_video_page(self):
        self.new_window = MediaWindow("video")
        self.new_window.show()
        self.close()

    def open_image_page(self):
        self.new_window = MediaWindow("image")
        self.new_window.show()
        self.close()

    def open_another_page(self, event):
        # مرحله اول: نمایش دیالوگ راهنما (مودال)
        guide_dialog = UserGuide_NearPlate_Dialog(self)
        guide_dialog.exec_()  # اجرای مودال، تا زمانی که بسته نشه، برنامه متوقف می‌مونه

        # مرحله دوم: بعد از بسته‌شدن دیالوگ، پنجره اصلی جدید رو باز کن
        self.new_window = Near_plate()
        self.new_window.show()
        self.close()



class MediaWindow(QMainWindow):
    def __init__(self, media_type):
        super().__init__()
        self.media_type = media_type
        self.setWindowTitle(f"PlakNet - {media_type.capitalize()}")
        self.setWindowIcon(QIcon("icon.png"))
        self.setAcceptDrops(True)

        self.setFocusPolicy(Qt.StrongFocus)

        self.media_files = []
        self.current_frame_index = 0

        self.video_path = None
        self.cap = None
        self.fps = None
        self.total_frames = 0

        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.sahel_font = QFont(font_family, 13)

        self.set_background()
        self.setup_ui()
        self.showMaximized()

    def set_background(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#1F1F1F"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
    def filter_file_list(self, text):
        text = text.lower().strip()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setHidden(text not in item.text().lower())

    def keyPressEvent(self, event):
        if self.file_list.count() == 0:
            return

        key = event.key()
        current_row = self.file_list.currentRow()

        direction = 0
        if key == Qt.Key_D:
            direction = 1
        elif key == Qt.Key_A:
            direction = -1
        else:
            return

        next_row = current_row + direction

        while 0 <= next_row < self.file_list.count():
            item = self.file_list.item(next_row)
            if not item.isHidden():  # یعنی در نتایج فیلترشده وجود داره
                self.file_list.setCurrentRow(next_row)
                self.display_selected_media(item)
                break
            next_row += direction

    def setup_ui(self):
        self.setup_menu()

        central_widget = QWidget()
        main_layout = QVBoxLayout()

        splitter = QSplitter(Qt.Horizontal)

        # ---------- تصویر یا فریم در scroll area ----------
        self.image_label = QLabel("هیچ رسانه‌ای انتخاب نشده است.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #828282; background-color: #1F1F1F; font-size: 18px;")
        self.image_label.setFont(self.sahel_font)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.image_label)

        # ---------- پنل راست: سرچ و لیست ----------
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Filename")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                padding: 4px;
                border-radius: 0px;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_file_list)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.display_selected_media)

        right_layout.addWidget(self.search_bar)
        right_layout.addWidget(self.file_list)
        right_panel.setLayout(right_layout)

        splitter.addWidget(scroll_area)
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 250])

        main_layout.addWidget(splitter)

        if self.media_type == "video":
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setMinimum(0)
            self.slider.valueChanged.connect(self.slider_moved)
            self.slider.setEnabled(False)
            main_layout.addWidget(self.slider)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)


    def setup_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar { background-color: #1F1F1F; color: white; border-bottom: 1px solid #333333; }
            QMenuBar::item:selected { background-color: #2a2a2a; }
            QMenu { background-color: #1F1F1F; color: white; border: 1px solid #444444; }
            QMenu::item:selected { background-color: #2a2a2a; }
        """)

        file_menu = QMenu("File", self)
        open_file_action = QAction("Open File", self)
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)

        if self.media_type != "video":
            open_dir_action = QAction("Open Dir", self)
            open_dir_action.triggered.connect(self.open_dir)
            file_menu.addAction(open_dir_action)

        file_menu.addSeparator()
        file_menu.addAction(QAction("Export", self))
        menu_bar.addMenu(file_menu)

        help_menu = QMenu("Help", self)
        shortcuts_action = QAction("کلید های میانبر", self)
        shortcuts_action.triggered.connect(self.open_shortcuts_dialog)
        UserGuide_action = QAction("راهنمای استفاده", self)
        UserGuide_action.triggered.connect(self.open_UserGuide_dialog)
        about_action = QAction("درباره", self)
        about_action.triggered.connect(self.open_about_dialog)
        help_menu.addAction(shortcuts_action)
        help_menu.addAction(UserGuide_action)
        help_menu.addAction(about_action)
        menu_bar.addMenu(help_menu)

    def open_shortcuts_dialog(self):
        dialog = ShortcutsDialog(self)
        dialog.exec_()

    def open_UserGuide_dialog(self):
        dialog = UserGuideDialog(self)
        dialog.exec_()

    def open_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            local_path = url.toLocalFile()
            ext = os.path.splitext(local_path)[1].lower()

            if self.media_type == "video":
                if ext in [".mp4", ".avi", ".mov", ".mkv"]:
                    self.add_media_file(local_path)
            else:
                if ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
                    self.add_media_file(local_path)

    def open_file(self):
        if self.media_type == "image":
            file_filter = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        else:
            file_filter = "Videos (*.mp4 *.avi *.mov *.mkv)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", file_filter)
        if file_path:
            self.add_media_file(file_path)

    def open_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Open Directory", "")
        if directory:
            self.load_files_from_dir(directory)

    def load_files_from_dir(self, directory):
        self.media_files.clear()
        self.file_list.clear()
        valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if os.path.isfile(path) and path.lower().endswith(valid_exts):
                self.add_media_file(path)

        if not self.media_files:
            self.image_label.clear()
            self.image_label.setText("هیچ رسانه‌ای انتخاب نشده است.")

    def add_media_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if self.media_type == "video":
            self.file_list.clear()
            self.extract_video_frames(file_path)
        else:
            if ext not in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
                return

            # نرمال‌سازی مسیر
            normalized_path = pathlib.Path(file_path).as_posix()

            if normalized_path not in self.media_files:
                self.media_files.append(normalized_path)
                self.file_list.addItem(normalized_path)

                if len(self.media_files) == 1:
                    self.display_selected_media(self.file_list.item(0))

    def extract_video_frames(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.slider.setMaximum(self.total_frames - 1)
        self.slider.setEnabled(True)
        self.file_list.clear()

        for i in range(self.total_frames):
            ms = int((i / self.fps) * 1000)
            s = ms // 1000
            ms_remainder = ms % 1000
            name = f"Frame {i:04}   {s//3600:02}_{(s%3600)//60:02}_{s%60:02}'_{ms_remainder}''"
            self.file_list.addItem(name)

        self.display_frame(0)

    def display_selected_media(self, item):
        i = self.file_list.row(item)
        if self.media_type == "image":
            pix = QPixmap(self.media_files[i])
            self.image_label.setPixmap(pix.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.display_frame(i)

    def display_frame(self, i):
        if not self.cap:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = self.cap.read()
        if not ret:
            return
        h, w, ch = frame.shape
        bytes_per_line = 3 * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pix = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pix.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.slider.blockSignals(True)
        self.slider.setValue(i)
        self.slider.blockSignals(False)

        self.file_list.blockSignals(True)
        self.file_list.setCurrentRow(i)
        self.file_list.blockSignals(False)

        self.current_frame_index = i

    def slider_moved(self, val):
        self.display_frame(val)







class Near_plate(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("پلاک با فاصله خیلی نزدیک")
        self.setWindowIcon(QIcon("icon.png"))
        self.setGeometry(250, 250, 400, 300)
        self.setStyleSheet("background-color: #f0f0f0;")

        label = QLabel("این یک صفحه دیگر است!", self)
        label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)



def sort_key(filename):
    numbers = re.findall(r'\d+', filename)
    return int(numbers[0]) if numbers else filename.lower()



class UserGuide_NearPlate_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("راهنمای استفاده")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(650, 500)
        self.setStyleSheet("background-color: #f0f0f0;")

        # بارگذاری فونت Sahel
        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        sahel_font = QFont(font_family, 11)

        # متن راهنما
        guide_text = (
            "فقط عکس پلاک از فاصله خیلی نزدیک رو به این قسمت وارد کنید.\n\n"
            "نکته: از اونجایی مدل هوش مصنوعیم، این پلاک رو تشخیص نمیده و خودتون دارید این رو بهش وارد میکنید، ممکنه که درصد اطمینان پایینی داشته باشه. یعنی اگر عکس یک پلاک رو بهش وارد کنید که از شدت تاری، تمام اطلاعاتش از بین رفته، در اون صورت خروجی اشتباه به شما میدهد. پس باید حواستان باشد که عکستان خیلی تار نباشد.\n"
            "یه راهنما برای تشخیص: \n"
            "تاریش حداکثر باید جوری باشه که بشه یکی دو کاراکتر رو، فقط هاله ای ازشون رو دید و حدس زد که این چیه. مثلا هفته یا هشته؟ یعنی حداقل بتونی یکیش رو راحت یا بزور تشخیص بدی که چیه.\n"
            "مثلاً باید عکستون مثل اینا باشد:"
        )

        guide_label = QLabel(guide_text)
        guide_label.setFont(sahel_font)
        guide_label.setWordWrap(True)
        guide_label.setStyleSheet("color: #333; padding: 5px;")
        guide_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)

        # اسکرول برای متن
        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_container = QWidget()
        text_layout = QVBoxLayout()
        text_layout.addWidget(guide_label)
        text_container.setLayout(text_layout)
        text_scroll.setWidget(text_container)
        text_scroll.setFixedHeight(300)

        # ------------------------------------
        # نمایش عکس‌ها از پوشه near_example
        # ------------------------------------
        image_folder = "./near_example"
        image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort(key=sort_key)  # مرتب‌سازی بر اساس شماره موجود در اسم

        image_layout = QHBoxLayout()
        image_layout.setSpacing(5)  # فاصله کم بین تصاویر
        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            pixmap = QPixmap(image_path).scaledToHeight(90, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            image_layout.addWidget(img_label)

        image_container = QWidget()
        image_container.setLayout(image_layout)

        # اگر عکس‌ها زیاد بودن، بذاریم در یک اسکرول افقی
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        image_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        image_scroll.setWidget(image_container)
        image_scroll.setFixedHeight(120)

        # ------------------------------------
        # چیدمان نهایی
        # ------------------------------------
        main_layout = QVBoxLayout()
        main_layout.addWidget(text_scroll)
        main_layout.addWidget(image_scroll)
        self.setLayout(main_layout)



class UserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowTitle(" ")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(650, 500)
        self.setStyleSheet("background-color: #f0f0f0;")

        # بارگذاری فونت Sahel
        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        sahel_font = QFont(font_family, 11)

        # عنوان
        title_label = QLabel("راهنمای استفاده")
        title_label.setFont(QFont(font_family, 14))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #222; margin: 10px;")

        # متن راهنما
        guide_text = (
            "وقتی که عکستون رو به این نرم افزار میدهید، اون به طور خودکار پلاک هایی که میتونه بخونه رو تشخیص میده، "
            "کیفیتشون رو بهبود میده، متن داخلش رو میخونه، و به شما نمایش میده.\n\n"
            "وقتی که پردازش یک عکس کامل میشه، اون پلاک رو آبی میکنه، و شما با کلیک روی اون پلاک، میتونید نتیجه پردازش رو ببینید. "
            "و میتونید ازش خروجی هم بگیرید.\n\n"
            "درصد اطمینان نرم افزار خیلی بالاست. قبلا عملکرد این نرم افزار با یک متخصص بهبود کیفیت تصویر مقایسه شد "
            "و مشخص شد که چندین برابر قوی‌تر عمل می‌کند.\n\n"
            "من مدل های هوش مصنوعیم رو، بر اساس پروژه های واقعی یک متخصص که به صورت دستی این کارو انجام میداد درست کردم. "
            "پس در نتیجه خود نرم افزار، پلاک‌هایی که با اطمینان بالا می‌تونه خروجی بده رو به طور خودکار تشخیص می‌ده و نیازی به وارد کردن دستی بهش نیست. "
            "و اگر این نرم‌افزار نتواند آن را بازگردانی کند، هیچ کس و هیچ چیز نمی‌تواند این کار را بکند، چون اطلاعاتش نابود شده است.\n\n"
            "-------------------- برای عکس‌های خیلی نزدیک --------------------\n"
            "اگر یک عکس پلاک از فاصله خیلی نزدیک داشتید، اون رو به این قسمت وارد کنید:\n"
            "صفحه اول برنامه، سمت راست پایین\n\n"
            "نکته: از اونجایی مدل هوش مصنوعیم، این پلاک رو تشخیص نمیده و خودتون دارید این رو بهش وارد میکنید، ممکنه که درصد اطمینان پایینی داشته باشه. یعنی اگر عکس یک پلاک رو بهش وارد کنید که از شدت تاری، تمام اطلاعاتش از بین رفته، در اون صورت خروجی اشتباه به شما میدهد. پس باید حواستان باشد که عکستان خیلی تار نباشد.\n"
            "یه راهنما برای تشخیص: \n"
            "تاریش حداکثر باید جوری باشه که بشه یکی دو کاراکتر رو، فقط هاله ای ازشون رو دید و حدس زد که این چیه. مثلا هفته یا هشته؟ یعنی حداقل بتونی یکیش رو راحت یا بزور تشخیص بدی که چیه.\n"
            "مثلاً باید عکستون مثل اینا باشد:"
        )

        guide_label = QLabel(guide_text)
        guide_label.setFont(sahel_font)
        guide_label.setWordWrap(True)
        guide_label.setStyleSheet("color: #333; padding: 5px;")
        guide_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)

        # اسکرول برای متن
        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_container = QWidget()
        text_layout = QVBoxLayout()
        text_layout.addWidget(guide_label)
        text_container.setLayout(text_layout)
        text_scroll.setWidget(text_container)
        text_scroll.setFixedHeight(300)

        # ------------------------------------
        # نمایش عکس‌ها از پوشه near_example
        # ------------------------------------
        image_folder = "./near_example"
        image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        image_files.sort(key=sort_key)  # مرتب‌سازی بر اساس شماره موجود در اسم

        image_layout = QHBoxLayout()
        image_layout.setSpacing(5)  # فاصله کم بین تصاویر
        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            pixmap = QPixmap(image_path).scaledToHeight(90, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            image_layout.addWidget(img_label)

        image_container = QWidget()
        image_container.setLayout(image_layout)

        # اگر عکس‌ها زیاد بودن، بذاریم در یک اسکرول افقی
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        image_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        image_scroll.setWidget(image_container)
        image_scroll.setFixedHeight(120)

        # ------------------------------------
        # چیدمان نهایی
        # ------------------------------------
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_label)
        main_layout.addWidget(text_scroll)
        main_layout.addWidget(image_scroll)
        self.setLayout(main_layout)







class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # حذف علامت سوال از نوار عنوان
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.setWindowTitle("کلیدهای میانبر")
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(500, 250)

        self.setStyleSheet("background-color: #f0f0f0;")

        # بارگذاری فونت Sahel
        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        sahel_font = QFont(font_family, 13)

        label = QLabel("میتونید با کلید D و A بین عکس ها جلو و عقب بروید.")
        label.setFont(sahel_font)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #222;")

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        self.setLayout(layout)







class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # حذف علامت سوال از نوار عنوان
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.setWindowTitle("درباره برنامه")
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(550, 300)
        self.setStyleSheet("background-color: #f0f0f0;")

        # بارگذاری فونت Sahel
        font_id = QFontDatabase.addApplicationFont("Sahel.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        sahel_font = QFont(font_family, 12)

        # متن درباره نرم‌افزار
        about_text = (
            "نرم‌افزار پلاک‌نت نسخه 1.0\n\n"
            "توسعه دهندگان:\n"
            "دیزاینر و برنامه نویس نرم افزار: متین محمدی\n"
            "ساخت مدل های هوش مصنوعی: متین محمدی\n\n"
            "کارایی نرم افزار: بهبود کیفیت و خواندن پلاک ماشین با هوش مصنوعی\n"
        )

        label = QLabel(about_text)
        label.setFont(sahel_font)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: #222; margin: 10px;")

        # آیکن لینکدین
        linkedin_icon = QLabel()
        pixmap = QPixmap("linkedin3.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        linkedin_icon.setPixmap(pixmap)
        linkedin_icon.setFixedSize(30, 30)
        linkedin_icon.setAlignment(Qt.AlignCenter)

        # لینک لینکدین در QLineEdit قابل انتخاب
        linkedin_link = QLineEdit("https://www.linkedin.com/in/matin-mohammadi-79a376373/")
        linkedin_link.setFont(QFont(font_family, 10))
        linkedin_link.setReadOnly(True)
        linkedin_link.setStyleSheet("background-color: #ffffff; color: #000; padding: 3px; border: 1px solid #ccc;")
        linkedin_link.setCursorPosition(0)

        # چینش افقی برای آیکن + عنوان + لینک
        link_layout = QHBoxLayout()
        link_layout.addWidget(linkedin_icon)
        link_layout.addWidget(linkedin_link)

        # چینش کلی
        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        layout.addLayout(link_layout)  # اضافه کردن لینکدین در انتها

        self.setLayout(layout)






if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
