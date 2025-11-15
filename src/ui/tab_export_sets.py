"""
All functions and classes related to the 'Export Sets' tab.
"""
import datetime
import logging
import webbrowser
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

from src.common import pad_frame
from src.sql_utility import write_daily_sets_to_html

logger = logging.getLogger(__name__)

class TabExportSets(ttk.Frame):
    """
    This frame is where the user can export all their sets into an HTML file.
    """

    def __init__(self, parent):
        """
        Constructor for this tab.
        :param parent: a reference to the notebook that stores this tab.
               Required by Tkinter.
        """
        super().__init__(parent)

        # -- Important variables --
        desc = ("You can export all your exercise sets into an HTML file here. "
                "This file can be opened in your web browser, modified, and "
                "imported like any other HTML file.")
        src_dir = Path(__file__).parent.resolve()
        html_dir = src_dir.parent / "html"
        default_filename = f"export-{datetime.date.today()}.html"
        header_font = tkfont.Font(family="Arial", size=16, weight=tkfont.BOLD)

        # --- Define widgets ---
        # self-level
        self.lbl_title = ttk.Label(self, text="Export Sets", font=header_font)
        self.lbl_desc = ttk.Label(self, text=desc)
        self.frm_choose_file = ttk.Frame(self)
        self.btn_export = ttk.Button(self, text="Export", command=self.export)

        # sub-self-level
        self.lbl_dir = ttk.Label(self.frm_choose_file, text="Directory")
        self.entry_dir = ttk.Entry(self.frm_choose_file, width=50)
        self.btn_browse = ttk.Button(self.frm_choose_file, text="Browse", command=self.browse_dir)
        self.lbl_filename = ttk.Label(self.frm_choose_file, text="Filename")
        self.entry_filename = ttk.Entry(self.frm_choose_file, width=50)

        # --- Grid widgets ---
        # self-level
        self.lbl_title.grid(row=0, column=0, sticky='W')
        self.lbl_desc.grid(row=1, column=0, sticky='W')
        self.frm_choose_file.grid(row=2, column=0, sticky='W')
        self.btn_export.grid(row=3, column=0, sticky='W')

        # sub-self-level
        self.lbl_dir.grid(row=0, column=0)
        self.entry_dir.grid(row=0, column=1)
        self.btn_browse.grid(row=0, column=2)

        self.lbl_filename.grid(row=1, column=0)
        self.entry_filename.grid(row=1, column=1)

        # --- Configure rows and columns to resize ---
        # Not needed for this basic tab.

        # --- Important set up ---
        # Here, we configure padding for this frame, which determines the spacing
        # between this widget and its parent
        self.configure(padding=(3, 3, 3, 3))
        pad_frame(self)
        pad_frame(self.frm_choose_file)

        self.entry_dir.insert(0, str(html_dir))
        self.entry_filename.insert(0, default_filename)

    def browse_dir(self):
        """Open window to browse for a directory."""
        filename = filedialog.askdirectory()
        if len(filename) == 0:
            return
        self.entry_dir.delete(0, END)
        self.entry_dir.insert(END, filename)

    def export(self):
        """Export exercise sets into an HTML file."""
        full_filepath = Path(self.entry_dir.get()) / self.entry_filename.get()

        if full_filepath.exists():
            proceed = messagebox.askokcancel("Warning", "This filename already exists. Are you sure you want to overwrite it?")
        else:
            proceed = True

        if proceed:
            write_daily_sets_to_html(full_filepath)
            logger.info(f"Done exporting file {full_filepath}")
            open_file = messagebox.askyesno("Success", "Your exercise sets were successfully exported. Open file?")
            if open_file:
                webbrowser.open(f"file://{str(full_filepath)}")

