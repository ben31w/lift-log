"""
All functions and classes related to the 'Import Sets' tab.
"""
import datetime
import logging
import os
import platform
import subprocess
from pathlib import Path
from threading import Thread
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
import tkinter.font as tkfont
from tkinter.scrolledtext import ScrolledText
import webbrowser

from tkcalendar import DateEntry
from tksheet import Sheet

from common import hash_html, pad_frame
from sql_utility import decompress_and_write_html, delete_import, get_import_file_hashes_only, \
    get_imports, import_sets_via_html, _log_import_msg
from sql_utility import logger as sql_logger
from vertical_scrolled_frame import VerticalScrolledFrame
from tab_my_sets import TabMySets
from window_alias_editor import WindowAliasEditor

logger = logging.getLogger(__name__)

# Column index is 0-based. These are the column indexes for the sheet of imports.
FILE_COL_IDX = 2
DELETE_COL_IDX = 3

class TabImportSets(ttk.Frame):
    """
    This frame is where the user imports exercise sets from various sources.
    - HTML imports (work-in-progress)
    - Apple Notes (TODO)
    - Manual imports (TODO)
    - Picture of journal (very ambitious TODO).

    There is an import status window and a way to remove previous imports.
    """

    def __init__(self, parent, tab_my_sets : TabMySets, starting_height : int = 1080):
        """
        Constructor for Import Sets tab.
        :param parent: a reference to the notebook that stores this tab.
               Required by Tkinter.
        :param tab_my_sets: a reference to the My Sets Tab is needed because
               we update elements on that tab as imports are managed.
        :param starting_height: starting height of this frame, passed to the
               VerticalScrolledFrame that this frame contains.
        """
        super().__init__(parent)

        # -- Important Attributes ---
        self.tab_my_sets = tab_my_sets
        self.alias_editor_is_open = False
        header_font = tkfont.Font(family="Arial", size=16, weight=tkfont.BOLD)

        # This frame contains a vertical scrolled frame, which contains an
        # interior frame where we must add content.
        main_frame = VerticalScrolledFrame(self, starting_height=starting_height)
        self.content_frame = main_frame.interior

        # Configure a very small padding between widgets on the content frame.
        # More padding can be added for specific widgets where we want to
        # delimit the sections better.
        # tuple is (padx_left, padx_right, pady_top, pady_bottom)
        self.content_frame.configure(padding=(3, 3, 3, 3))

        # --- Define widgets ---
        lbl_import_methods = ttk.Label(self.content_frame,
                                       text="Import Methods",
                                       font=header_font)
        import_method_notebook = ttk.Notebook(self.content_frame)
        tab_import_via_html = SubTabImportSetsViaHTML(import_method_notebook, self, tab_my_sets)
        tab_import_via_apple_notes = SubTabImportSetsViaAppleNotes(import_method_notebook, self, tab_my_sets)
        lbl_import_status = ttk.Label(self.content_frame,
                                      text="Import Status",
                                      font=header_font)
        self.status_msg_area = ScrolledText(self.content_frame, height=20, width=170)
        lbl_manage_imports_title = ttk.Label(self.content_frame,
                                             text="Manage Imports",
                                             font=header_font)
        lbl_manage_imports_desc = ttk.Label(self.content_frame,
                                            text="You can view and delete your imports here.")
        self.sheet = Sheet(self.content_frame,
                           theme="light green",
                           height=200,
                           width=600,
                           headers=["Method", "Date Time", "File", "Delete"])
        lbl_manage_exercise_aliases_title = ttk.Label(self.content_frame,
                                                      text="Manage Exercise Aliases",
                                                      font=header_font)
        lbl_manage_exercise_aliases_desc = ttk.Label(self.content_frame,
                                                     text="You can manage your exercise aliases here.")
        btn_manage_exercise_aliases = ttk.Button(self.content_frame,
                                                 text="Manage",
                                                 command=lambda: self.open_alias_editor())
        lbl_log_level = ttk.Label(self.content_frame,
                                  text="Log Level",
                                  font=header_font)
        self.combobox_log_level = ttk.Combobox(self.content_frame,
                                          values=[
                                              'DEBUG', 'INFO', 'WARNING',
                                              'ERROR', 'CRITICAL'
                                          ])

        # Additional configurations
        self.config_status_msg_area()
        self.config_sheet()
        self.config_combobox_log_level()

        # --- Grid widgets and configure rows to resize. ---
        # sticky='NSEW' -> widget stretches in all directions when window resizes.
        # sticky='W' -> widget sticks to west edge, but doesn't stretch
        main_frame.grid(row=0, column=0, sticky='NSEW')
        lbl_import_methods.grid(row=0, column=0, sticky='W')
        import_method_notebook.grid(row=1, column=0, sticky='NSEW')
        lbl_import_status.grid(row=2, column=0, pady=(20, 3), sticky='W')
        self.status_msg_area.grid(row=3, column=0, sticky='NSEW')
        lbl_manage_imports_title.grid(row=4, column=0, pady=(20, 3), sticky='W')
        lbl_manage_imports_desc.grid(row=5, column=0, sticky='W')
        self.sheet.grid(row=6, column=0, sticky='NSEW')
        lbl_manage_exercise_aliases_title.grid(row=7, column=0, pady=(20, 3), sticky='NSEW')
        lbl_manage_exercise_aliases_desc.grid(row=8, column=0, sticky='NSEW')
        btn_manage_exercise_aliases.grid(row=9, column=0, sticky='W')
        lbl_log_level.grid(row=10, column=0, pady=(20, 3), sticky='W')
        self.combobox_log_level.grid(row=11, column=0, sticky='W')

        # To get content to resize, we need to row/columnconfigure the content
        # frame, this class (done here), as well as the root Tk window (done
        # in LiftLog)
        self.content_frame.rowconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)
        self.content_frame.rowconfigure(2, weight=1)
        self.content_frame.rowconfigure(3, weight=1)
        self.content_frame.rowconfigure(4, weight=1)
        self.content_frame.rowconfigure(5, weight=1)
        self.content_frame.rowconfigure(6, weight=1)
        self.content_frame.rowconfigure(7, weight=1)
        self.content_frame.rowconfigure(8, weight=1)
        self.content_frame.rowconfigure(9, weight=1)
        self.content_frame.rowconfigure(10, weight=1)
        self.content_frame.rowconfigure(11, weight=1)
        self.content_frame.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Import Method Notebook tabs
        tab_import_via_html.grid(row=0, column=0, sticky='NSEW')
        tab_import_via_apple_notes.grid(row=0, column=0, sticky='NSEW')
        import_method_notebook.add(tab_import_via_html, text="HTML")
        import_method_notebook.add(tab_import_via_apple_notes, text="Apple Notes")

    def config_status_msg_area(self):
        """Configure import status msg area."""
        self.status_msg_area.configure(state='disabled')
        self.status_msg_area.tag_config("INFO", foreground="green3")
        self.status_msg_area.tag_config("WARNING", foreground="dark orange")
        self.status_msg_area.tag_config("ERROR", foreground="red")
        self.status_msg_area.tag_config("CRITICAL", foreground="white", background="red")

    def config_sheet(self):
        """Configure the sheet that displays previous imports"""
        # The sheet displays the method, date time, file, and delete button for each of the user's imports.
        # Each cell in the delete column has a note attached. The note is the SQLite rowid of the import.
        # Most of the columns only contain data, but the delete column contains notes.
        self.sheet.enable_bindings(
            ("single_select",  # allows cell selection
             "row_select",  # allows row selection
             "column_select",  # allows column selection
             "arrowkeys",  # navigation
             "right_click_popup_menu",
             "rc_select",
             "copy",
             "select_all",
             "drag_select",
             "column_width_resize",
             "double_click_column_resize"
             )
        )
        self.sheet.extra_bindings("cell_select", self.on_cell_select)
        self.update_sheet()

    def config_combobox_log_level(self):
        """
        Configure the combobox that sets the logger level of the sql_utility
        logger. (we control this logger because this is the file that handles
        everything SQL- and import-related).
        """
        self.combobox_log_level.set('INFO')
        self.combobox_log_level.bind("<<ComboboxSelected>>", self.update_log_level)
        # This spoofs the 'combobox selected event' to force a refresh.
        self.combobox_log_level.event_generate("<<ComboboxSelected>>")

    def on_cell_select(self, event):
        """
        Called when a cell is selected.
        :param event:
        :return:
        """
        content = event["selected"]
        cell_value = self.sheet.get_cell_data(content.row, content.column)

        # When a cell in the FILE COL is selected, display the selected file.
        # This creates an HTML file in the usr directory, and opens
        # the file in a web browser.
        if content.column == FILE_COL_IDX:
            # The import_id is stored as a note within this column.
            cell_note = self.sheet.props(content.row, content.column, "note")['note']
            imprt_id = int(cell_note)  # str to int

            file_to_write = decompress_and_write_html(imprt_id)
            webbrowser.open(f"file://{os.path.abspath(file_to_write)}")

        # When a cell in DELETE COL is selected, confirm the user wants to delete
        # the selected import.
        if content.column == DELETE_COL_IDX:
            proceed = messagebox.askokcancel("Warning", "Are you sure you want to delete this import?")
            if proceed:
                # The import_id is stored as a note within this column.
                cell_note = self.sheet.props(content.row, content.column, "note")['note']
                imprt_id = int(cell_note)  # str to int
                self.delete_import_from_sheet(imprt_id, content.row)

    def update_sheet(self):
        # Update data in the sheet.
        self.sheet.set_data(data=self._get_sheet_data())

        # Restyle the sheet.
        self._style_sheet()

    def _get_sheet_data(self):
        """
        Return list that is used to populate the sheet.

        This function ALSO double dips, and updates the notes for each cell!!
        :return: [[import1], [import2], ...]
        """
        sheet_data = []
        imports = get_imports()
        for i in range(len(imports)):
            imprt_method, imprt_date_time, imprt_id = imports[i]
            sheet_data.append([imprt_method, imprt_date_time, 'View', 'Delete'])
            # Update notes: store the import ID in some cells.
            self.sheet.note(i, FILE_COL_IDX, note=imprt_id)
            self.sheet.note(i, DELETE_COL_IDX, note=imprt_id)
        return sheet_data

    def _style_sheet(self):
        self.sheet.set_all_cell_sizes_to_text()  # Resize cells
        # Color the 'File' column blue
        self.sheet.highlight_cells(row="all",
                                   column=FILE_COL_IDX,
                                   bg="light blue",
                                   fg="white",
                                   overwrite=True)
        # Color the 'Delete' column red
        self.sheet.highlight_cells(row="all",
                                   column=DELETE_COL_IDX,
                                   bg="red",
                                   fg="white",
                                   overwrite=True)

    def delete_import_from_sheet(self, import_id, sheet_row):
        delete_import(import_id)
        self.sheet.delete_row(sheet_row)
        self.update_sheet()
        self.tab_my_sets.update_exercises()

    def open_alias_editor(self):
        if not self.alias_editor_is_open:
            WindowAliasEditor(self, self.tab_my_sets)

    def update_log_level(self, event: Event):
        """
        Set log level. Specifically, this sets the log level of the SQL utility
        that performs the import.
        """
        level = self.combobox_log_level.get()
        sql_logger.setLevel(level)
        logger.critical(f"Updating sql_utility logger's level to {level}")
        sql_logger.critical(f"  MY LEVEL: {sql_logger.getEffectiveLevel()}")


class SubTabImportSetsViaHTML(ttk.Frame):
    """
    This frame is where the user imports sets via an HTML file.
    """

    def __init__(self, parent, tab_import_sets: TabImportSets, tab_my_sets: TabMySets):
        """
        :param parent: the notebook that stores this tab
        :param tab_import_sets: the overarching tab
        """
        super().__init__(parent)
        self.tab_import_sets = tab_import_sets
        self.tab_my_sets = tab_my_sets

        # Define widgets, bindings, etc.
        lbl_import_via_html = ttk.Label(self, text="Import sets with an HTML file.")
        frm_html_filepath = ttk.Frame(self)
        btn_import_html = ttk.Button(self, text="Import", command=self.import_html_file)

        lbl_html_filepath = ttk.Label(frm_html_filepath, text="HTML Filepath")
        self.entry_html_filepath = ttk.Entry(frm_html_filepath, width=50)
        self.entry_html_filepath.bind("<Control-a>", self.select_all_text)
        btn_browse_html = ttk.Button(frm_html_filepath, text="Browse", command=self.browse_html_file)

        # Grid widgets onto their parents.
        # TODO make this more responsive. the entry could resize as the window resizes.
        lbl_import_via_html.grid(row=0, column=0, sticky='NSEW')
        frm_html_filepath.grid(row=1, column=0, sticky='NSEW')
        btn_import_html.grid(row=2, column=0, sticky='W')

        lbl_html_filepath.grid(row=0, column=0, sticky='W')
        self.entry_html_filepath.grid(row=0, column=1, sticky='W')
        btn_browse_html.grid(row=0, column=2, sticky='W')

    def browse_html_file(self):
        """Open window to browse for an HTML file."""
        filename = filedialog.askopenfilename(filetypes=(("HTML files", "*.html"), ("All files", "*.*")))
        if len(filename) == 0:
            return
        self.entry_html_filepath.delete(0, END)
        self.entry_html_filepath.insert(END, filename)

    def select_all_text(self, event : Event):
        """Select all text in the given Entry widget."""
        event.widget.select_range(0, END)
        event.widget.icursor(END)
        return 'break'

    def import_html_file(self):
        """Import the HTML file that the user has selected."""
        html_file = self.entry_html_filepath.get()

        # First, validate the HTML file. The user cannot proceed without a valid HTML file.
        if not os.path.exists(html_file):
            messagebox.showerror("Error", f"HTML file '{html_file}' does not exist.")
        elif len(html_file) > 5 and html_file[-5:] != '.html':
            messagebox.showerror("Error", f"'{html_file}' is not an HTML file.")
        else:
            # Next, check for non-critical warnings that the user can choose to ignore:
            # - duplicate HTML imports
            warning_msgs = []
            if self.file_already_imported(html_file):
                warning_msgs.append("This HTML file has already been imported. If you import this, you will have duplicate exercise sets.")

            if len(warning_msgs) > 0:
                full_warning = ""
                for msg in warning_msgs:
                    full_warning += f"{msg}\n\n"
                full_warning += "Want to continue?"
                proceed = messagebox.askokcancel("Warnings", full_warning)
            else:
                proceed = True

            if proceed:
                import_sets_via_html(html_file, text_widget=self.tab_import_sets.status_msg_area)
                self.tab_my_sets.update_exercises()
                self.tab_import_sets.update_sheet()

    def file_already_imported(self, html_filepath) -> bool:
        """
        Return true if the given HTML file is already imported, i.e., the
        file hash matches a file hash already there.
        :param html_filepath:
        :return: True/False
        """
        with open(html_filepath, 'r') as f:
            file_content = f.read()
        file_hash = hash_html(file_content)

        # Extract list of strings from list of tuples.
        file_hashes = [item[0] for item in get_import_file_hashes_only()]
        return file_hash in file_hashes

class SubTabImportSetsViaAppleNotes(ttk.Frame):
    """
    This frame is where the user imports sets via Apple Notes.
    """

    def __init__(self, parent, tab_import_sets: TabImportSets, tab_my_sets: TabMySets):
        """
        :param parent: the notebook that stores this tab
        :param tab_import_sets: the overarching tab
        """
        super().__init__(parent)

        # Define fields
        self.tab_import_sets = tab_import_sets
        self.tab_my_sets = tab_my_sets
        # Script directory is the directory of this Python file AND
        # the AppleScript (.scpt) file
        self.script_directory = Path(__file__).parent.resolve()

        # Define widgets
        # TODO add functionality to date entries (would require updating AppleScript file)
        lbl_desc = ttk.Label(self, text="Import exercise sets by scanning your Apple Notes. You must be using macOS.")
        lbl_start = ttk.Label(self, text="Start Date (nonfunctional)")
        date_entry_start = DateEntry(self, background='darkblue', foreground='white', borderwidth=2)
        date_entry_start.set_date(datetime.date(month=1, day=1, year=2000))
        lbl_end = ttk.Label(self, text="End Date (nonfunctional)")
        date_entry_end = DateEntry(self, background='darkblue', foreground='white', borderwidth=2)
        self.btn_import = ttk.Button(self, text="Import", command=self.import_notes)

        # Grid widgets
        lbl_desc.grid(row=0, column=0, columnspan=2, sticky='NSEW')
        lbl_start.grid(row=1, column=0)
        date_entry_start.grid(row=1, column=1)
        lbl_end.grid(row=2, column=0)
        date_entry_end.grid(row=2, column=1)
        self.btn_import.grid(row=3, column=0)

        # Configure columns to resize
        # TODO not working for some reason... column 0 is always equal in size to column 1
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

    def import_notes(self):
        """Initiate the Apple Notes import."""
        system = platform.system()
        if system != "Darwin":  # Darwin = macOS
            messagebox.showerror("Sorry", "You must use macOS to import sets via Apple Sets")
            return

        self.btn_import.config(state=DISABLED)
        self.tab_import_sets.status_msg_area.configure(state='normal')
        self.tab_import_sets.status_msg_area.delete("1.0", END)

        _log_import_msg("Retrieving Apple Notes... This may take a few minutes.", self.tab_import_sets.status_msg_area)

        # Run AppleScript file that gets workout notes into an HTML file
        # Spin this on a separate thread so it doesn't lock up the GUI.
        t = Thread(target=self.run_applescript)
        t.start()
        self.monitor(t)

    def run_applescript(self):
        """Run the script that retrieves workouts from Apple Notes."""
        subprocess.run(["osascript", f"{self.script_directory}/workout_notes.scpt"])

    def monitor(self, thread:Thread):
        """
        Monitor the given thread:
        - If the thread is alive, keep monitoring (check every second)
        - If the thread is done, import the HTML file that was generated and re-enable the import button.
        """
        if thread.is_alive():
            self.after(1000, lambda: self.monitor(thread))
        else:
            # Now import the HTML file that was generated.
            # TODO We label this as an HTML import (which it is), but it's really an Apple Notes import.
            import_sets_via_html(f"{self.script_directory}/../usr/my_apple_workouts.html",
                                 text_widget=self.tab_import_sets.status_msg_area, clear_text_widget=False)
            self.tab_my_sets.update_exercises()
            self.tab_import_sets.update_sheet()

            _log_import_msg("Done retrieving Apple Notes!", self.tab_import_sets.status_msg_area)
            self.btn_import.config(state=NORMAL)