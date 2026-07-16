"""
Desktop example: type into any focused window (OS-level keystrokes).

Sends realistic human keystrokes to whatever window has focus, using pynput.
Unlike the browser/mobile examples there is no element to target — you focus
the window yourself during the countdown.

Requirements:
    pip install pynput

Usage:
    python desktop_example.py
    Then click into a text editor (Notepad, VS Code, ...) within 3 seconds.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from humantyping import HumanTyper


def main():
    text = "Hello! This was typed like a human, straight into the focused window."

    typer = HumanTyper(wpm=70, rhythm="messaging")

    print("Click into the target window now (Notepad, editor, ...).")
    print("Typing starts in 3 seconds...")
    typer.type_desktop(text, start_delay=3.0)
    print("Done.")


if __name__ == "__main__":
    main()
