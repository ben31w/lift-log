from datetime import date
from tkinter import *
from tkinter import ttk
from typing import Dict

from exerciseset import ExerciseSet
from html_parser import HtmlParser


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

        self.html_parser = HtmlParser('my_workouts.html', 'aliases.txt')

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (FilterExercisesPage, AllExercisesPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self, html_parser=self.html_parser)
            self.frames[page_name] = frame

            # put all the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky=NSEW)

        self.show_frame("FilterExercisesPage")

    def show_frame(self, page_name):
        """Show a frame for the given page name"""
        frame = self.frames[page_name]
        frame.tkraise()


class FilterExercisesPage(ttk.Frame):
    def __init__(self, parent, controller, html_parser : HtmlParser):
        ttk.Frame.__init__(self, parent)

        self.controller = controller
        self.html_parser = html_parser

        btn_display_all = ttk.Button(self, text="Display All", command=lambda: controller.show_frame("AllExercisesPage"))
        btn_display_all.grid(row=0, column=0, sticky=W)

        lbl_my_sets = ttk.Label(self, text="My Sets")
        lbl_my_sets.grid(row=1, column=0, sticky=W)

        row2 = ttk.Frame(self)
        row2.grid(row=2, column=0, sticky=W)
        lbl_exercise = ttk.Label(row2, text="Exercise")
        lbl_exercise.pack(side=LEFT)
        exercises = sorted(list(self.html_parser.exercises))
        self.combobox = ttk.Combobox(row2, values=exercises, width=40)
        self.combobox.pack(side=RIGHT)
        self.combobox.bind("<<ComboboxSelected>>", self.filter_sets)

        self.text_area = Text(self, height=24, width=60)
        self.text_area.grid(row=3, column=0)

        pad_frame(self)

    def filter_sets(self, event: Event):
        """
        Filter the text area content to the exercise selected in the combobox.
        :param event:  Not used
        :return:
        """
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
        for d,l in date_sets_list_dict.items():
            # for s in l:
            #     print(s, end=' ')
            # print()
            to_insert += f"{build_date_sets_string(d, l)}\n\n"

        self.text_area.insert(END, to_insert)  # Update with new text


class AllExercisesPage(ttk.Frame):
    def __init__(self, parent, controller, html_parser: HtmlParser):
        ttk.Frame.__init__(self, parent)

        self.controller = controller
        self.html_parser = html_parser

        btn_filter = ttk.Button(self, text="Filter", command=lambda: controller.show_frame("FilterExercisesPage"))
        btn_filter.grid(row=0, column=0, sticky=W)

        lbl_my_sets = ttk.Label(self, text="My Sets")
        lbl_my_sets.grid(row=1, column=0, sticky=W)

        pad_frame(self)


if __name__ == '__main__':
    lift_log = LiftLogGUI()
    lift_log.mainloop()
