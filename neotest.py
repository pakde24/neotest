import subprocess
import sys
import os
import time
import threading
import ctypes
import winreg
import json
import shutil
import hashlib
from ctypes import wintypes
import win32api
import win32con
import win32gui
import win32process
import psutil
import keyboard
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

try:
    import requests
except ImportError:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "requests"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    import requests

# ============================================================
# KONSTANTA & KONFIGURASI
# ============================================================
CURRENT_VERSION   = "1.0.1"

VERSION_CHECK_URL = (
    "https://raw.githubusercontent.com/"
    "pakde24/neotest/refs/heads/main/version.json"
)

DEFAULT_URL   = "https://youtube.com/@ayobelajarterus/videos"
APP_TITLE     = "NeoTest"

# Runtime config (diisi dari online)
RUNTIME_URL   = DEFAULT_URL
RUNTIME_TITLE = APP_TITLE

EXIT_COMBO = {"p", "k", "r"}
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

BG_COLOR     = "#1a1a2e"
BTN_COLOR    = "#16213e"
BTN_HOVER    = "#0f3460"
ACCENT_COLOR = "#e94560"
TEXT_COLOR   = "#ffffff"
TIME_COLOR   = "#00d4aa"
DATE_COLOR   = "#aaaacc"
BAR_HEIGHT   = 40

# ============================================================
# PATH HELPER - DETEKSI MODE EXE ATAU PY
# ============================================================
def get_app_dir():
    """Direktori tempat EXE / script berada."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_current_exe_path():
    """Path EXE atau script yang sedang berjalan."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def get_updater_path():
    """
    Path updater.exe (harus ada di folder yang sama
    dengan neotest.exe).
    """
    return os.path.join(get_app_dir(), "updater.exe")


def is_exe_mode():
    """True jika berjalan sebagai EXE hasil build."""
    return getattr(sys, 'frozen', False)

# ============================================================
# AUTO UPDATE SYSTEM
# ============================================================
def get_file_hash(filepath):
    md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None


def fetch_version_info(timeout=10):
    try:
        resp = requests.get(VERSION_CHECK_URL, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print("[Update] Tidak ada koneksi internet.")
        return None
    except requests.exceptions.Timeout:
        print("[Update] Timeout saat cek versi.")
        return None
    except Exception as e:
        print(f"[Update] Gagal cek versi: {e}")
        return None


def compare_versions(v1, v2):
    try:
        def norm(v):
            return [int(x) for x in v.split('.')]
        p1, p2 = norm(v1), norm(v2)
        # Samakan panjang
        while len(p1) < len(p2): p1.append(0)
        while len(p2) < len(p1): p2.append(0)
        for a, b in zip(p1, p2):
            if a > b: return 1
            if a < b: return -1
        return 0
    except Exception:
        return 0


def download_file(url, dest_path, timeout=120):
    """Download file dengan progress, return True jika sukses."""
    try:
        print(f"[Update] Download: {url}")
        resp = requests.get(url, stream=True, timeout=timeout)
        resp.raise_for_status()

        total      = int(resp.headers.get('content-length', 0))
        downloaded = 0

        with open(dest_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 // total
                        print(f"\r[Update] {pct}% "
                              f"({downloaded//1024} KB / "
                              f"{total//1024} KB)", end='', flush=True)
        print(f"\n[Update] Download selesai.")
        return True

    except Exception as e:
        print(f"\n[Update] Download gagal: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def show_update_dialog(version_info):
    """Dialog pilihan update. Return True jika user setuju."""
    result = {'ok': False}

    dialog = tk.Tk()
    dialog.title("Update Tersedia")
    dialog.configure(bg=BG_COLOR)
    dialog.resizable(False, False)
    dialog.attributes('-topmost', True)

    w, h = 440, 240
    sw   = dialog.winfo_screenwidth()
    sh   = dialog.winfo_screenheight()
    dialog.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(
        dialog,
        text="🔄  Update Tersedia!",
        font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
        bg=BG_COLOR, fg=ACCENT_COLOR
    ).pack(pady=(18, 6))

    tk.Label(
        dialog,
        text=(f"Versi saat ini  :  {CURRENT_VERSION}\n"
              f"Versi terbaru   :  {version_info.get('version','?')}"),
        font=tkfont.Font(family="Segoe UI", size=10),
        bg=BG_COLOR, fg=TEXT_COLOR, justify='left'
    ).pack(padx=24, anchor='w')

    tk.Label(
        dialog,
        text=f"Perubahan  :  {version_info.get('changelog', '-')}",
        font=tkfont.Font(family="Segoe UI", size=9),
        bg=BG_COLOR, fg=DATE_COLOR,
        wraplength=390, justify='left'
    ).pack(padx=24, pady=(8, 0), anchor='w')

    # Info ukuran file
    size_mb = version_info.get('size_mb', '?')
    tk.Label(
        dialog,
        text=f"Ukuran file  :  {size_mb} MB",
        font=tkfont.Font(family="Segoe UI", size=9),
        bg=BG_COLOR, fg=DATE_COLOR
    ).pack(padx=24, anchor='w')

    frame_btn = tk.Frame(dialog, bg=BG_COLOR)
    frame_btn.pack(pady=14)

    btn_style = dict(
        font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
        relief='flat', bd=0, padx=14, pady=6, cursor='hand2'
    )

    def on_update():
        result['ok'] = True
        dialog.destroy()

    def on_skip():
        dialog.destroy()

    tk.Button(
        frame_btn, text="  Update Sekarang  ",
        bg=ACCENT_COLOR, fg=TEXT_COLOR,
        activebackground="#c73652",
        command=on_update, **btn_style
    ).pack(side='left', padx=8)

    tk.Button(
        frame_btn, text="  Lewati  ",
        bg=BTN_COLOR, fg=TEXT_COLOR,
        activebackground=BTN_HOVER,
        command=on_skip, **btn_style
    ).pack(side='left', padx=8)

    dialog.protocol("WM_DELETE_WINDOW", on_skip)
    dialog.mainloop()
    return result['ok']


def show_downloading_dialog():
    """
    Dialog progress download.
    Return (dialog_root, label_progress, label_pct).
    """
    win = tk.Tk()
    win.title("Mengunduh Update...")
    win.configure(bg=BG_COLOR)
    win.resizable(False, False)
    win.attributes('-topmost', True)

    w, h = 400, 140
    sw   = win.winfo_screenwidth()
    sh   = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(
        win, text="🔄  Mengunduh Update...",
        font=tkfont.Font(family="Segoe UI", size=12, weight="bold"),
        bg=BG_COLOR, fg=ACCENT_COLOR
    ).pack(pady=(18, 8))

    lbl_info = tk.Label(
        win, text="Mempersiapkan download...",
        font=tkfont.Font(family="Segoe UI", size=9),
        bg=BG_COLOR, fg=TEXT_COLOR
    )
    lbl_info.pack()

    lbl_pct = tk.Label(
        win, text="0%",
        font=tkfont.Font(family="Segoe UI", size=11, weight="bold"),
        bg=BG_COLOR, fg=TIME_COLOR
    )
    lbl_pct.pack(pady=6)

    return win, lbl_info, lbl_pct


def apply_update_exe(new_exe_path, version_info):
    """
    Jalankan updater.exe untuk mengganti EXE dan restart.
    Ini bekerja baik saat mode EXE maupun mode .py (dev).
    """
    current_exe  = get_current_exe_path()
    updater_path = get_updater_path()
    current_pid  = os.getpid()

    # ── Mode EXE: gunakan updater.exe ──────────────────────
    if is_exe_mode():
        if not os.path.exists(updater_path):
            # Coba download updater juga
            updater_url = version_info.get('updater_url', '')
            if updater_url:
                print("[Update] Mengunduh updater.exe...")
                download_file(updater_url, updater_path)

        if os.path.exists(updater_path):
            print(f"[Update] Menjalankan updater.exe...")
            print(f"         PID lama    : {current_pid}")
            print(f"         EXE baru    : {new_exe_path}")
            print(f"         Target      : {current_exe}")
            try:
                subprocess.Popen(
                    [
                        updater_path,
                        str(current_pid),
                        new_exe_path,
                        current_exe
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Tutup diri sendiri agar updater bisa mengganti file
                print("[Update] Menutup aplikasi untuk proses update...")
                time.sleep(1)
                os._exit(0)
            except Exception as e:
                print(f"[Update] Gagal jalankan updater: {e}")
        else:
            # Fallback: update manual tanpa updater.exe
            _apply_update_manual(new_exe_path, current_exe, current_pid)

    # ── Mode .py (development): ganti langsung ─────────────
    else:
        _apply_update_py(new_exe_path, current_exe)


def _apply_update_manual(new_exe_path, current_exe, current_pid):
    """
    Fallback: buat BAT file untuk mengganti EXE setelah proses tutup.
    Cara lama tapi reliable.
    """
    bat_path = os.path.join(get_app_dir(), "_update_helper.bat")
    bat_content = f"""@echo off
echo [Update] Menunggu proses lama berhenti...
:waitloop
tasklist /FI "PID eq {current_pid}" 2>NUL | find /I "neotest.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >NUL
    goto waitloop
)
echo [Update] Mengganti file EXE...
timeout /t 1 /nobreak >NUL
move /Y "{new_exe_path}" "{current_exe}"
echo [Update] Menjalankan versi baru...
start "" "{current_exe}"
echo [Update] Selesai.
del "%~f0"
"""
    try:
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        subprocess.Popen(
            ['cmd', '/c', bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW
                         | subprocess.DETACHED_PROCESS
        )
        print("[Update] BAT helper dijalankan.")
        time.sleep(1)
        os._exit(0)
    except Exception as e:
        print(f"[Update] Gagal jalankan BAT helper: {e}")


def _apply_update_py(new_file_path, current_script):
    """Update untuk mode development (.py)."""
    backup = current_script + ".backup"
    try:
        shutil.copy2(current_script, backup)
        shutil.copy2(new_file_path, current_script)
        os.remove(new_file_path)
        print("[Update] Script diperbarui, merestart...")
        subprocess.Popen([sys.executable, current_script] + sys.argv[1:])
        os._exit(0)
    except Exception as e:
        print(f"[Update] Gagal update py: {e}")
        if os.path.exists(backup):
            shutil.copy2(backup, current_script)


def check_and_update():
    """
    Fungsi utama: cek versi, download, apply.
    Return version_info dict atau None jika offline.
    """
    global RUNTIME_URL, RUNTIME_TITLE

    print(f"[Update] Mode        : {'EXE' if is_exe_mode() else 'Python Script'}")
    print(f"[Update] Versi ini   : {CURRENT_VERSION}")
    print(f"[Update] Cek update...")

    version_info = fetch_version_info()

    if version_info is None:
        print("[Update] Offline - pakai konfigurasi default.")
        return None

    # Ambil config runtime dari online
    RUNTIME_URL   = version_info.get('url',       DEFAULT_URL)
    RUNTIME_TITLE = version_info.get('app_title', APP_TITLE)

    print(f"[Update] URL online  : {RUNTIME_URL}")
    print(f"[Update] Title       : {RUNTIME_TITLE}")

    latest_version = version_info.get('version', CURRENT_VERSION)
    force_update   = version_info.get('force_update', False)

    # Pilih URL update yang tepat (exe atau py)
    if is_exe_mode():
        update_url = version_info.get('update_exe_url', '')
    else:
        update_url = version_info.get('update_url', '')

    if compare_versions(latest_version, CURRENT_VERSION) <= 0:
        print("[Update] Sudah versi terbaru ✓")
        return version_info

    print(f"[Update] Versi baru  : {latest_version} (ada update!)")

    if not update_url:
        print("[Update] URL update tidak tersedia.")
        return version_info

    # Tanya user
    if force_update:
        do_update = True
        print("[Update] Force update - otomatis diperbarui...")
    else:
        do_update = show_update_dialog(version_info)

    if not do_update:
        print("[Update] Update dilewati.")
        return version_info

    # Tentukan nama file temp
    ext      = ".exe" if is_exe_mode() else ".py"
    tmp_path = os.path.join(get_app_dir(), f"neotest_new{ext}")

    # Download dengan dialog progress
    dl_win, lbl_info, lbl_pct = show_downloading_dialog()

    download_done   = {'ok': False}
    download_error  = {'msg': ''}

    def do_download():
        try:
            resp = requests.get(update_url, stream=True, timeout=120)
            resp.raise_for_status()
            total      = int(resp.headers.get('content-length', 0))
            downloaded = 0
            with open(tmp_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = downloaded * 100 // total
                            kb  = downloaded // 1024
                            tkb = total // 1024
                            dl_win.after(0, lambda p=pct, k=kb, t=tkb: (
                                lbl_pct.config(text=f"{p}%"),
                                lbl_info.config(
                                    text=f"Mengunduh... {k} KB / {t} KB")
                            ))
            download_done['ok'] = True
        except Exception as e:
            download_error['msg'] = str(e)
        finally:
            dl_win.after(0, dl_win.destroy)

    threading.Thread(target=do_download, daemon=True).start()
    dl_win.mainloop()

    if not download_done['ok']:
        print(f"[Update] Download gagal: {download_error['msg']}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return version_info

    # Verifikasi hash (opsional tapi disarankan)
    expected_hash = version_info.get('md5', '')
    if expected_hash:
        actual_hash = get_file_hash(tmp_path)
        if actual_hash != expected_hash:
            print(f"[Update] Hash tidak cocok! "
                  f"Expected: {expected_hash}, Got: {actual_hash}")
            os.remove(tmp_path)
            return version_info
        print(f"[Update] Hash OK: {actual_hash}")

    # Apply update
    apply_update_exe(tmp_path, version_info)
    return version_info

# ============================================================
# DETEKSI PATH EDGE
# ============================================================
def find_edge():
    for path in EDGE_PATHS:
        if os.path.exists(path):
            return path
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"
        )
        val, _ = winreg.QueryValueEx(key, "")
        if os.path.exists(val):
            return val
    except Exception:
        pass
    return None

# ============================================================
# BLOKIR KEYBOARD
# ============================================================
def block_keys():
    try:
        ctrl_combos = [
            'ctrl+shift+esc', 'ctrl+shift+i',   'ctrl+shift+j',
            'ctrl+shift+c',   'ctrl+shift+k',   'ctrl+shift+u',
            'ctrl+shift+del', 'ctrl+shift+b',   'ctrl+shift+o',
            'ctrl+shift+n',   'ctrl+shift+p',   'ctrl+shift+t',
            'ctrl+shift+w',   'ctrl+alt+del',   'ctrl+alt+t',
            'ctrl+alt+f4',    'ctrl+esc',        'ctrl+f4',
            'ctrl+w',         'ctrl+t',          'ctrl+n',
            'ctrl+r',         'ctrl+l',          'ctrl+d',
            'ctrl+h',         'ctrl+j',          'ctrl+k',
            'ctrl+o',         'ctrl+p',          'ctrl+s',
            'ctrl+u',
        ]
        alt_combos = [
            'alt+tab',        'alt+shift+tab',   'alt+f4',
            'alt+space',      'alt+enter',       'alt+f',
            'alt+e',          'alt+d',           'alt+left',
            'alt+right',      'alt+home',
        ]
        win_combos = [
            'windows+d', 'windows+e', 'windows+r', 'windows+l',
            'windows+tab', 'windows+m', 'windows+shift+m',
            'windows+p', 'windows+a', 'windows+i', 'windows+k',
            'windows+s', 'windows+q', 'windows+x', 'windows+z',
            'windows+n', 'windows+h', 'windows+g', 'windows+u',
            'windows+v', 'windows+.', 'windows+space',
            'windows+pause', 'windows+break',
            'windows+1', 'windows+2', 'windows+3',
        ]
        single_keys = [
            'left windows', 'right windows', 'escape',
            'f1', 'f2', 'f3', 'f4', 'f6', 'f7', 'f8', 'f9',
            'f10', 'f11', 'f12', 'print screen',
            'scroll lock', 'pause', 'insert', 'menu',
        ]

        for combo in ctrl_combos + alt_combos + win_combos:
            try:
                keyboard.add_hotkey(combo, lambda: None, suppress=True)
            except Exception:
                pass
        for key in single_keys:
            try:
                keyboard.block_key(key)
            except Exception:
                pass

        print("[NeoTest] Keyboard berhasil diblokir.")
    except Exception as e:
        print(f"[WARN] block_keys error: {e}")


def unblock_keys():
    try:
        keyboard.unhook_all()
    except Exception:
        pass

# ============================================================
# GLOBAL STATE
# ============================================================
overlay_root   = None
edge_process   = None
is_refreshing  = False
monitor_active = True
exit_pressed   = set()
exit_lock      = threading.Lock()

# ============================================================
# KILL EDGE
# ============================================================
def kill_edge_processes():
    global edge_process
    if edge_process:
        try:
            parent = psutil.Process(edge_process.pid)
            for child in parent.children(recursive=True):
                try: child.kill()
                except Exception: pass
            parent.kill()
        except Exception:
            pass
        finally:
            edge_process = None

    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] and 'msedge' in proc.info['name'].lower():
                proc.kill()
        except Exception:
            pass

    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', 'msedge.exe', '/T'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
    except Exception:
        pass
    time.sleep(0.5)

# ============================================================
# EXIT HANDLER
# ============================================================
def do_exit():
    global monitor_active, overlay_root
    print("[NeoTest] Keluar...")
    monitor_active = False
    unblock_keys()
    kill_edge_processes()
    time.sleep(0.5)
    try:
        subprocess.run(
            ['taskkill', '/F', '/IM', 'msedge.exe', '/T'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3
        )
    except Exception:
        pass
    if overlay_root:
        try:
            overlay_root.after(0, overlay_root.destroy)
        except Exception:
            pass
    print("[NeoTest] Sampai jumpa!")
    os._exit(0)


def setup_exit_hotkey():
    def on_key(event):
        with exit_lock:
            if event.event_type == keyboard.KEY_DOWN:
                exit_pressed.add(event.name.lower())
                if EXIT_COMBO.issubset(exit_pressed):
                    do_exit()
            elif event.event_type == keyboard.KEY_UP:
                exit_pressed.discard(event.name.lower())
    keyboard.hook(on_key)

# ============================================================
# UTILITY
# ============================================================
def get_screen_size():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def find_edge_hwnd():
    result = []
    def callback(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return
            if 'Chrome_WidgetWin_1' in win32gui.GetClassName(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    if 'msedge' in psutil.Process(pid).name().lower():
                        result.append((hwnd, pid))
                except Exception:
                    pass
        except Exception:
            pass
    win32gui.EnumWindows(callback, None)
    return result


def reposition_edge_window():
    sw, sh = get_screen_size()
    for hwnd, pid in find_edge_hwnd():
        try:
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_BOTTOM,
                0, 0, sw, sh - BAR_HEIGHT,
                win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER
            )
        except Exception as e:
            print(f"[WARN] reposition: {e}")


def bring_overlay_front():
    global overlay_root
    if overlay_root:
        try:
            overlay_root.lift()
            overlay_root.attributes('-topmost', True)
        except Exception:
            pass

# ============================================================
# LAUNCH EDGE
# ============================================================
def launch_edge(url):
    global edge_process
    edge_path = find_edge()
    if not edge_path:
        ctypes.windll.user32.MessageBoxW(
            0,
            "Microsoft Edge tidak ditemukan!\n"
            "Pastikan Microsoft Edge sudah terinstall.",
            "NeoTest - Error", 0x10
        )
        sys.exit(1)

    sw, sh = get_screen_size()
    args = [
        edge_path, f"--app={url}",
        "--start-fullscreen",
        f"--window-size={sw},{sh}",
        "--window-position=0,0",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-popup-blocking",
        "--disable-translate",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        "--disable-restore-session-state",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-pinch",
        "--disable-features=TranslateUI",
        "--disable-features=DownloadBubble",
        "--block-new-web-contents",
        "--overscroll-history-navigation=0",
        "--no-message-box",
    ]
    edge_process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"[NeoTest] Edge PID: {edge_process.pid}")
    return edge_process

# ============================================================
# MONITOR EDGE
# ============================================================
def monitor_edge(url):
    global edge_process, is_refreshing
    time.sleep(4)
    while monitor_active:
        time.sleep(2)
        if is_refreshing:
            continue
        edge_alive = (edge_process and edge_process.poll() is None)
        if not edge_alive:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and \
                       'msedge' in proc.info['name'].lower():
                        edge_alive = True
                        break
                except Exception:
                    pass
        if not edge_alive:
            print("[NeoTest] Edge mati, restart...")
            time.sleep(1)
            edge_process = launch_edge(url)
            time.sleep(3)
            reposition_edge_window()
            bring_overlay_front()

# ============================================================
# JAM DIGITAL
# ============================================================
def start_clock(lbl_time, lbl_date):
    hari_map = {
        "Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
        "Thursday":"Kamis","Friday":"Jumat",
        "Saturday":"Sabtu","Sunday":"Minggu"
    }
    bulan_map = {
        "January":"Januari","February":"Februari","March":"Maret",
        "April":"April","May":"Mei","June":"Juni","July":"Juli",
        "August":"Agustus","September":"September",
        "October":"Oktober","November":"November","December":"Desember"
    }
    def tick():
        while monitor_active:
            now     = datetime.now()
            jam     = now.strftime("%H:%M:%S")
            tanggal = now.strftime("%A, %d %B %Y")
            for en, id_ in hari_map.items():
                tanggal = tanggal.replace(en, id_)
            for en, id_ in bulan_map.items():
                tanggal = tanggal.replace(en, id_)
            try:
                lbl_time.config(text=jam)
                lbl_date.config(text=tanggal)
            except Exception:
                break
            time.sleep(1)
    threading.Thread(target=tick, daemon=True).start()

# ============================================================
# OVERLAY
# ============================================================
def create_overlay(url, title):
    global overlay_root
    sw, sh = get_screen_size()

    root = tk.Tk()
    overlay_root = root
    root.title(title)
    root.geometry(f"{sw}x{BAR_HEIGHT}+0+{sh - BAR_HEIGHT}")
    root.configure(bg=BG_COLOR)
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.resizable(False, False)

    # Kiri: Brand
    tk.Label(
        root, text=f" ✦ {title}",
        font=tkfont.Font(family="Segoe UI", size=12, weight="bold"),
        bg=BG_COLOR, fg=ACCENT_COLOR, anchor='w'
    ).pack(side='left', padx=(4, 0))

    tk.Label(
        root, text=" │ ", bg=BG_COLOR, fg="#333355"
    ).pack(side='left')

    # Tengah: Jam
    frame_clock = tk.Frame(root, bg=BG_COLOR)
    frame_clock.pack(side='left', padx=(4, 0))

    lbl_time = tk.Label(
        frame_clock, text="00:00:00",
        font=tkfont.Font(family="Segoe UI", size=12, weight="bold"),
        bg=BG_COLOR, fg=TIME_COLOR, anchor='w'
    )
    lbl_time.pack(side='left', padx=(0, 6))

    lbl_date = tk.Label(
        frame_clock, text="",
        font=tkfont.Font(family="Segoe UI", size=8),
        bg=BG_COLOR, fg=DATE_COLOR, anchor='w'
    )
    lbl_date.pack(side='left')
    start_clock(lbl_time, lbl_date)

    # Kanan: Info
    tk.Label(
        root,
        text=f"v{CURRENT_VERSION}  |  H+Q keluar ",
        font=tkfont.Font(family="Segoe UI", size=8),
        bg=BG_COLOR, fg="#555566"
    ).pack(side='right')

    # Kanan: Refresh
    btn_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

    def on_enter(e): btn_ref.config(bg=BTN_HOVER)
    def on_leave(e): btn_ref.config(bg=BTN_COLOR)

    def do_refresh():
        global is_refreshing, edge_process
        if is_refreshing:
            return
        is_refreshing = True
        btn_ref.config(state='disabled', text=' ⟳ Loading... ', bg=BTN_HOVER)
        root.update()

        def _refresh():
            global edge_process, is_refreshing
            try:
                kill_edge_processes()
                time.sleep(0.8)
                edge_process = launch_edge(url)
                time.sleep(3)
                reposition_edge_window()
                bring_overlay_front()
            except Exception as e:
                print(f"[WARN] refresh: {e}")
            finally:
                is_refreshing = False
                root.after(0, lambda: btn_ref.config(
                    state='normal', text=' ⟳ Refresh ', bg=BTN_COLOR
                ))

        threading.Thread(target=_refresh, daemon=True).start()

    btn_ref = tk.Button(
        root, text=" ⟳ Refresh ",
        font=btn_font, bg=BTN_COLOR, fg=TEXT_COLOR,
        activebackground=BTN_HOVER, activeforeground=TEXT_COLOR,
        relief='flat', bd=0, padx=6, pady=0,
        cursor='hand2', command=do_refresh
    )
    btn_ref.pack(side='right', padx=(0, 6), pady=5)
    btn_ref.bind("<Enter>", on_enter)
    btn_ref.bind("<Leave>", on_leave)

    def keep_top():
        if overlay_root:
            try:
                overlay_root.lift()
                overlay_root.attributes('-topmost', True)
            except Exception:
                pass
            overlay_root.after(800, keep_top)

    root.after(800, keep_top)
    return root

# ============================================================
# ADMIN CHECK
# ============================================================
def ensure_admin():
    if ctypes.windll.shell32.IsUserAnAdmin():
        return
    try:
        params = ' '.join([f'"{a}"' for a in sys.argv])
        ret    = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1)
        if ret > 32:
            sys.exit(0)
    except Exception:
        pass

# ============================================================
# MAIN
# ============================================================
def main():
    ensure_admin()

    print("=" * 52)
    print(f"  {APP_TITLE}  v{CURRENT_VERSION}")
    print(f"  Mode: {'EXE' if is_exe_mode() else 'Python Script'}")
    print("=" * 52)

    # Cek update & ambil config online
    check_and_update()

    active_url   = RUNTIME_URL
    active_title = RUNTIME_TITLE

    print(f"  URL   : {active_url}")
    print(f"  Title : {active_title}")
    print("=" * 52)

    block_keys()
    setup_exit_hotkey()
    launch_edge(active_url)

    print("[NeoTest] Menunggu Edge siap...")
    time.sleep(3)

    root = create_overlay(active_url, active_title)

    def delayed_reposition():
        time.sleep(1.5)
        reposition_edge_window()
        bring_overlay_front()

    threading.Thread(target=delayed_reposition, daemon=True).start()
    threading.Thread(
        target=monitor_edge, args=(active_url,), daemon=True
    ).start()

    try:
        root.mainloop()
    except Exception as e:
        print(f"[ERR] mainloop: {e}")
    do_exit()


if __name__ == "__main__":
    main()
