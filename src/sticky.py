# -*- coding: utf-8 -*-
"""
轻便签 —— 桌面悬浮便签
- 置顶悬浮、无边框、可拖动、可缩放
- 支持待办勾选（点击行首方框）
- 多张便签切换，自动保存
- 多配色、字号、透明度
"""
import ctypes
import json
import os
import re
import sys
import time
import tkinter as tk
from tkinter import font as tkfont, simpledialog

APP_NAME = "轻便签"


def _app_home():
    """程序所在目录：打包后是 exe 同级，开发时是项目根。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DATA_DIR = os.path.join(_app_home(), "data")
DATA_FILE = os.path.join(DATA_DIR, "notes.json")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "StickyNotesLite"

TODO_UNDONE = "\u2610"   # ☐
TODO_DONE = "\u2611"     # ☑

THEMES = {
    "奶黄": dict(bg="#FDF7D9", bar="#F6E9A9", line="#EADFA0", fg="#3C3A32",
                 sub="#8F8763", accent="#C9962A", done="#A79C74", edge="#D6C57C"),
    "薄荷": dict(bg="#E6F6EC", bar="#C9EBD6", line="#B5DFC5", fg="#2E3D33",
                 sub="#6E8C79", accent="#2F9463", done="#8FAF9B", edge="#A6D5BA"),
    "淡蓝": dict(bg="#E8F1FB", bar="#CEDFF5", line="#BBD1EC", fg="#2C3A4A",
                 sub="#6C819A", accent="#2F72B8", done="#96A9BE", edge="#A7C4E2"),
    "淡粉": dict(bg="#FCEDF0", bar="#F6D3DB", line="#EFC3CD", fg="#463038",
                 sub="#96707C", accent="#C45E7B", done="#B89AA2", edge="#E7ACBA"),
    "夜间": dict(bg="#26282B", bar="#33363B", line="#3E4248", fg="#E4E7EA",
                 sub="#8B9199", accent="#6FA8DC", done="#6D747C", edge="#484D54"),
}

DEFAULT_DATA = {
    "settings": {
        "theme": "奶黄", "font_size": 11, "alpha": 0.96, "topmost": True,
        "x": None, "y": None, "w": 320, "h": 400,
    },
    "notes": [{"title": "便签 1", "content": ""}],
    "current": 0,
}


# ---------------------------------------------------------------- 系统小工具
def enable_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def already_running():
    ctypes.windll.kernel32.CreateMutexW(None, False, "StickyNotesLite_Mutex_v1")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def activate_existing():
    """已经开着的时候再次双击图标：把窗口叫回前台，而不是开第二个。"""
    try:
        u = ctypes.windll.user32
        hwnd = u.FindWindowW(None, APP_NAME)
        if not hwnd:
            return False
        u.ShowWindow(hwnd, 5)   # SW_SHOW
        u.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def app_exe():
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, RUN_NAME)
            return bool(val)
    except Exception:
        return False


def set_autostart(enabled):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ,
                                  '"%s"' % app_exe())
            else:
                try:
                    winreg.DeleteValue(k, RUN_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- 数据
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))
    base = json.loads(json.dumps(DEFAULT_DATA))
    base["settings"].update(d.get("settings") or {})
    notes = d.get("notes")
    if isinstance(notes, list) and notes:
        base["notes"] = [{"title": n.get("title") or "便签",
                          "content": n.get("content") or ""} for n in notes]
    cur = d.get("current", 0)
    base["current"] = cur if isinstance(cur, int) and 0 <= cur < len(base["notes"]) else 0
    return base


def save_data(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, DATA_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------- 控件
class FlatButton(tk.Label):
    """跟随主题的扁平按钮。"""

    def __init__(self, master, text, command, app, width=3, font=None):
        super().__init__(master, text=text, width=width, bd=0,
                         font=font or app.ui_font, cursor="hand2")
        self.command = command
        self.app = app
        self.hover = False
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _click(self, e):
        if self.command:
            self.command()

    def _enter(self, e):
        self.hover = True
        self.paint()

    def _leave(self, e):
        self.hover = False
        self.paint()

    def paint(self, bg=None, fg=None):
        th = self.app.theme
        b = bg if self.hover else (self.master["bg"] if bg is None else bg)
        self.configure(bg=self.app.theme["bar"] if self.hover else self.master["bg"],
                       fg=th["accent"] if self.hover else th["sub"])


# ---------------------------------------------------------------- 主程序
class StickyApp:
    def _set_icon(self):
        try:
            base = getattr(sys, "_MEIPASS", None) or os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            for cand in (os.path.join(base, "note.ico"),
                         os.path.join(base, "assets", "note.ico")):
                if os.path.exists(cand):
                    self.root.iconbitmap(default=cand)
                    return
        except Exception:
            pass

    def __init__(self):
        self.data = load_data()
        self.st = self.data["settings"]
        self.root = tk.Tk()
        self.root.title("轻便签")
        self._set_icon()
        self.root.configure(bg="#000000")
        self.root.withdraw()

        family = "Microsoft YaHei UI"
        self.ui_font = tkfont.Font(family=family, size=9)
        self.title_font = tkfont.Font(family=family, size=9, weight="bold")
        self.body_font = tkfont.Font(family=family, size=self.st["font_size"])
        self.icon_font = tkfont.Font(family=family, size=12)

        self.scale = self._dpi_scale()
        self._save_job = None
        self._loading = False
        self._dragging = False
        self.collapsed = False
        self._expanded_h = self.st["h"]
        self.var_topmost = tk.BooleanVar(master=self.root, value=bool(self.st["topmost"]))
        self.var_autostart = tk.BooleanVar(master=self.root, value=False)
        self.build_ui()
        self.apply_theme()
        self.load_note(self.data["current"])

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.bind("<Control-n>", lambda e: self.new_note())
        self.root.bind("<Control-d>", lambda e: self.make_todo())
        self.root.bind("<Control-s>", lambda e: self.force_save())
        self.root.bind("<Control-plus>", lambda e: self.change_font(1))
        self.root.bind("<Control-equal>", lambda e: self.change_font(1))
        self.root.bind("<Control-minus>", lambda e: self.change_font(-1))
        self.root.bind("<Escape>", lambda e: self.force_save())
        self.root.deiconify()
        self._make_borderless()
        self.restore_geometry()
        self.root.bind("<Map>", self._on_map)
        self.root.after(300, self._make_borderless)
        self.root.attributes("-topmost", bool(self.st["topmost"]))
        self.root.attributes("-alpha", float(self.st["alpha"]))
        self.root.after(120, lambda: self.text.focus_force())
        self.root.after(30000, self._tick_status)

    # ------------------------------------------------------------ 界面
    def _make_borderless(self):
        """去掉系统标题栏和边框，但保留任务栏按钮（可以从任务栏最小化/恢复）。

        必须幂等：SetWindowPos(SWP_FRAMECHANGED) 会触发 <Map>，若这里无条件重设，
        就会和 _on_map 形成自我触发的死循环，拖动结束后集中爆发直接崩进程。
        """
        try:
            u = ctypes.windll.user32
            u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            u.GetAncestor.restype = ctypes.c_void_p
            hwnd = u.GetAncestor(ctypes.c_void_p(self.root.winfo_id()), 2) or self.root.winfo_id()
            GWL_STYLE = -16
            try:
                u.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
                u.GetWindowLongPtrW.restype = ctypes.c_longlong
                style = int(u.GetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_STYLE))
                setter = u.SetWindowLongPtrW
                setter.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
                setter.restype = ctypes.c_longlong
            except AttributeError:
                style = int(u.GetWindowLongW(hwnd, GWL_STYLE))
                setter = u.SetWindowLongW
            # 已经是无标题栏、无粗边框 —— 说明处理过了，直接返回，别再动窗口
            if not (style & 0x00C00000) and not (style & 0x00040000):
                self._hwnd = hwnd
                return
            style &= ~0x00C00000   # WS_CAPTION
            style &= ~0x00040000   # WS_THICKFRAME
            style &= ~0x00010000   # WS_MAXIMIZEBOX
            style &= ~0x00080000   # WS_SYSMENU
            style |= 0x00020000    # WS_MINIMIZEBOX
            setter(ctypes.c_void_p(hwnd), GWL_STYLE, style)
            u.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_int, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            u.SetWindowPos(ctypes.c_void_p(hwnd), None, 0, 0, 0, 0, 0x0027)
            self._hwnd = hwnd
        except Exception:
            import traceback
            _log("borderless FAIL\n" + traceback.format_exc())

    def _on_map(self, event=None):
        """从任务栏恢复时重新置顶（iconify 之后 topmost 会失效）。

        注意这里绝不能再调 _make_borderless，否则形成事件回环。
        """
        if event is not None and event.widget is not self.root:
            return
        if self.st.get("topmost"):
            try:
                self.root.attributes("-topmost", True)
            except Exception:
                pass

    def minimize(self):
        """最小化到任务栏。"""
        self.force_save()
        try:
            self.root.iconify()
        except Exception:
            pass

    def _dpi_scale(self):
        try:
            return max(1.0, min(4.0, self.root.winfo_fpixels("1i") / 96.0))
        except Exception:
            return 1.0

    def S(self, v):
        """把 96dpi 下的逻辑像素换算成当前屏幕的物理像素。"""
        return max(1, int(round(v * self.scale)))

    def build_ui(self):
        self.border = tk.Frame(self.root, bg="#000000")
        self.border.pack(fill="both", expand=True)

        self.outer = tk.Frame(self.border)
        self.outer.pack(fill="both", expand=True, padx=1, pady=1)

        # 标题栏
        self.titlebar = tk.Frame(self.outer, height=self.S(30))
        self.titlebar.pack(fill="x")
        self.titlebar.pack_propagate(False)

        self.dot = tk.Label(self.titlebar, text="\u25cf", bd=0)  # ●
        self.dot.pack(side="left", padx=(self.S(10), self.S(4)))

        self.title_lbl = tk.Label(self.titlebar, text="便签", bd=0,
                                  font=self.title_font, anchor="w")
        self.title_lbl.pack(side="left", fill="x", expand=True)

        self.btn_menu = FlatButton(self.titlebar, "\u22ee", self.show_menu, self, width=2)
        self.btn_menu.pack(side="right", padx=(0, 6), pady=6)
        self.btn_close = FlatButton(self.titlebar, "\u2715", self.quit_app, self, width=2)
        self.btn_close.pack(side="right", pady=6)
        self.btn_min = FlatButton(self.titlebar, "\u2014", self.minimize, self, width=2)
        self.btn_min.pack(side="right", pady=6)
        self.btn_fold = FlatButton(self.titlebar, "\u25bc", self.toggle_collapse, self,
                                   width=2, font=self.icon_font)
        self.btn_fold.pack(side="right", pady=6)

        for w in (self.titlebar, self.dot, self.title_lbl):
            w.bind("<Button-1>", self.drag_start)
            w.bind("<B1-Motion>", self.drag_move)
            w.bind("<ButtonRelease-1>", self.drag_end)
            w.bind("<Button-3>", lambda e: self.show_menu(e))

        # 便签切换条
        self.tabbar = tk.Frame(self.outer, height=self.S(26))
        self.tabbar.pack(fill="x")
        self.tabbar.pack_propagate(False)

        # 状态栏（必须在文本区之前 pack，否则会被 expand 挤掉）
        self.statusbar = tk.Frame(self.outer, height=self.S(24))
        self.statusbar.pack(fill="x", side="bottom")
        self.statusbar.pack_propagate(False)
        self.status_lbl = tk.Label(self.statusbar, text="", anchor="w", bd=0,
                                   font=self.ui_font)
        self.status_lbl.pack(side="left", padx=self.S(10))
        self.status_right = tk.Label(self.statusbar, text="", anchor="e", bd=0,
                                     font=self.ui_font)
        self.status_right.pack(side="right", padx=(10, 20))

        # 文本区（最后 pack，占满剩余空间）
        self.text_frame = tk.Frame(self.outer)
        self.text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(self.text_frame, bd=0, highlightthickness=0,
                            wrap="word", undo=True, padx=self.S(12), pady=self.S(10),
                            font=self.body_font, spacing1=3, spacing3=3,
                            cursor="xterm", tabs=("28",))
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind("<<Modified>>", self.on_modified)
        self.text.bind("<Button-1>", self.on_click, add="+")
        self.text.bind("<Motion>", self.on_motion, add="+")
        self.text.bind("<Button-3>", self.show_menu)
        self.text.bind("<Control-MouseWheel>", self.on_ctrl_wheel)

        # 右下角缩放手柄（真实尺寸按缩放计算）
        self.grip = tk.Label(self.outer, text="\u25e2", bd=0, cursor="size_nw_se")
        self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.grip.bind("<Button-1>", self.resize_start)
        self.grip.bind("<B1-Motion>", self.resize_move)

        self.refresh_tabs()

    # ------------------------------------------------------------ 主题
    @property
    def theme(self):
        return THEMES.get(self.st["theme"], THEMES["奶黄"])

    def apply_theme(self):
        th = self.theme
        self.root.configure(bg=th["edge"])
        self.border.configure(bg=th["edge"])
        self.outer.configure(bg=th["bg"])
        self.titlebar.configure(bg=th["bar"])
        self.dot.configure(bg=th["bar"], fg=th["accent"])
        self.title_lbl.configure(bg=th["bar"], fg=th["fg"])
        for b in (self.btn_menu, self.btn_close, self.btn_min, self.btn_fold):
            b.configure(bg=th["bar"], fg=th["sub"])
        self.tabbar.configure(bg=th["bg"])
        self.text_frame.configure(bg=th["bg"])
        self.text.configure(bg=th["bg"], fg=th["fg"], insertbackground=th["accent"],
                            selectbackground=th["accent"], selectforeground=th["bg"])
        self.text.tag_configure("todo_done", foreground=th["done"], overstrike=True)
        self.text.tag_configure("todo_open", foreground=th["fg"])
        self.statusbar.configure(bg=th["line"])
        self.status_lbl.configure(bg=th["line"], fg=th["sub"])
        self.status_right.configure(bg=th["line"], fg=th["sub"])
        self.grip.configure(bg=th["bg"], fg=th["line"])
        self.refresh_tabs()
        self.refresh_tags()

    # ------------------------------------------------------------ 便签条
    def refresh_tabs(self):
        th = self.theme
        for w in self.tabbar.winfo_children():
            w.destroy()
        for i, n in enumerate(self.data["notes"]):
            active = (i == self.data["current"])
            lbl = tk.Label(self.tabbar, text=str(i + 1), width=2, bd=0,
                           font=self.ui_font, cursor="hand2",
                           bg=th["bar"] if active else th["bg"],
                           fg=th["fg"] if active else th["sub"])
            lbl.pack(side="left", padx=(6 if i == 0 else 2, 0), pady=4)
            lbl.bind("<Button-1>", lambda e, k=i: self.switch_note(k))
            lbl.bind("<Button-3>", lambda e, k=i: self.tab_menu(e, k))
            lbl.bind("<Enter>", lambda e, w=lbl: w.configure(fg=self.theme["accent"]))
            lbl.bind("<Leave>", lambda e, w=lbl, a=active:
                     w.configure(fg=self.theme["fg"] if a else self.theme["sub"]))
        add = tk.Label(self.tabbar, text="+", width=2, bd=0, font=self.ui_font,
                       cursor="hand2", bg=th["bg"], fg=th["sub"])
        add.pack(side="left", padx=2, pady=4)
        add.bind("<Button-1>", lambda e: self.new_note())
        add.bind("<Enter>", lambda e: add.configure(fg=self.theme["accent"]))
        add.bind("<Leave>", lambda e: add.configure(fg=self.theme["sub"]))

    def tab_menu(self, event, idx):
        th = self.theme
        m = tk.Menu(self.root, tearoff=0, bg=th["bg"], fg=th["fg"],
                    activebackground=th["accent"], activeforeground=th["bg"],
                    bd=0, font=self.ui_font)
        m.add_command(label="重命名", command=lambda: self.rename_note(idx))
        m.add_command(label="删除这张", command=lambda: self.delete_note(idx))
        m.tk_popup(event.x_root, event.y_root)

    def switch_note(self, idx):
        if idx == self.data["current"]:
            return
        self.stash_current()
        self.data["current"] = idx
        self.load_note(idx)
        self.refresh_tabs()
        self.save_now()

    def new_note(self):
        self.stash_current()
        self.data["notes"].append({"title": "便签 %d" % (len(self.data["notes"]) + 1),
                                   "content": ""})
        self.data["current"] = len(self.data["notes"]) - 1
        self.load_note(self.data["current"])
        self.refresh_tabs()
        self.save_now()
        self.text.focus_force()

    def rename_note(self, idx):
        old = self.data["notes"][idx]["title"]
        new = simpledialog.askstring("重命名", "便签名称：", initialvalue=old,
                                     parent=self.root)
        if new:
            self.data["notes"][idx]["title"] = new.strip()[:24]
            if idx == self.data["current"]:
                self.title_lbl.configure(text=self.data["notes"][idx]["title"])
            self.save_now()

    def delete_note(self, idx):
        if len(self.data["notes"]) <= 1:
            self.data["notes"][0]["content"] = ""
            self.data["notes"][0]["title"] = "便签 1"
            self.data["current"] = 0
        else:
            del self.data["notes"][idx]
            if self.data["current"] >= len(self.data["notes"]):
                self.data["current"] = len(self.data["notes"]) - 1
            elif idx < self.data["current"]:
                self.data["current"] -= 1
        self.load_note(self.data["current"])
        self.refresh_tabs()
        self.save_now()

    # ------------------------------------------------------------ 内容
    def load_note(self, idx):
        n = self.data["notes"][idx]
        self._loading = True
        self.text.delete("1.0", "end")
        self.text.insert("1.0", n.get("content", ""))
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._loading = False
        self.title_lbl.configure(text=n.get("title") or "便签")
        self.refresh_tags()
        self.text.mark_set("insert", "end-1c")
        self.text.see("insert")

    def stash_current(self):
        i = self.data["current"]
        if 0 <= i < len(self.data["notes"]):
            try:
                self.data["notes"][i]["content"] = self.text.get("1.0", "end-1c")
            except Exception:
                pass

    def on_modified(self, event=None):
        if self._loading:
            return
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.refresh_tags()
        self.schedule_save()

    def schedule_save(self):
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(700, self.save_now)

    def save_now(self):
        self._save_job = None
        self.stash_current()
        self.st["x"] = self.root.winfo_x()
        self.st["y"] = self.root.winfo_y()
        if not self.collapsed and self.scale:
            self.st["w"] = int(round(self.root.winfo_width() / self.scale))
            self.st["h"] = int(round(self.root.winfo_height() / self.scale))
        save_data(self.data)
        self.update_status(saved=True)

    def force_save(self):
        self.save_now()
        return "break"

    # ------------------------------------------------------------ 待办
    def refresh_tags(self):
        th = self.theme
        self.text.tag_remove("todo_done", "1.0", "end")
        self.text.tag_remove("todo_open", "1.0", "end")
        total = done = 0
        last = int(self.text.index("end-1c").split(".")[0])
        for i in range(1, last + 1):
            line = self.text.get("%d.0" % i, "%d.end" % i)
            s = line.lstrip()
            if s.startswith(TODO_UNDONE):
                total += 1
                self.text.tag_add("todo_open", "%d.0" % i, "%d.end" % i)
            elif s.startswith(TODO_DONE):
                total += 1
                done += 1
                self.text.tag_add("todo_done", "%d.0" % i, "%d.end" % i)
        self.todo_total, self.todo_done = total, done
        self.update_status()

    def update_status(self, saved=False):
        total = getattr(self, "todo_total", 0)
        done = getattr(self, "todo_done", 0)
        if total:
            left = "%d 项待办 · 完成 %d" % (total, done)
        else:
            left = "Ctrl+D 新建待办"
        self.status_lbl.configure(text=left)
        self.status_right.configure(
            text=("已保存 %s" % time.strftime("%H:%M")) if saved else
            ("%d 字" % len(self.text.get("1.0", "end-1c").strip())))
        self.statusbar.configure(bg=self.theme["line"])
        self.status_lbl.configure(bg=self.theme["line"], fg=self.theme["sub"])
        self.status_right.configure(bg=self.theme["line"], fg=self.theme["sub"])

    def _tick_status(self):
        try:
            self.update_status()
            self.root.after(30000, self._tick_status)
        except Exception:
            pass

    def line_has_todo(self, lineno):
        line = self.text.get("%d.0" % lineno, "%d.end" % lineno).lstrip()
        return line.startswith(TODO_UNDONE) or line.startswith(TODO_DONE)

    def on_motion(self, event):
        try:
            idx = self.text.index("@%d,%d" % (event.x, event.y))
            ln, col = (int(v) for v in idx.split("."))
            on_box = col <= 2 and self.line_has_todo(ln)
            self.text.configure(cursor="hand2" if on_box else "xterm")
        except Exception:
            pass

    def on_click(self, event):
        try:
            idx = self.text.index("@%d,%d" % (event.x, event.y))
            ln, col = (int(v) for v in idx.split("."))
            if col <= 2 and self.line_has_todo(ln):
                self.toggle_todo(ln)
                return "break"
        except Exception:
            pass

    def toggle_todo(self, ln):
        line = self.text.get("%d.0" % ln, "%d.end" % ln)
        stripped = line.lstrip()
        if stripped.startswith(TODO_DONE):
            new = line.replace(TODO_DONE, TODO_UNDONE, 1)
        elif stripped.startswith(TODO_UNDONE):
            new = line.replace(TODO_UNDONE, TODO_DONE, 1)
        else:
            return
        self.text.delete("%d.0" % ln, "%d.end" % ln)
        self.text.insert("%d.0" % ln, new)
        self.refresh_tags()
        self.schedule_save()

    def make_todo(self):
        """把当前行变成待办；空行则插入一条新待办。"""
        try:
            ln = int(self.text.index("insert").split(".")[0])
            line = self.text.get("%d.0" % ln, "%d.end" % ln)
            if line.lstrip().startswith(TODO_UNDONE) or line.lstrip().startswith(TODO_DONE):
                return "break"
            if not line.strip():
                self.text.insert("insert", TODO_UNDONE + " ")
            else:
                self.text.insert("%d.0" % ln, TODO_UNDONE + " ")
            self.refresh_tags()
            self.schedule_save()
        except Exception:
            pass
        return "break"

    # ------------------------------------------------------------ 窗口
    def restore_geometry(self):
        w = self.S(int(self.st.get("w") or 320))
        h = self.S(int(self.st.get("h") or 400))
        x, y = self.st.get("x"), self.st.get("y")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if x is None or y is None:
            x, y = sw - w - 40, 70
        else:
            # 钳到屏幕内：否则拖到边缘后重启，窗口会一半在屏幕外甚至完全找不到
            x = max(0, min(int(x), max(0, sw - w)))
            y = max(0, min(int(y), max(0, sh - h)))
        self._expanded_h = h
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _set_layered(self, on):
        """临时开/关窗口的分层（半透明）属性。

        半透明窗口（WS_EX_LAYERED）快速移动时 DWM 合成跟不上，会闪黑/撕裂。
        拖动期间关掉它，系统直接 blit 窗口内容，拖完再恢复。
        """
        try:
            u = ctypes.windll.user32
            hwnd = getattr(self, "_hwnd", None)
            if not hwnd:
                u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                u.GetAncestor.restype = ctypes.c_void_p
                hwnd = u.GetAncestor(ctypes.c_void_p(self.root.winfo_id()), 2) \
                    or self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            u.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            u.GetWindowLongPtrW.restype = ctypes.c_longlong
            u.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
            u.SetWindowLongPtrW.restype = ctypes.c_longlong
            ex = int(u.GetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE))
            if on:
                u.SetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex | WS_EX_LAYERED)
                u.SetLayeredWindowAttributes.argtypes = [
                    ctypes.c_void_p, ctypes.c_uint, ctypes.c_ubyte, ctypes.c_uint]
                u.SetLayeredWindowAttributes(
                    ctypes.c_void_p(hwnd), 0,
                    max(0, min(255, int(float(self.st.get("alpha", 0.96)) * 255))),
                    0x00000002)  # LWA_ALPHA
            else:
                u.SetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, ex & ~WS_EX_LAYERED)
            self._hwnd = hwnd
        except Exception:
            pass

    def drag_start(self, e):
        """拖动开始。

        不能用 SendMessageW(WM_NCLBUTTONDOWN) 交给系统拖 —— 那会让 Python 主线程
        整个阻塞在 C 调用里，而系统拖动循环还在派发消息，tk 回调在栈被冻住的状态下
        执行，会把 ucrtbase 干崩（BEX64 / c0000409）。
        """
        now = time.time()
        if now - getattr(self, "_last_click", 0) < 0.35:
            # 350ms 内第二次按下 = 双击，折叠/展开，不走拖动
            self._last_click = 0
            self.toggle_collapse()
            return "break"
        self._last_click = now
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()
        self._dragging = True
        self._set_layered(False)   # 拖动期间不透明，避免合成闪黑

    def drag_move(self, e):
        if not getattr(self, "_dragging", False):
            return
        self.root.geometry("+%d+%d" % (e.x_root - self._dx, e.y_root - self._dy))

    def drag_end(self, e):
        if getattr(self, "_dragging", False):
            self._dragging = False
            self._set_layered(True)   # 恢复半透明
        self.schedule_save()

    def resize_start(self, e):
        self._rw = self.root.winfo_width()
        self._rh = self.root.winfo_height()
        self._rx = e.x_root
        self._ry = e.y_root

    def resize_move(self, e):
        w = max(self.S(230), self._rw + (e.x_root - self._rx))
        h = max(self.S(150), self._rh + (e.y_root - self._ry))
        self.root.geometry("%dx%d" % (w, h))

    def toggle_collapse(self):
        if self.collapsed:
            self.root.geometry("%dx%d" % (self.root.winfo_width(), self._expanded_h))
            self.tabbar.pack(fill="x", after=self.titlebar)
            self.statusbar.pack(fill="x", side="bottom")
            self.text_frame.pack(fill="both", expand=True, after=self.tabbar)
            self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
            self.collapsed = False
        else:
            self._expanded_h = self.root.winfo_height()
            self.tabbar.pack_forget()
            self.text_frame.pack_forget()
            self.statusbar.pack_forget()
            self.grip.place_forget()
            self.root.geometry("%dx%d" % (self.root.winfo_width(), self.S(30) + 2))
            self.collapsed = True
        self.btn_fold.configure(text="\u25b2" if self.collapsed else "\u25bc")
        self.root.update_idletasks()
        self.schedule_save()

    def on_ctrl_wheel(self, event):
        self.change_font(1 if event.delta > 0 else -1)
        return "break"

    def change_font(self, delta):
        size = max(8, min(22, self.st["font_size"] + delta))
        self.st["font_size"] = size
        self.body_font.configure(size=size)
        self.schedule_save()

    def change_alpha(self, delta):
        a = round(min(1.0, max(0.45, float(self.st["alpha"]) + delta)), 2)
        self.st["alpha"] = a
        self.root.attributes("-alpha", a)
        self.schedule_save()

    def set_theme(self, name):
        self.st["theme"] = name
        self.apply_theme()
        self.schedule_save()

    def toggle_topmost(self):
        val = bool(self.var_topmost.get())
        self.st["topmost"] = val
        self.root.attributes("-topmost", val)
        self.schedule_save()

    def toggle_autostart(self):
        enabled = bool(self.var_autostart.get())
        if not set_autostart(enabled):
            self.var_autostart.set(autostart_enabled())

    def default_font(self):
        self.st["font_size"] = 11
        self.body_font.configure(size=11)
        self.schedule_save()

    def open_data_dir(self):
        try:
            os.startfile(DATA_DIR)
        except Exception:
            pass

    def about(self):
        info = ("轻便签 v1.0\n\n"
                "· 点击行首方框勾选待办\n"
                "· Ctrl+D 把当前行变成待办\n"
                "· Ctrl+N 新建便签　Ctrl+加减 调字号\n"
                "· 拖标题栏移动，拖右下角缩放\n"
                "· 双击标题栏收起/展开\n"
                "· 右键或 ⋮ 打开设置\n\n"
                "数据：%s" % DATA_FILE)
        try:
            from tkinter import messagebox
            messagebox.showinfo("使用说明", info, parent=self.root)
        except Exception:
            pass

    def show_menu(self, event=None):
        th = self.theme
        m = tk.Menu(self.root, tearoff=0, bg=th["bg"], fg=th["fg"],
                    activebackground=th["accent"], activeforeground=th["bg"],
                    bd=0, font=self.ui_font)

        tm = tk.Menu(m, tearoff=0, bg=th["bg"], fg=th["fg"],
                     activebackground=th["accent"], activeforeground=th["bg"],
                     bd=0, font=self.ui_font)
        for name in THEMES:
            tm.add_command(label=("✓ " if name == self.st["theme"] else "　 ") + name,
                           command=lambda n=name: self.set_theme(n))
        m.add_cascade(label="配色", menu=tm)

        fm = tk.Menu(m, tearoff=0, bg=th["bg"], fg=th["fg"],
                     activebackground=th["accent"], activeforeground=th["bg"],
                     bd=0, font=self.ui_font)
        fm.add_command(label="加大一档", command=lambda: self.change_font(1))
        fm.add_command(label="减小一档", command=lambda: self.change_font(-1))
        fm.add_command(label="恢复默认", command=self.default_font)
        m.add_cascade(label="字号 (%d)" % self.st["font_size"], menu=fm)

        am = tk.Menu(m, tearoff=0, bg=th["bg"], fg=th["fg"],
                     activebackground=th["accent"], activeforeground=th["bg"],
                     bd=0, font=self.ui_font)
        am.add_command(label="更透明", command=lambda: self.change_alpha(-0.08))
        am.add_command(label="更实一点", command=lambda: self.change_alpha(0.08))
        m.add_cascade(label="透明度", menu=am)

        self.var_topmost.set(bool(self.st["topmost"]))
        self.var_autostart.set(autostart_enabled())
        m.add_checkbutton(label="窗口置顶", command=self.toggle_topmost,
                          onvalue=1, offvalue=0, variable=self.var_topmost,
                          selectcolor=th["accent"])
        m.add_separator()
        m.add_command(label="最小化到任务栏", command=self.minimize)
        m.add_command(label="展开" if self.collapsed else "折叠成一条",
                      command=self.toggle_collapse)
        m.add_command(label="新建便签", command=self.new_note)
        m.add_command(label="重命名当前便签", command=lambda: self.rename_note(self.data["current"]))
        m.add_separator()
        m.add_checkbutton(label="开机自动启动",
                          command=self.toggle_autostart,
                          onvalue=1, offvalue=0,
                          variable=self.var_autostart,
                          selectcolor=th["accent"])
        m.add_command(label="打开数据文件夹", command=self.open_data_dir)
        m.add_command(label="使用说明", command=self.about)
        m.add_separator()
        m.add_command(label="退出", command=self.quit_app)

        try:
            if event is not None:
                m.tk_popup(event.x_root, event.y_root)
            else:
                m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            m.grab_release()

    def quit_app(self):
        try:
            self.save_now()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def _log(msg):
    try:
        with open(os.path.join(_app_home(), "startup.log"), "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def main():
    # 无控制台打包模式下 stdout/stderr 是 None，tkinter 初始化会卡住，必须补上
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    enable_dpi()
    if already_running():
        activate_existing()
        return
    try:
        StickyApp().run()
    except Exception:
        import traceback
        _log("CRASH\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
