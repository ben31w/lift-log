"""
Vertical Scrolled Frame class: a frame with a vertical scrollbar.
"""
import platform
from tkinter import *
from tkinter import ttk

class VerticalScrolledFrame(ttk.Frame):
    """
    https://coderslegacy.com/python/make-scrollable-frame-in-tkinter/

    Tkinter doesn't support putting a scrollbar directly on a frame :/
    But you can put a scrollbar on to a canvas, and put a frame on the canvas :)

    You can grid items on to the 'interior' frame of class. Be sure to configure
    any rows or columns you add to the interior frame to keep the layout
    responsive.
    """

    def __init__(self, parent, starting_width=600, starting_height=600, *args, **kw):
        """
        Constructor for VerticalScrolledFrame.
        :param parent: a reference to the parent is needed for any Tkinter widget.
        :param starting_width: can specify starting width of the canvas...
               this parameter isn't really used
        :param starting_height: can specify starting height of the canvas
        :param args: pass to Frame constructor
        :param kw:   pass to Frame constructor
        """
        ttk.Frame.__init__(self, parent, *args, **kw)

        # This sets the overall frame up with a responsive grid layout.
        # You still need to row/columnconfigure the overall Tk widget that holds
        # this frame and any row/column you add to the interior frame.
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        vscrollbar = ttk.Scrollbar(self, orient=VERTICAL)
        vscrollbar.grid(row=0, column=1, sticky=NS)

        self.canvas = Canvas(
            self,
            bd=0,
            width=starting_width, height=starting_height,
            yscrollcommand=vscrollbar.set)
        self.canvas.grid(row=0, column=0, sticky=NSEW)
        vscrollbar.config(command=self.canvas.yview)

        # Reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        self.interior = ttk.Frame(self.canvas)
        self.interior.bind('<Configure>', self._configure_interior)
        self.canvas.bind('<Configure>', self._configure_canvas)
        self.bind_mousewheel()
        self.interior_id = self.canvas.create_window(0, 0, window=self.interior, anchor=NW)

    def _configure_interior(self, event):
        """Configure widgets when the interior frame is configured (resized)"""
        requested_width = self.interior.winfo_reqwidth()
        requested_height = self.interior.winfo_reqheight()

        # Update the canvas's scroll region to match the size of the inner frame.
        self.canvas.config(scrollregion=(0, 0, requested_width, requested_height))
        # Update the canvas's width to fit the inner frame.
        if requested_width != self.canvas.winfo_width():
            self.canvas.config(width=requested_width)

    def _configure_canvas(self, event):
        if self.interior.winfo_reqwidth() != self.canvas.winfo_width():
            # Update the inner frame's width to fill the canvas.
            self.canvas.itemconfigure(self.interior_id, width=self.canvas.winfo_width())

    def bind_mousewheel(self):
        """Check OS and bind a mousewheel function so scrolling works."""
        system = platform.system()
        if system == "Windows" or system == "Darwin":  # Darwin = macOS
            self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        else:  # Assume Linux
            self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux)
            self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux)

    def on_mousewheel(self, event):
        """Scroll the canvas on Windows or macOS."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(self, event):
        """Scroll the canvas on Linux (event.num = 4 -> up, 5 -> down)"""
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")