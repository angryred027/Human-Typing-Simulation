from __future__ import annotations

import threading
import time
import unicodedata
from typing import Callable

from .typer import MarkovTyper

_ASCII_MAP = {
    "—": "-", "–": "-", "‒": "-", "―": "-",
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "…": "...", " ": " ", "•": "*", "→": "->", "·": "-",
}

BREAK_THRESHOLD = 0.6  # seconds; a pause longer than this counts as a break


def to_ascii(text: str) -> str:
    out = []
    for ch in text:
        if ch in _ASCII_MAP:
            out.append(_ASCII_MAP[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            norm = unicodedata.normalize("NFKD", ch)
            out.append("".join(c for c in norm if ord(c) < 128 and unicodedata.category(c) != "Mn"))
    return "".join(out)


def _extract_char(action: str) -> str:
    first_quote = action.index("'")
    last_quote = action.rindex("'")
    return action[first_quote + 1:last_quote]


def _is_error(action: str) -> bool:
    return any(k in action for k in ("ERROR", "SWAP", "OMIT", "INSERT", "DOUBLE"))


class TypingController:
    def __init__(self, on_progress: Callable | None = None,
                 on_sample: Callable | None = None,
                 on_state: Callable | None = None) -> None:
        self.on_progress = on_progress
        self.on_sample = on_sample
        self.on_state = on_state
        self.state = "idle"
        self.target_text = ""
        self._thread: threading.Thread | None = None
        self._pause = threading.Event()
        self._cancel = threading.Event()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        return self._pause.is_set()

    def start(self, text, wpm, rhythm, layout, start_delay, ensure_focus=None) -> None:
        if self.is_running():
            return
        self._pause.clear()
        self._cancel.clear()
        self.target_text = text
        self._thread = threading.Thread(
            target=self._run, args=(text, wpm, rhythm, layout, start_delay, ensure_focus), daemon=True)
        self._thread.start()

    def pause(self) -> None:
        if self.is_running() and not self._pause.is_set():
            self._pause.set()
            self._set_state("paused")

    def resume(self) -> None:
        if self.is_running() and self._pause.is_set():
            self._pause.clear()
            self._set_state("typing")

    def toggle(self) -> None:
        if self._pause.is_set():
            self.resume()
        else:
            self.pause()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.clear()

    def _set_state(self, state: str) -> None:
        self.state = state
        if self.on_state:
            self.on_state(state)

    def _sleep(self, seconds: float) -> None:
        end = time.time() + seconds
        while True:
            if self._cancel.is_set():
                return
            if self._pause.is_set():
                pstart = time.time()
                while self._pause.is_set() and not self._cancel.is_set():
                    time.sleep(0.03)
                end += time.time() - pstart
                continue
            remaining = end - time.time()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.02))

    def _run(self, text, wpm, rhythm, layout, start_delay, ensure_focus) -> None:
        from pynput.keyboard import Controller, Key

        text = to_ascii(text)
        try:
            typer = MarkovTyper(text, target_wpm=wpm, layout=layout, rhythm=rhythm)
        except ValueError:
            self._set_state("idle")
            return

        _, history = typer.run()
        total = len(text)
        total_time = history[-1][0] if history else 0.0
        keyboard = Controller()
        newline_shift = rhythm == "messaging"  # Shift+Enter avoids sending the message

        self._set_state("counting")
        deadline = time.time() + max(0.0, start_delay)
        while time.time() < deadline:
            if self._cancel.is_set():
                self._set_state("idle")
                return
            time.sleep(0.05)
        if ensure_focus:
            ensure_focus()
            time.sleep(0.15)

        self._set_state("typing")
        if self.on_progress:
            self.on_progress({"percent": 0.0, "typed": 0, "total": total, "eta": total_time, "caret": 0})

        last_t = 0.0
        for t, action, current in history:
            if "INIT" in action:
                continue
            if self._cancel.is_set():
                break
            delay = t - last_t
            self._sleep(delay)
            if self._cancel.is_set():
                break
            last_t = t
            if ensure_focus:
                ensure_focus()

            if "BACKSPACE" in action:
                keyboard.tap(Key.backspace)
            elif "ARROW_LEFT" in action:
                keyboard.tap(Key.left)
            elif "ARROW_RIGHT" in action:
                keyboard.tap(Key.right)
            elif "TYPED" in action:
                for ch in to_ascii(_extract_char(action)):
                    if ch == "\n" and newline_shift:
                        with keyboard.pressed(Key.shift):
                            keyboard.tap(Key.enter)
                    else:
                        keyboard.type(ch)

            typed = len(current)
            if self.on_progress:
                self.on_progress({
                    "percent": 100.0 * typed / total if total else 100.0,
                    "typed": typed,
                    "total": total,
                    "eta": max(0.0, total_time - t),
                    "caret": min(typed, total),
                })
            if self.on_sample and "TYPED" in action:
                self.on_sample({"iki": delay, "error": _is_error(action),
                                "typed": typed, "break": delay >= BREAK_THRESHOLD})

        self._set_state("done" if not self._cancel.is_set() else "idle")
