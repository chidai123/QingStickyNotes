# -*- coding: utf-8 -*-
"""轻便签 v2：Windows 原生桌面便签，Python 3.9+，无第三方运行依赖。"""
import json
import os
import sys
import uuid
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

APP_NAME = '轻便签'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
RUN_NAME = 'QingStickyNotes'
PALETTES = [
    ('奶油黄', '#FFF1B8', '#FFF8DC'), ('薄荷绿', '#C6F0D5', '#E8F9EB'),
    ('天空蓝', '#CDE9FC', '#EFF8FF'), ('樱花粉', '#FFD5DE', '#FFF0F4'),
    ('淡紫色', '#E4D8FF', '#F5F0FF'), ('暖白色', '#E7E7E7', '#FAFAFA'),
]
DATA_DIR = Path(os.getenv('APPDATA') or Path.home()) / 'QingStickyNotes'
DATA_FILE = DATA_DIR / 'notes.json'
FONT = 'Microsoft YaHei UI'


def launch_command():
    """EXE 使用当前 EXE；源码使用 pythonw.exe 启动，均不弹出控制台。"""
    if getattr(sys, 'frozen', False):
        return f'"{Path(sys.executable).resolve()}"'
    interpreter = Path(sys.executable).resolve()
    if interpreter.name.lower() == 'python.exe':
        candidate = interpreter.with_name('pythonw.exe')
        if candidate.exists():
            interpreter = candidate
    return f'"{interpreter}" "{Path(__file__).resolve()}"'


def startup_enabled():
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
        return True
    except FileNotFoundError:
        return False


def set_startup(enabled):
    """仅写入当前用户启动项，不需要管理员权限。"""
    if sys.platform != 'win32':
        raise OSError('开机自启只支持 Windows')
    import winreg
    if enabled:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, launch_command())
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, RUN_NAME)
        except FileNotFoundError:
            pass


class StickyApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.notes = {}
        self.windows = {}
        self.pending_save = None
        self.load()
        if not self.notes:
            self.add_note()
        else:
            for key in list(self.notes):
                self.open_note(key)
        self.root.bind_all('<Control-Shift-N>', lambda e: self.add_note())
        self.root.mainloop()

    def load(self):
        try:
            if DATA_FILE.exists():
                payload = json.loads(DATA_FILE.read_text(encoding='utf-8'))
                if isinstance(payload, dict) and isinstance(payload.get('notes'), list):
                    for note in payload['notes']:
                        if isinstance(note, dict) and isinstance(note.get('id'), str) and note['id']:
                            # 兼容 v1：保留原文字/颜色/尺寸，补上新字段
                            note.setdefault('tasks', [])
                            if not isinstance(note['tasks'], list):
                                note['tasks'] = []
                            self.notes[note['id']] = note
        except (OSError, ValueError, UnicodeError) as exc:
            messagebox.showwarning(APP_NAME, f'读取旧便签失败，原文件未删除：\n{exc}')

    def save_later(self):
        if self.pending_save is not None:
            self.root.after_cancel(self.pending_save)
        self.pending_save = self.root.after(350, self.save)

    def save(self):
        if self.pending_save is not None:
            self.root.after_cancel(self.pending_save)
            self.pending_save = None
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            temp = DATA_FILE.with_suffix('.tmp')
            temp.write_text(json.dumps({'version': 2, 'notes': list(self.notes.values())}, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, DATA_FILE)
        except OSError as exc:
            messagebox.showerror('保存失败', f'便签无法保存：\n{exc}')

    def add_note(self):
        key = uuid.uuid4().hex
        offset = (len(self.notes) % 8) * 28
        self.notes[key] = {'id': key, 'text': '', 'tasks': [], 'color': 0, 'topmost': False,
                           'geometry': f'355x480+{140+offset}+{110+offset}'}
        self.open_note(key)
        self.save_later()

    def open_note(self, key):
        note = self.notes[key]
        win = tk.Toplevel(self.root)
        self.windows[key] = win
        win.title('轻便签 · 待办与随手记')
        win.geometry(note.get('geometry') or '355x480+140+110')
        win.minsize(300, 340)
        win.attributes('-topmost', bool(note.get('topmost', False)))
        idx = int(note.get('color', 0)) % len(PALETTES)
        header, paper = PALETTES[idx][1:]
        bar = tk.Frame(win, bg=header, height=43)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        title = tk.Label(bar, text='✦ 轻便签', bg=header, fg='#333', font=(FONT, 11, 'bold'))
        title.pack(side='left', padx=12)

        def flat_btn(label, action, width=4):
            b = tk.Button(bar, text=label, command=action, bg=header, fg='#333', relief='flat',
                          bd=0, width=width, font=(FONT, 9), activebackground=header, cursor='hand2')
            b.pack(side='right', padx=1, pady=4)
            return b

        flat_btn('＋', self.add_note, 3)

        def toggle_top():
            note['topmost'] = not bool(note.get('topmost'))
            win.attributes('-topmost', note['topmost'])
            pin.configure(text='已置顶' if note['topmost'] else '置顶')
            self.save_later()

        pin = flat_btn('已置顶' if note.get('topmost') else '置顶', toggle_top, 5)
        flat_btn('换色', lambda: recolor(), 5)
        flat_btn('设置', lambda: settings(), 5)

        content = tk.Frame(win, bg=paper)
        content.pack(fill='both', expand=True)
        tk.Label(content, text='随手记录', bg=paper, fg='#6D6D6D', anchor='w',
                 font=(FONT, 9, 'bold')).pack(fill='x', padx=14, pady=(8, 0))
        txt = tk.Text(content, undo=True, wrap='word', bg=paper, fg='#252525',
                      font=(FONT, 11), relief='flat', bd=0, height=6,
                      padx=14, pady=7, insertbackground='#333', selectbackground='#A4C9EC')
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', note.get('text', ''))
        tk.Label(content, text='待办事项（勾选即完成）', bg=paper, fg='#6D6D6D', anchor='w',
                 font=(FONT, 9, 'bold')).pack(fill='x', padx=14, pady=(6, 4))
        input_bar = tk.Frame(content, bg=paper)
        input_bar.pack(fill='x', padx=12)
        task_input = tk.Entry(input_bar, font=(FONT, 10), bd=1, relief='solid')
        task_input.pack(side='left', fill='x', expand=True, ipady=5)
        task_list_container = tk.Frame(content, bg=paper)
        task_list_container.pack(fill='both', expand=True, padx=11, pady=(7, 2))
        task_canvas = tk.Canvas(task_list_container, bg=paper, highlightthickness=0, height=105)
        scrollbar = tk.Scrollbar(task_list_container, orient='vertical', command=task_canvas.yview)
        task_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        task_canvas.pack(side='left', fill='both', expand=True)
        task_rows = tk.Frame(task_canvas, bg=paper)
        rows_window = task_canvas.create_window((0, 0), window=task_rows, anchor='nw')
        task_rows.bind('<Configure>', lambda e: task_canvas.configure(scrollregion=task_canvas.bbox('all')))
        task_canvas.bind('<Configure>', lambda e: task_canvas.itemconfigure(rows_window, width=e.width))

        def render_tasks():
            for child in task_rows.winfo_children():
                child.destroy()
            for task in list(note['tasks']):
                if not isinstance(task, dict):
                    continue
                row = tk.Frame(task_rows, bg=paper)
                row.pack(fill='x', pady=2)
                checked = tk.BooleanVar(value=bool(task.get('done', False)))
                def on_check(t=task, v=checked):
                    t['done'] = bool(v.get())
                    self.save_later()
                    render_tasks()
                cb = tk.Checkbutton(row, variable=checked, command=on_check, bg=paper,
                                    activebackground=paper, highlightthickness=0, bd=0)
                cb.pack(side='left')
                lab = tk.Label(row, text=str(task.get('text', '')), bg=paper, anchor='w',
                               justify='left', wraplength=235, font=(FONT, 10),
                               fg='#999999' if checked.get() else '#333333')
                if checked.get():
                    lab.configure(font=(FONT, 10, 'overstrike'))
                lab.pack(side='left', fill='x', expand=True)
                def delete_task(t=task):
                    note['tasks'].remove(t)
                    self.save_later()
                    render_tasks()
                tk.Button(row, text='×', command=delete_task, bd=0, relief='flat',
                          bg=paper, fg='#B07070', cursor='hand2', font=(FONT, 11)).pack(side='right')

        def add_task(event=None):
            value = task_input.get().strip()
            if value:
                note['tasks'].append({'id': uuid.uuid4().hex, 'text': value, 'done': False})
                task_input.delete(0, 'end')
                render_tasks()
                self.save_later()
            return 'break'

        tk.Button(input_bar, text='添加 +', command=add_task, bg=header, bd=0, relief='flat',
                  font=(FONT, 9), padx=8, cursor='hand2').pack(side='right', padx=(6, 0), ipady=4)
        task_input.bind('<Return>', add_task)
        render_tasks()

        footer = tk.Frame(win, bg=paper, height=31)
        footer.pack(fill='x')
        info = tk.Label(footer, text='自动保存 · Ctrl+Shift+N 新建', bg=paper, fg='#777', font=(FONT, 8))
        info.pack(side='left', padx=12)

        def recolor():
            note['color'] = (int(note.get('color', 0)) + 1) % len(PALETTES)
            h, p = PALETTES[note['color']][1:]
            bar.configure(bg=h)
            for widget in bar.winfo_children():
                widget.configure(bg=h)
                if isinstance(widget, tk.Button):
                    widget.configure(activebackground=h)
            content.configure(bg=p)
            txt.configure(bg=p)
            input_bar.configure(bg=p)
            task_list_container.configure(bg=p)
            task_canvas.configure(bg=p)
            task_rows.configure(bg=p)
            footer.configure(bg=p)
            info.configure(bg=p)
            for child in content.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=p)
            for row in task_rows.winfo_children():
                row.configure(bg=p)
                for child in row.winfo_children():
                    if isinstance(child, (tk.Label, tk.Button, tk.Checkbutton)):
                        child.configure(bg=p)
                        if isinstance(child, tk.Checkbutton):
                            child.configure(activebackground=p)
            self.save_later()

        def settings():
            dialog = tk.Toplevel(win)
            dialog.title('轻便签设置')
            dialog.geometry('325x150')
            dialog.resizable(False, False)
            dialog.transient(win)
            dialog.grab_set()
            tk.Label(dialog, text='软件设置', font=(FONT, 12, 'bold')).pack(anchor='w', padx=18, pady=(15, 8))
            enabled = tk.BooleanVar(value=startup_enabled())
            def change_startup():
                try:
                    set_startup(enabled.get())
                except (OSError, PermissionError) as exc:
                    enabled.set(startup_enabled())
                    messagebox.showerror('设置失败', f'无法修改开机自启：\n{exc}', parent=dialog)
            tk.Checkbutton(dialog, text='登录 Windows 时自动启动轻便签', variable=enabled,
                           command=change_startup, font=(FONT, 10)).pack(anchor='w', padx=15)
            tk.Label(dialog, text='只影响当前 Windows 用户，无需管理员权限',
                     fg='#777', font=(FONT, 8)).pack(anchor='w', padx=20, pady=6)

        def remove():
            if messagebox.askyesno('删除便签', '确定永久删除这张便签及待办事项吗？', parent=win):
                self.notes.pop(key, None)
                self.windows.pop(key, None)
                win.destroy()
                self.save()
                if not self.windows:
                    self.root.quit()
        tk.Button(footer, text='删除便签', command=remove, relief='flat', bd=0, bg=paper,
                  fg='#A45454', font=(FONT, 9), cursor='hand2').pack(side='right', padx=10)

        def changed(event=None):
            note['text'] = txt.get('1.0', 'end-1c')
            self.save_later()
        txt.bind('<<Modified>>', lambda e: (txt.edit_modified(False), changed()) if txt.edit_modified() else None)
        txt.edit_modified(False)

        def geometry_changed(event):
            if event.widget is win and win.state() == 'normal':
                note['geometry'] = win.geometry()
                self.save_later()
        win.bind('<Configure>', geometry_changed)

        def close():
            note['text'] = txt.get('1.0', 'end-1c')
            if win.state() == 'normal':
                note['geometry'] = win.geometry()
            self.windows.pop(key, None)
            win.destroy()
            self.save()
            if not self.windows:
                self.root.quit()
        win.protocol('WM_DELETE_WINDOW', close)
        txt.focus_set()


if __name__ == '__main__':
    StickyApp()
