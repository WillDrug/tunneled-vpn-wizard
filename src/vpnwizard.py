import os
from argparse import ArgumentParser
import tkinter as tk
from model.connection_frame import ConnectionFrame
from model.configure_menu_frame import ConfigMenu
from model.baseframe import BaseFrame
from model.cli import LogFrame
from controller.command import SSHCommand, TEST_SUCCESS, TEST_FAIL
from controller.connection import SSHChannel
from controller.scp_processor import RemoteFile
from subprocess import PIPE, run

import zlib
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d



def obscure(data: str) -> bytes:
    return b64e(zlib.compress(data.encode(), 9))


def unobscure(obscured: bytes) -> str:
    return zlib.decompress(b64d(obscured)).decode()


from dataclasses import dataclass, replace
import pickle
# This python file is horrifically disorganized. Use and edit at your own risk.


def clear_dir(top):
    """
    CAREFUL. DANGEROUS
    :param top:
    :return:
    """
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

@dataclass
class MainConfig:
    host: str = '127.0.0.1'
    port: int = 22
    username: str = ''
    password: str | bytes = ''
    keypath: str = ''


class MainController:
    def set_frame(self, frame: BaseFrame.__class__):
        if not self.__gui:
            return
        if self.frame is not None:
            self.frame.destroy()
        self.frame = frame(self.root, self)
        self.frame.grid()
        self.frame.tkraise()
        self.frame.winfo_toplevel().title('Tunneled VPN Wizard')

    def __init__(self, gui=True):
        self.__gui = gui
        self.__ssh = None
        self.root = None
        if self.__gui:
            self.root = tk.Tk()
        self.cfg = MainConfig()
        self.load_cache()
        self.frame = None
        if not self.__gui:
            self.frame = LogFrame(None, self)
        try:
            self.add_connection(cached=True)
        except Exception:
            self.set_frame(ConnectionFrame)
        else:
            self.set_frame(ConfigMenu)

    def load_cache(self):
        try:
            with open('cache', 'rb') as f:
                self.cfg = pickle.loads(f.read())
                self.cfg.password = unobscure(self.cfg.password)
        except FileNotFoundError:
            pass

    def dump_cache(self):
        with open('cache', 'wb') as f:
            cfg = replace(self.cfg)
            cfg.password = obscure(self.cfg.password)
            f.write(pickle.dumps(cfg))

    def add_connection(self, cached=False):
        # expecting tested and working connection here
        ch = SSHChannel(self.cfg.host, self.cfg.port, self.cfg.username, keyfile=self.cfg.keypath,
                        password=self.cfg.password)
        ch.connect()  # exceptions processed in the frame
        ch.client.get_transport().set_keepalive(1)
        self.dump_cache()
        self.__ssh = ch
        if not cached:
            # open next frame.
            self.set_frame(ConfigMenu)

    def __run_command(self, cmd: SSHCommand):
        self.frame.log_line(f'Testing <{cmd.desc}> command')
        if not self.__ssh.check_command(cmd):
            try:
                self.frame.log_line(f'Change not made, instantiating <{cmd.desc}>')
                success = self.__ssh.execute_command(cmd, listener=self.frame.log_line)
                if not success:
                    raise ValueError(f'Failed to run <{cmd.desc}>, check log for detail')
                return True, True, None
            except Exception as e:
                return False, True, e
        else:
            return True, False, None

    def process_command_set(self, cmds: list) -> bool:
        stack = []
        try:
            for c in cmds:
                success, ran, error = self.__run_command(c)
                if success and ran:
                    stack.append(c)
                if not success:
                    raise error
            return True
        except Exception as e:
            self.frame.log_line(f'Encountered an error {e.__str__()}; Rolling back')
            try:
                while len(stack) > 0 and (c := stack.pop()):
                    self.frame.log_line(f'Rolling back <{c.desc}>')
                    success = self.__ssh.rollback_command(c, listener=self.frame.log_line)
                    if not success:
                        raise ValueError(f'Command <{c.desc}> failed, check log for details.')
            except Exception as e:
                self.frame.log_line(f'PANIC! Failed to rollback <{c.desc}>: {e.__str__()}')
        return False

    def perform_base_config(self) -> bool:
        return self.process_command_set([SSHCommand('apt update -y', 'Update apt', elevated=True,
                                                    rollback='dpkg --configure -a'),
                                         SSHCommand('kill $(ps -aux | grep "[a]pt upgrade -y" | '
                                                    'awk \'"\'"\'{ print $2 }\'"\'"\')',
                                                    'kill running upgrade',
                                                    test='ps -aux | grep "update" | awk \'"\'"\'{  }\'"\'"\' '
                                                         f'&& echo {TEST_SUCCESS} || echo {TEST_FAIL}',
                                                    elevated=True),
                                         SSHCommand('apt upgrade -y', 'Upgrade apt', elevated=True)])

    def protect_file(self, filename, create_folder=False):
        if create_folder:
            p = "/".join(filename.split('/')[:-1])
            f = filename.split('/')[-1]
            ok, ran, _ = self.__run_command(SSHCommand(f'mkdir -p {p}',
                                                       f'checking directory for {f}', elevated=True,
                                                       test=f'[ -d {p} ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'))
            if not ok:
                raise ValueError(f'Failed to create directory {p} for file {f}. Connection error?')
            if ran:
                return lambda: 1, lambda: 1  # nothing to protect
        ok, ran, _ = self.__run_command(
            SSHCommand(f'cp {filename} {filename}.old', f'Protecting {filename}',
                       elevated=True,  # test is reversed. file existing is a reason to protect it
                       test=f'[ -f {filename} ] && echo {TEST_FAIL} || echo {TEST_SUCCESS}'
                       )
        )
        if not ok:
            raise ValueError(f'Failed to copy file {filename}. Connection error?')

        def commit():
            nonlocal ran
            nonlocal filename
            if ran:
                ok, _, _ = self.__run_command(SSHCommand(f'rm -f {filename}.old', f'removing tempfile for {filename}',
                                                         elevated=True))
                return ok
            return True

        def cancel():
            nonlocal ran
            nonlocal filename
            if ran:
                ok, _, _ = self.__run_command(SSHCommand(f'mv {filename}.old {filename}', f'restore {filename}',
                                                         elevated=True))
            else:
                ok, _, _ = self.__run_command(SSHCommand(f'rm -f {filename}', f'restore (delete) {filename}',
                                                         elevated=True,
                                                         test=f'[ -f {filename} ] && echo {TEST_FAIL} || '
                                                              f'echo {TEST_SUCCESS}'))
            return ok

        return cancel, commit

    def get_command_set(self, filename, common_name, elevated=False, test=None, rollback=None,
                        translate=None):
        if translate is None:
            translate = {}
        with open(f'data/{filename}', 'r') as f:
            command_dump = f.read()
        ret = []
        for q in command_dump.split('\n'):
            if q == '':
                continue
            for k in translate:
                q = q.replace(k, translate[k])
            ret.append(SSHCommand(q, common_name + ' ' + q, elevated=elevated, test=test, rollback=rollback))
        return ret

    def config_ssh(self) -> bool:
        try:
            cancel_keys, commit_keys = self.protect_file(f'/home/{self.cfg.username}/.ssh/authorized_keys', create_folder=True)
        except ValueError as e:
            self.frame.log_line(f'ERR: Encountered an error {e.__str__()}')
            return False

        if self.cfg.keypath is None:
            success = self.process_command_set([
                SSHCommand(f'ssh-keygen -f {self.cfg.username}.key -N ""', 'Generate SSH Keys',
                           rollback=f'rm -f {self.cfg.username}.key {self.cfg.username}.key.pub'),  # create key file
                SSHCommand(f'cat {self.cfg.username}.key.pub >> /home/{self.cfg.username}/.ssh/authorized_keys',
                           'authorize keyfile', elevated=True),  # add keyfile to auth
                SSHCommand(f'chmod 600 /home/{self.cfg.username}/.ssh/authorized_keys', 'protect authorized_keys',
                           elevated=True),
                SSHCommand(f'chown {self.cfg.username} /home/{self.cfg.username}/.ssh/authorized_keys',
                           'own auth key file', elevated=True),
                SSHCommand(f'rm -f {self.cfg.username}.key.pub', 'removing public keyfile')
            ])
            if success:
                self.get_file(f'{self.cfg.username}.key', f'{self.cfg.username}.key', delete_original=True)
                self.cfg.keypath = os.path.abspath(f'{self.cfg.username}.key')
                commit_keys()
            else:
                cancel_keys()
                self.frame.log_line('ERR: Failed to set a keyfile for the user!')
                return False
        # protect ssh config
        cancel_config, commit_config = self.protect_file('/etc/ssh/sshd_config')
        # upload new ssh config
        self.put_file('data/sshd_config', f'/home/{self.cfg.username}/sshd_config')
        # reload ssh config
        success = self.process_command_set([  # override new ssh config
            SSHCommand(f'mv -f /home/{self.cfg.username}/sshd_config /etc/ssh/sshd_config', 'overwriting SSH config',
                       elevated=True),
            SSHCommand('sshd -t', 'testing sshd_config', elevated=True),  # test ssh okay, reload service,
            SSHCommand('systemctl restart ssh', 'restarting SSHD', elevated=True)
        ])
        if not success:
            cancel_config()
            cancel_keys()
            self.__run_command(SSHCommand(f'rm {self.cfg.username}.key {self.cfg.username}.key.pub',
                                          'cleaning up keyfiles'))
            return False
        else:
            commit_config()
            commit_keys()
        self.cfg.keypath = os.path.abspath(f'{self.cfg.username}.key')
        self.dump_cache()
        return True

    def config_iptables(self):
        # config iptables
        iptables_config = self.get_command_set('iptables_config.sh', 'configuring iptables', elevated=True)
        ok = self.process_command_set([
            SSHCommand(f'iptables-save > /home/{self.cfg.username}/iptables.old', 'protecting iptables', elevated=True,
                       rollback=f'iptables-restore < /home/{self.cfg.username}/iptables.old'),
            *iptables_config,
            SSHCommand(f'iptables-save > /etc/iptables.rules', 'snapshot rules', elevated=True),
            SSHCommand(f'echo "iptables-restore < /etc/iptables.rules" > '
                       f'/etc/network/if-pre-up.d/tunneled_wizard_table_rules', 'automate rules',
                       elevated=True),
            SSHCommand(f'chmod +x /etc/network/if-pre-up.d/tunneled_wizard_table_rules', 'enable automate rules',
                       elevated=True),
            SSHCommand(f'sysctl net.ipv4.ip_forward=1', 'set ip foward', elevated=True)
        ])
        if not ok:
            return False

        self.__run_command(SSHCommand(f'rm /home/{self.cfg.username}/iptables.old', 'cleanup', elevated=True))
        return True

    def install_software(self):
        # upload
        self.put_file('data/stunnel-5.69.tar.gz', 'stunnel-5.69.tar.gz')
        self.put_file('data/openvpn-2.6.4.tar.gz', 'openvpn-2.6.4.tar.gz')
        success = self.process_command_set([
            SSHCommand('apt install -y make build-essential libnl-3-dev libnl-genl-3-dev pkg-config libcap-ng-dev'
                       ' libssl-dev liblz4-dev liblzo2-dev libpam0g-dev',
                       'installing make', elevated=True),
            SSHCommand('tar xfz openvpn-2.6.4.tar.gz', 'unpack openvpn', rollback='rm -rf openvpn-2.6.4'),
            SSHCommand(f'cd /home/{self.cfg.username}/openvpn-2.6.4/; ./configure', 'configure openvpn', elevated=True,
                       test=f'openvpn --version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand(f'cd /home/{self.cfg.username}/openvpn-2.6.4; make', 'make openvpn', elevated=True,
                       test=f'openvpn --version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand(f'cd /home/{self.cfg.username}/openvpn-2.6.4; make install', 'install openvpn', elevated=True,
                       test=f'openvpn --version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand('tar xfz stunnel-5.69.tar.gz', 'unpacking stunnel', rollback='rm -rf stunnel-5.69'),
            SSHCommand(f'cd /home/{self.cfg.username}/stunnel-5.69; ./configure', 'configure stunnel',
                       elevated=True, test=f'stunnel -version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand(f'cd /home/{self.cfg.username}/stunnel-5.69; make', 'make stunnel', elevated=True,
                       test=f'stunnel -version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand(f'cd /home/{self.cfg.username}/stunnel-5.69; make install', 'install stunnel', elevated=True,
                       test=f'stunnel -version > /dev/null && [ $? -eq 0 ] && echo {TEST_SUCCESS} || echo {TEST_FAIL}'),
            SSHCommand(f'rm -rf openvpn-2.6.4 openvpn-2.6.4.tar.gz stunnel-5.69 stunnel-5.69.tar.gz', 'cleanup',
                       elevated=True)
        ])
        return success

    def configure_software(self):
        self.put_file('data/EasyRSA-3.1.5.tgz', 'EasyRSA-3.1.5.tgz')
        self.put_file('data/vars', 'vars')
        self.put_file('data/ovpn_server_config', 'openvpn-server.conf')
        self.put_file('data/openvpn.service', 'openvpn.service')
        self.put_file('data/openvpn@.service', 'openvpn@.service')
        self.put_file('data/stunnel_config', 'stunnel.conf')
        self.put_file('data/stunnel.service', 'stunnel.service')
        success = self.process_command_set([
            SSHCommand(f'tar zxvf EasyRSA-3.1.5.tgz', 'unpack EasyRSA', rollback='rm -rf EasyRSA-3.1.5.tgz'),
            SSHCommand('cp vars EasyRSA-3.1.5/vars', 'setting vars'),
            SSHCommand('cd EasyRSA-3.1.5 && ./easyrsa --vars=./vars init-pki', 'initialize easyrsa',
                       rollback='rm -rf EasyRSA-3.1.5'),
            SSHCommand('cd EasyRSA-3.1.5 && ./easyrsa --batch --vars=./vars build-ca nopass', 'build CA'),
            SSHCommand('cd EasyRSA-3.1.5 && ./easyrsa --vars=./vars build-server-full openvpn-server nopass',
                       'create server certificate', stdin=('yes',)),
            SSHCommand('cd EasyRSA-3.1.5 && ./easyrsa --vars=./vars build-client-full openvpn-client nopass',
                       'create client certificate', stdin=('yes',)),
            SSHCommand('mkdir -p /etc/openvpn', 'create server config folder',
                       elevated=True),
            SSHCommand('cp -p EasyRSA-3.1.5/pki/ca.crt EasyRSA-3.1.5/pki/private/openvpn-server.key '
                       'EasyRSA-3.1.5/pki/issued/openvpn-server.crt /etc/openvpn/', 'copy server certificates',
                       elevated=True, rollback='rm -r /etc/openvpn/*'),
            SSHCommand(f'mkdir -p usercertificates', 'openvpn config directory', rollback='rmdir usercertificates'),
            SSHCommand(f'mv EasyRSA-3.1.5/pki/ca.crt EasyRSA-3.1.5/pki/private/openvpn-client.key '
                       f'EasyRSA-3.1.5/pki/issued/openvpn-client.crt '
                       f'usercertificates/', 'move ovpn certificates',
                       rollback='rm -r usercertificates/*'),
            SSHCommand('openvpn --genkey secret /etc/openvpn/ta.key', 'generating secret', elevated=True,
                       rollback='rm /etc/openvpn/ta.key'),
            SSHCommand('cp /etc/openvpn/ta.key usercertificates/ta.key', 'copy secret', elevated=True,
                       rollback='rm usercertificates/ta.key'),
            SSHCommand(f"sed -i 's/SED_IP_ADDR/{self.cfg.host}/g' openvpn-server.conf", 'server config',
                       rollback='rm -f openvpn-server.conf'),
            SSHCommand('mv openvpn-server.conf /etc/openvpn/openvpn-server.conf', 'copying config',
                       elevated=True, rollback='rm /etc/openvpn/openvpn-server.conf'),
            SSHCommand('chmod +r /etc/openvpn/*', 'make ovpn readable', elevated=True),
            SSHCommand('mv openvpn.service openvpn@.service /lib/systemd/system', 'establishing service', elevated=True,
                       rollback='rm /lib/systemd/system/openvpn.service /lib/systemd/system/openvpn@.service'),
            SSHCommand('chmod 600 /etc/openvpn/*', 'protect ovpn config', elevated=True),
            SSHCommand('mkdir -p /run/openvpn', 'create pid folder', elevated=True),
            SSHCommand('systemctl daemon-reload', 'reload service', elevated=True),
            SSHCommand('systemctl start openvpn@openvpn-server && systemctl enable openvpn@openvpn-server',
                       'start ovpn service',
                       elevated=True),
            SSHCommand(f"sed -i 's/SED_USERNAME/{self.cfg.username}/g' stunnel.conf", 'stunnel config',
                       rollback='rm -f stunnel.conf'),
            SSHCommand('mkdir -p /etc/stunnel', 'create stunnel dir', elevated=True),
            SSHCommand('mkdir -p /var/stunnel', 'create stunnel dir 2', elevated=True),
            SSHCommand(f'chown {self.cfg.username}:{self.cfg.username} /var/stunnel', 'own stunnel dir', elevated=True),
            SSHCommand('mv stunnel.conf /etc/stunnel/stunnel.conf', 'move stunnel config', elevated=True),
            SSHCommand('openssl req -newkey rsa:2048 -nodes -keyout stunnel-server.key -x509 '
                       '-days 3650 -subj "/CN=stunnel-server" -out stunnel-server.crt', 'create stunnel server cert',
                       rollback='rm -f stunnel-server.crt stunnel-server.key'),
            SSHCommand(f'openssl req -newkey rsa:2048 -nodes -keyout {self.cfg.username}-desktop.key '
                       f'-x509 -days 3650 -subj '
                       f'"/CN={self.cfg.username}-desktop" -out {self.cfg.username}-desktop.crt',
                       'create user desktop cert', rollback=f'rm {self.cfg.username}-desktop.crt'),
            SSHCommand(f'openssl req -newkey rsa:2048 -nodes -keyout {self.cfg.username}-mobile.key '
                       f'-x509 -days 3650 -subj'
                       f' "/CN={self.cfg.username}-mobile" -out {self.cfg.username}-mobile.crt',
                       'create user mobile cert', rollback=f'rm {self.cfg.username}-mobile.crt'),
            SSHCommand(f'openssl pkcs12 -export -in {self.cfg.username}-mobile.crt -inkey '
                       f'{self.cfg.username}-mobile.key -out {self.cfg.username}-mobile.p12',
                       'create user mobile p12 key', rollback=f'rm {self.cfg.username}-mobile.p12', stdin=('', '')),
            SSHCommand(f'cat {self.cfg.username}-desktop.crt > clients.crt', 'build client crt file'),
            SSHCommand(f'cat {self.cfg.username}-mobile.crt >> clients.crt', 'build client crt file 2'),
            SSHCommand('cp clients.crt stunnel-server.crt stunnel-server.key /etc/stunnel/', 'move config',
                       elevated=True),
            SSHCommand('rm -f stunnel-server.key clients.crt', 'cleanup'),
            SSHCommand('mv stunnel.service /lib/systemd/system', 'create stunnel service',
                       rollback='rm /lib/systemd/system/stunnel.service', elevated=True),
            SSHCommand('chmod +r /etc/stunnel/*', 'readability of stunnel folder', elevated=True),
            SSHCommand('systemctl daemon-reload', 'reload service', elevated=True),
            SSHCommand('systemctl start stunnel; systemctl enable stunnel', 'enable stunnel', elevated=True),
            SSHCommand(f'mv stunnel-server.crt {self.cfg.username}-* usercertificates/', 'save certificates',
                       rollback=f'rm usercertificates/{self.cfg.username}-* usercertificates/stunnel-server.crt'),
            SSHCommand(f'chown -R {self.cfg.username}:{self.cfg.username} usercertificates/*', 'owning folder',
                       elevated=True)
        ])
        if success:
            os.system('mkdir output\\usercertificates')
            self.get_file('usercertificates', 'output', recursive=True, delete_original=True)
        self.__run_command(
            SSHCommand('rm -rf EasyRSA* openvpn* stunnel* usercertificates vars', 'cleanup', elevated=True)
        )
        if not success:
            return False
        # bundle resulting config files.
        if 'dist' in os.listdir('output'):
            clear_dir('output\\dist')
        else:
            os.makedirs('output\\dist')
        os.makedirs('output\\dist\\stunnel')
        os.system('copy output\\usercertificates\\stunnel* output\\dist\\stunnel\\')
        os.system(f'copy output\\usercertificates\\{self.cfg.username}-* output\\dist\\stunnel\\')
        self.dist_file('data\\client_stunnel_conf', 'output\\dist\\stunnel\\stunnel.conf', replace={
            'SED_USERNAME': self.cfg.username,
            'SED_HOST': self.cfg.host
        })

        os.makedirs('output\\dist\\openvpn')
        os.system('copy output\\usercertificates\\openvpn-* output\\dist\\openvpn\\')
        os.system('copy output\\usercertificates\\ta.key output\\dist\\openvpn\\')
        os.system(f'copy output\\usercertificates\\ca.crt output\\dist\\openvpn\\')
        self.dist_file('data\\client_ovpn_config', 'output\\dist\\openvpn\\openvpn-client.ovpn')
        ta = self.ingest_file('output\\usercertificates\\ta.key')
        ca = self.ingest_file('output\\usercertificates\\ca.crt')
        cert = self.ingest_file('output\\usercertificates\\openvpn-client.crt')
        key = self.ingest_file('output\\usercertificates\\openvpn-client.key')

        self.dist_file('data\\openvpn-client-android.ovpn', 'output\\dist\\openvpn\\openvpn-client-android.ovpn',
                       replace={
                           'SED_CA_DATA': ca,
                           'SED_CERT_DATA': cert,
                           'SED_KEY_DATA': key,
                           'SED_TA_KEY': ta
                       })

        clear_dir('output\\usercertificates')
        os.rmdir('output\\usercertificates')
        return True

    def ingest_file(self, filename):
        with open(filename, 'r') as f:
            return f.read()

    def dist_file(self, filename, dest, replace=None):
        if replace is None:
            replace = {}
        with open(filename, 'r') as f:
            data = f.read()
        for k in replace:
            data = data.replace(k, replace[k])
        with open(dest, 'w') as f:
            f.write(data)

    def get_file(self, remote_path, local_path, delete_original=False, recursive=False):
        file = RemoteFile(self.__ssh.client.get_transport(), local_path, remote_path)
        # single responsibility function proxy
        file.download(recursive=recursive)
        if delete_original:
            ok, _, _ = self.__run_command(SSHCommand(f'rm -rf {file.remote_name}', f'Removing {file.remote_name}',
                                                     elevated=True))
            # process error

    def put_file(self, local_path, remote_path, delete_original=False):
        file = RemoteFile(self.__ssh.client.get_transport(), local_path, remote_path)
        file.upload()
        if delete_original:
            os.remove(file.local_name)

    def switch_user(self, username, password) -> bool:
        create_cmd = SSHCommand(f'useradd -G sudo -m {username}', 'create user', stdin=(password, password),
                                test=f'id {username} && echo "{TEST_SUCCESS}" || echo "{TEST_FAIL}"',
                                rollback=f'deluser --remove-home {username}', elevated=True)
        # check if user exists or create
        ok, ran_create, err = self.__run_command(
            create_cmd
        )

        def rollback_if_needed():
            nonlocal ran_create
            nonlocal create_cmd
            if ran_create:
                self.__ssh.rollback_command(create_cmd, listener=self.frame.log_line)
            return False

        if not ok:
            return False
        if ran_create:
            ok, ran, err = self.__run_command(SSHCommand(f'passwd {username}', 'Set password',
                                                         stdin=(password, password),
                                                         elevated=True))
            if not ok:
                return rollback_if_needed()
        # check su -> fail if not
        ok, ran, err = self.__run_command(SSHCommand(f'su -c "echo ok" {username}',
                                                     'test user access', stdin=(password,)))
        if not ok:
            return rollback_if_needed()
        # update cached creds
        self.cfg.username = username
        self.cfg.password = password
        self.cfg.keypath = None
        self.dump_cache()
        self.add_connection(cached=True)
        return True

    def finalize_config(self, stunnel_config, ovpn_config):
        def process(command):
            res = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
            for l in res.stdout.split('\n'):
                self.frame.log_line(f'OUT: {l}')
            for l in res.stderr.split('\n'):
                self.frame.log_line(f'ERR: {l}')

        self.frame.log_line('CLEARING STUNNEL CONFIG')
        clear_dir(stunnel_config)
        self.frame.log_line('COPYING STUNNEL CONFIG')
        process(f'copy output\\dist\\stunnel\\* "{stunnel_config}"')

        self.frame.log_line('CLEARING STUNNEL CONFIG')
        clear_dir(ovpn_config)
        self.frame.log_line('COPYYING OVPN CONFIG')
        process(f'copy output\\dist\\openvpn\\* "{ovpn_config}"')
        return True


    @staticmethod
    def process_error(container, error_text):
        modal = tk.Toplevel(container)
        modal.transient(container)
        modal.geometry(f'+{container.winfo_rootx() + 20}+{container.winfo_rooty() + 20}')  # todo may be center?

        def close_modal():
            nonlocal modal
            modal.destroy()
            container.focus_set()

        tk.Label(modal, text=error_text).grid(row=1, column=1, sticky='we')
        tk.Button(modal, text='Ok', command=close_modal).grid(row=2, column=1, sticky='we')


if __name__ == "__main__":
    parser = ArgumentParser()
    # leave room for CMD only run.
    # m = MainController(gui=False)
    # m.perform_base_config()
    # m.configure_software()
    # m.install_software()
    # m.config_iptables()
    # m.get_file('~/testfile', 'testicular', delete_original=True)
    # m.config_iptables()
    # exit()

    parser.add_argument('--gui', type=bool, default=True)  # todo: add CLI options.
    args = parser.parse_args()
    if args.gui:
        controller = MainController()
        controller.root.mainloop()
