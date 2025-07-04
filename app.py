import json
import logging.config
from tkinter import Tk
from tkinter import ttk
import sys

from sql_utility import create_tables
from tab_import_sets import TabImportSets
from tab_my_sets import TabMySets

WINDOW_HEIGHT = 1080
WINDOW_WIDTH = 1750

# LOAD + CONFIGURE LOGGER
with open("logging_config.json", "r") as f:
    config = json.load(f)

logging.config.dictConfig(config)
logger = logging.getLogger(__name__)

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
        self.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}')
        self.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Initialize SQLite data first.
        create_tables()

        # Init main notebook and tabs
        main_notebook = ttk.Notebook(self)
        main_notebook.pack(fill='both', expand=True)
        tab_my_sets = TabMySets(main_notebook)
        tab_my_sets.pack(fill='both', expand=True)
        tab_import_sets = TabImportSets(main_notebook, tab_my_sets)
        tab_import_sets.pack(fill='both', expand=True)
        main_notebook.add(tab_my_sets, text="My Sets")
        main_notebook.add(tab_import_sets, text="Import Sets")

    # This is needed for full exception logging: sometimes Tkinter swallows exceptions.
    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        logger.critical("Uncaught Tkinter exception", exc_info=(exc_type, exc_value, exc_traceback))
        # Optional: show message to user
        # messagebox.showerror("Error", str(exc_value))

if __name__ == '__main__':
    logger.info("App started")
    lift_log = LiftLog()
    lift_log.mainloop()
    logger.info("App closed\n")
