from tkinter import Tk
from tkinter import ttk

from sql_utility import create_tables
from tab_import_sets import TabImportSets
from tab_my_sets import TabMySets

WINDOW_HEIGHT = 1080
WINDOW_WIDTH = 1700

# TODO use styles? add more styles?
ttk.Style().configure("TButton", padding=6, relief="flat",
                      background="#ccc")

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

if __name__ == '__main__':
    lift_log = LiftLog()
    lift_log.mainloop()
