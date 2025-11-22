"""
All functions and classes related to the 'Training Arcs' tab.
"""
from datetime import datetime
import logging
import webbrowser
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

from tksheet import Sheet

from src.common import pad_frame
from src.obj.exercise_arc import DailySets, ExerciseArc
from src.sql_utility import get_daily_sets, get_exercises, _split_sets_string

logger = logging.getLogger(__name__)


def get_arcs(exercise: str,
             separator: int = 30
             ) -> list[ExerciseArc]:
    """
    Return arcs for the given exercise.
    An arc represents a training period for an exercise, and it consists of
    an ordered list of daily_sets items over a training time period.

    Ex: [
     ('bb bench', '2023-08-22', '10, 9, 5 @ 155', ''),
     ('bb bench', '2023-09-06', '3x7 @ 175', ''),
     ('bb bench', '2023-09-10', '3x7 @ 175', ''),
    ]

    :param exercise: the exercise to fetch arcs for
    :param separator: minimum num days that separates one arc from another
    :return: arcs
    """
    daily_sets: list[DailySets] = [DailySets(t) for t in get_daily_sets(exercise)]
    arcs: list[ExerciseArc] = []
    curr_arc: ExerciseArc = ExerciseArc([daily_sets[0]])

    for i in range(1, len(daily_sets)):
        # Find timedelta between current item and previous item
        curr = daily_sets[i]
        prev = daily_sets[i - 1]
        diff = curr.date - prev.date

        if diff.days < separator:
            # current item is part of current arc.
            curr_arc.add_daily_sets_obj(curr)
        else:
            # current item is the start of a new arc.
            arcs.append(curr_arc)
            curr_arc = ExerciseArc([curr])

    arcs.append(curr_arc)

    arcs = prune_arcs(arcs)

    return arcs


def prune_arcs(arcs: list[ExerciseArc],
               min_len: int = 4,
               ) -> list[ExerciseArc]:
    """
    Remove arcs that are too short. Except the most recent arc. That can stay.

    :param arcs: list of arcs to prune
    :param min_len: minimum length an arc must be
    :return: pruned arcs
    """
    filtered_arcs = []
    last_idx = len(arcs) - 1
    for idx, arc in enumerate(arcs):
        if len(arc) > min_len or idx == last_idx:
            filtered_arcs.append(arc)
    return filtered_arcs


def config_sheet(sheet: Sheet) -> None:
    """Configure a Sheet."""
    sheet.readonly()
    sheet.enable_bindings(
        "single_select", "drag_select", "select_all", "column_select",
        "row_select", "column_width_resize", "double_click_column_resize",
        "arrowkeys", "right_click_popup_menu", "copy",
        "find", "ctrl_click_select"
    )
    sheet.set_all_cell_sizes_to_text()


def format_sets_string_for_cell(sets_str: str) -> str:
    """Format a sets string to display in a cell."""
    if sets_str.count("@") < 2:
        # Unweighted sets or all sets are at the same weight.
        # Render on one line/return as-is.
        return sets_str
    else:
        # Render each weight on a new line.
        lines = []
        split_by_wt = _split_sets_string(sets_str)
        for i in range(0, len(split_by_wt), 2):
            setsxreps = split_by_wt[i].replace(" ", "")
            wt = split_by_wt[i+1].strip()
            line = f"{setsxreps} @ {wt}"
            lines.append(line)
        return "\n".join(lines)


class TabTrainingArcs(ttk.Frame):
    """
    This frame is where the user can view the training arcs of a particular
    exercise.
    """

    def __init__(self, parent):
        """
        Constructor for this tab.
        :param parent: a reference to the notebook that stores this tab.
               Required by Tkinter.
        """
        super().__init__(parent)

        # --- Define widgets ---
        self.frm_controls = ttk.Frame(self)  # statically sized frame at top of tab
        self.frm_results = ttk.Frame(self)  # dynamically sized frame where results will appear

        self.lbl_exercise = ttk.Label(self.frm_controls, text="Exercise: ")
        self.combobox = ttk.Combobox(self.frm_controls, width=20)
        self.lbl_separator = ttk.Label(self.frm_controls, text="Separator: ")
        self.entry_separator = ttk.Entry(self.frm_controls)
        self.entry_separator.insert(0, "30")  # default value
        self.lbl_days = ttk.Label(self.frm_controls, text="days")
        self.btn_search = ttk.Button(self.frm_controls, text="Search", command=self.update_arcs_results)
        self.lbl_found_arcs = ttk.Label(self.frm_controls)  # blank until a search is run

        # --- Manage layout of widgets ---
        self.frm_controls.grid(row=0, column=0, sticky="NSEW")
        self.frm_results.grid(row=1, column=0, sticky="NSEW")

        self.lbl_exercise.grid(row=0, column=0, columnspan=3, sticky="NSEW")
        self.combobox.grid(row=0, column=1, columnspan=3, sticky="NSEW")
        self.lbl_separator.grid(row=1, column=0, sticky="NSEW")
        self.entry_separator.grid(row=1, column=1, sticky="NSEW")
        self.lbl_days.grid(row=1, column=2, sticky="NSEW")
        self.btn_search.grid(row=2, column=0, sticky="NSEW")
        self.lbl_found_arcs.grid(row=3, column=0, columnspan=3, sticky="NSEW")

        # Configure the responsive layout for each row and column.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # padding = WNES spacing between a widget and its parent
        self.configure(padding=(3, 3, 3, 3))
        pad_frame(self.frm_controls)

        self.update_exercises()

    def update_exercises(self) -> None:
        """Update list of exercises in the combobox."""
        self.combobox["values"] = get_exercises()

    def update_arcs_results(self) -> None:
        """
        Search for training arcs with the selected exercise and separator.
        Update the results frame.
        """
        # Get training arcs from current selection
        exercise = self.combobox.get()
        try:
            separator = int(self.entry_separator.get())
            if separator < 1:
                raise ValueError
        except ValueError:
            self.lbl_found_arcs.config(text="Separator must be a positive integer.")
            return
        arcs = get_arcs(exercise, separator)
        self.lbl_found_arcs.config(text=f"Found {len(arcs)} arcs.")

        # Clear current results
        for w in self.frm_results.winfo_children():
            w.destroy()

        # Display new results
        for idx, arc in enumerate(arcs):
            logger.info(f"\nARC {idx}")
            for i in arc.daily_sets_list:
                logger.info(i)

            # Create a frame to store a label and a Tksheet.
            new_frm = ttk.Frame(self.frm_results)
            new_lbl = ttk.Label(new_frm, text=f"ARC {idx}")
            new_sheet = Sheet(new_frm,
                              theme="light green",
                              height=150,
                              width=1000,
                              headers=[ds.date for ds in arc.daily_sets_list])
            new_sheet.set_data(data=[format_sets_string_for_cell(ds.sets_string)
                                     for ds in arc.daily_sets_list])
            config_sheet(new_sheet)

            new_frm.grid(row=len(arcs)-idx, column=0)
            new_lbl.grid(row=0, column=0)
            new_sheet.grid(row=1, column=0)

        pad_frame(self.frm_results)

