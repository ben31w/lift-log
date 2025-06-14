"""
All functions and classes related to the 'Import Sets' tab.
"""
import os
from tkinter import *
from tkinter import messagebox
from tkinter import ttk

from tksheet import Sheet

from common import pad_frame
from sql_utility import delete_import, get_imports, import_sets_via_html
from tab_my_sets import TabMySets

DELETE_COL_IDX = 3  # column with delete buttons. Column index is 0-based.

class TabImportSets(ttk.Frame):
    """
    This frame is where the user imports exercise sets from various sources.
    - HTML imports (work-in-progress)
    - Apple Notes (TODO)
    - Manual imports (TODO)
    - Picture of journal (very ambitious TODO).

    There is an import status window and a way to remove previous imports.
    TODO implement status window.
    """

    def __init__(self, parent, tab_my_sets: TabMySets):
        ttk.Frame.__init__(self, parent)
        self.tab_my_sets = tab_my_sets

        # Container row 0
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0, sticky=W)
        lbl_import_methods = ttk.Label(row0, text="Import Methods")
        lbl_import_methods.grid(row=0, column=0)

        # Container row 1
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=0, sticky=W)
        import_method_notebook = ttk.Notebook(row1)
        import_method_notebook.grid(row=0, column=0)
        tab_import_via_html = SubTabImportSetsViaHTML(import_method_notebook, self, tab_my_sets)
        tab_import_via_html.pack(fill='both', expand=True)
        import_method_notebook.add(tab_import_via_html, text="HTML")

        # Container row 2
        row2 = ttk.Frame(self)
        row2.grid(row=2, column=0, sticky=W)
        lbl_import_status = ttk.Label(row2, text="Import Status")
        lbl_import_status.grid(row=0, column=0)

        # Container row 3
        row3 = ttk.Frame(self)
        row3.grid(row=3, column=0, sticky=W)
        status_msg_area = Text(row3, height=20, width=170)
        status_msg_area.configure(state='disabled')  # user can't type here.
        status_msg_area.grid(row=0, column=0)
        scrollbar = ttk.Scrollbar(row3, command=status_msg_area.yview)
        scrollbar.grid(row=0, column=1, sticky=NSEW)
        status_msg_area['yscrollcommand'] = scrollbar.set

        # Container row 4
        row4 = ttk.Frame(self)
        row4.grid(row=4, column=0, sticky=W)
        lbl_undo_imports_title = ttk.Label(row4, text="Undo Imports")
        lbl_undo_imports_title.grid(row=0, column=0)

        # Container row 5
        row5 = ttk.Frame(self)
        row5.grid(row=5, column=0, sticky=W)
        lbl_undo_imports_desc = ttk.Label(row5,
                                          text="You can view all your imports and delete them here.")
        lbl_undo_imports_desc.grid(row=0, column=0)

        # Container row 6
        # The sheet displays the method, date time, file, and delete button for each of the user's imports.
        # Each cell in the delete column has a note attached. The note is the SQLite rowid of the import.
        # Most of the columns only contain data, but the delete column contains notes.
        row6 = ttk.Frame(self)
        row6.grid(row=6, column=0, sticky=W)
        self.sheet = Sheet(row6,
                           theme="light green",
                           height=250,
                           width=1200,
                           headers=["Method", "Date Time", "File", "Delete"]
                           )
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
        self.sheet.grid(row=0, column=0)

        pad_frame(self)
        pad_frame(row1)

    def on_cell_select(self, event):
        """
        Called when a cell is selected.
        :param event:
        :return:
        """
        content = event["selected"]
        cell_value = self.sheet.get_cell_data(content.row, content.column)
        print(f"{cell_value} ({content.row}, {content.column})")
        if content.column == DELETE_COL_IDX:
            cell_note = self.sheet.props(content.row, content.column, "note")['note']
            imprt_id = int(cell_note)
            print("  Deleting import.")
            self.delete_import_from_sheet(imprt_id, content.row)

    def update_sheet(self):
        # Update data in the sheet.
        self.sheet.set_data(data=self._get_sheet_data())

        # Restyle the sheet.
        self._style_sheet()

    def _get_sheet_data(self):
        """
        Return list that is used to populate the sheet.

        This function ALSO double dips, and updates the notes for each cell in
        the DELETE COL!!
        :return: [[import1], [import2], ...]
        """
        sheet_data = []
        imports = get_imports()
        for i in range(len(imports)):
            imprt_method, imprt_date_time, imprt_filepath, imprt_id = imports[i]
            sheet_data.append([imprt_method, imprt_date_time, imprt_filepath, 'Delete'])
            # Update notes in the DELETE COL
            self.sheet.note(i, DELETE_COL_IDX, note=imprt_id)
        return sheet_data

    def _style_sheet(self):
        self.sheet.set_all_cell_sizes_to_text()  # Resize cells
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


class SubTabImportSetsViaHTML(ttk.Frame):
    """
    This frame is where the user imports sets via an HTML file.
    """

    def __init__(self, parent, tab_import_sets: TabImportSets, tab_my_sets: TabMySets):
        """
        :param parent: the notebook that stores this tab
        :param tab_import_sets: the overarching tab
        """
        ttk.Frame.__init__(self, parent)
        self.tab_import_sets = tab_import_sets
        self.tab_my_sets = tab_my_sets

        # Container row 0
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0, sticky=W)
        lbl_import_via_html = ttk.Label(row0,
                                        text="Import sets with an HTML (required) and alias (TXT, optional) file.")
        lbl_import_via_html.grid(row=0, column=0)

        # Container row 1
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=0, sticky=W)
        lbl_html_filepath = ttk.Label(row1, text="HTML Filepath")
        lbl_html_filepath.grid(row=0, column=0)
        self.entry_html_filepath = ttk.Entry(row1, width=50)
        self.entry_html_filepath.grid(row=0, column=1)
        btn_browse_html = ttk.Button(row1, text="Browse")
        btn_browse_html.grid(row=0, column=2)

        # Container row 2
        row2 = ttk.Frame(self)
        row2.grid(row=2, column=0, sticky=W)
        lbl_alias_filepath = ttk.Label(row2, text="Alias Filepath")
        lbl_alias_filepath.grid(row=0, column=0)
        self.entry_alias_filepath = ttk.Entry(row2, width=50)
        # default filepath (for now)
        self.entry_alias_filepath.insert(0, "/home/ben31w/projects/lift-log/html/aliases.txt")
        self.entry_alias_filepath.grid(row=0, column=1)
        btn_browse_alias = ttk.Button(row2, text="Browse")
        btn_browse_alias.grid(row=0, column=2)

        # Container row 3
        row3 = ttk.Frame(self)
        row3.grid(row=3, column=0, sticky=W)
        btn_import_html = ttk.Button(row3, text="Import", command=self.import_html_file)
        btn_import_html.grid(row=0, column=0)

        pad_frame(self)

    def browse_html_file(self):
        """Open window to browse for an HTML file."""
        # TODO

    def browse_alias_file(self):
        """Open window to browse for an alias (TXT) file."""
        # TODO

    def import_html_file(self):
        """Import the HTML file that the user has selected."""
        html_file = self.entry_html_filepath.get()
        alias_file = self.entry_alias_filepath.get()

        # First, validate the HTML file. The user cannot proceed without a valid HTML file.
        if not os.path.exists(html_file):
            messagebox.showerror("Error", f"HTML file '{html_file}' does not exist.")
        elif len(html_file) > 5 and html_file[-5:] != '.html':
            messagebox.showerror("Error", f"'{html_file}' is not an HTML file.")
        else:
            # Next, validate the alias file and check for duplicate HTML imports.
            # These are non-critical warnings that the user can choose to ignore.
            warning_msgs = []
            if len(alias_file) > 0 and not os.path.exists(alias_file):
                warning_msgs.append(f"Alias file '{alias_file}' does not exist.")
            # TODO validate format of alias file.
            # TODO Check for duplicate HTML imports

            if len(warning_msgs) > 0:
                full_warning = ""
                for msg in warning_msgs:
                    full_warning += f"{msg}\n\n"
                full_warning += "Want to continue?"
                proceed = messagebox.askokcancel("Warnings", full_warning)
            else:
                proceed = True

            if proceed:
                import_sets_via_html(html_file, alias_file)
                self.tab_my_sets.update_exercises()
                self.tab_import_sets.update_sheet()

