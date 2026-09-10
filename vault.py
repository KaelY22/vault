import os
import sys
import json
import time
import shutil
import subprocess
import threading
import queue
import datetime
import platform
import webbrowser
from pathlib import Path
from tkinter import messagebox, simpledialog, filedialog

try:
    import customtkinter as ctk
except ImportError:
    print("Error: No se encontró la librería 'customtkinter'.")
    print("Instálala con: pip install customtkinter")
    sys.exit(1)

APP_NAME = "VAULT"
VERSION = "1.0"
IS_WIN = platform.system() == "Windows"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if IS_WIN else 0

THEMES = {
    "dark": {
        "bg": "#0E1412", "surface": "#141A17", "surface2": "#1A211D", "border": "#26302A",
        "text": "#E6E8EE", "muted": "#9AA3B2", "accent": "#2DD4A7", "accent_hover": "#4FE0B5",
        "ok": "#00C853", "err": "#FF5252", "sidebar": "#0A0F0D", "console_bg": "#0A0F0D",
        "console_text": "#C9CDD6", "on_accent": "#0B0D11", "chip_ok": "#0A1F14",
        "chip_err": "#2A1212", "danger": "#2A1212", "danger_hover": "#3A1A1A",
    },
    "light": {
        "bg": "#F2F5F3", "surface": "#FFFFFF", "surface2": "#E6EBE8", "border": "#CBD3CE",
        "text": "#15191B", "muted": "#5C6761", "accent": "#0E9F7E", "accent_hover": "#0B8A6D",
        "ok": "#007A3D", "err": "#B3261E", "sidebar": "#E9EEEA", "console_bg": "#F7F9F8",
        "console_text": "#3A4340", "on_accent": "#FFFFFF", "chip_ok": "#DCF5E6",
        "chip_err": "#FBE3E3", "danger": "#FBE3E3", "danger_hover": "#F6D0D0",
    },
}

BG = SURFACE = SURFACE_2 = BORDER = TEXT = MUTED = ACCENT = ACCENT_HOVER = OK = ERR = ""
SIDEBAR = CONSOLE_BG = CONSOLE_TEXT = ON_ACCENT = CHIP_OK_BG = CHIP_ERR_BG = DANGER_BG = DANGER_HOVER = ""


def apply_theme(name):
    global BG, SURFACE, SURFACE_2, BORDER, TEXT, MUTED, ACCENT, ACCENT_HOVER, OK, ERR
    global SIDEBAR, CONSOLE_BG, CONSOLE_TEXT, ON_ACCENT, CHIP_OK_BG, CHIP_ERR_BG, DANGER_BG, DANGER_HOVER
    t = THEMES.get(name, THEMES["dark"])
    BG, SURFACE, SURFACE_2, BORDER = t["bg"], t["surface"], t["surface2"], t["border"]
    TEXT, MUTED, ACCENT, ACCENT_HOVER = t["text"], t["muted"], t["accent"], t["accent_hover"]
    OK, ERR = t["ok"], t["err"]
    SIDEBAR, CONSOLE_BG, CONSOLE_TEXT = t["sidebar"], t["console_bg"], t["console_text"]
    ON_ACCENT, CHIP_OK_BG, CHIP_ERR_BG = t["on_accent"], t["chip_ok"], t["chip_err"]
    DANGER_BG, DANGER_HOVER = t["danger"], t["danger_hover"]


apply_theme("dark")

if IS_WIN:
    F_DISPLAY = ("Bahnschrift", 30, "bold")
    F_SUB = ("Bahnschrift", 12)
    F_NAV = ("Segoe UI", 13)
    F_BODY = ("Segoe UI", 12)
    F_SMALL = ("Segoe UI", 11)
    F_MONO = ("Consolas", 11)
    F_MONO_SMALL = ("Consolas", 10)
else:
    F_DISPLAY = ("DejaVu Sans", 30, "bold")
    F_SUB = ("DejaVu Sans", 12)
    F_NAV = ("DejaVu Sans", 13)
    F_BODY = ("DejaVu Sans", 12)
    F_SMALL = ("DejaVu Sans", 11)
    F_MONO = ("DejaVu Sans Mono", 11)
    F_MONO_SMALL = ("DejaVu Sans Mono", 10)

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

if IS_WIN:
    USER_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "VAULT"
else:
    USER_DIR = Path.home() / ".config" / "vault"
try:
    USER_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    USER_DIR = BASE_DIR
CONFIG_PATH = USER_DIR / "vault_config.json"

DEFAULTS = {
    "pc_dir": str(USER_DIR / "Respaldo"),
    "phone_dir": "/storage/emulated/0",
    "adb_path": "adb",
    "include_data": False,
    "include_hidden": False,
    "extra_excludes": "",
    "date_filter": "",
    "category": "Todo",
}

CATEGORIES = {
    "Todo": {"exts": None, "desc": "Todos los archivos del teléfono, excepto las exclusiones seguras (caches, LOST.DIR, stickers de WhatsApp, etc.)."},
    "Fotos": {"exts": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".svg"}, "desc": "Todas las imágenes del teléfono, de cualquier carpeta: .jpg, .png, .gif, .webp, .heic..."},
    "Videos": {"exts": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".3gp", ".m4v"}, "desc": "Todos los videos del teléfono, de cualquier carpeta: .mp4, .mkv, .avi, .mov..."},
    "Música": {"exts": {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".opus"}, "desc": "Toda la música y audios del teléfono, de cualquier carpeta: .mp3, .flac, .wav..."},
    "Documentos": {"exts": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"}, "desc": "Documentos y archivos de texto: .pdf, .docx, .xlsx, .txt, .md..."},
    "Comprimidos": {"exts": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}, "desc": "Archivos comprimidos: .zip, .rar, .7z, .tar, .gz..."},
    "APKs": {"exts": {".apk"}, "desc": "Solo instaladores de apps: archivos .apk de cualquier carpeta."},
}

EXCL_DIRS = {
    "Android/data", "Android/obb", "Android/obj",
    "cache", "code_cache", "Caches", "cachefiles",
    "LOST.DIR",
    ".thumbnails", "thumbnails", ".Trash", "trash", ".recycle", "Recycle",
    "WhatsApp Stickers", "WhatsApp Sticker Packs",
    "WhatsApp Backup Excluded Stickers",
    "WhatsApp AI Media", "WhatsApp Bug Report Attachments",
}


def load_config():
    cfg = dict(DEFAULTS)
    try:
        old = BASE_DIR / "vault_config.json"
        if old.exists() and not CONFIG_PATH.exists():
            cfg.update(json.loads(old.read_text(encoding="utf-8")))
            try:
                old.rename(CONFIG_PATH)
            except OSError:
                pass
        elif CONFIG_PATH.exists():
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False


class ADB:
    def __init__(self, path="adb"):
        self.path = path
        self._find_method_cached = None

    def run(self, args, timeout=None):
        return subprocess.run([self.path] + args, capture_output=True, text=True,
                              encoding="utf-8", errors="ignore", timeout=timeout,
                              creationflags=NO_WINDOW)

    def shell(self, cmd, timeout=None):
        return self.run(["shell", cmd], timeout=timeout)

    def get_state(self):
        try:
            r = self.run(["get-state"], timeout=10)
            return "device" in r.stdout
        except Exception:
            return False

    def device_info(self):
        info = {}
        try:
            info["modelo"] = self.shell("getprop ro.product.model").stdout.strip()
        except Exception:
            info["modelo"] = "?"
        try:
            info["android"] = self.shell("getprop ro.build.version.release").stdout.strip()
        except Exception:
            info["android"] = "?"
        try:
            bat = self.shell("dumpsys battery").stdout
            for line in bat.splitlines():
                line = line.strip()
                if line.startswith("level:"):
                    info["bateria"] = line.split(":")[1].strip() + "%"
                    break
            else:
                info["bateria"] = "?"
        except Exception:
            info["bateria"] = "?"
        try:
            df = self.shell("df -h /storage/emulated/0").stdout
            for line in df.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    info["almacenamiento"] = f"{parts[3]} libres"
                    break
            else:
                info["almacenamiento"] = "?"
        except Exception:
            info["almacenamiento"] = "?"
        try:
            ip = self.shell("getprop dhcp.wlan0.ipaddress").stdout.strip()
            if not ip:
                ip_out = self.shell("ip -f inet addr show wlan0").stdout
                for line in ip_out.splitlines():
                    if "inet " in line:
                        ip = line.split()[1].split("/")[0]
                        break
            info["ip"] = ip or "?"
        except Exception:
            info["ip"] = "?"
        try:
            mem = self.shell("cat /proc/meminfo").stdout
            total = avail = 0
            for line in mem.splitlines():
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail = int(line.split()[1])
            info["ram"] = f"{avail / 1048576:.1f}G libres de {total / 1048576:.1f}G" if total else "?"
        except Exception:
            info["ram"] = "?"
        return info

    def _find_method(self):
        if self._find_method_cached:
            return self._find_method_cached
        method = "ls"
        for name, cmd in (
            ("printf", "find /system -maxdepth 1 -type f -printf '%s|%T@|%p\\n'"),
            ("stat", "find /system -maxdepth 1 -type f -exec stat -c '%s|%Y|%n' {} +"),
        ):
            try:
                r = self.shell(cmd)
            except Exception:
                continue
            if "|" in r.stdout:
                method = name
                break
        self._find_method_cached = method
        return method

    def _ls_find(self, phone_dir):
        r = self.shell(f"ls -laR '{phone_dir}'")
        entries = []
        cur_dir = None
        for ln in r.stdout.splitlines():
            ln = ln.rstrip()
            if ln.endswith(":") and not ln.startswith("total") and not ln.startswith(" "):
                cur_dir = ln[:-1]
                continue
            parts = ln.split()
            if len(parts) < 8 or not parts[0].startswith("-"):
                continue
            name = " ".join(parts[7:])
            if name in (".", ".."):
                continue
            size = parts[4]
            try:
                mtime = int(datetime.datetime.strptime(parts[5] + " " + parts[6], "%Y-%m-%d %H:%M").timestamp())
            except ValueError:
                mtime = 0
            path = (cur_dir.rstrip("/") + "/" + name) if cur_dir else name
            entries.append(f"{size}|{mtime}|{path}")
        return entries

    def find_files(self, phone_dir, include_data, include_hidden, min_ts, exts, extra_excl=None):
        tokens = EXCL_DIRS | set(extra_excl or [])
        method = self._find_method()
        if method == "printf":
            r = self.shell(f"find '{phone_dir}' -type f -printf '%s|%T@|%p\\n'")
            lines = r.stdout.splitlines()
        elif method == "stat":
            r = self.shell(f"find '{phone_dir}' -type f -exec stat -c '%s|%Y|%n' {{}} +")
            lines = r.stdout.splitlines()
        else:
            lines = self._ls_find(phone_dir)
        archivos = []
        for line in lines:
            if line.count("|") < 2:
                continue
            size_s, ts_s, path = line.split("|", 2)
            try:
                f_size = int(size_s)
                f_ts = float(ts_s)
            except ValueError:
                continue
            if (not include_data and "/Android/data" in path) or f_ts < min_ts:
                continue
            if ADB._is_excluded(path, tokens):
                continue
            if not include_hidden:
                rel = path.replace(phone_dir + "/", "")
                if any(seg.startswith(".") for seg in rel.split("/")):
                    continue
            if exts and Path(path).suffix.lower() not in exts:
                continue
            archivos.append((f_ts, f_size, path))
        archivos.sort(key=lambda x: x[0])
        return archivos

    @staticmethod
    def _is_excluded(path, tokens=None):
        p = path.replace("\\", "/")
        for token in tokens or EXCL_DIRS:
            if f"/{token}/" in f"/{p}/":
                return True
        return False

    @staticmethod
    def _win_path(p):
        if IS_WIN and len(str(p)) > 240:
            return "\\\\?\\" + str(Path(p).resolve())
        return str(p)

    def pull(self, remote, local):
        return subprocess.run([self.path, "pull", remote, ADB._win_path(local)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600,
                              creationflags=NO_WINDOW)

    def push(self, local, remote):
        return subprocess.run([self.path, "push", ADB._win_path(local), remote],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600,
                              creationflags=NO_WINDOW)

    def screencap(self, dest):
        try:
            r = self.shell("screencap -p /sdcard/_vault_shot.png")
            if r.returncode != 0:
                return False
            r2 = self.pull("/sdcard/_vault_shot.png", dest)
            self.shell("rm -f /sdcard/_vault_shot.png")
            return r2.returncode == 0
        except Exception:
            return False

    def exec_custom(self, cmd_text):
        return subprocess.run(cmd_text, shell=True, capture_output=True, text=True,
                              encoding="utf-8", errors="ignore", creationflags=NO_WINDOW)


def safe_thread(fn):
    def wrapper(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except Exception as e:
            try:
                self._ui_queue.put(("set_busy", False))
                self._spinner_stop()
                self._tlog(f"[-] Error: {e}")
            except Exception:
                pass
    return wrapper


class VaultApp(ctk.CTk):
    def __init__(self):
        self._cancel_requested = False
        self._ui_queue = queue.Queue()
        self._log_fh = None
        self._log_path = None
        self._console = None
        self._busy = False
        self._current_view = None
        self.config = load_config()
        apply_theme(self.config.get("theme", "dark"))
        ctk.set_appearance_mode(self.config.get("theme", "dark"))
        self.adb = ADB(self.config.get("adb_path", "adb"))

        super().__init__()

        self.title(f"{APP_NAME} — Respaldo ADB")
        self.geometry("1080x680")
        self.minsize(960, 600)
        self.configure(fg_color=BG)

        try:
            if IS_WIN:
                ico = BASE_DIR / "vault.ico"
                if ico.exists():
                    self.iconbitmap(str(ico))
            else:
                png = BASE_DIR / "vault.png"
                if png.exists():
                    from tkinter import PhotoImage
                    self.iconphoto(True, PhotoImage(file=str(png)))
        except Exception:
            pass

        self._build_sidebar()
        self._build_main()
        self.show_view("respaldo")

        self.after(80, self._maximize)
        self.after(300, self.refresh_device_status)
        self.after(600, self._check_adb_binary)
        self.after(100, self._poll_ui_queue)

    def _check_adb_binary(self):
        path = self.config.get("adb_path", "adb")
        found = os.path.isfile(path) if os.sep in path or "/" in path else shutil.which(path) is not None
        if found:
            return
        ok = messagebox.askyesno(
            "VAULT",
            "No se encontró ADB en tu sistema.\n\n"
            "ADB es la herramienta gratuita de Google que VAULT usa para hablar con tu teléfono.\n\n"
            "¿Quieres abrir la página para descargarla?",
        )
        if ok:
            webbrowser.open("https://developer.android.com/tools/releases/platform-tools")

    def _maximize(self):
        try:
            self.state("zoomed")
        except Exception:
            pass

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=SIDEBAR, width=212, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        try:
            logo_png = BASE_DIR / "vault.png"
            if logo_png.exists():
                from PIL import Image
                logo_img = ctk.CTkImage(light_image=Image.open(logo_png), dark_image=Image.open(logo_png), size=(44, 44))
                ctk.CTkLabel(self.sidebar, text="", image=logo_img).pack(pady=(26, 0))
        except Exception:
            pass

        logo = ctk.CTkLabel(self.sidebar, text=APP_NAME, font=F_DISPLAY, text_color=ACCENT)
        logo.pack(pady=(16 if (BASE_DIR / "vault.png").exists() else 30, 0))

        sub = ctk.CTkLabel(self.sidebar, text="Respaldo de emergencia · sin root", font=F_SUB, text_color=MUTED)
        sub.pack(pady=(2, 26))

        self.nav_btns = {}
        for key, label in (("respaldo", "Respaldo"), ("restaurar", "Restaurar"),
                           ("conexion", "Conexión"), ("apps", "Apps"),
                           ("explorador", "Explorador"), ("comandos", "Comandos"),
                           ("archivo", "Archivo"), ("ajustes", "Ajustes"),
                           ("acerca", "Acerca de")):
            b = ctk.CTkButton(self.sidebar, text=label, command=lambda k=key: self.show_view(k),
                              font=F_NAV, fg_color="transparent", text_color=TEXT,
                              hover_color=SURFACE_2, corner_radius=6, height=34, anchor="w")
            b.pack(fill="x", padx=14, pady=2)
            self.nav_btns[key] = b

        self.dev_frame = ctk.CTkFrame(self.sidebar, fg_color=SURFACE, corner_radius=8,
                                      border_width=1, border_color=BORDER)
        self.dev_frame.pack(side="bottom", fill="x", padx=14, pady=(10, 10))

        dev_title = ctk.CTkLabel(self.dev_frame, text="DISPOSITIVO", font=F_MONO_SMALL,
                                 text_color=MUTED, anchor="w")
        dev_title.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_dev_model = ctk.CTkLabel(self.dev_frame, text="—", font=F_SMALL,
                                          text_color=TEXT, anchor="w")
        self.lbl_dev_model.pack(fill="x", padx=12)
        self.lbl_dev_bat = ctk.CTkLabel(self.dev_frame, text="", font=F_SMALL,
                                        text_color=MUTED, anchor="w")
        self.lbl_dev_bat.pack(fill="x", padx=12)
        self.lbl_dev_storage = ctk.CTkLabel(self.dev_frame, text="", font=F_SMALL,
                                            text_color=MUTED, anchor="w")
        self.lbl_dev_storage.pack(fill="x", padx=12)
        self.lbl_dev_ip = ctk.CTkLabel(self.dev_frame, text="", font=F_SMALL,
                                       text_color=MUTED, anchor="w")
        self.lbl_dev_ip.pack(fill="x", padx=12)
        self.lbl_dev_ram = ctk.CTkLabel(self.dev_frame, text="", font=F_SMALL,
                                        text_color=MUTED, anchor="w")
        self.lbl_dev_ram.pack(fill="x", padx=12, pady=(0, 10))

        self.status_chip = ctk.CTkLabel(self.sidebar, text="Teléfono: verificando...", font=F_MONO_SMALL,
                                        text_color=MUTED, fg_color=SURFACE_2, corner_radius=4, height=26)
        self.status_chip.pack(side="bottom", fill="x", padx=14, pady=(0, 14))

    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

    def show_view(self, key):
        self._current_view = key
        for w in self.main.winfo_children():
            w.destroy()
        self._console = None
        builders = {
            "respaldo": self._view_respaldo,
            "restaurar": self._view_restaurar,
            "conexion": self._view_conexion,
            "apps": self._view_apps,
            "explorador": self._view_explorador,
            "comandos": self._view_comandos,
            "archivo": self._view_archivo,
            "ajustes": self._view_ajustes,
            "acerca": self._view_acerca,
        }
        builders[key]()
        self._apply_busy_state()
        for k, b in self.nav_btns.items():
            active = k == key
            b.configure(fg_color=ACCENT if active else "transparent",
                        text_color=ON_ACCENT if active else TEXT,
                        hover_color=ACCENT_HOVER if active else SURFACE_2)

    def _card(self, parent=None):
        return ctk.CTkFrame(parent or self.main, fg_color=SURFACE, corner_radius=10,
                            border_width=1, border_color=BORDER)

    def _view_header(self, title, desc):
        t = ctk.CTkLabel(self.main, text=title, font=F_DISPLAY, text_color=TEXT, anchor="w")
        t.pack(fill="x", padx=34, pady=(30, 0))
        d = ctk.CTkLabel(self.main, text=desc, font=F_BODY, text_color=MUTED, anchor="w")
        d.pack(fill="x", padx=34, pady=(2, 18))

    def _view_respaldo(self):
        self._view_header("Respaldo", "Copia los archivos del teléfono a tu PC.")
        card = self._card()
        card.pack(fill="x", padx=34, pady=(0, 12))

        self.include_data_var = ctk.BooleanVar(value=self.config.get("include_data", False))
        ctk.CTkCheckBox(card, text="Incluir carpeta Android/data", variable=self.include_data_var,
                        font=F_BODY, text_color=TEXT, fg_color=SURFACE_2,
                        border_color=BORDER, hover_color=ACCENT).pack(anchor="w", padx=20, pady=(16, 10))

        self.include_hidden_var = ctk.BooleanVar(value=self.config.get("include_hidden", False))
        ctk.CTkCheckBox(card, text="Incluir archivos ocultos (carpetas que empiezan con '.')",
                        variable=self.include_hidden_var, font=F_BODY, text_color=TEXT, fg_color=SURFACE_2,
                        border_color=BORDER, hover_color=ACCENT).pack(anchor="w", padx=20, pady=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(row, text="Filtrar desde fecha (YYYY-MM-DD):", font=F_BODY,
                     text_color=MUTED).pack(side="left", padx=(0, 12))
        self.entry_date = ctk.CTkEntry(row, width=150, height=34, corner_radius=6,
                                       fg_color=SURFACE_2, border_color=BORDER,
                                       text_color=TEXT, font=F_MONO)
        self.entry_date.insert(0, self.config.get("date_filter", ""))
        self.entry_date.pack(side="left")

        cat_frame = ctk.CTkFrame(card, fg_color="transparent")
        cat_frame.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(cat_frame, text="¿Qué quieres respaldar?", font=F_BODY,
                     text_color=TEXT, anchor="w").pack(fill="x", pady=(0, 8))

        grid = ctk.CTkFrame(cat_frame, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self._cat_btns = {}
        self._cat_key = self.config.get("category", "Todo")
        if self._cat_key not in CATEGORIES:
            self._cat_key = "Todo"
        for i, key in enumerate(CATEGORIES.keys()):
            b = ctk.CTkButton(grid, text=key, command=lambda k=key: self._set_category(k),
                              font=F_SMALL, corner_radius=6, height=30, border_width=1,
                              fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                              border_color=BORDER)
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, 8 if i % 2 == 0 else 0), pady=3)
            self._cat_btns[key] = b

        self.lbl_cat_desc = ctk.CTkLabel(cat_frame, text="", font=F_SMALL, text_color=MUTED,
                                         anchor="w", wraplength=600, justify="left")
        self.lbl_cat_desc.pack(fill="x", pady=(6, 0))
        self._set_category(self._cat_key)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(14, 16))

        self.btn_backup = ctk.CTkButton(btn_row, text="Iniciar respaldo", command=self.start_backup,
                                        font=F_NAV, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                        text_color=ON_ACCENT, corner_radius=6, height=42, width=190)
        self.btn_backup.pack(side="left")

        ctk.CTkButton(btn_row, text="Respaldo de emergencia", command=self.emergency_backup,
                      font=F_NAV, fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                      corner_radius=6, height=42, width=200).pack(side="left", padx=(12, 0))

        hint = ctk.CTkLabel(card, text="Iniciar respaldo = usa lo que elegiste arriba (categoría, fecha, opciones).  "
                                       "Respaldo de emergencia = copia TODO sin filtros, ideal antes de un formateo.",
                            font=F_SMALL, text_color=MUTED, anchor="w", wraplength=760, justify="left")
        hint.pack(fill="x", padx=20, pady=(0, 16))

        self.btn_cancel = ctk.CTkButton(btn_row, text="Cancelar", command=self.request_cancel,
                                        font=F_NAV, fg_color=DANGER_BG, hover_color=DANGER_HOVER,
                                        text_color=ERR, corner_radius=6, height=42, width=130,
                                        state="disabled")
        self.btn_cancel.pack(side="left", padx=(12, 0))

        self.progress = ctk.CTkProgressBar(self.main, height=6, corner_radius=4,
                                           fg_color=SURFACE_2, progress_color=ACCENT)
        self.progress.pack(fill="x", padx=34, pady=(0, 4))
        self.progress.set(0)

        self.lbl_progress = ctk.CTkLabel(self.main, text="", font=F_MONO, text_color=ACCENT, anchor="w")
        self.lbl_progress.pack(fill="x", padx=34, pady=(0, 12))

        self.console = ctk.CTkTextbox(self.main, fg_color=CONSOLE_BG, text_color=CONSOLE_TEXT,
                                      font=F_MONO, wrap="word", corner_radius=10,
                                      border_width=1, border_color=BORDER, padx=16, pady=16)
        self.console.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._console = self.console

    def _view_restaurar(self):
        self._view_header("Restaurar", "Devuelve los archivos del respaldo al teléfono.")
        card = self._card()
        card.pack(fill="x", padx=34, pady=(0, 12))

        self.include_data_var = ctk.BooleanVar(value=self.config.get("include_data", False))
        ctk.CTkCheckBox(card, text="Incluir carpeta Android/data", variable=self.include_data_var,
                        font=F_BODY, text_color=TEXT, fg_color=SURFACE_2,
                        border_color=BORDER, hover_color=ACCENT).pack(anchor="w", padx=20, pady=(16, 14))

        warn = ctk.CTkFrame(card, fg_color=DANGER_BG, corner_radius=8)
        warn.pack(fill="x", padx=20, pady=(0, 14))
        ctk.CTkLabel(warn, text="Los archivos del teléfono con el mismo nombre serán REEMPLAZADOS. "
                                "Esto restaura archivos sueltos (fotos, documentos...), NO apps ni ajustes.",
                     font=F_SMALL, text_color=ERR, anchor="w", wraplength=700, justify="left").pack(fill="x", padx=14, pady=10)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        self.btn_restore = ctk.CTkButton(btn_row, text="Iniciar restauración", command=self.start_restore,
                                         font=F_NAV, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                         text_color=ON_ACCENT, corner_radius=6, height=42, width=190)
        self.btn_restore.pack(side="left")

        self.btn_cancel = ctk.CTkButton(btn_row, text="Cancelar", command=self.request_cancel,
                                        font=F_NAV, fg_color=DANGER_BG, hover_color=DANGER_HOVER,
                                        text_color=ERR, corner_radius=6, height=42, width=130,
                                        state="disabled")
        self.btn_cancel.pack(side="left", padx=(12, 0))

        self.progress = ctk.CTkProgressBar(self.main, height=6, corner_radius=4,
                                           fg_color=SURFACE_2, progress_color=ACCENT)
        self.progress.pack(fill="x", padx=34, pady=(0, 4))
        self.progress.set(0)

        self.lbl_progress = ctk.CTkLabel(self.main, text="", font=F_MONO, text_color=ACCENT, anchor="w")
        self.lbl_progress.pack(fill="x", padx=34, pady=(0, 12))

        self.console = ctk.CTkTextbox(self.main, fg_color=CONSOLE_BG, text_color=CONSOLE_TEXT,
                                      font=F_MONO, wrap="word", corner_radius=10,
                                      border_width=1, border_color=BORDER, padx=16, pady=16)
        self.console.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._console = self.console

    def _set_category(self, key):
        self._cat_key = key
        for k, b in self._cat_btns.items():
            active = k == key
            b.configure(fg_color=ACCENT if active else SURFACE_2,
                        text_color=ON_ACCENT if active else TEXT,
                        border_color=ACCENT if active else BORDER,
                        hover_color=ACCENT_HOVER if active else BORDER)
        self.lbl_cat_desc.configure(text=CATEGORIES[key]["desc"])

    def _view_conexion(self):
        self._view_header("Conexión", "Conecta tu teléfono por USB o WiFi.")

        card = self._card()
        card.pack(fill="x", padx=34, pady=(0, 12))

        p1 = ctk.CTkFrame(card, fg_color="transparent")
        p1.pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(p1, text="1. Habilitar ADB por WiFi", font=F_NAV, text_color=TEXT, anchor="w").pack(side="left")
        ctk.CTkButton(p1, text="Habilitar (tcpip 5555)", command=self.wifi_enable, font=F_NAV,
                      fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                      corner_radius=6, height=34).pack(side="right")
        ctk.CTkLabel(card, text="Con el teléfono conectado por USB, habilita el modo WiFi. Solo hace falta una vez por reinicio del teléfono.",
                     font=F_SMALL, text_color=MUTED, anchor="w", wraplength=620, justify="left").pack(fill="x", padx=20, pady=(0, 6))

        p2 = ctk.CTkFrame(card, fg_color="transparent")
        p2.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(p2, text="2. Vincular (Android 11+)", font=F_NAV, text_color=TEXT, anchor="w").pack(side="left")
        ctk.CTkLabel(p2, text="Ajustes → Opciones de desarrollador → Depuración inalámbrica → Vincular con código",
                     font=F_SMALL, text_color=MUTED, anchor="e").pack(side="right")

        p2row = ctk.CTkFrame(card, fg_color="transparent")
        p2row.pack(fill="x", padx=20, pady=(6, 4))
        self.ent_pair_ip = ctk.CTkEntry(p2row, placeholder_text="IP:PUERTO (ej: 192.168.0.5:43117)", fg_color=SURFACE_2,
                                        border_color=BORDER, corner_radius=6, height=36, text_color=TEXT, font=F_MONO)
        self.ent_pair_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ent_pair_code = ctk.CTkEntry(p2row, placeholder_text="Código 6 dígitos", width=150, fg_color=SURFACE_2,
                                          border_color=BORDER, corner_radius=6, height=36, text_color=TEXT, font=F_MONO)
        self.ent_pair_code.pack(side="left", padx=(0, 10))
        ctk.CTkButton(p2row, text="Vincular", command=self.wifi_pair, font=F_NAV,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                      corner_radius=6, height=36, width=100).pack(side="left")

        p3 = ctk.CTkFrame(card, fg_color="transparent")
        p3.pack(fill="x", padx=20, pady=(10, 4))
        ctk.CTkLabel(p3, text="3. Conectar por WiFi", font=F_NAV, text_color=TEXT, anchor="w").pack(side="left")

        p3row = ctk.CTkFrame(card, fg_color="transparent")
        p3row.pack(fill="x", padx=20, pady=(6, 16))
        self.ent_conn_ip = ctk.CTkEntry(p3row, placeholder_text="IP del teléfono (ej: 192.168.0.5)", fg_color=SURFACE_2,
                                        border_color=BORDER, corner_radius=6, height=36, text_color=TEXT, font=F_MONO)
        self.ent_conn_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(p3row, text="Conectar", command=self.wifi_connect, font=F_NAV,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
                      corner_radius=6, height=36, width=110).pack(side="left")

        self.console = ctk.CTkTextbox(self.main, fg_color=CONSOLE_BG, text_color=CONSOLE_TEXT,
                                      font=F_MONO, wrap="word", corner_radius=10,
                                      border_width=1, border_color=BORDER, padx=16, pady=16)
        self.console.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._console = self.console

    def wifi_enable(self):
        threading.Thread(target=self._wifi_enable, daemon=True).start()

    @safe_thread
    def _wifi_enable(self):
        self._tlog("[*] Habilitando ADB por WiFi (tcpip 5555)...")
        r = self.adb.run(["tcpip", "5555"])
        if r.returncode == 0:
            self._tlog("[+] Listo. Desconecta el cable y usa 'Conectar por WiFi'.")
        else:
            self._tlog("[-] Falló. ¿Está el teléfono conectado por USB y autorizado?")

    def wifi_pair(self):
        ip = self.ent_pair_ip.get().strip()
        code = self.ent_pair_code.get().strip()
        if not ip or not code:
            self.log("[-] Ingresa IP:PUERTO y el código de 6 dígitos.")
            return
        threading.Thread(target=self._wifi_pair, args=(ip, code), daemon=True).start()

    @safe_thread
    def _wifi_pair(self, ip, code):
        self._tlog(f"[*] Vinculando con {ip}...")
        r = self.adb.run(["pair", ip, code], timeout=30)
        if r.returncode == 0:
            self._tlog("[+] Vinculado correctamente.")
        else:
            self._tlog(f"[-] Falló la vinculación: {r.stdout.strip() or r.stderr.strip()}")

    def wifi_connect(self):
        ip = self.ent_conn_ip.get().strip()
        if not ip:
            self.log("[-] Ingresa la IP del teléfono.")
            return
        threading.Thread(target=self._wifi_connect, args=(ip,), daemon=True).start()

    @safe_thread
    def _wifi_connect(self, ip):
        self._tlog(f"[*] Conectando a {ip}:5555...")
        r = self.adb.run(["connect", f"{ip}:5555"], timeout=30)
        if r.returncode == 0 and "connected" in r.stdout:
            self._tlog("[+] Conectado por WiFi.")
            self.refresh_device_status()
        else:
            self._tlog(f"[-] No se pudo conectar: {r.stdout.strip() or r.stderr.strip()}")

    def _view_apps(self):
        self._view_header("Apps", "Apps de terceros instaladas en el teléfono.")
        top = ctk.CTkFrame(self.main, fg_color="transparent")
        top.pack(fill="x", padx=34, pady=(0, 10))
        ctk.CTkButton(top, text="Actualizar lista", command=self.load_apps, font=F_NAV,
                      fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                      corner_radius=6, height=34, width=150).pack(side="left")
        self.lbl_apps_status = ctk.CTkLabel(top, text="", font=F_SMALL, text_color=MUTED)
        self.lbl_apps_status.pack(side="left", padx=14)
        self.apps_frame = ctk.CTkScrollableFrame(self.main, fg_color=SURFACE, corner_radius=10,
                                                 border_width=1, border_color=BORDER)
        self.apps_frame.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self.load_apps()

    def load_apps(self):
        for w in self.apps_frame.winfo_children():
            w.destroy()
        self._spinner_start(self.apps_frame)
        threading.Thread(target=self._load_apps, daemon=True).start()

    @safe_thread
    def _load_apps(self):
        if not self.adb.get_state():
            self._ui_queue.put(("apps", None))
            return
        r = self.adb.shell("pm list packages -3")
        pkgs = sorted(ln.replace("package:", "").strip() for ln in r.stdout.splitlines() if ln.strip())
        self._ui_queue.put(("apps", pkgs))

    def _render_apps(self, pkgs):
        for w in self.apps_frame.winfo_children():
            w.destroy()
        if pkgs is None:
            ctk.CTkLabel(self.apps_frame, text="No hay dispositivo conectado.",
                         font=F_SMALL, text_color=MUTED).pack(pady=20)
            self.lbl_apps_status.configure(text="")
            return
        if not pkgs:
            ctk.CTkLabel(self.apps_frame, text="No hay apps de terceros instaladas.",
                         font=F_SMALL, text_color=MUTED).pack(pady=20)
            self.lbl_apps_status.configure(text="")
            return
        self.lbl_apps_status.configure(text=f"{len(pkgs)} apps de terceros")
        for pkg in pkgs:
            row = ctk.CTkFrame(self.apps_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=pkg, font=F_MONO_SMALL, text_color=TEXT,
                         anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Extraer APK", width=100, height=30, font=F_SMALL,
                          command=lambda p=pkg: self.extract_apk(p), fg_color=SURFACE_2,
                          hover_color=BORDER, text_color=TEXT, corner_radius=6).pack(side="left", padx=2)
            ctk.CTkButton(row, text="Abrir app", width=80, height=30, font=F_SMALL,
                          command=lambda p=pkg: self.open_app(p), fg_color=SURFACE_2,
                          hover_color=BORDER, text_color=TEXT, corner_radius=6).pack(side="left", padx=2)
            ctk.CTkButton(row, text="Detener app", width=90, height=30, font=F_SMALL,
                          command=lambda p=pkg: self.stop_app(p), fg_color=DANGER_BG,
                          hover_color=DANGER_HOVER, text_color=ERR, corner_radius=6).pack(side="left", padx=2)

    def extract_apk(self, pkg):
        threading.Thread(target=self._extract_apk, args=(pkg,), daemon=True).start()

    @safe_thread
    def _extract_apk(self, pkg):
        r = self.adb.shell(f"pm path {pkg}")
        paths = [ln.replace("package:", "").strip() for ln in r.stdout.splitlines() if ln.strip()]
        if not paths:
            self._ui_queue.put(("apps_status", f"No se encontró APK para {pkg}"))
            return
        apk_dir = os.path.join(self.config.get("pc_dir", ""), "APKs")
        os.makedirs(apk_dir, exist_ok=True)
        for i, ap in enumerate(paths, 1):
            dest = os.path.join(apk_dir, f"{pkg}{'_' + str(i) if len(paths) > 1 else ''}.apk")
            self._ui_queue.put(("apps_status", f"Extrayendo APK de {pkg}..."))
            r2 = self.adb.pull(ap, dest)
            if r2.returncode == 0:
                self._ui_queue.put(("apps_status", f"APK de {pkg} guardado en Respaldo/APKs/"))
            else:
                self._ui_queue.put(("apps_status", f"Falló la extracción de {pkg}"))

    def open_app(self, pkg):
        threading.Thread(target=self._open_app, args=(pkg,), daemon=True).start()

    @safe_thread
    def _open_app(self, pkg):
        ok = self.adb.shell(f"monkey -p {pkg} 1").returncode == 0
        self._ui_queue.put(("apps_status", f"{pkg} abierta." if ok else f"No se pudo abrir {pkg}"))

    def stop_app(self, pkg):
        threading.Thread(target=self._stop_app, args=(pkg,), daemon=True).start()

    @safe_thread
    def _stop_app(self, pkg):
        ok = self.adb.shell(f"am force-stop {pkg}").returncode == 0
        self._ui_queue.put(("apps_status", f"{pkg} detenida." if ok else f"No se pudo detener {pkg}"))

    def _view_explorador(self):
        self._view_header("Explorador", "Navega los archivos del teléfono.")
        nav = ctk.CTkFrame(self.main, fg_color="transparent")
        nav.pack(fill="x", padx=34, pady=(0, 10))
        self.entry_path = ctk.CTkEntry(nav, fg_color=SURFACE, border_color=BORDER,
                                       corner_radius=6, height=36, text_color=TEXT, font=F_MONO)
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_path.bind("<Return>", lambda e: self.explorer_go())
        for label, cmd in (("Ir", self.explorer_go), ("Subir", self.explorer_up),
                           ("Nueva carpeta", self.explorer_mkdir), ("Subir archivo", self.explorer_upload)):
            ctk.CTkButton(nav, text=label, command=cmd, font=F_NAV, fg_color=SURFACE_2,
                          hover_color=BORDER, text_color=TEXT, corner_radius=6,
                          height=36, width=118).pack(side="left", padx=(0, 8))
        self.explorer_frame = ctk.CTkScrollableFrame(self.main, fg_color=SURFACE, corner_radius=10,
                                                     border_width=1, border_color=BORDER)
        self.explorer_frame.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._explorer_path = self.config.get("phone_dir", "/storage/emulated/0")
        self.explorer_go()

    def explorer_go(self):
        path = self.entry_path.get().strip() or self._explorer_path
        self._explorer_path = path.rstrip("/") or "/"
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, self._explorer_path)
        for w in self.explorer_frame.winfo_children():
            w.destroy()
        self._spinner_start(self.explorer_frame)
        threading.Thread(target=self._explorer_ls, daemon=True).start()

    @safe_thread
    def _explorer_ls(self):
        path = self._explorer_path.replace("'", "'\\''")
        r = self.adb.shell(f"ls -la '{path}'")
        entries = []
        for ln in r.stdout.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("total"):
                continue
            parts = ln.split()
            if len(parts) < 8:
                continue
            perms = parts[0]
            if perms.startswith("d") or perms.startswith("-") or perms.startswith("l"):
                name = " ".join(parts[7:])
                if name in (".", ".."):
                    continue
                kind = "d" if perms.startswith("d") else "f"
                size = parts[4] if len(parts) > 4 else "0"
                entries.append((kind, size, name))
        entries.sort(key=lambda e: (e[0] != "d", e[2].lower()))
        self._ui_queue.put(("explorer", entries))

    def _render_explorer(self, entries):
        for w in self.explorer_frame.winfo_children():
            w.destroy()
        if not entries:
            ctk.CTkLabel(self.explorer_frame, text="Carpeta vacía.", font=F_SMALL,
                         text_color=MUTED).pack(pady=20)
            return
        for kind, size, name in entries:
            row = ctk.CTkFrame(self.explorer_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            icon = "DIR " if kind == "d" else "    "
            ctk.CTkLabel(row, text=icon + name, font=F_MONO_SMALL,
                         text_color=ACCENT if kind == "d" else TEXT,
                         anchor="w").pack(side="left", fill="x", expand=True)
            size_txt = "—" if kind == "d" else self._fmt_size(int(size) if size.isdigit() else 0)
            ctk.CTkLabel(row, text=size_txt, font=F_MONO_SMALL, text_color=MUTED,
                         width=90, anchor="e").pack(side="left", padx=6)
            full = self._explorer_path.rstrip("/") + "/" + name
            if kind == "d":
                ctk.CTkButton(row, text="Entrar", width=56, height=30, font=F_SMALL,
                              command=lambda p=full: self.explorer_enter(p), fg_color=SURFACE_2,
                              hover_color=BORDER, text_color=TEXT, corner_radius=6).pack(side="left", padx=2)
            else:
                ctk.CTkButton(row, text="Bajar", width=56, height=30, font=F_SMALL,
                              command=lambda p=full: self.explorer_download(p), fg_color=SURFACE_2,
                              hover_color=BORDER, text_color=TEXT, corner_radius=6).pack(side="left", padx=2)
            ctk.CTkButton(row, text="Borrar", width=60, height=30, font=F_SMALL,
                          command=lambda p=full, d=(kind == "d"): self.explorer_delete(p, d),
                          fg_color=DANGER_BG, hover_color=DANGER_HOVER, text_color=ERR,
                          corner_radius=6).pack(side="left", padx=2)

    def _fmt_size(self, n):
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    def explorer_enter(self, path):
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, path)
        self.explorer_go()

    def explorer_up(self):
        parent = os.path.dirname(self._explorer_path)
        if parent and parent != self._explorer_path:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, parent)
            self.explorer_go()

    def explorer_download(self, path):
        threading.Thread(target=self._explorer_download, args=(path,), daemon=True).start()

    @safe_thread
    def _explorer_download(self, path):
        dest = os.path.join(self.config.get("pc_dir", ""), os.path.basename(path))
        self._tlog(f"[*] Bajando {path}...")
        r = self.adb.pull(path, dest)
        self._tlog(f"[+] Guardado en {dest}" if r.returncode == 0 else f"[-] Falló al bajar {path}")

    def explorer_delete(self, path, is_dir):
        if not messagebox.askyesno("Borrar", f"¿Borrar {'la carpeta' if is_dir else 'el archivo'}?\n{path}\n\nNo se puede deshacer."):
            return
        threading.Thread(target=self._explorer_delete, args=(path, is_dir), daemon=True).start()

    @safe_thread
    def _explorer_delete(self, path, is_dir):
        safe = path.replace("'", "'\\''")
        cmd = f"rm -rf '{safe}'" if is_dir else f"rm -f '{safe}'"
        r = self.adb.shell(cmd)
        self._tlog("[+] Borrado." if r.returncode == 0 else f"[-] Falló al borrar {path}")
        self._ui_queue.put(("explorer_reload",))

    def explorer_mkdir(self):
        name = simpledialog.askstring("Nueva carpeta", "Nombre de la carpeta:", parent=self)
        if not name:
            return
        threading.Thread(target=self._explorer_mkdir, args=(name.strip(),), daemon=True).start()

    @safe_thread
    def _explorer_mkdir(self, name):
        if not name:
            return
        safe = name.replace("'", "'\\''")
        path = self._explorer_path.rstrip("/") + "/" + safe
        r = self.adb.shell(f"mkdir -p '{path}'")
        self._tlog("[+] Carpeta creada." if r.returncode == 0 else f"[-] Falló al crear {name}")
        self._ui_queue.put(("explorer_reload",))

    def explorer_upload(self):
        src = filedialog.askopenfilename(parent=self)
        if not src:
            return
        threading.Thread(target=self._explorer_upload, args=(src,), daemon=True).start()

    @safe_thread
    def _explorer_upload(self, src):
        dest = self._explorer_path.rstrip("/") + "/" + os.path.basename(src)
        self._tlog(f"[*] Subiendo {os.path.basename(src)}...")
        r = self.adb.push(src, dest)
        self._tlog("[+] Subido." if r.returncode == 0 else f"[-] Falló al subir {os.path.basename(src)}")
        self._ui_queue.put(("explorer_reload",))

    def _view_comandos(self):
        self._view_header("Comandos", "Terminal ADB y acciones rápidas.")

        quick = self._card()
        quick.pack(fill="x", padx=34, pady=(0, 12))

        quick_row = ctk.CTkFrame(quick, fg_color="transparent")
        quick_row.pack(fill="x", padx=20, pady=16)

        quick_actions = [
            ("Screencap", self.quick_screencap),
            ("Logcat", self.quick_logcat),
            ("Listar apps", self.quick_apps),
            ("Info dispositivo", self.quick_info),
        ]
        for label, cmd in quick_actions:
            b = ctk.CTkButton(quick_row, text=label, command=cmd, font=F_NAV,
                              fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                              corner_radius=6, height=38, width=120)
            b.pack(side="left", padx=(0, 10))

        danger_row = ctk.CTkFrame(quick, fg_color="transparent")
        danger_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(danger_row, text="Reiniciar", command=self.quick_reboot, font=F_NAV,
                      fg_color=DANGER_BG, hover_color=DANGER_HOVER, text_color=ERR,
                      corner_radius=6, height=38, width=120).pack(side="left", padx=(0, 10))
        ctk.CTkButton(danger_row, text="Apagar", command=self.quick_poweroff, font=F_NAV,
                      fg_color=DANGER_BG, hover_color=DANGER_HOVER, text_color=ERR,
                      corner_radius=6, height=38, width=120).pack(side="left")

        lc_row = ctk.CTkFrame(quick, fg_color="transparent")
        lc_row.pack(fill="x", padx=20, pady=(0, 16))
        running = getattr(self, "_logcat_proc", None) is not None
        self.btn_logcat = ctk.CTkButton(lc_row, text="Detener logcat" if running else "Logcat en vivo",
                                        command=self.logcat_stop if running else self.logcat_start,
                                        font=F_NAV, fg_color=ACCENT if running else SURFACE_2,
                                        hover_color=ACCENT_HOVER if running else BORDER,
                                        text_color=ON_ACCENT if running else TEXT,
                                        corner_radius=6, height=34, width=150)
        self.btn_logcat.pack(side="left")

        cmd_row = ctk.CTkFrame(self.main, fg_color="transparent")
        cmd_row.pack(fill="x", padx=34, pady=(0, 10))

        self.entry_cmd = ctk.CTkEntry(cmd_row, placeholder_text="Ej: adb shell pm list packages",
                                      fg_color=SURFACE, border_color=BORDER, corner_radius=6,
                                      height=40, text_color=TEXT, font=F_MONO)
        self.entry_cmd.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_cmd.bind("<Return>", self.execute_custom_cmd)

        self.btn_exec = ctk.CTkButton(cmd_row, text="Ejecutar", command=self.execute_custom_cmd,
                                      font=F_NAV, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                      text_color=ON_ACCENT, corner_radius=6, height=40, width=110)
        self.btn_exec.pack(side="left")

        hint = ctk.CTkLabel(self.main, text="Estos comandos se ejecutan en tu PC. Usa adb shell ... para ejecutar en el teléfono.",
                            font=F_SMALL, text_color=MUTED, anchor="w")
        hint.pack(fill="x", padx=34, pady=(0, 8))

        self.console = ctk.CTkTextbox(self.main, fg_color=CONSOLE_BG, text_color=CONSOLE_TEXT,
                                      font=F_MONO, wrap="word", corner_radius=10,
                                      border_width=1, border_color=BORDER, padx=16, pady=16)
        self.console.pack(fill="both", expand=True, padx=34, pady=(0, 30))
        self._console = self.console

    def _view_archivo(self):
        self._view_header("Archivo", "Estado del respaldo guardado en tu PC.")
        pc_dir = self.config.get("pc_dir", "")

        info = self._card()
        info.pack(fill="x", padx=34, pady=(0, 12))

        self._arch_labels = {}
        rows = [
            ("Ubicación", pc_dir or "—"),
            ("Archivos", "calculando..."),
            ("Tamaño total", "calculando..."),
            ("Último respaldo", "calculando..."),
        ]
        for i, (k, v) in enumerate(rows):
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(12 if i == 0 else 2, 2))
            ctk.CTkLabel(row, text=k, font=F_BODY, text_color=MUTED, width=130, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text=v, font=F_MONO, text_color=TEXT, anchor="w")
            lbl.pack(side="left")
            self._arch_labels[k] = lbl

        self._spinner_start(self.main, "Calculando tamaño del respaldo...")

        btn_row = ctk.CTkFrame(info, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(14, 16))

        ctk.CTkButton(btn_row, text="Abrir carpeta", command=lambda: self.open_folder(pc_dir),
                      font=F_NAV, fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT,
                      corner_radius=6, height=38, width=140).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Borrar respaldo", command=self.delete_backup,
                      font=F_NAV, fg_color=DANGER_BG, hover_color=DANGER_HOVER, text_color=ERR,
                      corner_radius=6, height=38, width=150).pack(side="left")

        hint = ctk.CTkLabel(self.main, text="El respaldo es incremental: cada sesión solo copia lo nuevo o modificado.",
                            font=F_SMALL, text_color=MUTED, anchor="w")
        hint.pack(fill="x", padx=34, pady=(0, 12))

        def worker():
            try:
                total_files = 0
                total_size = 0
                newest = None
                if os.path.isdir(pc_dir):
                    for root, _, fs in os.walk(pc_dir):
                        for f in fs:
                            p = Path(os.path.join(root, f))
                            try:
                                st = p.stat()
                            except OSError:
                                continue
                            total_files += 1
                            total_size += st.st_size
                            if newest is None or st.st_mtime > newest:
                                newest = st.st_mtime
                self._ui_queue.put(("archivo", total_files, total_size, newest))
            except Exception as e:
                self._tlog(f"[-] Error al analizar el respaldo: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _view_ajustes(self):
        self._view_header("Ajustes", "Rutas y configuración de VAULT.")

        card = self._card()
        card.pack(fill="x", padx=34, pady=(0, 12))

        fields = [
            ("Carpeta de respaldo (PC)", "pc_dir"),
            ("Carpeta del teléfono", "phone_dir"),
            ("Ruta de ADB", "adb_path"),
            ("Exclusiones extra (separadas por coma)", "extra_excludes"),
        ]
        self._cfg_entries = {}
        for i, (label, key) in enumerate(fields):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(16 if i == 0 else 10, 0))
            ctk.CTkLabel(row, text=label, font=F_BODY, text_color=MUTED, width=200, anchor="w").pack(side="left")
            e = ctk.CTkEntry(row, fg_color=SURFACE_2, border_color=BORDER, corner_radius=6,
                             height=34, text_color=TEXT, font=F_MONO)
            e.insert(0, self.config.get(key, ""))
            e.pack(side="left", fill="x", expand=True)
            self._cfg_entries[key] = e

        help_txt = ("Separa con comas los nombres de carpeta o archivo que quieras excluir del respaldo y la restauración. "
                    "Ej: DCIM, downloads, backup_old")
        ctk.CTkLabel(card, text=help_txt, font=F_SMALL, text_color=MUTED, anchor="w",
                     wraplength=760).pack(fill="x", padx=20, pady=(8, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(18, 16))

        ctk.CTkButton(btn_row, text="Guardar configuración", command=self.save_settings,
                      font=F_NAV, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color=ON_ACCENT, corner_radius=6, height=40, width=210).pack(side="left")

        card2 = self._card()
        card2.pack(fill="x", padx=34, pady=(0, 12))
        row2 = ctk.CTkFrame(card2, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(row2, text="Apariencia", font=F_BODY, text_color=TEXT, width=200, anchor="w").pack(side="left")
        self._theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        ctk.CTkSwitch(row2, text="Modo claro", variable=self._theme_var, onvalue="light", offvalue="dark",
                      command=self._toggle_theme, font=F_BODY, text_color=TEXT,
                      progress_color=ACCENT, fg_color=SURFACE_2, border_color=BORDER,
                      button_color=ACCENT, button_hover_color=ACCENT_HOVER).pack(side="left")

        ver = ctk.CTkLabel(self.main, text=f"{APP_NAME} {VERSION}", font=F_MONO_SMALL, text_color=MUTED, anchor="w")
        ver.pack(fill="x", padx=34, pady=(0, 30))

    def _toggle_theme(self):
        new = self._theme_var.get()
        self.config["theme"] = new
        save_config(self.config)
        apply_theme(new)
        ctk.set_appearance_mode(new)
        self._rebuild_ui()

    def _rebuild_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._build_sidebar()
        self._build_main()
        self.show_view(self._current_view or "respaldo")
        self.after(300, self.refresh_device_status)

    def _view_acerca(self):
        self._view_header("Acerca de", "VAULT — el respaldo de emergencia sin root.")
        card = self._card()
        card.pack(fill="x", padx=34, pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=24)
        try:
            logo_png = BASE_DIR / "vault.png"
            if logo_png.exists():
                from PIL import Image
                logo_img = ctk.CTkImage(light_image=Image.open(logo_png), dark_image=Image.open(logo_png), size=(96, 96))
                ctk.CTkLabel(inner, text="", image=logo_img).pack(side="left", padx=(0, 24))
        except Exception:
            pass

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(txt, text=f"{APP_NAME} {VERSION}", font=F_DISPLAY, text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(txt, text="Respaldo y restauración de Android por ADB, sin root.",
                     font=F_BODY, text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(txt, text="Hecho por Kael", font=F_BODY, text_color=TEXT, anchor="w").pack(fill="x", pady=(10, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=30, pady=(0, 20))
        ctk.CTkButton(btn_row, text="Ver en GitHub", command=self._open_github,
                      font=F_NAV, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color=ON_ACCENT, corner_radius=6, height=38, width=150).pack(side="left")

        ctk.CTkLabel(self.main, text="Licencia MIT — ver LICENSE junto al programa.",
                     font=F_MONO_SMALL, text_color=MUTED, anchor="w").pack(fill="x", padx=34, pady=(0, 30))

    def _open_github(self):
        webbrowser.open("https://github.com/KaelY22/vault")

    def save_settings(self):
        for key, e in self._cfg_entries.items():
            val = e.get().strip()
            if key == "pc_dir" and not val:
                self.log("[-] La carpeta de respaldo no puede estar vacía.")
                return
            if key == "phone_dir" and not val.startswith("/"):
                self.log("[-] La carpeta del teléfono debe ser una ruta absoluta (ej: /storage/emulated/0).")
                return
            if key == "adb_path" and not val:
                self.log("[-] La ruta de ADB no puede estar vacía.")
                return
            self.config[key] = val
        if save_config(self.config):
            self.adb.path = self.config.get("adb_path", "adb")
            self.log("[+] Configuración guardada.")
        else:
            self.log("[-] No se pudo guardar la configuración.")

    def open_folder(self, path):
        if not path or not os.path.isdir(path):
            self.log("[-] La carpeta de respaldo no existe aún.")
            return
        try:
            if IS_WIN:
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log(f"[-] No se pudo abrir la carpeta: {e}")

    def delete_backup(self):
        pc_dir = self.config.get("pc_dir", "")
        if not os.path.isdir(pc_dir):
            self.log("[-] No hay respaldo que borrar.")
            return
        ok = messagebox.askyesno(
            "Borrar respaldo",
            f"Se borrará TODO el respaldo en:\n{pc_dir}\n\nEsta acción no se puede deshacer. ¿Continuar?",
        )
        if not ok:
            return
        try:
            shutil.rmtree(pc_dir)
            self.log("[+] Respaldo eliminado.")
        except Exception as e:
            self.log(f"[-] Error al borrar: {e}")

    def _tlog(self, message):
        self._ui_queue.put(("log", message))

    def _spinner_start(self, parent, text="Cargando..."):
        self._spinner_text = text
        self._spinner_idx = 0
        self._spinner_lbl = ctk.CTkLabel(parent, text="◐ " + text, font=F_SMALL, text_color=MUTED)
        self._spinner_lbl.pack(pady=20)
        self._spin_tick()

    def _spin_tick(self):
        if not hasattr(self, "_spinner_lbl") or not self._spinner_lbl.winfo_exists():
            return
        chars = "◐◓◑◒"
        self._spinner_idx = (self._spinner_idx + 1) % len(chars)
        self._spinner_lbl.configure(text=chars[self._spinner_idx] + " " + self._spinner_text)
        self.after(120, self._spin_tick)

    def _spinner_stop(self):
        if hasattr(self, "_spinner_lbl"):
            try:
                self._spinner_lbl.destroy()
            except Exception:
                pass

    def log(self, message):
        if self._console is not None:
            self._console.insert("end", f"{message}\n")
            self._console.see("end")
        if self._log_path is None:
            return
        try:
            if self._log_fh is None:
                self._log_fh = open(self._log_path, "a", encoding="utf-8")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._log_fh.write(f"[{ts}] {message}\n")
            self._log_fh.flush()
        except Exception:
            pass

    @staticmethod
    def _fmt_bytes(n):
        n = float(n)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:.1f} {unit}"
            n /= 1024

    @staticmethod
    def _fmt_eta(secs):
        secs = int(max(0, secs))
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m:02d}m {s:02d}s"
        return f"{m}m {s:02d}s"

    def _open_session(self, titulo):
        try:
            if self._log_fh is not None:
                self._log_fh.close()
        except Exception:
            pass
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = BASE_DIR / f"vault_{stamp}.log"
        self._log_fh = None
        self._tlog(f"[==] {titulo} — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _sess_summary(self, done, errores, omitidos, cancelado, op):
        self._tlog(f"[i] {op} — procesados: {done} | con error: {errores} | omitidos: {omitidos} | cancelado: {cancelado}")

    def _sess_stats(self, done, transferidos, elapsed):
        vel = transferidos / elapsed if elapsed > 0 else 0
        rpm = done / elapsed * 60 if elapsed > 0 else 0
        self._tlog(f"[i] Tiempo: {self._fmt_eta(elapsed)} · Velocidad media: {self._fmt_bytes(vel)}/s · {rpm:.0f} archivos/min")

    def set_busy(self, busy):
        self._busy = busy
        if busy:
            self._cancel_requested = False
            self.progress.set(0)
            self.lbl_progress.configure(text="")
            self.status_chip.configure(text="Respaldo en curso...", text_color=ACCENT, fg_color=SURFACE_2)
        else:
            try:
                if self._log_fh is not None:
                    self._log_fh.close()
                    self._log_fh = None
            except Exception:
                pass
            self.refresh_device_status()
        self._apply_busy_state()

    def _apply_busy_state(self):
        busy = self._busy
        state = "disabled" if busy else "normal"
        if self._current_view == "respaldo":
            if hasattr(self, "btn_backup"):
                self.btn_backup.configure(state=state)
            if hasattr(self, "btn_cancel"):
                self.btn_cancel.configure(state="normal" if busy else "disabled")
        elif self._current_view == "restaurar":
            if hasattr(self, "btn_restore"):
                self.btn_restore.configure(state=state)
            if hasattr(self, "btn_cancel"):
                self.btn_cancel.configure(state="normal" if busy else "disabled")
        elif self._current_view == "comandos":
            if hasattr(self, "btn_exec"):
                self.btn_exec.configure(state=state)
            if hasattr(self, "entry_cmd"):
                self.entry_cmd.configure(state=state)
        elif self._current_view == "conexion":
            for attr in ("btn_tcpip", "btn_pair", "btn_conn"):
                b = getattr(self, attr, None)
                if b is not None:
                    b.configure(state=state)

    def request_cancel(self):
        self._cancel_requested = True
        self.log("[-] Cancelación solicitada, terminando tras el archivo actual...")

    def should_cancel(self):
        return self._cancel_requested

    def start_backup(self):
        if not self.check_adb():
            return
        include_data = self.include_data_var.get()
        include_hidden = self.include_hidden_var.get()
        date_str = self.entry_date.get().strip()
        if date_str:
            try:
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning(
                    "VAULT",
                    f"La fecha '{date_str}' no es válida.\n\nUsa el formato YYYY-MM-DD, por ejemplo: 2026-09-01",
                )
                return
        cat_key = getattr(self, "_cat_key", "Todo")
        self.set_busy(True)
        threading.Thread(target=self.run_backup, args=(include_data, include_hidden, date_str, cat_key), daemon=True).start()

    def emergency_backup(self):
        if not self.check_adb():
            return
        ok = messagebox.askyesno(
            "Respaldo de emergencia",
            "Esto copiará TODO el teléfono (fotos, videos, documentos, música, APKs)\n"
            "sin filtros y sin Android/data, ignorando tu selección actual.\n\n"
            "Es el respaldo rápido ideal antes de un formateo. ¿Continuar?",
        )
        if not ok:
            return
        self.set_busy(True)
        threading.Thread(target=self.run_backup, args=(False, False, "", "Todo"), daemon=True).start()

    def start_restore(self):
        if not self.check_adb():
            return
        include_data = self.include_data_var.get()
        self.set_busy(True)
        threading.Thread(target=self.run_restore, args=(include_data,), daemon=True).start()

    def check_adb(self):
        if self.adb.get_state():
            self.status_chip.configure(text="Teléfono: conectado", text_color=OK, fg_color=CHIP_OK_BG)
            return True
        self.status_chip.configure(text="Teléfono: desconectado", text_color=ERR, fg_color=DANGER_BG)
        messagebox.showwarning(
            "VAULT",
            "No se detecta un dispositivo ADB conectado.\n\nConecta el teléfono y revisa que esté autorizado.",
        )
        return False

    def refresh_device_status(self):
        def worker():
            try:
                ok = self.adb.get_state()
                info = self.adb.device_info() if ok else {}
                self._ui_queue.put(("status", ok, info))
            except Exception:
                self._ui_queue.put(("status", False, {}))
        threading.Thread(target=worker, daemon=True).start()
        self.after(30000, self.refresh_device_status)

    def _poll_ui_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                try:
                    self._handle_ui_item(item)
                except Exception as e:
                    self._tlog(f"[-] Error interno: {e}")
        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _handle_ui_item(self, item):
        kind = item[0]
        if kind == "progress":
            _, frac, text = item
            self.progress.set(frac)
            self.lbl_progress.configure(text=text)
        elif kind == "count":
            self.lbl_progress.configure(text=item[1])
        elif kind == "log":
            self.log(item[1])
        elif kind == "status":
            _, ok, info = item
            if ok:
                self.status_chip.configure(text="Teléfono: conectado", text_color=OK, fg_color=CHIP_OK_BG)
                if hasattr(self, "lbl_dev_model"):
                    self.lbl_dev_model.configure(text=info.get("modelo", "?"))
                    self.lbl_dev_bat.configure(text=f"Batería: {info.get('bateria', '?')}")
                    self.lbl_dev_storage.configure(text=f"Almacenamiento: {info.get('almacenamiento', '?')}")
                    self.lbl_dev_ip.configure(text=f"IP: {info.get('ip', '?')}")
                    self.lbl_dev_ram.configure(text=f"RAM: {info.get('ram', '?')}")
            else:
                self.status_chip.configure(text="Teléfono: desconectado", text_color=ERR, fg_color=DANGER_BG)
                if hasattr(self, "lbl_dev_model"):
                    self.lbl_dev_model.configure(text="—")
                    self.lbl_dev_bat.configure(text="")
                    self.lbl_dev_storage.configure(text="")
                    self.lbl_dev_ip.configure(text="")
                    self.lbl_dev_ram.configure(text="")
        elif kind == "archivo":
            _, n, size, newest = item
            self._spinner_stop()
            if self._current_view == "archivo" and hasattr(self, "_arch_labels"):
                self._arch_labels["Archivos"].configure(text=f"{n:,}")
                self._arch_labels["Tamaño total"].configure(text=self._fmt_bytes(size))
                self._arch_labels["Último respaldo"].configure(
                    text=datetime.datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M") if newest else "—")
        elif kind == "ask":
            _, titulo, msg, evt, result = item
            result[0] = messagebox.askyesno(titulo, msg)
            evt.set()
        elif kind == "info":
            _, titulo, msg = item
            messagebox.showinfo(titulo, msg)
        elif kind == "apps":
            if self._current_view == "apps" and hasattr(self, "apps_frame"):
                self._render_apps(item[1])
        elif kind == "apps_status":
            if self._current_view == "apps" and hasattr(self, "lbl_apps_status"):
                self.lbl_apps_status.configure(text=item[1])
        elif kind == "explorer":
            if self._current_view == "explorador" and hasattr(self, "explorer_frame"):
                self._render_explorer(item[1])
        elif kind == "explorer_reload":
            if self._current_view == "explorador" and hasattr(self, "entry_path"):
                self.explorer_go()
        elif kind == "logcat":
            _, level, line = item
            color = {"E": ERR, "W": ACCENT, "I": OK, "D": MUTED, "V": MUTED}.get(level, MUTED)
            self._log_line(line, color)
        elif kind == "logcat_done":
            if getattr(self, "_logcat_proc", None) is None and hasattr(self, "btn_logcat"):
                self.btn_logcat.configure(text="Logcat en vivo", command=self.logcat_start,
                                          fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT)
        elif kind == "set_busy":
            self.set_busy(item[1])

    def _scheduled_update_progress(self, frac, text):
        try:
            self._ui_queue.put(("progress", frac, text))
        except Exception:
            pass

    def _confirm_operation(self, op, total, total_size, orden):
        evt = threading.Event()
        result = [False]
        if op == "Restauración":
            msg = (f"Se van a restaurar {total} archivos ({self._fmt_bytes(total_size)}) {orden}.\n\n"
                   "Los archivos del teléfono con el mismo nombre serán REEMPLAZADOS.\n"
                   "Esto restaura archivos sueltos (fotos, documentos...), NO apps ni ajustes.\n\n¿Continuar?")
        else:
            msg = (f"Se van a respaldar {total} archivos ({self._fmt_bytes(total_size)}) {orden}.\n\n¿Continuar?")
        self._ui_queue.put(("ask", f"Confirmar {op}", msg, evt, result))
        if not evt.wait(timeout=300):
            self._tlog("[-] La confirmación tardó demasiado, operación cancelada.")
            return False
        return result[0]

    @safe_thread
    def run_backup(self, include_data, include_hidden, date_str, cat_key):
        self._open_session("RESPALDO")
        self._tlog("[*] Iniciando respaldo...")
        pc_dir = self.config.get("pc_dir", "")
        phone_dir = self.config.get("phone_dir", "/storage/emulated/0")
        try:
            os.makedirs(pc_dir, exist_ok=True)
        except Exception as e:
            self._tlog(f"[-] No se pudo crear la carpeta de respaldo: {e}")
            self._ui_queue.put(("set_busy", False))
            return

        min_ts = 0.0
        if date_str:
            try:
                min_ts = datetime.datetime.strptime(date_str, "%Y-%m-%d").timestamp()
            except ValueError:
                self._tlog("[-] Fecha inválida, usando formato YYYY-MM-DD.")

        exts = CATEGORIES[cat_key]["exts"] if cat_key in CATEGORIES else None
        self.config["category"] = cat_key
        self.config["date_filter"] = date_str
        self.config["include_data"] = include_data
        self.config["include_hidden"] = include_hidden
        save_config(self.config)
        extra_excl = [x.strip() for x in self.config.get("extra_excludes", "").split(",") if x.strip()]

        try:
            self._tlog(f"[*] Buscando archivos en {phone_dir}...")
            archivos = self.adb.find_files(phone_dir, include_data, include_hidden, min_ts, exts, extra_excl)
        except Exception as e:
            self._tlog(f"[-] Error al listar archivos: {e}")
            self._ui_queue.put(("set_busy", False))
            return

        if not archivos:
            self._tlog("[-] No hay archivos que respaldar.")
            self._sess_summary(0, 0, 0, False, "Backup")
            self._ui_queue.put(("info", "VAULT", "No hay archivos que respaldar."))
            self._ui_queue.put(("set_busy", False))
            return

        total = len(archivos)
        total_size = sum(a[1] for a in archivos)
        self._tlog(f"[*] {total} archivos detectados ({self._fmt_bytes(total_size)}).")

        if not self._confirm_operation("Backup", total, total_size, "de más antiguo a más nuevo"):
            self._tlog("[-] Operación cancelada por el usuario.")
            self._ui_queue.put(("set_busy", False))
            return

        omitidos = 0
        a_copiar = []
        for ts, size, r_path in archivos:
            rel = r_path.replace(phone_dir + "/", "").replace("/", os.sep)
            loc = os.path.join(pc_dir, rel)
            try:
                stale = os.stat(loc).st_size == size and abs(os.stat(loc).st_mtime - ts) < 60
            except OSError:
                stale = False
            if stale:
                omitidos += 1
                continue
            a_copiar.append((ts, size, r_path))

        if not a_copiar:
            self._tlog("[+] Todo está al día. Nada que copiar (incremental).")
            self._tlog(f"[i] Omitidos: {omitidos}")
            self._ui_queue.put(("count", "0 nuevos · todo al día"))
            self._ui_queue.put(("progress", 1.0, "Sin cambios"))
            self._ui_queue.put(("info", "VAULT", "Todo está al día.\nNada nuevo que respaldar."))
            self._ui_queue.put(("set_busy", False))
            return

        copiar_total = len(a_copiar)
        self._tlog(f"[*] Copiando {copiar_total}/{total} (omitidos {omitidos} por estar al día).")
        done = 0
        errores = 0
        start_all = time.time()
        transferidos = 0

        for i, (ts, size, r_path) in enumerate(a_copiar, 1):
            if self.should_cancel():
                self._tlog("[-] Operación cancelada por el usuario.")
                break
            if i % 20 == 0 and not self.adb.get_state():
                self._tlog("[-] El dispositivo se desconectó. Respaldo detenido.")
                self._ui_queue.put(("set_busy", False))
                return
            done += 1
            rel = r_path.replace(phone_dir + "/", "").replace("/", os.sep)
            loc = os.path.join(pc_dir, rel)
            try:
                os.makedirs(os.path.dirname(loc), exist_ok=True)
            except OSError:
                pass
            self._tlog(f"[{i}/{copiar_total}] -> {rel}")
            try:
                r = self.adb.pull(r_path, loc)
            except subprocess.TimeoutExpired:
                self._tlog(f"[!] Timeout al copiar: {rel}")
                errores += 1
                continue
            if r.returncode != 0:
                errores += 1
            else:
                transferidos += size
            try:
                os.utime(loc, (ts, ts))
            except OSError:
                pass

            if r.returncode == 0:
                try:
                    if os.path.getsize(loc) != size:
                        errores += 1
                        self._tlog(f"[!] Verificación fallida (tamaño): {rel}")
                except OSError:
                    pass

            elapsed = time.time() - start_all
            vel = transferidos / elapsed if elapsed > 0 else 0
            quedan = (copiar_total - done) * (elapsed / done) if done > 0 else 0
            texto = f"{done}/{copiar_total} · {self._fmt_bytes(vel)}/s · falta {self._fmt_eta(quedan)}"
            self._scheduled_update_progress(done / copiar_total, texto)

        cancelado = self.should_cancel()
        self._sess_summary(done, errores, omitidos, cancelado, "Backup")
        self._sess_stats(done, transferidos, time.time() - start_all)
        self._ui_queue.put(("count", f"{done} nuevos · {omitidos} al día"))
        if not cancelado:
            self._ui_queue.put(("progress", 1.0, "Completado"))
        titulo = "Cancelado" if cancelado else "Backup Completado"
        msg = (f"Procesados: {done}\nCon errores: {errores}\nAl día (omitidos): {omitidos}\n"
               f"Cancelado: {cancelado}\n\nLog: {self._log_path.name}")
        self._ui_queue.put(("info", titulo, msg))
        self._ui_queue.put(("set_busy", False))

    @safe_thread
    def run_restore(self, include_data):
        self._open_session("RESTAURACIÓN")
        self._tlog("[*] Iniciando restauración...")
        pc_dir = self.config.get("pc_dir", "")
        phone_dir = self.config.get("phone_dir", "/storage/emulated/0")

        archivos = []
        extra_excl = [x.strip() for x in self.config.get("extra_excludes", "").split(",") if x.strip()]
        tokens = EXCL_DIRS | set(extra_excl)
        if os.path.isdir(pc_dir):
            for root, _, fs in os.walk(pc_dir):
                if not include_data and f"Android{os.sep}data" in root:
                    continue
                rel_root = os.path.relpath(root, pc_dir)
                if ADB._is_excluded(rel_root, tokens):
                    continue
                for f in fs:
                    p = Path(os.path.join(root, f))
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    archivos.append((p, st.st_mtime, st.st_size))

        archivos.sort(key=lambda x: x[1])
        if not archivos:
            self._tlog("[-] No hay archivos que restaurar en el respaldo.")
            self._sess_summary(0, 0, 0, False, "Restauración")
            self._ui_queue.put(("info", "VAULT", "No hay archivos en el respaldo."))
            self._ui_queue.put(("set_busy", False))
            return

        total = len(archivos)
        total_size = sum(a[2] for a in archivos)
        self._tlog(f"[*] {total} archivos detectados ({self._fmt_bytes(total_size)}).")

        if not self._confirm_operation("Restauración", total, total_size, "de más antiguo a más nuevo"):
            self._tlog("[-] Operación cancelada por el usuario.")
            self._ui_queue.put(("set_busy", False))
            return

        done = 0
        errores = 0
        start_all = time.time()
        transferidos = 0

        for i, (p, m, size) in enumerate(archivos, 1):
            if self.should_cancel():
                self._tlog("[-] Operación cancelada por el usuario.")
                break
            if i % 20 == 0 and not self.adb.get_state():
                self._tlog("[-] El dispositivo se desconectó. Restauración detenida.")
                self._ui_queue.put(("set_busy", False))
                return
            done += 1
            rel = p.relative_to(pc_dir).as_posix()
            if ADB._is_excluded(rel, tokens):
                continue
            rem = f"{phone_dir}/{rel}"
            self._tlog(f"[{i}/{total}] <- {rel}")
            self.adb.shell(f"mkdir -p '{os.path.dirname(rem)}'")
            try:
                r = self.adb.push(p, rem)
            except subprocess.TimeoutExpired:
                self._tlog(f"[!] Timeout al copiar: {rel}")
                errores += 1
                continue
            if r.returncode != 0:
                errores += 1
            else:
                transferidos += size
            ts = datetime.datetime.fromtimestamp(m).strftime("%Y%m%d%H%M")
            self.adb.shell(f"touch -t {ts} '{rem}'")

            if r.returncode == 0:
                info = self.adb.shell(f"stat -c %s '{rem}'")
                try:
                    if int(info.stdout.strip()) != size:
                        errores += 1
                        self._tlog(f"[!] Verificación fallida (tamaño): {rel}")
                except ValueError:
                    pass

            elapsed = time.time() - start_all
            vel = transferidos / elapsed if elapsed > 0 else 0
            quedan = (total - done) * (elapsed / done) if done > 0 else 0
            texto = f"{done}/{total} · {self._fmt_bytes(vel)}/s · falta {self._fmt_eta(quedan)}"
            self._scheduled_update_progress(done / total, texto)

        cancelado = self.should_cancel()
        self._sess_summary(done, errores, 0, cancelado, "Restauración")
        self._sess_stats(done, transferidos, time.time() - start_all)
        self._ui_queue.put(("count", f"{done} / {total} archivos"))
        if not cancelado:
            self._ui_queue.put(("progress", 1.0, "Completado"))
        titulo = "Cancelado" if cancelado else "Restauración Completada"
        msg = (f"Procesados: {done}\nCon errores: {errores}\nCancelado: {cancelado}\n\n"
               f"Log: {self._log_path.name}")
        self._ui_queue.put(("info", titulo, msg))
        self._ui_queue.put(("set_busy", False))

    def execute_custom_cmd(self, event=None):
        cmd_text = self.entry_cmd.get().strip()
        if not cmd_text:
            return
        self.entry_cmd.delete(0, "end")
        prompt_str = "C:" if IS_WIN else "$"
        self.log(f"> {prompt_str} {cmd_text}")
        threading.Thread(target=self.run_custom_cmd, args=(cmd_text,), daemon=True).start()

    @safe_thread
    def run_custom_cmd(self, cmd_text):
        try:
            result = self.adb.exec_custom(cmd_text)
            if result.stdout:
                self._tlog(result.stdout.strip())
            if result.stderr:
                self._tlog(f"[-] ERROR:\n{result.stderr.strip()}")
        except Exception as e:
            self._tlog(f"[-] Error: {e}")

    def _require_device(self):
        if self.adb.get_state():
            return True
        self._tlog("[-] No hay dispositivo ADB conectado.")
        return False

    def quick_screencap(self):
        threading.Thread(target=self._quick_screencap, daemon=True).start()

    @safe_thread
    def _quick_screencap(self):
        if not self._require_device():
            return
        pc_dir = self.config.get("pc_dir", "")
        try:
            os.makedirs(pc_dir, exist_ok=True)
        except OSError:
            pass
        name = f"screencap_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        dest = os.path.join(pc_dir, name)
        self._tlog("[*] Tomando captura...")
        if self.adb.screencap(dest):
            self._tlog(f"[+] Captura guardada: {dest}")
        else:
            self._tlog("[-] Falló la captura.")

    def quick_logcat(self):
        threading.Thread(target=self._quick_logcat, daemon=True).start()

    @safe_thread
    def _quick_logcat(self):
        if not self._require_device():
            return
        self._tlog("[*] Obteniendo logcat (últimas 200 líneas)...")
        r = self.adb.shell("logcat -d -t 200")
        if r.stdout:
            self._tlog(r.stdout.strip())
        else:
            self._tlog("[-] Sin salida de logcat.")

    def logcat_start(self):
        if getattr(self, "_logcat_proc", None):
            return
        try:
            self._logcat_proc = subprocess.Popen(
                [self.adb.path, "logcat", "-v", "brief"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="ignore",
                creationflags=NO_WINDOW)
        except Exception as e:
            self._tlog(f"[-] No se pudo iniciar logcat: {e}")
            return
        self._tlog("[*] Logcat en vivo iniciado. Pulsa 'Detener logcat' para cortar.")
        if hasattr(self, "btn_logcat"):
            self.btn_logcat.configure(text="Detener logcat", command=self.logcat_stop,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT)
        threading.Thread(target=self._logcat_read, daemon=True).start()

    def _logcat_read(self):
        proc = self._logcat_proc
        for line in proc.stdout:
            if not line.strip():
                continue
            level = line[0] if line and line[0] in "VDIWEF" else "I"
            self._ui_queue.put(("logcat", level, line.rstrip()))
        self._ui_queue.put(("logcat_done",))

    def logcat_stop(self):
        proc = getattr(self, "_logcat_proc", None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
            self._logcat_proc = None
            self._tlog("[-] Logcat detenido.")
            if hasattr(self, "btn_logcat"):
                self.btn_logcat.configure(text="Logcat en vivo", command=self.logcat_start,
                                          fg_color=SURFACE_2, hover_color=BORDER, text_color=TEXT)

    def _log_line(self, line, color):
        if self._console is None:
            return
        tag = "c" + color[1:]
        try:
            self._console.tag_config(tag, foreground=color)
        except Exception:
            pass
        self._console.insert("end", line + "\n", (tag,))
        self._console.see("end")

    def quick_apps(self):
        threading.Thread(target=self._quick_apps, daemon=True).start()

    @safe_thread
    def _quick_apps(self):
        if not self._require_device():
            return
        self._tlog("[*] Apps de terceros instaladas:")
        r = self.adb.shell("pm list packages -3")
        apps = [ln.replace("package:", "").strip() for ln in r.stdout.splitlines() if ln.strip()]
        if apps:
            self._tlog("\n".join(apps))
        else:
            self._tlog("[-] Sin apps de terceros o sin permisos.")

    def quick_info(self):
        threading.Thread(target=self._quick_info, daemon=True).start()

    @safe_thread
    def _quick_info(self):
        if not self._require_device():
            return
        info = self.adb.device_info()
        self._tlog("[*] Información del dispositivo:")
        self._tlog(f"    Modelo: {info.get('modelo')}")
        self._tlog(f"    Android: {info.get('android')}")
        self._tlog(f"    Batería: {info.get('bateria')}")
        self._tlog(f"    Almacenamiento: {info.get('almacenamiento')}")
        self._tlog(f"    RAM: {info.get('ram')}")
        self._tlog(f"    IP: {info.get('ip')}")

    def quick_reboot(self):
        threading.Thread(target=self._quick_reboot, daemon=True).start()

    @safe_thread
    def _quick_reboot(self):
        if not self._require_device():
            return
        evt = threading.Event()
        result = [False]
        self._ui_queue.put(("ask", "VAULT", "¿Reiniciar el dispositivo?", evt, result))
        evt.wait()
        if result[0]:
            self._tlog("[*] Reiniciando dispositivo...")
            self.adb.run(["reboot"])

    def quick_poweroff(self):
        threading.Thread(target=self._quick_poweroff, daemon=True).start()

    @safe_thread
    def _quick_poweroff(self):
        if not self._require_device():
            return
        evt = threading.Event()
        result = [False]
        self._ui_queue.put(("ask", "VAULT", "¿Apagar el dispositivo?", evt, result))
        evt.wait()
        if result[0]:
            self._tlog("[*] Apagando dispositivo...")
            self.adb.shell("reboot -p")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = VaultApp()
    app.mainloop()