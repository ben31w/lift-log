"""
All functions and classes related to the 'Training Arcs' tab.
"""
from datetime import datetime, date, timedelta
import logging
import webbrowser
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import mplcursors
from matplotlib.colors import Colormap
from matplotlib.figure import Figure
from tkcalendar import DateEntry
import tksheet
from tksheet import Sheet

from src.common import pad_frame
from src.obj.exercise_arc import DailySets, ExerciseArc
from src.sql_utility import get_daily_sets, get_exercise_sets_dict, get_exercises, _split_sets_string
from src.ui.vertical_scrolled_frame import VerticalScrolledFrame

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


def format_sets_string_for_cell(sets_str: str) -> str:
    """Format a single sets string instance to display in a cell."""
    if sets_str.count("@") < 2:
        # Unweighted sets or all sets are at the same weight.
        # Render on one line, but adjust spacing.
        return sets_str.replace(" ", "").replace("@", " @ ")
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


def format_sets_string_list(sets_strings: list[str]) -> tuple[list[str], int]:
    """
    Format a list of sets strings to display in a sheet.
    Each distinct weight within the sets string will appear on its own line.
    Ex: "10@135, 8@145, 6@155" ->
        "10 @ 135\n8 @ 145,\n6 @ 155"  (3 lines)

    Also, return the max number of lines among the formatted sets strings.

    :param sets_strings: list of sets_strings
    :return: list of formatted sets strings AND max number of lines
    """
    formatted_strings = []
    max_lines = 1

    for sets_string in sets_strings:
        formatted = format_sets_string_for_cell(sets_string)
        lines = formatted.count("\n") + 1
        formatted_strings.append(formatted)
        max_lines = max(max_lines, lines)

    return formatted_strings, max_lines


def create_arc_sheet(parent_frame: ttk.Frame, arc: ExerciseArc) -> tksheet.Sheet:
    """Create a Tksheet for the given training arc."""
    new_sheet = Sheet(parent_frame,
                      theme="light green",
                      # height=200,
                      width=1680,
                      show_y_scrollbar=False,
                      headers=[ds.date for ds in arc.daily_sets_list])

    formatted_sets_strings, max_lines = format_sets_string_list([ds.sets_string for ds in arc.daily_sets_list])
    new_sheet.set_data(data=formatted_sets_strings)

    new_sheet.readonly()
    new_sheet.enable_bindings(
        "single_select", "drag_select", "select_all", "column_select",
        "row_select", "column_width_resize", "double_click_column_resize",
        "arrowkeys", "right_click_popup_menu", "copy",
        "find", "ctrl_click_select"
    )
    new_sheet.set_all_cell_sizes_to_text()

    # Resize sheet based on number of lines.
    # 1 weight = 1 line of text
    # Each line is 25px. Add 100px on top of that to account for header (35px),
    # x-scrollbar (25 px), and extra space (40px).
    # Even though it looks unaesthetic, the extra space provides better
    # UX. When the tksheet is too short, you can vertically scroll it, which
    # we want to prevent.
    new_sheet.config(height=25 * max_lines + 100)

    return new_sheet


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
        # This frame contains a vertical scrolled frame, which contains an
        # interior frame where we must add content.
        main_frame = VerticalScrolledFrame(self, starting_height=1080)
        self.content_frame = main_frame.interior

        self.frm_controls = ttk.Frame(self.content_frame)  # statically sized frame at top of tab
        self.frm_results = ttk.Frame(self.content_frame)  # dynamically sized frame where results will appear

        self.lbl_exercise = ttk.Label(self.frm_controls, text="Exercise: ")
        self.combobox = ttk.Combobox(self.frm_controls, width=20)
        self.lbl_separator = ttk.Label(self.frm_controls, text="Separator: ")
        self.entry_separator = ttk.Entry(self.frm_controls)
        self.entry_separator.insert(0, "30")  # default value
        self.lbl_days = ttk.Label(self.frm_controls, text="days")
        self.btn_search = ttk.Button(self.frm_controls, text="Search", command=self.update_arcs_results)
        self.lbl_found_arcs = ttk.Label(self.frm_controls)  # blank until a search is run

        # --- Manage layout of widgets ---
        main_frame.grid(row=0, column=0, sticky="NSEW")

        self.frm_controls.grid(row=0, column=0, sticky="NSEW")
        self.frm_results.grid(row=1, column=0, sticky="NSEW")

        self.lbl_exercise.grid(row=0, column=0, columnspan=3, sticky="NSEW")
        self.combobox.grid(row=0, column=1, columnspan=3, sticky="NSEW")
        self.lbl_separator.grid(row=1, column=0, sticky="NSEW")
        self.entry_separator.grid(row=1, column=1, sticky="NSEW")
        self.lbl_days.grid(row=1, column=2, sticky="NSEW")
        self.btn_search.grid(row=2, column=0, sticky="NSEW")
        self.lbl_found_arcs.grid(row=3, column=0, columnspan=3, sticky="NSEW")

        # Configure rows/cols of each frame to resize.
        #  The row containing controls should not resize.
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=0)
        self.content_frame.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # padding = WNES spacing between a widget and its parent
        self.configure(padding=(3, 3, 3, 3))
        pad_frame(self.frm_controls)

        # --- Important attributes ---
        self.figsize = (6.4, 4.8)  # temporary
        self.title_size = 16
        self.tick_size = 9.6

        # TODO it would be nice if this were shared with the progress_plots variable,
        #  since they are intended to always be identical... but I'm having a hard
        #  time creating a variable that is updated in one file (sql_utility)
        #  and accessed in others (the frames).
        self.esd = {}  # ESD = Exercises-Sets Dictionary. Maps 'exercise' -> [ExerciseSet]
        self.update_exercises()

    def update_exercises(self) -> None:
        """Update the exercises-sets dictionary and the combobox."""
        self.esd = get_exercise_sets_dict()
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

            # Create a frame to store a label, a subframe (with two plots), and a Tksheet.
            new_frm = ttk.Frame(self.frm_results)
            new_lbl = ttk.Label(new_frm, text=f"ARC {idx}")
            new_sub_frm = self.create_frame_for_plots(new_frm, arc)
            new_sheet = create_arc_sheet(new_frm, arc)

            new_frm.grid(row=len(arcs)-idx, column=0)
            new_lbl.grid(row=0, column=0)
            new_sheet.grid(row=1, column=0)
            new_sub_frm.grid(row=2, column=0)

        pad_frame(self.frm_results)

    def create_frame_for_plots(self, parent_frame: ttk.Frame, arc: ExerciseArc):
        """Create frame that displays plots for given training arc."""
        frm = ttk.Frame(parent_frame)

        selected_exercise = self.combobox.get()
        if selected_exercise == '':
            return frm

        # daily_sets items within the arc are ordered by date.
        start_date = arc.daily_sets_list[0].date
        end_date = arc.daily_sets_list[-1].date
        date_filtered_sets = [s for s in self.esd[selected_exercise] if
                              start_date <= s.date <= end_date]

        # Get sets of 1-9 and 10+ reps.
        # TODO it would be cool if we got the rep ranges more dynamically/intelligently
        sets_1_9 = [s for s in date_filtered_sets if s.reps <= 9]
        sets_10_up = [s for s in date_filtered_sets if s.reps >= 10]

        self.add_plot(frm, sets_1_9, min_reps=1, max_reps=9, start_date=start_date, end_date=end_date, cmap=matplotlib.colormaps['viridis'], row=0, col=0)
        self.add_plot(frm, sets_10_up, min_reps=10, max_reps=20, start_date=start_date, end_date=end_date, cmap=matplotlib.colormaps['viridis'], row=0, col=1)

        return frm

    def add_plot(self, parent_frame: ttk.Frame, list_sets, min_reps : int, max_reps : int, start_date : date, end_date : date, cmap : Colormap, row : int, col : int):
        """Add plot to a frame"""
        fig = Figure(self.figsize)
        ax = fig.add_subplot(111)  # figure has a subplot with 1 row, 1 col, and pos 1
        if max_reps is None:
            max_reps = ""
        fig.suptitle(f"Load Over Time for Sets of {min_reps}-{max_reps} Reps", fontsize=self.title_size)

        if len(list_sets) == 0:
            # Currently displays empty graph with weird axis ticks, probably not the behavior we want
            x, y, colors = [], [], []
        else:
            x = [s.date for s in list_sets]
            y = [s.weight for s in list_sets]
            colors = [s.reps for s in list_sets]

        # Matplotlib attempts to "automatically expand" the axis limits if they
        # are the same. This isn't the behavior we want, so there is a check
        # for identical axis limits.
        if start_date == end_date:
            start_date = start_date - timedelta(days=1)
            end_date = end_date + timedelta(days=1)
        # We want 10 ticks on the x-axis. Calculate the interval needed for 10 ticks
        interval = int((end_date - start_date).days / 10) + 1
        ax.set_xlim(left=start_date, right=end_date)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))

        # Rotates and right-aligns the x labels so they don't crowd each other.
        for label in ax.get_xticklabels(which='major'):
            label.set(rotation=20, horizontalalignment='right')
            label.set_fontsize(self.tick_size)
        for label in ax.get_yticklabels(which='major'):
            label.set_fontsize(self.tick_size)
        fig.subplots_adjust()

        # Create scatter, and attach it to the canvas
        scatter = ax.scatter(x, y, c=colors, cmap=cmap, marker='o')
        mplcursors.cursor(scatter)
        fig.colorbar(scatter, format="%d", ticks=list(range(min_reps, max_reps + 1)))
        canvas = FigureCanvasTkAgg(fig, parent_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=row, column=col, sticky='NSEW')
