import tkinter as tk
from tkinter.filedialog import askopenfile
from controller.connection import SSHChannelException
from .baseframe import BaseFrame

# stdin, stdout, stderr = client.exec_command('ls /var')

class ConnectionFrame(BaseFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        # todo add cache file ingestion
        self.__port = tk.StringVar()
        self.__port.set(self.controller.cfg.port)

        row = 1

        def tick_row():
            nonlocal row
            row += 1

        tk.Label(self, name='addr_label', text='IP Address: ').grid(column=1, row=row, columnspan=3)
        h = tk.Entry(self, name='host')
        h.insert(0, self.controller.cfg.host)
        h.grid(column=4, row=row, columnspan=3, sticky='we')
        tick_row()

        tk.Label(self, name='port_label', text='Port: ').grid(column=1, row=row, columnspan=3)
        tk.Entry(self, name='port', textvariable=self.__port).grid(column=4, row=row, columnspan=3)
        tick_row()

        tk.Label(self, name='username_label', text='username').grid(row=row, column=1, columnspan=3)
        tk.Label(self, name='password_label', text='password').grid(row=row, column=4, columnspan=3)
        tick_row()

        self.__username = tk.StringVar()
        self.__password = tk.StringVar()
        u = tk.Entry(self, name='username', textvariable=self.__username)
        u.insert(0, self.controller.cfg.username)
        u.grid(row=row, column=1, columnspan=3)
        p = tk.Entry(self, name='password', textvariable=self.__password, show='*')
        p.insert(0, self.controller.cfg.password)
        p.grid(row=row, column=4, columnspan=3)
        tick_row()

        tk.Button(self, name='keyfile', text='Use key file', command=self.add_keyfile) \
            .grid(row=row, column=0, columnspan=2)
        self.__keyfile_name = tk.StringVar()
        self.__keyfile_name.set(self.controller.cfg.keypath)
        tk.Label(self, name='keyfile_path', textvariable=self.__keyfile_name, background='grey', justify='center'). \
            grid(row=row, column=2, columnspan=4, sticky='we')
        tk.Button(self, name='clearkey', text='X', command=lambda: self.__keyfile_name.set('')).\
            grid(row=row, column=6, columnspan=1, sticky='we')
        tick_row()

        tk.Button(self, name='connect_button', text='Connect', command=self.connect, background='green'). \
            grid(column=1, row=row, columnspan=6, sticky='we')
        # tk.Label()

    def draw_attention(self, childname):
        self.children[childname].focus_set()
        old_background = self.children[childname].cget('background')
        self.children[childname].configure(background='red')
        self.after(1500, lambda: self.children[childname].configure(background=old_background))

    def connect(self):
        try:
            port = int(self.__port.get())
        except ValueError:
            return self.controller.process_error(self, 'Port must be a number.')
        host = self.children['host'].get()
        if host == '':
            return self.draw_attention('host')
        username = self.__username.get()
        if username == '':
            return self.draw_attention('username')
        kf = self.__keyfile_name.get()
        if kf == '':
            kf = None
        ps = self.__password.get()
        if ps == '':
            return self.draw_attention('password')
        try:
            self.controller.cfg.host = host
            self.controller.cfg.port = port
            self.controller.cfg.username = username
            self.controller.cfg.keypath = kf
            self.controller.cfg.password = ps
            return self.controller.add_connection()
        except SSHChannelException as e:
            return self.controller.process_error(self, e.__str__())

    def add_keyfile(self):
        self.__keyfile_name.set(askopenfile().name)

