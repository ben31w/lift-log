"""
Common utility functions for the project.
"""
from tkinter import ttk

def pad_frame(frame: ttk.Frame):
    """
    Add padding to each widget inside a frame. Call this after the frame's
    widgets have been initialized and placed inside the frame.
    :param frame:
    :return:
    """
    for child in frame.winfo_children():
        child.grid_configure(padx=5, pady=5)