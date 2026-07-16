"""
HumanTyping - realistic human keystroke simulation for a focused desktop window.

Types text into whatever window has focus, reproducing human timing, errors, and
corrections. See README for the config.json specification and build instructions.
"""

__version__ = "2.0.0"
__license__ = "MIT"

from .typer import MarkovTyper
from .controller import TypingController
from . import config

__all__ = ["MarkovTyper", "TypingController", "config"]
