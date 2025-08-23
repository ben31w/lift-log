"""
All functions and classes related to the 'View & Edit Sets' tab.
"""
import datetime
import logging
from tkinter import *
from tkinter import ttk

from tkcalendar import DateEntry
from tksheet import Sheet

from sql_utility import (get_daily_sets, get_first_date,
                         update_user_edited_daily_sets, delete_daily_sets)
from common import pad_frame, ANY, HAS_COMMENTS, NO_COMMENTS, VALID, INVALID
from tab_progress_plots import TabProgressPlots

logger = logging.getLogger(__name__)

# Column index is 0-based. These are the column indexes for the sheet of exercise sets.
DATE_COL = 0
EXERCISE_COL = 1
SETS_STRING_COL = 2
COMMENTS_COL = 3
VALID_COL = 4
IMPORT_NAME_COL = 5
IMPORT_TIME_COL = 6
DELETE_COL = 7

class TabViewEditSets(ttk.Frame):
    """
    This frame displays the user's exercise sets in a tabular format, and the
    user can view or edit them.
    """

    def __init__(self, parent, tab_progress_plots: TabProgressPlots, starting_height: int = 1080):
        """
        Constructor for View & Edit Sets tab.
        :param parent: a reference to the notebook that stores this tab.
               Required by Tkinter.
        :param tab_progress_plots: a reference to the Progress Plots Tab is needed because
               we update elements on that tab as imports are managed.
        :param starting_height: starting height of this frame, passed to the
               VerticalScrolledFrame that this frame contains.
        """
        super().__init__(parent)

        # -- Important attributes --
        self.tab_progress_plots = tab_progress_plots
        # When the user is done editing a cell, track the following fields:
        # (date, exercise, sets_string, comments, rowid)
        # and add them to this list. When the  user clicks SAVE, update the
        # SQLite data to match this list.
        self.edited_daily_sets = []
        # When the user deletes a daily sets items, track the following fields:
        # (rowid, ) [storing as tuple makes it easier to executemany in SQLite3]
        # and add them to this list. When the user clicks SAVE, delete
        # everything we tracked from SQLite.
        self.deleted_daily_sets = []

        # --- Define widgets ---
        # self-level
        self.frm_entries = ttk.Frame(self, padding=(12, 12, 3, 3))
        self.frm_radiobuttons = ttk.Frame(self, padding=(12, 12, 3, 3))
        self.btn_save = ttk.Button(self, text="SAVE CHANGES", state=DISABLED, command=self.save_changes)
        # TODO the sheet doesn't update when an import is added or deleted.
        self.sheet = Sheet(self,
                           theme="light green",
                           height=980,
                           width=1680,
                           headers=["Date", "Exercise", "Sets", "Comments",
                                    "Valid*", "Import*", "Import Time*", "Delete*"])

        # sub-self-level
        self.lbl_exercise = ttk.Label(self.frm_entries, text="Exercise")

        self.combobox = ttk.Combobox(self.frm_entries, width=20)
        exercises = sorted(list(self.tab_progress_plots.esd.keys()))
        self.combobox['values'] = [ALL] + exercises
        self.combobox.set(ALL)
        self.combobox.bind("<<ComboboxSelected>>", self.update_sheet_from_combobox)

        self.lbl_start_date = ttk.Label(self.frm_entries, text="Start Date")
        self.date_entry_start = DateEntry(self.frm_entries,
                                          width=12,
                                          background='darkblue',
                                          foreground='white',
                                          borderwidth=2)
        self.date_entry_start.bind("<<DateEntrySelected>>", self.update_sheet)
        self.lbl_end_date = ttk.Label(self.frm_entries, text="End Date")
        self.date_entry_end = DateEntry(self.frm_entries,
                                        width=12,
                                        background='darkblue',
                                        foreground='white',
                                        borderwidth=2)
        self.date_entry_end.bind("<<DateEntrySelected>>", self.update_sheet)

        self.lbl_comments = ttk.Label(self.frm_radiobuttons, text="Comments")
        self.selected_comments = StringVar(value=ANY)
        self.rb_any_comments = ttk.Radiobutton(self.frm_radiobuttons,
                                               text=ANY,
                                               value=ANY,
                                               variable=self.selected_comments,
                                               command=self._update_sheet)
        self.rb_has_comments = ttk.Radiobutton(self.frm_radiobuttons,
                                               text=HAS_COMMENTS,
                                               value=HAS_COMMENTS,
                                               variable=self.selected_comments,
                                               command=self._update_sheet)
        self.rb_no_comments = ttk.Radiobutton(self.frm_radiobuttons,
                                              text=NO_COMMENTS,
                                              value=NO_COMMENTS,
                                              variable=self.selected_comments,
                                              command=self._update_sheet)

        self.lbl_valid = ttk.Label(self.frm_radiobuttons, text="Valid")
        self.selected_valid = StringVar(value=ANY)
        self.rb_any_valid = ttk.Radiobutton(self.frm_radiobuttons,
                                            text=ANY,
                                            value=ANY,
                                            variable=self.selected_valid,
                                            command=self._update_sheet)
        self.rb_invalid = ttk.Radiobutton(self.frm_radiobuttons,
                                          text=INVALID,
                                          value=INVALID,
                                          variable=self.selected_valid,
                                          command=self._update_sheet)
        self.rb_valid = ttk.Radiobutton(self.frm_radiobuttons,
                                        text=VALID,
                                        value=VALID,
                                        variable=self.selected_valid,
                                        command=self._update_sheet)

        # --- Grid widgets ---
        # self-level
        self.frm_entries.grid(row=0, column=0, sticky='W')
        self.frm_radiobuttons.grid(row=1, column=0, sticky='W')
        self.btn_save.grid(row=2, column=0, sticky='W')
        self.sheet.grid(row=3, column=0, sticky='NSEW')

        # sub-self-level
        self.lbl_exercise.grid(row=0, column=0, sticky='W')
        self.combobox.grid(row=0, column=1, sticky='W')
        self.lbl_start_date.grid(row=0, column=2, sticky='W')
        self.date_entry_start.grid(row=0, column=3, sticky='W')
        self.lbl_end_date.grid(row=0, column=4, sticky='W')
        self.date_entry_end.grid(row=0, column=5, sticky='W')

        self.lbl_comments.grid(row=0, column=0, sticky='W')
        self.rb_any_comments.grid(row=0, column=1, sticky='W')
        self.rb_has_comments.grid(row=0, column=2, sticky='W')
        self.rb_no_comments.grid(row=0, column=3, sticky='W')
        self.lbl_valid.grid(row=1, column=0, sticky='W')
        self.rb_any_valid.grid(row=1, column=1, sticky='W')
        self.rb_invalid.grid(row=1, column=2, sticky='W')
        self.rb_valid.grid(row=1, column=3, sticky='W')

        # --- Configure rows and columns to resize ---
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)

        # Important set up
        self.config_sheet()
        pad_frame(self.frm_radiobuttons)
        self.selected_comments.set(ANY)
        self.selected_valid.set(ANY)
        # Here, we configure padding for this frame, which determines the spacing
        # between this widget and its parent
        self.configure(padding=(3, 3, 3, 3))

    def config_sheet(self):
        """Configure the sheet."""
        # only certain columns will be editable
        self.sheet.readonly_columns([VALID_COL, IMPORT_NAME_COL, IMPORT_TIME_COL, DELETE_COL])

        self.sheet.enable_bindings(
            ("single_select", "drag_select", "select_all", "column_select",
             "row_select", "column_width_resize", "double_click_column_resize",
             "arrowkeys", "right_click_popup_menu", "sort_rows", "copy", "cut",
             "paste", "delete", "undo",
             "edit_cell", # only certain columns are editable b/c of readonly_columns
             "find", "replace", "ctrl_click_select"
             )
        )
        # self.sheet.extra_bindings("delete", self.track_edit)
        # self.sheet.extra_bindings("end_ctrl_x", self.track_edit)
        # self.sheet.extra_bindings("end_ctrl_v", self.track_edit)
        self.sheet.extra_bindings("end_edit_cell", self.track_edit)
        self.sheet.extra_bindings("cell_select", self.on_cell_select)
        # Update sheet by spoofing combobox select event
        self.combobox.set(self.combobox.get())
        self.combobox.event_generate("<<ComboboxSelected>>")

    def update_sheet(self, event:Event):
        self._update_sheet()

    def update_sheet_from_combobox(self, event:Event):
        """
        In addition to updating the sheet to the selected exercise, the combobox
        also resets the date entries.
        :param event:
        :return:
        """
        self.date_entry_start.set_date(get_first_date(exercise=self.combobox.get()))
        self.date_entry_end.set_date(datetime.date.today())
        self._update_sheet()

    def _update_sheet(self):
        """Update sheet to match the current filters."""
        exercise = self.combobox.get()
        start_date = self.date_entry_start.get_date()
        end_date = self.date_entry_end.get_date()
        comments = self.selected_comments.get()
        valid = self.selected_valid.get()

        # Update data in the sheet.
        total_rows = self.sheet.get_total_rows()
        self.sheet.delete_rows(iter(range(total_rows)))
        self.sheet.set_data(data=self._get_sheet_data(exercise, start_date, end_date, comments, valid))

        # Restyle the sheet.
        self._style_sheet()

    def _get_sheet_data(self, exercise=ALL, start_date=None, end_date=None, comments=ANY, valid=ANY):
        """
        Return list that is used to populate the sheet.

        This function ALSO double dips, and updates the notes for each cell!!
        :return: [[daily_sets1], [daily_sets2], ...]
        """
        sheet_data = []
        items = get_daily_sets(exercise=exercise, start_date=start_date, end_date=end_date, comments=comments, valid=valid)
        for i in range(len(items)):
            sets_rowid, sets_date, sets_exercise, sets_string, comments, is_valid, imprt_name, imprt_date_time = items[i]
            sheet_data.append([sets_date, sets_exercise, sets_string, comments, is_valid, imprt_name, imprt_date_time, 'Delete'])
            # Update notes: store rowid in the date column
            self.sheet.note(i, DATE_COL, note=sets_rowid)
        return sheet_data

    def _style_sheet(self):
        self.sheet.set_all_cell_sizes_to_text()  # Resize cells

        self.sheet.dehighlight_all()

        # For any row the user has staged for deletion, color the text red.
        # For any row where the user has staged an edit, color the text green.
        edited_rowids = [tup[4] for tup in self.edited_daily_sets]
        logger.info(f"edited rowids: {edited_rowids}")
        for r in range(self.sheet.get_total_rows()):
            rowid = self.sheet.props(r, DATE_COL, "note")['note']
            if (rowid,) in self.deleted_daily_sets:
                self.sheet.highlight_cells(row=r,
                                           column="all",
                                           bg="white",
                                           fg="red",
                                           overwrite=True)
            elif rowid in edited_rowids:
                self.sheet.highlight_cells(row=r,
                                           column="all",
                                           bg="white",
                                           fg="green",
                                           overwrite=True)

        # Color the 'Delete' column red
        self.sheet.highlight_cells(row="all",
                                   column=DELETE_COL,
                                   bg="red",
                                   fg="white",
                                   overwrite=True)

    def track_edit(self, event):
        """
        Called when a cell is done being edited.
        Track the change, so it can be saved later.
        """
        content = event["selected"]

        new_date = self.sheet.get_cell_data(content.row, DATE_COL)
        new_exercise = self.sheet.get_cell_data(content.row, EXERCISE_COL)
        new_sets_string = self.sheet.get_cell_data(content.row, SETS_STRING_COL)
        new_comments = self.sheet.get_cell_data(content.row, COMMENTS_COL)
        rowid = self.sheet.props(content.row, DATE_COL, "note")['note']
        t = (new_date, new_exercise, new_sets_string, new_comments, rowid)

        # TODO it would be nice if we only track changes when content has truly changed.
        self.edited_daily_sets.append(t)

        self.update_controls_and_display()

    def save_changes(self):
        """Update edited and deleted rows in SQLite."""
        # Update all items that have a tracked edit
        update_user_edited_daily_sets(self.edited_daily_sets)

        # Delete all items that have been staged for deletion
        delete_daily_sets(self.deleted_daily_sets)

        # Clear the lists that are tracking changes
        self.edited_daily_sets.clear()
        self.deleted_daily_sets.clear()

        self.update_controls_and_display()

    def on_cell_select(self, event):
        """
        Called when a cell is selected. Check if the cell is a DELETE button,
        and start tracking rows that the user wants to delete.
        """
        content = event["selected"]

        # When a cell in DELETE COL is selected, add or remove it from the
        #  tracking list.
        if content.column == DELETE_COL:
            rowid = self.sheet.props(content.row, DATE_COL, "note")['note']
            if (rowid,) in self.deleted_daily_sets:
                self.deleted_daily_sets.remove((rowid,))
            else:
                self.deleted_daily_sets.append((rowid,))
            self.update_controls_and_display()

    def update_btn_save(self):
        """
        Check if there are staged changes (edits or deletions).
        If so, enable the save button. Otherwise, disable it.
        """
        if len(self.edited_daily_sets) > 0 or len(self.deleted_daily_sets) > 0:
            self.btn_save.configure(state=NORMAL)
        else:
            self.btn_save.configure(state=DISABLED)

    def update_controls_and_display(self):
        """Update controls (save button) and display (sheet styling)"""
        self._style_sheet()
        self.update_btn_save()


