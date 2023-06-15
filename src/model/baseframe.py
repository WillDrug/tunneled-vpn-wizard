import tkinter as tk


class BaseFrame(tk.Frame):
    def __init__(self, root, controller):
        super().__init__(root)
        self.controller = controller

    def log_line(self, text):
        pass