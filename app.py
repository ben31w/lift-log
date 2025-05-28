from datetime import date
from tkinter import *
from tkinter import ttk
from typing import Dict

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import mplcursors
from matplotlib.colors import Colormap
from matplotlib.figure import Figure
from tkcalendar import DateEntry

from exercise_set import ExerciseSet
from html_parser import HtmlParser
from sql_utility import create_tables, get_imports, get_exercise_sets_dict


WINDOW_HEIGHT = 1080
WINDOW_WIDTH = 1700

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


def pad_frame(frame: ttk.Frame):
    """
    Add padding to each widget inside a frame. Call this after the frame's
    widgets have been initialized and placed inside the frame.
    :param frame:
    :return:
    """
    for child in frame.winfo_children():
        child.grid_configure(padx=5, pady=5)


class LiftLogGUI(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("Lift Log")
        self.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}')

        self.html_parser = HtmlParser('my_workouts.html', 'aliases.txt')

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        tab_my_sets = TabMySets(self.notebook, self.html_parser)
        tab_import_sets = TabImportExercises(self.notebook, self.html_parser)

        tab_my_sets.pack(fill='both', expand=True)
        tab_import_sets.pack(fill='both', expand=True)

        self.notebook.add(tab_my_sets, text="My Sets")
        self.notebook.add(tab_import_sets, text="Import Sets")


class TabMySets(ttk.Frame):
    """
    A frame where users can view their exercise sets in list and graph form for
    a selected exercise.
    """
    def __init__(self, parent, html_parser : HtmlParser):
        ttk.Frame.__init__(self, parent)

        self.html_parser = html_parser

        # Container row 0
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0, sticky=W)
        lbl_exercise = ttk.Label(row0, text="Exercise")
        lbl_exercise.pack(side=LEFT)
        exercises = sorted(list(self.html_parser.exercises))
        self.combobox = ttk.Combobox(row0, values=exercises, width=40)
        self.combobox.pack(side=LEFT)
        self.combobox.bind("<<ComboboxSelected>>", self.filter_sets)
        
        # Create labels and date entries for the start and end date, but DON'T 
        # add them to the GUI yet. Wait for the first exercise to be selected.
        self.dates_visible = False
        self.lbl_start_date = ttk.Label(row0, text="Start Date")
        self.date_entry_start = DateEntry(row0, width=12, background='darkblue',
                                          foreground='white', borderwidth=2)
        self.lbl_end_date = ttk.Label(row0, text="End Date")
        self.date_entry_end = DateEntry(row0, width=12, background='darkblue',
                                        foreground='white', borderwidth=2)

        # Container row 1
        self.row1 = ttk.Frame(self)
        self.row1.grid(row=1, column=0, sticky=W)
        self.text_area = Text(self.row1, height=48, width=30)
        self.text_area.grid(row=0, column=0, sticky=W)
        scrollbar = ttk.Scrollbar(self.row1, command=self.text_area.yview)
        scrollbar.grid(row=0, column=1, sticky=NSEW)
        self.text_area['yscrollcommand'] = scrollbar.set
        self.plot_grid = ttk.Frame(self.row1)  # This frame is a 2x2 grid
        self.plot_grid.grid(row=0, column=2)

        pad_frame(self)
        pad_frame(self.row1)

    def filter_sets(self, event: Event):
        """
        When a new exercise is selected in the combobox, filter the sets being
        displayed in the text area and show new plots.
        """
        if not self.dates_visible:
            self.lbl_start_date.pack(side=LEFT)
            self.date_entry_start.pack(side=LEFT)
            self.lbl_end_date.pack(side=LEFT)
            self.date_entry_end.pack(side=LEFT)
            self.dates_visible = True
            self.date_entry_start.bind("<<DateEntrySelected>>", self.show_plots)
            self.date_entry_end.bind("<<DateEntrySelected>>", self.show_plots)
        
        self.update_text_area()
        self.show_plots(event)


    def update_text_area(self):
        """Update the text area with dates and sets for the selected exercise."""
        selected_exercise = self.combobox.get()
        self.text_area.delete("1.0", END)  # Clear existing text

        to_insert = ""  # Everything to insert in the text area
        list_sets = self.html_parser.exercise_set_dict[selected_exercise]
        date_sets_list_dict: Dict[date, list[ExerciseSet]] = {}  # {2024-10-10: [set1, set2]}

        # Build dict from list of sets
        print("\nfiltering sets")
        for the_set in list_sets:
            the_date = the_set.date
            print(the_set)

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


    def show_plots(self, event : Event):
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

        # Find default start and end dates if none were provided.
        if start_date is None:
            start_date = min([s.date for s in self.html_parser.exercise_set_dict[selected_exercise]])
        if end_date is None:
            end_date = max([s.date for s in self.html_parser.exercise_set_dict[selected_exercise]])
        print(start_date)
        print(end_date)
        date_filtered_sets = [s for s in self.html_parser.exercise_set_dict[selected_exercise] if
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
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=0, plot_grid_col=0)
        self.show_plot(list_sets=sets_6_8, min_reps=6, max_reps=8, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=0, plot_grid_col=1)
        self.show_plot(list_sets=sets_9_11, min_reps=9, max_reps=11, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=1, plot_grid_col=0)
        self.show_plot(list_sets=sets_12_up, min_reps=12, max_reps=20, start_date=start_date, end_date=end_date,
                       cmap=matplotlib.colormaps['viridis'], plot_grid_row=1, plot_grid_col=1)
        pad_frame(self.row1)


    def show_plot(self, list_sets : list[ExerciseSet], min_reps : int, max_reps : int, start_date : date, end_date : date, cmap : Colormap, plot_grid_row : int, plot_grid_col : int):
        """
        Plot load over time for a particular exercise and rep range.
        :param list_sets:     list of ExerciseSet objects
        :param min_reps:      minimum reps per set
        :param max_reps:      maximum reps per set
        :param start_date:    the start date for this plot
        :param end_date:      the end date for this plot
        :param cmap:          colormap to use
        :param plot_grid_row: row to place this plot within the plot grid
        :param plot_grid_col: column to place this plot within the plot grid
        :return:
        """
        fig = Figure()
        ax = fig.add_subplot(111)
        fig.suptitle(f"Load Over Time for Sets of {min_reps}-{max_reps} Reps")

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
            start_date = start_date.replace(day=start_date.day - 1)
            end_date = end_date.replace(day=end_date.day + 1)
        # We want 10 ticks on the x-axis. Calculate the interval needed for 10 ticks
        interval = int((end_date - start_date).days / 10) + 1
        ax.set_xlim(left=start_date, right=end_date)
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%y-%m-%d'))

        # Rotates and right-aligns the x labels so they don't crowd each other.
        for label in ax.get_xticklabels(which='major'):
            label.set(rotation=30, horizontalalignment='right')

        # Create scatter, and attach it to the canvas
        scatter = ax.scatter(x, y, c=colors, cmap=cmap, marker='o')
        mplcursors.cursor(scatter)
        fig.colorbar(scatter, format="%d", ticks=list(range(min_reps, max_reps+1)))
        canvas = FigureCanvasTkAgg(fig, self.plot_grid)
        canvas.draw()
        canvas.get_tk_widget().grid(row=plot_grid_row, column=plot_grid_col)

class TabImportExercises(ttk.Frame):
    """A frame that allows the user to import exercise sets via HTML or Apple Notes."""
    def __init__(self, parent, html_parser : HtmlParser):
        ttk.Frame.__init__(self, parent)

        self.html_parser = html_parser

        # Container row 0
        row0 = ttk.Frame(self)
        row0.grid(row=0, column=0, sticky=W)
        lbl_import_methods = ttk.Label(row0, text="Import Methods")
        lbl_import_methods.grid(row=0, column=0)

        # Container row 1
        row1 = ttk.Frame(self)
        row1.grid(row=1, column=0, sticky=W)

        frm_html = ttk.Frame(row1)
        frm_html.grid(row=0, column=0)
        lbl_via_html = ttk.Label(frm_html, text="Via HTML File")
        lbl_via_html.grid(row=0, column=0)
        lbl_via_html_desc = ttk.Label(frm_html, text="You can import exercise sets via an existing HTML file.")
        lbl_via_html_desc.grid(row=1, column=0)
        btn_browse = ttk.Button(frm_html, text="Browse")
        btn_browse.grid(row=2, column=0)

        frm_apple = ttk.Frame(row1)
        frm_apple.grid(row=0, column=1)
        lbl_via_apple = ttk.Label(frm_apple, text="Via Apple Notes")
        lbl_via_apple.grid(row=0, column=0)
        lbl_via_apple_desc = ttk.Label(frm_apple, text="You can import exercise sets via Apple Notes.")
        lbl_via_apple_desc.grid(row=1, column=0)
        btn_go = ttk.Button(frm_apple, text="Go")
        btn_go.grid(row=2, column=0)

        # Container row 2
        row2 = ttk.Frame(self)
        row2.grid(row=2, column=0, sticky=W)
        lbl_import_status = ttk.Label(row2, text="Import Status")
        lbl_import_status.grid(row=0, column=0)

        # Container row 3
        row3 = ttk.Frame(self)
        row3.grid(row=3, column=0, sticky=W)
        status_msg_area = Text(row3, height=20, width=170)
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
        row6 = ttk.Frame(self)
        row6.grid(row=6, column=0, sticky=W)

        imports_table = ttk.Frame(row6)
        imports_table.grid(row=0, column=0)
        imports = get_imports()

        lbl_method = ttk.Label(imports_table, text='Method')
        lbl_method.grid(row=0, column=0)
        lbl_date_time = ttk.Label(imports_table, text='Date Time')
        lbl_date_time.grid(row=0, column=1)
        lbl_file = ttk.Label(imports_table, text='File')
        lbl_file.grid(row=0, column=2)
        lbl_delete = ttk.Label(imports_table, text='Delete')
        lbl_delete.grid(row=0, column=3)

        curr_row = 1
        for imprt in imports:
            imprt_method, imprt_date_time, imprt_filepath = imprt
            lbl_imprt_method = ttk.Label(imports_table, text=imprt_method)
            lbl_imprt_method.grid(row=curr_row, column=0)
            lbl_date_time = ttk.Label(imports_table, text=imprt_date_time)
            lbl_date_time.grid(row=curr_row, column=1)
            # TODO add functionality to buttons so they open the file
            btn_imprt_filepath = ttk.Button(imports_table, text=imprt_filepath)
            btn_imprt_filepath.grid(row=curr_row, column=2)
            # TODO add functionality to buttons so they delete the import
            btn_delete = ttk.Button(imports_table, text='Delete')
            btn_delete.grid(row=curr_row, column=3)
            curr_row += 1

        pad_frame(self)
        pad_frame(row1)
        pad_frame(frm_html)
        pad_frame(frm_apple)
        pad_frame(imports_table)

    # def build_imports_table(self):


if __name__ == '__main__':
    lift_log = LiftLogGUI()
    lift_log.mainloop()
