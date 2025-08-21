"""
Common utility functions for the project.
"""
import hashlib
from tkinter import END, Text
from tkinter import ttk
import zlib

ALL = 'all'
ANY = "Any"
HAS_COMMENTS = "Has comments"
NO_COMMENTS = "No comments"
INVALID = "Invalid"
VALID = "Valid"

def pad_frame(frame: ttk.Frame):
    """
    Add padding to each widget inside a frame. Call this after the frame's
    widgets have been initialized and placed inside the frame.
    :param frame:
    :return:
    """
    for child in frame.winfo_children():
        child.grid_configure(padx=5, pady=5)

def hash_html(content: str) -> str:
    """
    Hash a string. This produces a unique identifier that is concise but not
    reverse engineerable.

    :param content: string
    :return: hash value
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def compress_html(content: str) -> bytes:
    """
    Compress a string into bytes. This produces a binary string that is
    reverse engineerable.

    :param content: string
    :return: binary string
    """
    return zlib.compress(content.encode('utf-8'))

def decompress_html(blob: bytes) -> str:
    """
    Reverse engineer binary string.

    :param blob: binary string
    :return: string
    """
    return zlib.decompress(blob).decode('utf-8')

def print_to_text_widget(msg: str, text_widget: Text, level: str = "INFO"):
    """Print msg to a text widget."""
    if text_widget is not None:
        text_widget.insert(END, msg + "\n", level)
