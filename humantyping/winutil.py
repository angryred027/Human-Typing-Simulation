"""Windows helpers: window enumeration, focus, and a Raw Input global hotkey.

The hotkey uses WM_INPUT rather than a low-level hook so it keeps working under
apps that install their own hook and swallow keys (adapted from Toggle Mouse Input).
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import threading

import win32api
import win32con
import win32gui
import win32process

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

user32 = ctypes.WinDLL("user32", use_last_error=True)

RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEKEYBOARD = 1
RI_KEY_BREAK = 0x01
WM_INPUT = 0x00FF
MAPVK_VK_TO_CHAR = 2


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT),
                ("Reserved", wintypes.USHORT), ("VKey", wintypes.USHORT),
                ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("keyboard", RAWKEYBOARD)]


user32.RegisterRawInputDevices.restype = wintypes.BOOL
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.GetRawInputData.restype = wintypes.UINT
user32.GetRawInputData.argtypes = [
    wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.VkKeyScanW.restype = ctypes.c_short
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]

# Scan-code keyboard injection. Remote desktop / RDP / games forward physical
# scan codes, not the Unicode/VK path pynput.type() uses, so uppercase and
# shifted characters otherwise lose their Shift on the remote side.
ULONG_PTR = ctypes.c_size_t
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
VK_SHIFT = 0x10
MAPVK_VK_TO_VSC = 0


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def _key_event(scan, up, extended=False):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, scan & 0xFFFF, flags, 0, 0)))


def _unicode_event(codepoint, up):
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(0, codepoint, flags, 0, 0)))


def _send(events):
    arr = (INPUT * len(events))(*events)
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def send_char(ch):
    r = user32.VkKeyScanW(ch)
    vk = r & 0xFF
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC) if r != -1 else 0
    if r == -1 or vk == 0xFF or scan == 0:
        cp = ord(ch)
        _send([_unicode_event(cp, False), _unicode_event(cp, True)])
        return
    shift = bool((r >> 8) & 1)
    shift_scan = user32.MapVirtualKeyW(VK_SHIFT, MAPVK_VK_TO_VSC)
    seq = []
    if shift:
        seq.append(_key_event(shift_scan, False))
    seq += [_key_event(scan, False), _key_event(scan, True)]
    if shift:
        seq.append(_key_event(shift_scan, True))
    _send(seq)


def send_key(vk, shift=False, extended=False):
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    shift_scan = user32.MapVirtualKeyW(VK_SHIFT, MAPVK_VK_TO_VSC)
    seq = []
    if shift:
        seq.append(_key_event(shift_scan, False))
    seq += [_key_event(scan, False, extended), _key_event(scan, True, extended)]
    if shift:
        seq.append(_key_event(shift_scan, True))
    _send(seq)


def get_window_app_name(hwnd):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
    finally:
        kernel32.CloseHandle(handle)
    exe = buf.value.rsplit("\\", 1)[-1]
    if exe.lower().endswith(".exe"):
        exe = exe[:-4]
    return exe


def enum_visible_windows():
    own_pid = os.getpid()
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == own_pid:
                return True
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def get_foreground():
    return win32gui.GetForegroundWindow()


def focus_window(hwnd):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        cur = win32api.GetCurrentThreadId()
        target = win32process.GetWindowThreadProcessId(hwnd)[0]
        fg = win32gui.GetForegroundWindow()
        fg_thread = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
        threads = {t for t in (target, fg_thread) if t and t != cur}
        for t in threads:
            user32.AttachThreadInput(cur, t, True)
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            for t in threads:
                user32.AttachThreadInput(cur, t, False)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False


def ensure_foreground(hwnd):
    if hwnd and win32gui.IsWindow(hwnd) and win32gui.GetForegroundWindow() != hwnd:
        focus_window(hwnd)


MODIFIER_VK_GROUPS = {
    "ctrl": frozenset({0x11, 0xA2, 0xA3}),
    "alt": frozenset({0x12, 0xA4, 0xA5}),
    "shift": frozenset({0x10, 0xA0, 0xA1}),
    "windows": frozenset({0x5B, 0x5C}),
}

KEY_NAME_TO_VK = {
    "escape": 0x1B, "esc": 0x1B, "tab": 0x09, "space": 0x20, "enter": 0x0D,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
    "page up": 0x21, "page down": 0x22, "left": 0x25, "up": 0x26, "right": 0x27,
    "down": 0x28, "print screen": 0x2C, "scroll lock": 0x91, "pause": 0x13, "caps lock": 0x14,
}
for _i in range(1, 25):
    KEY_NAME_TO_VK[f"f{_i}"] = 0x70 + _i - 1

MODIFIER_VK_TO_NAME = {}
for _name, _group in MODIFIER_VK_GROUPS.items():
    for _vk in _group:
        MODIFIER_VK_TO_NAME[_vk] = _name

VK_TO_KEY_NAME = {vk: name for name, vk in KEY_NAME_TO_VK.items()}

KEY_DISPLAY_ALIASES = {
    "windows": "Win", "escape": "Esc", "delete": "Del", "insert": "Ins",
    "page up": "PgUp", "page down": "PgDn", "print screen": "PrtSc",
    "scroll lock": "ScrLk", "caps lock": "Caps", "backspace": "Bksp",
}


def vk_to_key_name(vk):
    if vk in VK_TO_KEY_NAME:
        return VK_TO_KEY_NAME[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    ch = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR) & 0xFFFF
    return chr(ch).lower() if ch else None


def normalize_key_name(name):
    name = name.strip().lower()
    for prefix in ("left ", "right "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    if name in ("control", "ctrl"):
        return "ctrl"
    if name in ("menu", "alt", "alt gr"):
        return "alt"
    if name in ("windows", "win", "cmd", "super"):
        return "windows"
    return name


def key_name_to_vk(name):
    if name in KEY_NAME_TO_VK:
        return KEY_NAME_TO_VK[name]
    if len(name) == 1:
        result = user32.VkKeyScanW(name)
        if result != -1:
            return result & 0xFF
    return None


def parse_hotkey(hotkey):
    modifiers = []
    trigger = None
    for part in hotkey.split("+"):
        name = normalize_key_name(part)
        if name in MODIFIER_VK_GROUPS:
            modifiers.append(MODIFIER_VK_GROUPS[name])
        elif trigger is None:
            vk = key_name_to_vk(name)
            if vk is None:
                return None
            trigger = vk
        else:
            return None
    if trigger is None:
        return None
    return modifiers, trigger


def format_hotkey(hotkey):
    parts = []
    for part in hotkey.split("+"):
        name = normalize_key_name(part)
        parts.append(KEY_DISPLAY_ALIASES.get(name, name.capitalize()))
    text = " + ".join(parts)
    if len(text) > 18:
        text = "+".join(parts)
    return text


class RawInputHotkey:
    def __init__(self):
        self._combo = None
        self._callback = None
        self._capture_cb = None
        self._pressed = set()
        self._lock = threading.Lock()
        self.ready = threading.Event()

    def set_hotkey(self, combo, callback):
        with self._lock:
            self._combo = combo
            self._callback = callback

    def start_capture(self, on_capture):
        with self._lock:
            self._capture_cb = on_capture

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = "HumanTypingRawInput"
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = win32api.GetModuleHandle(None)
        atom = win32gui.RegisterClass(wc)
        hwnd = win32gui.CreateWindow(atom, "raw input sink", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)
        rid = RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd)
        if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(RAWINPUTDEVICE)):
            return
        self.ready.set()
        win32gui.PumpMessages()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._handle_input(lparam)
            except Exception:
                pass
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _handle_input(self, lparam):
        size = wintypes.UINT(0)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
        if size.value == 0:
            return
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size),
                                  ctypes.sizeof(RAWINPUTHEADER)) != size.value:
            return
        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        if raw.header.dwType != RIM_TYPEKEYBOARD:
            return
        vk = raw.keyboard.VKey
        if vk == 0 or vk == 0xFF:
            return
        if raw.keyboard.Flags & RI_KEY_BREAK:
            self._pressed.discard(vk)
            return
        first_press = vk not in self._pressed
        self._pressed.add(vk)
        if not first_press:
            return

        with self._lock:
            capture_cb = self._capture_cb
            combo, callback = self._combo, self._callback

        if capture_cb is not None:
            if vk in MODIFIER_VK_TO_NAME:
                return
            name = vk_to_key_name(vk)
            if name is None:
                return
            mods = [m for m in ("ctrl", "shift", "alt", "windows") if MODIFIER_VK_GROUPS[m] & self._pressed]
            with self._lock:
                self._capture_cb = None
            capture_cb("+".join(mods + [name]))
            return

        if combo is None or callback is None:
            return
        modifiers, trigger = combo
        if vk == trigger and all(group & self._pressed for group in modifiers):
            callback()
