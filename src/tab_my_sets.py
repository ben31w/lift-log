"""
All functions and classes related to the 'My Sets' tab.
"""
from datetime import date, timedelta
import logging
from tkinter import *
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import mplcursors
from matplotlib.colors import Colormap
from matplotlib.figure import Figure
from tkcalendar import DateEntry

from exercise_set import ExerciseSet
from sql_utility import get_exercise_sets_dict

logger = logging.getLogger(__name__)
matplotlib.set_loglevel('warning')  # reduces log file clutter.

def build_date_sets_string(date_obj: date, list_of_sets: list[ExerciseSet]) -> str:
    """
    Given a date and a list of ExerciseSets performed on that date, create a string
    representing this info. This 'reverse engineers' the sets into a string that
    closely resembles how they are logged.
    :param date_obj:   date object
    :param list_of_sets:  list of ExerciseSet objects
    :return:  date: [8@200, 8@200, 6@210] -> "date\n 2x8@200, 6@210"
    """
    date_sets_str = f"{date_obj}\n"
    for i in range(len(list_of_sets)):
        curr_set = list_of_sets[i]
        # first set. The " 1x" will get removed later, but it's necessary to include for processing the next set
        if i == 0:
            date_sets_str += f" 1x{curr_set.simple_str()}"
        else:
            prev_set = list_of_sets[i - 1]
            # Increment number in front of 'x'
            if prev_set.simple_str() == curr_set.simple_str():
                last_part = date_sets_str.rsplit(" ", 1)[1]
                pre_x, post_x = last_part.rsplit("x", 1)
                num_sets = int(
                    pre_x[len(pre_x) - 1])  # take digit in front of 'x' (this won't work for multiple digits)
                new_part = f"{pre_x[:len(pre_x) - 1]}{num_sets + 1}x{post_x}"
                date_sets_str = date_sets_str.replace(last_part, new_part)
            # Keep weight from the last set, but add new number of reps
            elif prev_set.weight == curr_set.weight:
                last_part = date_sets_str.rsplit(" ", 1)[1]
                pre_at, post_at = last_part.split("@")
                new_part = f"{pre_at},1x{curr_set.reps}@{post_at}"
                date_sets_str = date_sets_str.replace(last_part, new_part)
            # Completely new weight, append the set to the end
            else:
                date_sets_str += f", 1x{curr_set.simple_str()}"
    date_sets_str = date_sets_str.replace("1x", "")
    return date_sets_str



class TabMySets(ttk.Frame):
    """
    This frame is where the user views their exercise sets.
    The user selects an exercise, and their sets are displayed in text and
    graphical view.
    """
    def __init__(self, parent, mpl_scale):
        """
        Constructor for My Sets tab.
        :param parent: a reference to the notebook that stores this tab.
               Required by Tkinter.
        :param mpl_scale: MatPlotLib scale: when the MPL plots are created, they
               will be sized according to this scale. 1 is ideal scale for 1080p.
        """
        super().__init__(parent)

        # Here, we configure padding for this frame, which determines the spacing
        # between all widgets that are direct children of this frame.
        self.configure(padding=(3,3,3,3))

        # --- Define widgets ---
        # There are two frames placed on the root.
        # The Controls Frame will not resize as the window resizes?
        # The Display Frame will resize.
        #
        # self
        # |__frm_controls
        # |  |__ exercise + data selectors
        # |__frm_display
        #    |__ exercise sets + plot display
        self.frm_controls = ttk.Frame(self, padding=(3, 3, 12, 12))
        self.lbl_exercise = ttk.Label(self.frm_controls, text="Exercise")
        self.combobox = ttk.Combobox(self.frm_controls, width=20)
        self.lbl_start_date = ttk.Label(self.frm_controls, text="Start Date")
        self.date_entry_start = DateEntry(self.frm_controls,
                                          width=12,
                                          background='darkblue',
                                          foreground='white',
                                          borderwidth=2)
        self.date_entry_start.bind("<<DateEntrySelected>>", self.show_plots)
        self.lbl_end_date = ttk.Label(self.frm_controls, text="End Date")
        self.date_entry_end = DateEntry(self.frm_controls,
                                        width=12,
                                        background='darkblue',
                                        foreground='white',
                                        borderwidth=2)
        self.date_entry_end.bind("<<DateEntrySelected>>", self.show_plots)

        self.frm_display = ttk.Frame(self, padding=(3, 3, 3, 3))
        self.text_area = ScrolledText(self.frm_display, width=30)
        self.text_area.configure(state='disabled')  # user can't type here

        # --- Manage layout of widgets ---
        self.frm_controls.grid(row=0, column=0, sticky='NSEW')
        self.lbl_exercise.grid(row=0, column=0)
        self.combobox.grid(row=0, column=1)
        self.lbl_start_date.grid(row=0, column=2)
        self.date_entry_start.grid(row=0, column=3)
        self.lbl_end_date.grid(row=0, column=4)
        self.date_entry_end.grid(row=0, column=5)

        self.frm_display.grid(row=1, column=0, sticky='NSEW')
        self.text_area.grid(row=0, column=0, rowspan=2, sticky='NSW')

        # Configure the responsive layout for each row and column.
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.frm_display.columnconfigure(0, weight=0)
        self.frm_display.columnconfigure(1, weight=1)
        self.frm_display.columnconfigure(2, weight=1)
        self.frm_display.rowconfigure(0, weight=1)
        self.frm_display.rowconfigure(1, weight=1)

        # --- Define data structures and fields ---
        self.esd = {}  # ESD = Exercises-Sets Dictionary. Maps 'exercise' -> [ExerciseSet]
        self.update_exercises()

        # Base MatPlotLib dimensions (ideal for 1080p res)
        base_figsize = (6.4, 4.8)
        base_title_size = 16
        base_tick_size = 9.6

        # Scale everything
        self.figsize = (base_figsize[0] * mpl_scale, base_figsize[1] * mpl_scale)
        self.title_size = base_title_size * mpl_scale
        self.tick_size = base_tick_size * mpl_scale


    def update_exercises(self):
        """
        Update the exercises-sets dictionary and the combobox.
        :return:
        """
        self.esd = get_exercise_sets_dict()
        exercises = sorted(list(self.esd.keys()))
        self.combobox['values'] = exercises
        self.combobox.bind("<<ComboboxSelected>>", self.filter_sets)
        # This spoofs the 'combobox selected event' to force a refresh.
        self.combobox.set(self.combobox.get())
        self.combobox.event_generate("<<ComboboxSelected>>")

    def filter_sets(self, event: Event):
        """
        When a new exercise is selected in the combobox, filter the sets being
        displayed in the text area and show new plots.
        """
        selected_exercise = self.combobox.get()
        if selected_exercise == '':
            return
        if selected_exercise not in self.esd.keys():
            # This case only occurs when the aliases are updated and exercises
            # are merged.
            self.text_area.configure(state="normal")
            self.text_area.delete("1.0", END)
            self.text_area.configure(state="disabled")
            self.combobox.selection_clear()
            for widget in self.frm_display.winfo_children():
                # Since the exercise doesn't exist anymore, destroy the canvases
                # for this exercise.
                if isinstance(widget, Canvas):
                    widget.destroy()
            return

        self.update_text_area()
        self.show_plots(event)

    def update_text_area(self):
        """Update the text area with dates and sets for the selected exercise."""
        selected_exercise = self.combobox.get()
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", END)  # Clear existing text

        to_insert = ""  # Everything to insert in the text area
        list_sets = sorted(self.esd[selected_exercise], key=lambda eset: eset.date)
        date_sets_list_dict: Dict[date, list[ExerciseSet]] = {}  # {2024-10-10: [set1, set2]}

        # Build dict from list of sets
        logger.info(f"Filtering sets for {selected_exercise}")
        for the_set in list_sets:
            the_date = the_set.date
            logger.debug(the_set)

            if the_date not in date_sets_list_dict.keys():
                # Filter list of sets to this date. Add this list to the dict.
                sets_by_date = [s for s in list_sets if s.date == the_date]
                date_sets_list_dict[the_date] = sets_by_date
            else:
                continue  # This date has already been processed.

        # Go through each date in the dict, and build the string to insert.
        for d, l in date_sets_list_dict.items():
            to_insert += f"{build_date_sets_string(d, l)}\n\n"

        self.text_area.insert(END, to_insert)  # Update with new text
        self.text_area.configure(state="disabled")
        logger.info(f"Done filtering sets for {selected_exercise}")

    def show_plots(self, event : Event):
        """
        Update the plots being shown. This is called whenever the dates are
        adjusted or a new exercise is selected.
        """
        if event.widget == self.combobox:
            self._show_plots()
        if event.widget == self.date_entry_start or event.widget == self.date_entry_end:
            self._show_plots(start_date=self.date_entry_start.get_date(), end_date=self.date_entry_end.get_date())

    def _show_plots(self, start_date : date = None, end_date : date = None):
        """
        Show plots for the selected exercise. The plots are filtered to the given
        start and end date. If no start or end date is given, then default dates
        will be found.
        The plots depict load over time for sets of
        - 1-5 reps
        - 6-8 reps
        - 9-11 reps
        - 12+ reps
        """
        selected_exercise = self.combobox.get()
        if selected_exercise == '':
            return

        # Find default start and end dates if none were provided.
        if start_date is None:
            start_date = min([s.date for s in self.esd[selected_exercise]])
        if end_date is None:
            end_date = max([s.date for s in self.esd[selected_exercise]])
        logger.info(f"start_date: {start_date}  | end_date: {end_date}")
        date_filtered_sets = [s for s in self.esd[selected_exercise] if
                              start_date <= s.date <= end_date]

        # Get sets of 1-5, 6-8, 9-11, and 12+ reps
        sets_1_5 =   [s for s in date_filtered_sets if s.reps <= 5]
        sets_6_8 =   [s for s in date_filtered_sets if 6 <= s.reps <= 8]
        sets_9_11 =  [s for s in date_filtered_sets if 9 <= s.reps <= 11]
        sets_12_up = [s for s in date_filtered_sets if s.reps >= 12]

        # Update date entry widgets (this is necessary for when this function is
        # called with no start or end date)
        self.date_entry_start.set_date(start_date)
        self.date_entry_end.set_date(end_date)

        # Show plots
        self.show_plot(list_sets=sets_1_5, min_reps=1, max_reps=5, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=0, plot_grid_col=1)
        self.show_plot(list_sets=sets_6_8, min_reps=6, max_reps=8, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=0, plot_grid_col=2)
        self.show_plot(list_sets=sets_9_11, min_reps=9, max_reps=11, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=1, plot_grid_col=1)
        self.show_plot(list_sets=sets_12_up, min_reps=12, max_reps=20, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=1, plot_grid_col=2)

    def show_plot(self, list_sets : list[ExerciseSet], min_reps : int, max_reps : int, start_date : date, end_date : date, cmap : Colormap, plot_grid_row : int, plot_grid_col : int):
        """
        Plot load over time for a particular exercise and rep range.
        :param list_sets:     list of ExerciseSet objects
        :param min_reps:      minimum reps per set
        :param max_reps:      maximum reps per set
        :param start_date:    the start date for this plot
        :param end_date:      the end date for this plot
        :param cmap:          colormap to use
        :param plot_grid_row: row to place this plot within frm_display
        :param plot_grid_col: column to place this plot within frm_display
        :return:
        """
        fig = Figure(self.figsize)
        ax = fig.add_subplot(111)
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
        fig.colorbar(scatter, format="%d", ticks=list(range(min_reps, max_reps+1)))
        canvas = FigureCanvasTkAgg(fig, self.frm_display)
        canvas.draw()
        canvas.get_tk_widget().grid(row=plot_grid_row, column=plot_grid_col, sticky='NSEW')
