import os
import sys
import json
import winreg
import subprocess
import ctypes
from ctypes import wintypes
import customtkinter as ctk
from tkinter import filedialog

if os.name != "nt": 
    sys.exit()

LOCAL_APP_DATA = os.getenv("LOCALAPPDATA")
APP_DIR = os.path.join(LOCAL_APP_DATA, "YanardagWallpaper")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
PYW_FILE = os.path.join(APP_DIR, "arkaplan.pyw")

os.makedirs(APP_DIR, exist_ok=True)

# --- ARKA PLAN VİDEO MOTORU (PYW) ---
PYW_CODE = r"""import os
import sys
import json
import ctypes
from ctypes import wintypes

os.environ["QT_OPENGL"] = "software"

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "YanardagWallpaper_App_Mutex")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

def find_workerw():
    progman = ctypes.windll.user32.FindWindowW("Progman", None)
    if not progman: return 0
    ctypes.windll.user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, None)
    workerw_hwnd = ctypes.c_ulong(0)

    def enum_callback(hwnd, _):
        shell_dll = ctypes.windll.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if shell_dll:
            ww = ctypes.windll.user32.FindWindowExW(0, hwnd, "WorkerW", None)
            if ww: workerw_hwnd.value = ww
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    return workerw_hwnd.value

class HardwareAcceleratedWallpaper(QWidget):
    def __init__(self, screen_geometry):
        super().__init__()
        self.screen_w = screen_geometry.width()
        self.screen_h = screen_geometry.height()
        self.is_paused = False

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding) 
        layout.addWidget(self.video_widget)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.0)
        
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(-1)

        self.current_video_path = ""
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.monitor_system)
        self.timer.start(1000)
        
        self.check_config()

    def check_config(self):
        path = os.path.join(os.getenv("LOCALAPPDATA"), "YanardagWallpaper", "config.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                    saved_path = config.get("video_path", "")
                    if saved_path and saved_path != self.current_video_path and os.path.exists(saved_path):
                        self.current_video_path = saved_path
                        self.player.setSource(QUrl.fromLocalFile(saved_path))
                        self.player.play()
                        self.is_paused = False
            except:
                pass

    def check_fullscreen(self):
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd: return False

        shell_hwnd = ctypes.windll.user32.GetShellWindow()
        desktop_hwnd = ctypes.windll.user32.GetDesktopWindow()
        
        if hwnd == shell_hwnd or hwnd == desktop_hwnd:
            return False

        class_name = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in ("WorkerW", "Progman"):
            return False

        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top

        return w >= self.screen_w and h >= self.screen_h

    def monitor_system(self):
        self.check_config()
        if not self.current_video_path: 
            return

        is_fullscreen = self.check_fullscreen()

        if is_fullscreen and not self.is_paused:
            self.player.pause() 
            self.is_paused = True
        elif not is_fullscreen and self.is_paused:
            self.player.play()  
            self.is_paused = False

    def embed_into_workerw(self):
        workerw = find_workerw()
        if workerw:
            ctypes.windll.user32.SetParent(int(self.winId()), workerw)
            self.setGeometry(0, 0, self.screen_w, self.screen_h)
            self.show()

if __name__ == "__main__":
    ctypes.windll.user32.SetProcessDPIAware()
    app = QApplication(sys.argv)
    screen_geo = app.primaryScreen().geometry()
    
    win = HardwareAcceleratedWallpaper(screen_geo)
    win.showFullScreen()
    QTimer.singleShot(500, win.embed_into_workerw)
    sys.exit(app.exec())
"""

def get_pythonw_path():
    if getattr(sys, 'frozen', False):
        return "pythonw"
    else:
        return sys.executable.replace("python.exe", "pythonw.exe")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- KONTROL PANELİ (GUI) ---
class WallpaperManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Yanardağ Wallpaper Engine")
        # Gereksiz butonlar kalktığı için pencere boyutu küçültüldü
        self.geometry("450x260") 
        self.resizable(False, False)

        self.texts = {
            "tr": {
                "title": "Yanardağ Wallpaper Engine",
                "saved": "Kayıtlı: ",
                "no_selection": "Seçim yapılmadı",
                "select_video": "Yüksek Kalite Video Seç",
                "startup_on": "Başlangıçta Çalıştır: AÇIK",
                "startup_off": "Başlangıçta Çalıştır: KAPALI"
            },
            "en": {
                "title": "Yanardag Wallpaper Engine",
                "saved": "Saved: ",
                "no_selection": "No selection",
                "select_video": "Select High Quality Video",
                "startup_on": "Run on Startup: ON",
                "startup_off": "Run on Startup: OFF"
            }
        }

        self.config_data = self.load_config()
        self.video_path = self.config_data.get("video_path", "")
        self.lang = self.config_data.get("language", "tr")

        self.lbl_title = ctk.CTkLabel(self, text="", font=("Segoe UI", 20, "bold"))
        self.lbl_title.pack(pady=(20, 5))

        self.btn_lang = ctk.CTkButton(self, text="", width=35, height=25, font=("Segoe UI", 12, "bold"), fg_color="#333333", hover_color="#555555", command=self.toggle_lang)
        self.btn_lang.place(relx=0.96, rely=0.06, anchor="ne")

        self.lbl_video = ctk.CTkLabel(self, text="", font=("Segoe UI", 11), text_color="#A9A9A9")
        self.lbl_video.pack(pady=(0, 20))

        self.btn_select = ctk.CTkButton(self, text="", command=self.select_video, height=40, font=("Segoe UI", 13, "bold"))
        self.btn_select.pack(pady=10, padx=50, fill="x")

        self.btn_startup = ctk.CTkButton(self, text="", command=self.toggle_startup, height=40, font=("Segoe UI", 13, "bold"))
        self.btn_startup.pack(pady=10, padx=50, fill="x")

        self.update_ui_texts()

    def update_ui_texts(self):
        t = self.texts[self.lang]
        
        self.lbl_title.configure(text=t["title"])
        self.btn_lang.configure(text="TR" if self.lang == "tr" else "EN")
        
        video_name = os.path.basename(self.video_path) if self.video_path else t["no_selection"]
        self.lbl_video.configure(text=f"{t['saved']}{video_name}")
        
        self.btn_select.configure(text=t["select_video"])
        
        self.check_startup_status()

    def toggle_lang(self):
        self.lang = "en" if self.lang == "tr" else "tr"
        self.save_config()
        self.update_ui_texts()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as j:
            json.dump({
                "video_path": self.video_path,
                "language": self.lang
            }, j)

    def select_video(self):
        f = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv")])
        if f:
            self.video_path = f
            self.save_config()
            t = self.texts[self.lang]
            self.lbl_video.configure(text=f"{t['saved']}{os.path.basename(f)}")

    def check_startup_status(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        t = self.texts[self.lang]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, "YanardagWallpaper")
                self.btn_startup.configure(text=t["startup_on"], fg_color="#2FA572", hover_color="#106A43")
        except FileNotFoundError:
            self.btn_startup.configure(text=t["startup_off"], fg_color="#C23B22", hover_color="#8E2312")

    def toggle_startup(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        t = self.texts[self.lang]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    winreg.QueryValueEx(key, "YanardagWallpaper")
                    winreg.DeleteValue(key, "YanardagWallpaper")
                    self.btn_startup.configure(text=t["startup_off"], fg_color="#C23B22", hover_color="#8E2312")
                except FileNotFoundError:
                    winreg.SetValueEx(key, "YanardagWallpaper", 0, winreg.REG_SZ, f'"{get_pythonw_path()}" "{PYW_FILE}"')
                    self.btn_startup.configure(text=t["startup_on"], fg_color="#2FA572", hover_color="#106A43")
        except:
            pass

if __name__ == "__main__":
    with open(PYW_FILE, "w", encoding="utf-8") as f:
        f.write(PYW_CODE)

    pythonw_cmd = get_pythonw_path()
    try:
        subprocess.Popen([pythonw_cmd, PYW_FILE], creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        sys.exit(1)

    app = WallpaperManager()
    app.mainloop()