from tkinter import *
from tkinter import ttk

from html_parser import HtmlParser

class LiftLogGUI:
    def __init__(self, root: Tk):
        root.title("Lift Log")

        # Main Frame widget
        frm = ttk.Frame(root, padding=10)
        frm.grid(row=0, column=0, sticky=NSEW)

        self.html_parser = HtmlParser('my_workouts.html')

        # Create widgets
        ttk.Label(frm, text="My Sets").grid(row=0, column=0)

        row1 = ttk.Frame(frm)
        row1.grid(row=1, column=0)
        ttk.Label(row1, text="Exercise").grid(column=0)
        exercises = sorted(list(self.html_parser.exercises))
        self.combobox = ttk.Combobox(row1, values=exercises)
        self.combobox.grid(column=1)
        self.combobox.bind("<<ComboboxSelected>>", self.filter_sets)

        self.text_area = Text(frm, height=24)
        self.text_area.grid(row=2, column=0)

        ttk.Button(frm, text="Exit", command=root.destroy).grid(row=3, column=0)

        # Add padding to each widget
        for child in frm.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def filter_sets(self, event: Event):
        selected_value = self.combobox.get()
        self.text_area.delete("1.0", END)  # Clear existing text
        self.text_area.insert(END, f"You selected: {selected_value}")  # Update with new text


if __name__ == '__main__':
    root = Tk()
    LiftLogGUI(root)
    root.mainloop()
