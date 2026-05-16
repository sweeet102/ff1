#!/usr/bin/env python3
"""Pomodoro Timer - 桌面番茄钟"""

import tkinter as tk
from tkinter import ttk
import math
import subprocess
import platform
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------
CONFIG_FILE = Path.home() / ".pomodoro_config.json"

def load_config():
    defaults = {"work": 25, "break": 5, "sessions": 4}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            defaults.update(d)
    except Exception:
        pass
    return defaults

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

def notify(title, body):
    if IS_MAC:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{body}" with title "{title}" sound name "Ping"'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif IS_WIN:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, body, duration=4, threaded=True)
        except ImportError:
            pass

def play_sound(name="ping"):
    """Play a system sound."""
    if IS_MAC:
        sounds = {
            "ping": "/System/Library/Sounds/Ping.aiff",
            "glass": "/System/Library/Sounds/Glass.aiff",
            "pop": "/System/Library/Sounds/Pop.aiff",
            "frog": "/System/Library/Sounds/Frog.aiff",
        }
        path = sounds.get(name, sounds["ping"])
        if os.path.exists(path):
            subprocess.run(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif IS_WIN:
        import winsound
        freqs = {"ping": (1000, 300), "glass": (800, 200), "pop": (600, 100), "frog": (500, 400)}
        freq, dur = freqs.get(name, (1000, 300))
        winsound.Beep(freq, dur)

# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
class PomodoroApp:
    COLORS = {
        "bg":           "#161616",
        "surface":      "#1e1e1e",
        "surface2":     "#2a2a2a",
        "text":         "#e8e8e8",
        "sub":          "#888888",
        "work":         "#ff6b6b",
        "work_hover":   "#ff8787",
        "work_dim":     "#4a2020",
        "break":        "#51cf66",
        "break_hover":  "#69db7c",
        "break_dim":    "#1a3a20",
        "ring_bg":      "#2e2e2e",
        "btn_bg":       "#2e2e2e",
        "btn_hover":    "#3a3a3a",
        "dot_empty":    "#333333",
    }

    def __init__(self):
        self.config = load_config()
        self.mode = "work"          # work | break
        self.running = False
        self.paused = False
        self.time_left = self.config["work"] * 60
        self.total_time = self.time_left
        self.session_count = 0
        self.total_sessions = self.config["sessions"]
        self.after_id = None

        self._build_ui()
        self._sync_ui()

    # ---- UI Construction --------------------------------------------------
    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.configure(bg=self.COLORS["bg"])
        self.root.minsize(340, 500)
        self.root.geometry("360x560")

        # Try to set app icon / dock name
        if IS_MAC:
            try:
                self.root.createcommand("tkAboutDialog", lambda: None)
            except Exception:
                pass

        # Window positioned near center
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 360, 560
        x = (sw - w) // 2
        y = (sh - h) // 2 - 40
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- Mode tabs ----
        mode_frame = tk.Frame(self.root, bg=self.COLORS["surface2"], bd=0, highlightthickness=0)
        mode_frame.pack(pady=(24, 16))
        mode_frame.configure(borderwidth=0)

        inner_tabs = tk.Frame(mode_frame, bg=self.COLORS["surface2"])
        inner_tabs.pack(padx=3, pady=3)

        self.btn_work = tk.Button(
            inner_tabs, text="   专注   ", font=("Helvetica Neue", 13),
            relief="flat", bd=0, highlightthickness=0,
            command=lambda: self._switch_mode("work"),
        )
        self.btn_work.pack(side="left", padx=2)

        self.btn_break = tk.Button(
            inner_tabs, text="   休息   ", font=("Helvetica Neue", 13),
            relief="flat", bd=0, highlightthickness=0,
            command=lambda: self._switch_mode("break"),
        )
        self.btn_break.pack(side="left", padx=2)

        # ---- Timer canvas ----
        self.canvas_size = 260
        self.canvas = tk.Canvas(
            self.root, width=self.canvas_size, height=self.canvas_size,
            bg=self.COLORS["bg"], highlightthickness=0,
        )
        self.canvas.pack(pady=(8, 0))

        # Center coordinates
        cx, cy = self.canvas_size / 2, self.canvas_size / 2
        r = 110
        self.circle_cx = cx
        self.circle_cy = cy
        self.circle_r = r

        # Draw background ring
        self.canvas.create_oval(
            cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8,
            outline=self.COLORS["ring_bg"], width=8, fill="",
        )

        # Foreground progress arc (draw from top, clockwise)
        # We'll redraw this on every tick
        self.progress_arc = None

        # Center text
        self.time_text = self.canvas.create_text(
            cx, cy - 6, text="25:00",
            font=("Helvetica Neue", 46, "normal"),
            fill=self.COLORS["text"],
        )
        self.status_text = self.canvas.create_text(
            cx, cy + 36, text="就绪",
            font=("Helvetica Neue", 12),
            fill=self.COLORS["sub"],
        )

        # ---- Controls ----
        ctrl_frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        ctrl_frame.pack(pady=(12, 8))

        self.btn_reset = self._make_icon_button(ctrl_frame, "⏮", "重置", self._reset)
        self.btn_reset.pack(side="left", padx=8)

        self.btn_play = tk.Button(
            ctrl_frame, text="▶", font=("Helvetica Neue", 22),
            width=3, height=1,
            relief="flat", bd=0, highlightthickness=0,
            command=self._toggle_play,
        )
        self.btn_play.pack(side="left", padx=8)

        self.btn_skip = self._make_icon_button(ctrl_frame, "⏭", "跳过", self._skip)
        self.btn_skip.pack(side="left", padx=8)

        # ---- Session dots ----
        self.dots_frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        self.dots_frame.pack(pady=(8, 4))
        self.dot_labels = []

        # ---- Settings ----
        settings_frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        settings_frame.pack(pady=(4, 20))

        self._make_setting(settings_frame, "专注", "work", 0)
        self._make_setting(settings_frame, "休息", "break", 1)
        self._make_setting(settings_frame, "轮次", "sessions", 2)

        # ---- Keyboard bindings ----
        self.root.bind("<space>", lambda e: self._toggle_play())
        self.root.bind("r", lambda e: self._reset())
        self.root.bind("R", lambda e: self._reset())
        self.root.bind("s", lambda e: self._skip())
        self.root.bind("S", lambda e: self._skip())
        self.root.bind("<Escape>", lambda e: self._minimize())
        self.root.bind("<Command-w>", lambda e: self._minimize())

        self.root.bind("<FocusIn>", lambda e: self._focus_changed())

    def _make_icon_button(self, parent, text, tooltip, command):
        btn = tk.Button(
            parent, text=text, font=("Helvetica Neue", 18),
            width=2, height=1,
            relief="flat", bd=0, highlightthickness=0,
            command=command,
        )
        return btn

    def _make_setting(self, parent, label, key, col):
        frame = tk.Frame(parent, bg=self.COLORS["bg"])
        frame.pack(side="left", padx=12)

        lbl = tk.Label(
            frame, text=label,
            font=("Helvetica Neue", 11),
            fg=self.COLORS["sub"], bg=self.COLORS["bg"],
        )
        lbl.pack(side="left")

        var = tk.StringVar(value=str(self.config[key]))
        entry = tk.Entry(
            frame, textvariable=var, width=3,
            font=("Helvetica Neue", 11),
            fg=self.COLORS["text"], bg=self.COLORS["surface"],
            insertbackground=self.COLORS["text"],
            relief="flat", bd=0, highlightthickness=1,
            justify="center",
        )
        entry.pack(side="left", padx=(4, 0))
        entry.bind("<FocusOut>", lambda e, k=key, v=var: self._on_setting_change(k, v))

        # Store reference
        setattr(self, f"var_{key}", var)

        return frame

    # ---- Drawing ----------------------------------------------------------
    def _draw_progress(self, fraction):
        """Draw/fill the progress arc. fraction 0..1 (1 = full ring)."""
        self.canvas.delete("progress")

        if fraction <= 0.001:
            return

        cx, cy, r = self.circle_cx, self.circle_cy, self.circle_r

        # Degrees: 0 at top, go clockwise. fraction=1 -> 359.99 degrees
        # tkinter canvas: 0 is at 3 o'clock, going counter-clockwise
        # To start at top (12 o'clock), we set start = 90
        extent = -fraction * 360  # negative = clockwise in tkinter

        color = self.COLORS["work"] if self.mode == "work" else self.COLORS["break"]

        # Draw arc with rounded caps using a series of small segments
        # Or simpler: just draw the arc
        self.canvas.create_arc(
            cx - r - 4, cy - r - 4,
            cx + r + 4, cy + r + 4,
            start=90, extent=extent,
            outline=color, width=8,
            style="arc",
            tags="progress",
        )

    def _draw_dots(self):
        for lbl in self.dot_labels:
            lbl.destroy()
        self.dot_labels.clear()

        for i in range(self.total_sessions):
            if i < self.session_count:
                color = self.COLORS["work"]
            elif i == self.session_count and self.running and self.mode == "work":
                color = self.COLORS["work"]
            else:
                color = self.COLORS["dot_empty"]

            dot = tk.Label(
                self.dots_frame,
                text="●",
                font=("Helvetica Neue", 14),
                fg=color, bg=self.COLORS["bg"],
            )
            dot.pack(side="left", padx=3)
            self.dot_labels.append(dot)

    # ---- UI Sync ----------------------------------------------------------
    def _sync_ui(self):
        """Update all UI elements to reflect current state."""
        mins, secs = divmod(self.time_left, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.canvas.itemconfig(self.time_text, text=time_str)

        if self.running:
            status = "专注中" if self.mode == "work" else "休息中"
        else:
            if self.paused:
                status = "已暂停"
            else:
                status = "就绪"

        # Update window title
        icon = "●" if self.running else "○"
        mode_label = "专注" if self.mode == "work" else "休息"
        self.root.title(f"{icon} {time_str} - {mode_label} | 番茄钟")

        self.canvas.itemconfig(self.status_text, text=status)

        # Progress
        fraction = self.time_left / self.total_time if self.total_time > 0 else 0
        self._draw_progress(fraction)

        # Mode tabs
        if self.mode == "work":
            self.btn_work.configure(
                bg=self.COLORS["work"], fg="white",
                activebackground=self.COLORS["work_hover"], activeforeground="white",
            )
            self.btn_break.configure(
                bg=self.COLORS["surface2"], fg=self.COLORS["sub"],
                activebackground=self.COLORS["btn_hover"], activeforeground=self.COLORS["text"],
            )
        else:
            self.btn_break.configure(
                bg=self.COLORS["break"], fg="white",
                activebackground=self.COLORS["break_hover"], activeforeground="white",
            )
            self.btn_work.configure(
                bg=self.COLORS["surface2"], fg=self.COLORS["sub"],
                activebackground=self.COLORS["btn_hover"], activeforeground=self.COLORS["text"],
            )

        # Play button
        play_color = self.COLORS["work"] if self.mode == "work" else self.COLORS["break"]
        play_hover = self.COLORS["work_hover"] if self.mode == "work" else self.COLORS["break_hover"]
        play_text = "⏸" if self.running else "▶"

        self.btn_play.configure(
            text=play_text,
            bg=play_color, fg="white",
            activebackground=play_hover, activeforeground="white",
        )

        # Dots
        self._draw_dots()

    # ---- Timer Logic ------------------------------------------------------
    def _tick(self):
        if not self.running:
            return

        self.time_left -= 1
        self._sync_ui()

        if self.time_left <= 0:
            self._on_timeout()

        if self.running:
            self.after_id = self.root.after(1000, self._tick)

    def _on_timeout(self):
        self.running = False

        if self.mode == "work":
            self.session_count += 1
            play_sound("ping")
            self._sync_ui()

            if self.session_count >= self.total_sessions:
                notify("番茄钟", f"全部 {self.total_sessions} 轮完成！休息一下吧。")
                self.session_count = 0
                self._switch_mode("break")
                self.time_left = self.config["break"] * 60
                self.total_time = self.time_left
                self._sync_ui()
                return

            notify("番茄钟", "专注时间结束，休息一下。")
            self._switch_mode("break")
        else:
            play_sound("glass")
            notify("番茄钟", "休息结束，继续专注吧。")
            self._switch_mode("work")

        self._sync_ui()

    def _toggle_play(self):
        if self.running:
            self.running = False
            self.paused = True
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            self._sync_ui()
        else:
            # On first start after pause, re-lock mode to current
            self.paused = False
            if self.after_id is None:
                self.running = True
                self._sync_ui()
                self.after_id = self.root.after(600, self._tick)

    def _reset(self):
        self.running = False
        self.paused = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.session_count = 0
        self._switch_mode("work")
        self._sync_ui()

    def _skip(self):
        was_running = self.running
        self.running = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        if self.mode == "work":
            self.session_count += 1
            if self.session_count >= self.total_sessions:
                self.session_count = 0
                self._switch_mode("work")
                self._sync_ui()
                return
            self._switch_mode("break")
        else:
            self._switch_mode("work")

        self._sync_ui()

        if was_running:
            self.running = True
            self.after_id = self.root.after(600, self._tick)
            self._sync_ui()

    def _switch_mode(self, new_mode):
        self.mode = new_mode
        key = "work" if new_mode == "work" else "break"
        self.time_left = self.config[key] * 60
        self.total_time = self.time_left

    # ---- Settings ---------------------------------------------------------
    def _on_setting_change(self, key, var):
        try:
            val = int(var.get())
            if val < 1:
                val = 1
            if key in ("work", "break") and val > 120:
                val = 120
            if key == "sessions" and val > 12:
                val = 12
            self.config[key] = val
            save_config(self.config)
            var.set(str(val))

            if key == "sessions":
                self.total_sessions = val
                if not self.running:
                    self.session_count = 0
                    self._sync_ui()
            if key == "work" and self.mode == "work" and not self.running:
                self.time_left = val * 60
                self.total_time = self.time_left
                self._sync_ui()
            if key == "break" and self.mode == "break" and not self.running:
                self.time_left = val * 60
                self.total_time = self.time_left
                self._sync_ui()
        except ValueError:
            var.set(str(self.config[key]))

    def _focus_changed(self):
        """Re-apply button styling when window regains focus (fixes macOS tkinter issue)."""
        self._sync_ui()

    def _minimize(self):
        self.root.iconify()

    def _on_close(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Entry point with .app bundle support
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # When double-clicked as .command or .app, set working dir
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = PomodoroApp()
    app.run()
