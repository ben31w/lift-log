import logging.config
from tkinter import END

class TextWidgetHandler(logging.Handler):
    """
    To send logging output to another area (in this case, a tkinter Text or
    ScrolledText widget), you must define a Handler class that implements emit.
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

        # Define tags for each log level
        self.text_widget.tag_config("DEBUG", foreground="gray")
        self.text_widget.tag_config("INFO", foreground="black")
        self.text_widget.tag_config("WARNING", foreground="orange")
        self.text_widget.tag_config("ERROR", foreground="red")
        self.text_widget.tag_config("CRITICAL", foreground="white", background="red")

    def emit(self, record):
        msg = record.getMessage()
        level = record.levelname

        def append():
            self.text_widget.insert(END, msg + "\n", level)
            self.text_widget.see(END)
        self.text_widget.after(0, append)
