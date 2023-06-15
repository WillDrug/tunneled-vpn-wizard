import os.path
import tkinter as tk
from tkinter.ttk import Separator
from .baseframe import BaseFrame


class ConfigMenu(BaseFrame):
    def set_as_loading(self, component, textvariable):
        loading = True
        text = '◯'
        old_text = textvariable.get()
        old_background = component.cget('background')
        def update():
            nonlocal loading
            nonlocal text
            nonlocal old_text
            textvariable.set(text)
            text = text + '◯' if len(text) < 3 else '◯'
            if loading:
                component.after(400, update)
            else:
                textvariable.set(old_text)


        def cancel():
            nonlocal loading
            nonlocal old_background
            nonlocal textvariable
            nonlocal old_text
            loading = False
            component.configure({'background': old_background, 'state': 'normal'})
            textvariable.set(old_text)

        component.configure({'background': 'grey', 'state': 'disabled'})
        update()
        return cancel

    @staticmethod
    def __flash(component, old, new):
        component.configure({'background': new})
        component.after(500, lambda: component.configure({'background': old}))
        component.after(1000, lambda: component.configure({'background': new}))
        component.after(1500, lambda: component.configure({'background': old}))
        component.after(2000, lambda: component.configure({'background': new}))
        component.after(2500, lambda: component.configure({'background': old}))

    def flash_result(self, component, success):
        old_background = component.cget('background')
        new_background = 'green' if success else 'red'
        self.__flash(component, old_background, new_background)

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # apt update upgrade
        self.__update_button_text = tk.StringVar()
        self.__update_button_text.set('Perform Base Config')
        row = 0

        def tick_row():
            nonlocal row
            row += 1

        self.__mainframe = tk.Frame(self)
        self.__mainframe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Button(self.__mainframe, name='base_config_button', textvariable=self.__update_button_text,
                  background='grey', command=self.__base_config). \
            grid(row=row, column=0, columnspan=6, sticky='we')
        self.__mainframe.children['base_config_button'].configure(width=30)
        tick_row()


        tk.Label(self.__mainframe, name='switchuser', text='Switch/Create user', background='white')\
            .grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()

        tk.Label(self.__mainframe, name='newusernamelabel', text='Username')\
            .grid(row=row, column=0, columnspan=3, sticky='we')
        tk.Label(self.__mainframe, name='newuserpasswordlabel', text='Password')\
            .grid(row=row, column=3, columnspan=3, sticky='we')
        tick_row()

        self.__switch_username = tk.StringVar()
        self.__switch_password = tk.StringVar()
        tk.Entry(self.__mainframe, name='susername', textvariable=self.__switch_username)\
            .grid(row=row, column=0, columnspan=3, sticky='we')
        tk.Entry(self.__mainframe, name='spassword', textvariable=self.__switch_password, show='*')\
            .grid(row=row, column=3, columnspan=3, sticky='we')
        tick_row()
        self.__susercmd_text = tk.StringVar()
        self.__susercmd_text.set('Switch/Create User')
        tk.Button(self.__mainframe, name='susercmd', command=self.__switch_user, background='grey',
                  textvariable=self.__susercmd_text)\
            .grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()
        self.__sshconfig_text = tk.StringVar()
        self.__sshconfig_text.set('Configure SSHD')
        tk.Button(self.__mainframe, name='sshconfig', textvariable=self.__sshconfig_text, background='grey',
                  command=self.__ssh_config).grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()

        self.__iptables_text = tk.StringVar()
        self.__iptables_text.set('Configure iptables')
        tk.Button(self.__mainframe, name='ipconfig', textvariable=self.__iptables_text, background='grey',
                  command=self.__iptables_config).grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()

        self.__install_text = tk.StringVar()
        self.__install_text.set('Install Software')  # todo: pack samey tk instructions
        tk.Button(self.__mainframe, name='install', textvariable=self.__install_text, background='grey',
                  command=self.__install_command).grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()

        self.__configure_text = tk.StringVar()
        self.__configure_text.set('Configure Software')
        tk.Button(self.__mainframe, name='configure', textvariable=self.__configure_text, background='grey',
                  command=self.__configure_command).grid(row=row, column=0, columnspan=6, sticky='we')
        tick_row()

        tk.Label(self.__mainframe, text='Stunnel Config Path').grid(row=row, columnspan=6, column=0, sticky='we')
        tick_row()

        self.__stunnel_path = tk.StringVar()
        self.__stunnel_path.set(r'C:\Program Files (x86)\stunnel\config')
        tk.Entry(self.__mainframe, name='stunnelpath', textvariable=self.__stunnel_path).\
            grid(row=row, columnspan=6, column=0, sticky='we')
        tick_row()

        tk.Label(self.__mainframe, text='OpenVPN Config Path').grid(row=row, columnspan=6, column=0, sticky='we')
        tick_row()

        self.__ovpn_path = tk.StringVar()
        self.__ovpn_path.set(os.path.expanduser('~') + r'\OpenVPN\config')
        tk.Entry(self.__mainframe, name='ovpnpath', textvariable=self.__ovpn_path).\
            grid(row=row, columnspan=6, column=0, sticky='we')
        tick_row()

        self.__move_config_text = tk.StringVar()
        self.__move_config_text.set('Finalize Home Config')
        tk.Button(self.__mainframe, name='finalize', textvariable=self.__move_config_text, command=self.__finalize).\
            grid(row=row, columnspan=6, column=0, sticky='we')

        self.__logframe = tk.Frame(self)
        self.__logframe.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Text(self.__logframe, name='log').pack()

    def __finalize(self):
        cancel = self.set_as_loading(self.__mainframe.children['finalize'], self.__move_config_text)
        success = False
        try:
            success = self.controller.finalize_config(self.__stunnel_path.get(), self.__ovpn_path.get())
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['finalize'], success)

    def __configure_command(self):
        cancel = self.set_as_loading(self.__mainframe.children['configure'], self.__configure_text)
        success = False
        try:
            success = self.controller.configure_software()
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['configure'], success)

    def __install_command(self):
        cancel = self.set_as_loading(self.__mainframe.children['install'], self.__install_text)
        success = False
        try:
            success = self.controller.install_software()
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['install'], success)

    def __ssh_config(self):
        cancel = self.set_as_loading(self.__mainframe.children['sshconfig'], self.__sshconfig_text)
        success = False
        try:
            success = self.controller.config_ssh()
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['sshconfig'], success)

    def __iptables_config(self):
        cancel = self.set_as_loading(self.__mainframe.children['ipconfig'], self.__iptables_text)
        success = False
        try:
            success = self.controller.config_iptables()
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['ipconfig'], success)

    def __base_config(self):
        cancel = self.set_as_loading(self.__mainframe.children['base_config_button'], self.__update_button_text)
        success = False
        try:
            success = self.controller.perform_base_config()
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['base_config_button'], success)

    def __switch_user(self):
        if self.__switch_username.get().strip() == '':
            return self.flash_result(self.__mainframe.children['susername'], False)
        if self.__switch_password.get().strip() == '':
            return self.flash_result(self.__mainframe.children['spassword'], False)
        cancel = self.set_as_loading(self.__mainframe.children['susercmd'], self.__susercmd_text)
        success = False
        try:
            success = self.controller.switch_user(self.__switch_username.get(),
                                                  self.__switch_password.get())
        except Exception as e:
            self.controller.process_error(self, e.__str__())
        finally:
            cancel()
        self.flash_result(self.__mainframe.children['susercmd'], success)

    def log_line(self, text):
        self.__logframe.children['log'].insert('end', text + '\n')
        self.__logframe.children['log'].see('end')
        self.__logframe.update()
