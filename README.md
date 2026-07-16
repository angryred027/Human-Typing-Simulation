# HumanTyping

A small Windows desktop app that types text into **any focused window** with
realistic human keystrokes — variable speed, real typo patterns, natural
corrections (backspace and arrow-key word-level fixes), and research-based pause
rhythms. Built on a Markov/stochastic typing engine calibrated to large
keystroke datasets (Dhakal et al. 2018; Baaijen et al. 2012).

## Features

- Types into a selected **target window**, keeping it focused for the whole run
  (OS-level keystrokes via `pynput`); leave it on "None" to use the current focus.
- ASCII-only output — smart punctuation (em-dash, curly quotes, …) is normalized
  and accents are transliterated, so only real keyboard keys are sent.
- In `messaging` rhythm, newlines are typed as **Shift+Enter** so they don't send
  the message.
- Human error model: substitution, omission, insertion, doubling, transposition,
  and Shift/case mistakes — all noticed and corrected like a real typist.
- Two correction styles: immediate backspacing and deferred word-level fixes
  (arrow-key navigation to the error and back).
- Typing rhythm presets (`writing` / `coding` / `messaging`) with mixture pause
  distributions at word / sentence / paragraph boundaries.
- Tkinter UI with a live progress view, system tray, and a global hotkey.
- Config dialog with a rhythm graph of the last run (speed + errors).

## Install & run

Requires Python 3.10+ on Windows.

```bash
pip install -r requirements.txt
python main.py
```

This launches the GUI. Set your text and options via **Config**, pick a target
window with **Select Window** (or leave it on the current focus), then
**Start**. You have `start_delay` seconds to focus the target before typing
begins.

### Controls

| Control | Action |
|---|---|
| **Select Window** | Choose the target window (or "None" = current focus). |
| **Shortcut (P/R)** | Capture a global hotkey that Start / Pause / Resumes. |
| **Start / Pause / Resume** | Main action; label reflects state. |
| **Stop / Cancel** | Abort the current run. |
| Tray left-click | Start / Pause / Resume. |
| Tray right-click | Menu: Show/Hide, Start/Pause/Resume, Cancel, Config, Quit. |

Tray icon: green triangle = ready, red squares = paused, blinking red/gray =
typing. Closing the window hides it to the tray; **Quit** from the tray exits.

## Configuration (`config.json`)

User settings live in `humantyping/config.json` (next to the executable when
frozen). The Config dialog edits them; you can also edit the file directly. The
research-derived model internals live in `humantyping/config.py`.

| Field | Type | Default | Meaning | Applies |
|---|---|---|---|---|
| `text` | string | `""` | Text to type. | live |
| `wpm` | number | `60` | Target average speed (words per minute). | live |
| `layout` | `"qwerty"` \| `"azerty"` | `"qwerty"` | Keyboard layout for neighbor-key error modeling. | live |
| `rhythm` | `"messaging"` \| `"writing"` \| `"coding"` | `"messaging"` | Pause rhythm preset (boundary pause lengths + fluency). | live |
| `start_delay` | number | `3.0` | Seconds to focus the target window before typing. | live |
| `hotkey` | string | `"ctrl+alt+t"` | Global Start/Pause/Resume shortcut (e.g. `ctrl+shift+j`). | live |
| `graph_chars` | number | `120` | How many recent characters the rhythm graph shows (20–2000). | live |
| `base_error_rate` | number | `0.03` | Master typo rate; scales all error types by research ratios. | restart |
| `prob_notice_error` | number | `0.4` | Chance an error is caught immediately vs. deferred to a word-level fix. | restart |
| `prob_word_level_correction` | number | `0.7` | Share of deferred fixes done via arrow-key navigation. | restart |

"live" fields take effect on the next run; "restart" fields are read at startup
(restart the app to apply). The rhythm presets and all model constants
(timing distributions, error weights, speed factors) are documented inline in
`humantyping/config.py`.

## Build a standalone .exe (PyInstaller)

```bat
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --onefile --windowed ^
  --name HumanTyping ^
  --icon humantyping/appicon.ico ^
  --add-data "humantyping/config.json;humantyping" ^
  --add-data "humantyping/appicon.ico;humantyping" ^
  --collect-submodules pynput ^
  --collect-submodules pystray ^
  main.py
```

Notes:
- `--windowed` hides the console (GUI app). The `^` line-continuation is for
  `cmd.exe`; in PowerShell use a backtick `` ` `` or put it all on one line.
- The bundled `config.json` is read-only inside the exe; the app reads and
  writes its live `config.json` next to `HumanTyping.exe`, so settings persist.
- `appicon.ico` is the window/taskbar/exe icon.
- The onefile exe launches `HumanTyping.exe` — no Python install required.

## How it works

`MarkovTyper` (`humantyping/typer.py`) simulates the full keystroke stream
(including mistakes and corrections) with per-key timing, then `TypingController`
(`humantyping/controller.py`) replays that stream as real key events on a
background thread with pause/resume/cancel and progress callbacks. The GUI
(`humantyping/gui.py`) drives it and shows progress, tray status, and the rhythm
graph. Windows helpers for window selection and the Raw Input global hotkey are
in `humantyping/winutil.py`.

## License

MIT
