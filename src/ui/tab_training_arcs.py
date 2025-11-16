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

from src.common import pad_frame
from src.sql_utility import get_daily_sets, get_exercises

logger = logging.getLogger(__name__)


def get_arcs(exercise: str,
             separator: int = 30
             ) -> list[list[tuple[str, str, str, str]]]:
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
    daily_sets = get_daily_sets(exercise)
    arcs = []
    curr_arc = [daily_sets[0]]

    idx_exercise = 0
    idx_date = 1
    idx_sets_string = 2
    idx_comments = 3

    for i in range(1, len(daily_sets)):
        # Find timedelta between current item and previous item
        curr = daily_sets[i]
        prev = daily_sets[i - 1]
        curr_date = datetime.strptime(curr[idx_date], "%Y-%m-%d").date()
        prev_date = datetime.strptime(prev[idx_date], "%Y-%m-%d").date()
        diff = curr_date - prev_date

        if diff.days < separator:
            # current item is part of current arc.
            curr_arc.append(curr)
        else:
            # current item is the start of a new arc.
            arcs.append(curr_arc)
            curr_arc = [curr]

    arcs.append(curr_arc)

    arcs = prune_arcs(arcs)

    return arcs


def prune_arcs(arcs: list[list[tuple[str, str, str, str]]],
               min_len: int = 4,
               ) -> list[list[tuple[str, str, str, str]]]:
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
        self.lbl_found_arcs.grid(row=3, column=0, sticky="NSEW")

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
            for i in arc:
                logger.info(i)
            new_lbl = ttk.Label(self.frm_results, text=f"ARC {idx}")
            new_lbl.grid(row=len(arcs)-idx, column=0)

        pad_frame(self.frm_results)


