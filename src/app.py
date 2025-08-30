"""
The main script for running the application.
This script:
- sets up logging
- defines the top-level Tk widget that everything is gridded on to
- runs the top-level Tk widget
"""
import json
import logging.config
from tkinter import Tk
from tkinter import ttk
import sys

from screeninfo import get_monitors

from sql_utility import create_tables
from tab_view_edit_sets import TabViewEditSets
from tab_import_sets import TabImportSets
from tab_progress_plots import TabProgressPlots


# LOAD + CONFIGURE LOGGER
# ---LOGGER AND HANDLER LOGIC---
#  LOGGERS              LOGGER_LEVEL    HANDLERS (name, HANDLER_LEVEL)
#  root (app.py)              DEBUG  => handlers (file, INFO; console, WARNING)
#     tab_import_sets           //   =>   //
#     tab_view_edit_sets        //   =>   //
#     tab_progress_plots        //   =>   //
#     sql_utility             INFO*  =>   //
#  matplotlib root           WARNING =>   //
#
# *The level of this particular logger can be adjusted through GUI TODO is this needed anymore?
#
# root logger level and handler levels are set inside logging_config.json.
# matplotlib logger level is set programmatically.
#
# In order to see DEBUG messages, you need to manually update one of the
#  handlers in logging_config.json. None of the handlers enable this by default
#  to reduce clutter.
with open("logging_config.json", "r") as f:
    config = json.load(f)

logging.config.dictConfig(config)
logger = logging.getLogger()  # root logger

def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log Ctrl+C
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_uncaught_exceptions


class LiftLog(Tk):
    def __init__(self, *args, **kwargs):
        # Init window
        Tk.__init__(self, *args, **kwargs)
        self.title("Lift Log")

        # Width/height of the user's primary display determines starting
        # width/height of the application.

        # Check for a primary display, and get its width and height.
        # We arbitrarily assume a starting screen res of 1920x1080, but this
        # should get overridden when we check for a primary display.
        screen_width_px = 1920
        screen_height_px = 1080
        for m in get_monitors():
            if m.is_primary:
                screen_width_px = m.width
                screen_height_px = m.height
                break

        # Using the screen width and height, set a 'Matplotlib scale'.
        # If the screen isn't 1920x1080, we can use the scale to adjust the
        # size + fonts of the MPL plots so they display nicely.
        self.mpl_scale = min(screen_width_px / 1920, screen_height_px / 1080)

        # The app looks consistently best at full screen, so make that the
        # default dimensions
        self.geometry(f"{int(screen_width_px)}x{int(screen_height_px)}")

        # Initialize SQLite data first.
        create_tables()

        # Init main notebook and tabs. Each notebook tab is a frame.
        main_notebook = ttk.Notebook(self)
        self.tab_progress_plots = TabProgressPlots(main_notebook, self.mpl_scale)
        self.tab_view_edit_sets = TabViewEditSets(main_notebook, screen_height_px)
        self.tab_import_sets = TabImportSets(main_notebook, screen_height_px)

        # Define layout. For the frames to stretch:
        # - specify sticky when gridding AND
        # - specify weight on the parent's rows and columns!!
        main_notebook.grid(row=0, column=0, sticky='NSEW')
        self.tab_progress_plots.grid(row=0, column=0, sticky='NSEW')
        self.tab_view_edit_sets.grid(row=0, column=0, sticky='NSEW')
        self.tab_import_sets.grid(row=0, column=0, sticky='NSEW')

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        main_notebook.add(self.tab_progress_plots, text="Progress Plots")
        main_notebook.add(self.tab_view_edit_sets, text="View & Edit Sets")
        main_notebook.add(self.tab_import_sets, text="Import Sets")

        main_notebook.bind('<<NotebookTabChanged>>', self.on_tab_change)

    # This is needed for full exception logging: sometimes Tkinter swallows exceptions.
    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        logger.critical("Uncaught Tkinter exception", exc_info=(exc_type, exc_value, exc_traceback))
        # Optional: show message to user
        # messagebox.showerror("Error", str(exc_value))

    # Tab change events.
    def on_tab_change(self, event):
        tab = event.widget.tab('current')['text']
        if tab == "Progress Plots":
            self.tab_progress_plots.update_exercises()
        if tab == "View & Edit Sets":
            self.tab_view_edit_sets.update_sheet()

if __name__ == '__main__':
    logger.info("App started")
    lift_log = LiftLog()
    lift_log.mainloop()
    logger.info("App closed\n")
