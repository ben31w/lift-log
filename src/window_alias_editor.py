"""
This class is a window where the user can edit their exercise aliases.
"""
from tkinter import TclError, Toplevel
from tkinter import messagebox
from tkinter import ttk
from tkinter.constants import END, INSERT, SEL
from tkinter.scrolledtext import ScrolledText

from sql_utility import ALIASES_FILE, update_daily_sets_to_alias

WINDOW_HEIGHT = 100
WINDOW_WIDTH = 100

class WindowAliasEditor(Toplevel):
    def __init__(self, tab_import_sets, tab_progress_plots):
        """
        A window for the exercise alias editor.

        :param tab_import_sets: a reference to the Import Sets tab is needed
               to allow only one instance of this window to be open.
        :param tab_progress_plots: a reference to the Progress Plots tab is needed
               to update exercises.
        """
        super().__init__()
        self.tab_import_sets = tab_import_sets
        self.tab_progress_plots = tab_progress_plots

        self.tab_import_sets.alias_editor_is_open = True

        # Row 0
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0)
        btn_save = ttk.Button(row0, text="Save", command=self.save)
        btn_save.grid(row=0, column=0)

        # Row 1
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=0)
        self.edit_area = ScrolledText(row1, undo=True, height=40, width=120)
        with open(ALIASES_FILE, 'r') as f:
            self.edit_area.insert(END, f.read())
        self.edit_area.grid(row=0, column=0)

        # Key bindings for the edit area
        # Prevent default Ctrl+Y paste
        self.edit_area.bind_class("Text", "<Control-y>", lambda e: "break")
        self.edit_area.bind("<Control-z>", self.undo)
        self.edit_area.bind("<Control-Shift-z>", self.redo)
        self.edit_area.bind("<Control-a>", self.select_all)
        self.edit_area.bind("<Control-A>", self.select_all)  # just in case caps lock is on

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def undo(self, event=None):
        try:
            self.edit_area.edit_undo()
            return 'break'
        except TclError:
            pass

    def redo(self, event=None):
        try:
            self.edit_area.edit_redo()
            return 'break'
        except TclError:
            pass

    # Select all the text in self.edit_area
    def select_all(self, event):
        self.edit_area.tag_add(SEL, "1.0", END)
        self.edit_area.mark_set(INSERT, "1.0")
        self.edit_area.see(INSERT)
        return 'break'

    def save(self):
        """
        Save the alias file AND update all imports to match the new alias.
        """
        # Save file
        after_edits = self.edit_area.get("1.0", END).strip()
        with open(ALIASES_FILE, 'w') as f:
            f.write(after_edits)

        update_daily_sets_to_alias()  # update SQLite
        self.tab_progress_plots.update_exercises() # update Progress Plots tab

    def close_window(self):
        # Check if the file has been modified, and ask the user if they want to
        # save first.
        with open(ALIASES_FILE, 'r') as f:
            before_edits = f.read().strip()
        after_edits = self.edit_area.get("1.0", END).strip()
        if after_edits != before_edits:
            save_before_exit = messagebox.askyesnocancel(title="Save file?",
                                                         message="Would you like to save before exiting?")
            if save_before_exit is None:
                # cancel, i.e., don't close the window
                return
            if save_before_exit:
                self.save()
        # Close this window TODO not reaching here
        self.tab_import_sets.alias_editor_is_open = False
        self.destroy()

