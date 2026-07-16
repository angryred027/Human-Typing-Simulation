import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import winsound
import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk

from . import config
from . import winutil
from .controller import TypingController, to_ascii

UI_SCALE = 4
GREEN = (58, 190, 110)
RED = (214, 69, 69)
GRAY = (181, 181, 181)
BLUE = (58, 120, 190)
ORANGE = (232, 150, 40)


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def load_font(px, bold=False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(name, px)
    except OSError:
        return ImageFont.load_default()


def play_toggle_sound(is_on):
    frequency = 2500 if is_on else 1200
    duration = 200 if is_on else 120
    threading.Thread(target=winsound.Beep, args=(frequency, duration), daemon=True).start()


def tray_image(kind):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if kind == "ready":
        draw.polygon([(8, 3), (8, 61), (61, 32)], fill=GREEN)
    elif kind == "paused":
        draw.rectangle((7, 3, 27, 61), fill=RED)
        draw.rectangle((37, 3, 57, 61), fill=RED)
    elif kind == "typing_on":
        draw.rounded_rectangle((2, 2, 62, 62), radius=12, fill=RED)
    else:
        draw.rounded_rectangle((2, 2, 62, 62), radius=12, fill=GRAY)
    return img


def app_icon_image():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((16, 16, size - 16, size - 16), radius=48, fill=BLUE)
    draw.polygon([(100, 76), (100, 180), (188, 128)], fill=(255, 255, 255))
    return img


class RoundedButton(tk.Canvas):
    def __init__(self, master, text="", command=None, width=160, height=46, radius=18, **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bd=0, **kwargs)
        self.btn_width = width
        self.btn_height = height
        self.radius = radius
        self.command = command
        self.text = text
        self.enabled = True
        self.fill = (255, 255, 255)
        self.hover_fill = (240, 240, 240)
        self.disabled_fill = (236, 236, 236)
        self.outline = (130, 130, 130)
        self.text_color = (26, 26, 26)
        self._hovering = False
        self._photo = None
        self.configure(bg=master.winfo_toplevel().cget("bg"), cursor="hand2")
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.redraw()

    def _on_click(self, event):
        if self.enabled and self.command:
            self.command()

    def _set_hover(self, hovering):
        self._hovering = hovering
        self.redraw()

    def set_text(self, text):
        if text != self.text:
            self.text = text
            self.redraw()

    def set_enabled(self, enabled):
        if enabled != self.enabled:
            self.enabled = enabled
            self.configure(cursor="hand2" if enabled else "arrow")
            self.redraw()

    def redraw(self):
        s = UI_SCALE
        w, h = self.btn_width * s, self.btn_height * s
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill = self.disabled_fill if not self.enabled else (self.hover_fill if self._hovering else self.fill)
        inset = 2 * s
        draw.rounded_rectangle((inset, inset, w - 1 - inset, h - 1 - inset), radius=self.radius * s,
                               fill=fill, outline=self.outline, width=s)
        color = self.text_color if self.enabled else (150, 150, 150)
        draw.text((w / 2, h / 2), self.text, font=load_font(12 * s), fill=color, anchor="mm")
        img = img.resize((self.btn_width, self.btn_height), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.delete("all")
        self.create_image(0, 0, image=self._photo, anchor="nw")


def draw_rhythm_graph(canvas, samples, window):
    canvas.delete("all")
    w = int(canvas["width"])
    h = int(canvas["height"])
    left, right, top, bottom = 36, 12, 18, 18
    canvas.create_rectangle(0, 0, w, h, fill="#fafafa", outline="#cccccc")
    data = samples[-int(window):]
    if len(data) < 2:
        canvas.create_text(w / 2, h / 2, text="No typing recorded yet", fill="#999999")
        return

    x0, x1 = left, w - right
    y0, y1 = top, h - bottom
    plot_w, plot_h = x1 - x0, y1 - y0
    n = len(data)
    step = plot_w / (n - 1)
    speeds = [1.0 / s["iki"] if s.get("iki") else 0.0 for s in data]
    peak = max(speeds) or 1.0

    for i in range(5):
        y = y0 + i * plot_h / 4
        canvas.create_line(x0, y, x1, y, fill="#ececec")
        val = peak * (4 - i) / 4
        canvas.create_text(x0 - 4, y, anchor="e", text=f"{val:.1f}", fill="#999999", font=("Segoe UI", 7))
    for i in range(0, n, max(1, (n - 1) // 5)):
        x = x0 + i * step
        canvas.create_line(x, y0, x, y1, fill="#f2f2f2")
        canvas.create_text(x, y1 + 2, anchor="n", text=str(data[i].get("typed", i)),
                           fill="#999999", font=("Segoe UI", 7))

    def sy(cps):
        return y1 - (cps / peak) * plot_h
    speed_pts = [(x0 + i * step, sy(cps)) for i, cps in enumerate(speeds)]
    canvas.create_line(*[c for p in speed_pts for c in p], fill="#3a7bd5", width=2)

    outputs = [s.get("typed", 0) for s in data]
    omax = max(outputs) or 1
    out_pts = [(x0 + i * step, y1 - (o / omax) * plot_h) for i, o in enumerate(outputs)]
    canvas.create_line(*[c for p in out_pts for c in p], fill="#3aae6e", width=1, dash=(3, 2))

    for i, s in enumerate(data):
        x, y = speed_pts[i]
        if s.get("error"):
            canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#d64545", outline="")
        if s.get("break"):
            canvas.create_line(x, y0, x, y1, fill="#e89628", width=1)

    canvas.create_text(4, y0 - 12, anchor="w", text="c/s", fill="#999999", font=("Segoe UI", 7))
    canvas.create_text(x1, y1 + 2, anchor="ne", text="chars", fill="#999999", font=("Segoe UI", 7))
    legend = [("speed", "#3a7bd5"), ("errors", "#d64545"), ("breaks", "#e89628"), ("output", "#3aae6e")]
    lx = x0
    for label, color in legend:
        canvas.create_text(lx, top - 10, anchor="w", text=label, fill=color, font=("Segoe UI", 8))
        lx += 7 * len(label) + 16


class ConfigDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Configuration")
        self.resizable(False, False)
        self.transient(app)
        self.grab_set()

        s = app.settings
        self.vars = {
            "wpm": tk.StringVar(value=str(s["wpm"])),
            "rhythm": tk.StringVar(value=s["rhythm"]),
            "layout": tk.StringVar(value=s["layout"]),
            "base_error_rate": tk.StringVar(value=str(s["base_error_rate"])),
            "prob_notice_error": tk.StringVar(value=str(s["prob_notice_error"])),
            "prob_word_level_correction": tk.StringVar(value=str(s["prob_word_level_correction"])),
            "start_delay": tk.StringVar(value=str(s["start_delay"])),
            "coding_indent": tk.StringVar(value=s.get("coding_indent", "tab")),
            "graph_chars": tk.StringVar(value=str(s.get("graph_chars", 120))),
            "paraphrase_model_path": tk.StringVar(value=s.get("paraphrase_model_path", "")),
        }

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        frm.columnconfigure(1, weight=1)

        rows = [
            ("Speed (WPM)", "wpm", None),
            ("Rhythm", "rhythm", sorted(config.RHYTHM_PRESETS)),
            ("Layout", "layout", ["qwerty", "azerty"]),
            ("Error rate (restart)", "base_error_rate", None),
            ("Notice error (restart)", "prob_notice_error", None),
            ("Word-level fix (restart)", "prob_word_level_correction", None),
            ("Start delay (s)", "start_delay", None),
            ("Coding indent", "coding_indent", ["tab", "none"]),
        ]
        r = 0
        for label, key, choices in rows:
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=3)
            if choices:
                ttk.Combobox(frm, textvariable=self.vars[key], values=choices,
                             state="readonly").grid(row=r, column=1, sticky="ew", pady=3, padx=(12, 0))
            else:
                ttk.Entry(frm, textvariable=self.vars[key]).grid(
                    row=r, column=1, sticky="ew", pady=3, padx=(12, 0))
            r += 1

        ttk.Label(frm, text="Graph chars").grid(row=r, column=0, sticky="w", pady=3)
        ttk.Spinbox(frm, from_=20, to=2000, increment=20, textvariable=self.vars["graph_chars"],
                    command=self._redraw).grid(row=r, column=1, sticky="ew", pady=3, padx=(12, 0))
        r += 1

        ttk.Label(frm, text="Paraphrase model (writing)").grid(row=r, column=0, sticky="w", pady=3)
        pf = ttk.Frame(frm)
        pf.grid(row=r, column=1, sticky="ew", pady=3, padx=(12, 0))
        pf.columnconfigure(0, weight=1)
        ttk.Entry(pf, textvariable=self.vars["paraphrase_model_path"]).grid(row=0, column=0, sticky="ew")
        ttk.Button(pf, text="...", width=3, command=self._browse_model).grid(row=0, column=1, padx=(4, 0))
        self._test_btn = ttk.Button(pf, text="Test", width=5, command=self._test_model)
        self._test_btn.grid(row=0, column=2, padx=(4, 0))
        r += 1

        ttk.Label(frm, text="Last typing rhythm").grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 2))
        r += 1
        self.graph = tk.Canvas(frm, width=460, height=170, highlightthickness=0)
        self.graph.grid(row=r, column=0, columnspan=2)
        self._redraw()
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Save", command=self.on_save).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")

    def _graph_window(self):
        try:
            return max(20, min(2000, int(float(self.vars["graph_chars"].get()))))
        except ValueError:
            return 120

    def _redraw(self):
        draw_rhythm_graph(self.graph, self.app.samples, self._graph_window())

    def _browse_model(self):
        path = filedialog.askdirectory(title="Select paraphrase model folder")
        if path:
            self.vars["paraphrase_model_path"].set(path)

    def _test_model(self):
        path = self.vars["paraphrase_model_path"].get().strip()
        if not path:
            messagebox.showwarning("Paraphrase model", "Set a model folder first.", parent=self)
            return
        self._test_btn.config(state="disabled", text="...")

        def work():
            from .paraphrase import Paraphraser
            try:
                sample = Paraphraser(path).test_load()
                result = ("ok", f"Model loaded successfully.\n\nSample paraphrase:\n{sample}")
            except Exception as e:
                result = ("fail", f"Failed to load model:\n\n{type(e).__name__}: {e}")
            self.after(0, lambda: self._test_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _test_done(self, result):
        self._test_btn.config(state="normal", text="Test")
        kind, msg = result
        if kind == "ok":
            messagebox.showinfo("Paraphrase model", msg, parent=self)
        else:
            messagebox.showerror("Paraphrase model", msg, parent=self)

    def on_save(self):
        s = self.app.settings
        s["rhythm"] = self.vars["rhythm"].get()
        s["layout"] = self.vars["layout"].get()
        s["coding_indent"] = self.vars["coding_indent"].get()
        s["paraphrase_model_path"] = self.vars["paraphrase_model_path"].get()
        for key, cast in (("wpm", float), ("base_error_rate", float), ("prob_notice_error", float),
                          ("prob_word_level_correction", float), ("start_delay", float),
                          ("graph_chars", int)):
            try:
                s[key] = cast(self.vars[key].get())
            except ValueError:
                pass
        self.app.save()
        self.app.on_settings_changed()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Human Typing")

        self.settings = config.load_settings()
        self.samples = []
        self.window_visible = True
        self.tray = None
        self._blink_on = True
        self._blinking = False
        self._caret = 0

        try:
            self.iconbitmap(resource_path("appicon.ico"))
        except tk.TclError:
            try:
                self._icon_photo = ImageTk.PhotoImage(app_icon_image())
                self.iconphoto(True, self._icon_photo)
            except tk.TclError:
                pass

        self.controller = TypingController(
            on_progress=lambda d: self.after(0, lambda: self._on_progress(d)),
            on_sample=lambda d: self.after(0, lambda: self._on_sample(d)),
            on_state=lambda st: self.after(0, lambda: self._on_state(st)),
        )

        self.hotkey = winutil.RawInputHotkey()
        self.hotkey.start()
        self._rebind_hotkey(self.settings["hotkey"])

        self._build_ui()
        self._build_tray()
        self._refresh()

        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        self.resizable(False, True)

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

    def _build_ui(self):
        pad = ttk.Frame(self, padding=12)
        pad.pack(fill="both", expand=True)

        self.text_view = tk.Text(pad, width=44, height=5, wrap="word",
                                 bg="#ffffff", relief="solid", bd=1, font=("Segoe UI", 10))
        self.text_view.pack(fill="both", expand=True)
        self.text_view.insert("1.0", self.settings.get("text", ""))
        self.text_view.tag_configure("caret", foreground="#d64545",
                                     font=("Segoe UI", 10, "bold"), underline=True)

        self.progress = ttk.Progressbar(pad, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(10, 2))
        self.progress_label = ttk.Label(pad, text="", anchor="center")
        self.progress_label.pack(fill="x")

        grid = ttk.Frame(pad)
        grid.pack(pady=(12, 0))
        self.btn_window = RoundedButton(grid, command=self.on_select_window)
        self.btn_shortcut = RoundedButton(grid, command=self.on_set_shortcut)
        self.btn_action = RoundedButton(grid, command=self.on_action)
        self.btn_cancel = RoundedButton(grid, text="Stop / Cancel", command=self.on_cancel)
        self.btn_window.grid(row=0, column=0, padx=6, pady=6)
        self.btn_shortcut.grid(row=0, column=1, padx=6, pady=6)
        self.btn_action.grid(row=1, column=0, padx=6, pady=6)
        self.btn_cancel.grid(row=1, column=1, padx=6, pady=6)

    def _set_editing(self, editing):
        self.text_view.configure(state="normal")
        self.text_view.delete("1.0", "end")
        self.text_view.insert("1.0", self.settings.get("text", ""))
        self.text_view.tag_remove("caret", "1.0", "end")
        if not editing:
            self.text_view.configure(state="disabled")

    def _render_text(self, caret):
        text = self.settings.get("text", "")
        self.text_view.configure(state="normal")
        self.text_view.delete("1.0", "end")
        self.text_view.insert("1.0", text)
        self.text_view.tag_remove("caret", "1.0", "end")
        if text and caret < len(text):
            start = self.text_view.index(f"1.0 + {caret} chars")
            self.text_view.tag_add("caret", start, f"{start} + 1 chars")
            self.text_view.see(start)
        self.text_view.configure(state="disabled")

    def _action_label(self):
        st = self.controller.state
        if st == "typing":
            return "Pause"
        if st == "paused":
            return "Resume"
        if st == "counting":
            return "Starting..."
        if st == "loading":
            return "Loading..."
        return "Start"

    def _refresh(self):
        self.btn_window.set_text(self._window_label())
        self.btn_shortcut.set_text(winutil.format_hotkey(self.settings["hotkey"]))
        self.btn_action.set_text(self._action_label())
        running = self.controller.is_running()
        self.btn_cancel.set_enabled(running)
        self.btn_window.set_enabled(not running)

    def _window_label(self):
        title = self.settings.get("window_title")
        return title[:18] if title else "Select Window"

    def save(self):
        config.save_settings({k: v for k, v in self.settings.items()
                              if k not in ("window_hwnd", "window_title")})

    # --- actions ---
    def on_action(self):
        if self.controller.is_running():
            self.controller.toggle()
            return
        text = to_ascii(self.text_view.get("1.0", "end-1c"))
        if not text.strip():
            return
        self.settings["text"] = text
        self.save()
        self.samples = []
        self._caret = 0
        self._set_editing(False)
        hwnd = self.settings.get("window_hwnd")
        focus_once = (lambda: winutil.focus_window(hwnd)) if hwnd else None
        is_focused = (lambda: winutil.get_foreground() == hwnd) if hwnd else None
        make_paraphraser = None
        model_path = self.settings.get("paraphrase_model_path", "")
        if model_path and self.settings["rhythm"] == "writing":
            from .paraphrase import Paraphraser
            make_paraphraser = lambda: Paraphraser(model_path)
        self.controller.start(text=text, wpm=self.settings["wpm"], rhythm=self.settings["rhythm"],
                              layout=self.settings["layout"], start_delay=self.settings["start_delay"],
                              focus_once=focus_once, is_focused=is_focused,
                              make_paraphraser=make_paraphraser,
                              coding_indent=self.settings.get("coding_indent", "tab"))

    def on_cancel(self):
        self.controller.cancel()

    def on_select_window(self):
        picker = tk.Toplevel(self)
        picker.title("Select Window")
        picker.geometry("340x320")
        picker.transient(self)
        picker.grab_set()
        listbox = tk.Listbox(picker)
        listbox.pack(fill="both", expand=True, padx=8, pady=8)
        listbox.insert("end", "None (type into current focus)")
        windows = winutil.enum_visible_windows()
        for _, title in windows:
            listbox.insert("end", title)

        def confirm():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                if idx == 0:
                    self.settings["window_hwnd"] = None
                    self.settings["window_title"] = ""
                else:
                    hwnd, title = windows[idx - 1]
                    self.settings["window_hwnd"] = hwnd
                    self.settings["window_title"] = title
                self._refresh()
            picker.destroy()

        ttk.Button(picker, text="Select", command=confirm).pack(pady=(0, 8))

    def on_set_shortcut(self):
        self.btn_shortcut.set_text("Press keys...")
        self.hotkey.start_capture(lambda combo: self.after(0, lambda: self._apply_hotkey(combo)))

    def _apply_hotkey(self, combo):
        self.settings["hotkey"] = combo
        self.save()
        self._rebind_hotkey(combo)
        self._refresh()

    def _rebind_hotkey(self, hotkey):
        parsed = winutil.parse_hotkey(hotkey)
        if parsed:
            self.hotkey.set_hotkey(parsed, lambda: self.after(0, self.on_action))

    def on_settings_changed(self):
        self._refresh()

    # --- controller callbacks (main thread) ---
    def _on_progress(self, d):
        self._caret = d["caret"]
        self.progress["value"] = d["percent"]
        eta = d["eta"]
        eta_txt = f"{int(eta // 60)}m {int(eta % 60)}s" if eta >= 60 else f"{int(eta)}s"
        self.progress_label.configure(
            text=f"{d['percent']:.1f}%  ·  {d['typed']}/{d['total']} chs  ·  {eta_txt} left")
        self._render_text(self._caret)

    def _on_sample(self, d):
        self.samples.append(d)

    def _on_state(self, st):
        self._refresh()
        self._update_tray()
        if st == "typing":
            play_toggle_sound(True)
        elif st in ("paused", "done", "idle"):
            play_toggle_sound(False)
        if st in ("done", "idle"):
            self._set_editing(True)
        if st == "typing" and not self._blinking:
            self._blinking = True
            self._blink()

    # --- tray ---
    def _build_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem(lambda i: self._action_label(), lambda i: self.after(0, self.on_action), default=True),
            pystray.MenuItem(lambda i: "Show" if not self.window_visible else "Hide",
                             lambda i: self.after(0, self.toggle_window)),
            pystray.MenuItem("Cancel", lambda i: self.after(0, self.on_cancel)),
            pystray.MenuItem("Config", lambda i: self.after(0, self.open_config)),
            pystray.MenuItem("Quit", lambda i: self.after(0, self.quit_app)),
        )
        self.tray = pystray.Icon("humantyping", tray_image("ready"), "HumanTyping", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _tray_kind(self):
        st = self.controller.state
        if st == "paused":
            return "paused"
        if st == "typing":
            return "typing_on" if self._blink_on else "typing_off"
        return "ready"

    def _update_tray(self):
        if self.tray:
            self.tray.icon = tray_image(self._tray_kind())
            self.tray.title = f"HumanTyping — {self.controller.state}"
            self.tray.update_menu()

    def _blink(self):
        if self.controller.state != "typing":
            self._blinking = False
            return
        self._blink_on = not self._blink_on
        self._update_tray()
        self.after(500, self._blink)

    # --- window visibility ---
    def hide_window(self):
        self.withdraw()
        self.window_visible = False
        self._update_tray()

    def toggle_window(self):
        if self.window_visible:
            self.hide_window()
        else:
            self.deiconify()
            self.window_visible = True
            self._update_tray()

    def open_config(self):
        if not self.window_visible:
            self.toggle_window()
        ConfigDialog(self)

    def quit_app(self):
        self.controller.cancel()
        if self.tray:
            self.tray.stop()
        self.destroy()


def run():
    App().mainloop()
