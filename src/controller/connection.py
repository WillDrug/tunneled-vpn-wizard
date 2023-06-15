import paramiko
from os import path
from .command import SSHCommand, TEST_FAIL, TEST_SUCCESS

class SSHChannelException(Exception):
    pass

class SSHChannel:
    def __init__(self, host: str, port: int, username: str, password: str = None, keyfile: str = None):
        # error check
        if not isinstance(port, int):
            raise ValueError('Port must be an integer')
        if password is None and keyfile is None:
            raise ValueError('Supply password or keyfile path')
        self.__keyauth = False
        if keyfile is not None:
            self.__keyauth = True
            if not path.exists(path.dirname(keyfile)):
                raise ValueError(f'Key path is not a valid path! Got {keyfile}')

        self.host = host
        self.port = port
        self.username = username
        self.password = password  # save password for sudo
        self.auth = keyfile or password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        try:
            key = None
            if self.__keyauth:
                key = paramiko.RSAKey.from_private_key_file(self.auth)
            self.client.connect(self.host, self.port, self.username, password=self.auth if not self.__keyauth else None,
                                pkey=key, timeout=5)
        except TimeoutError as e:
            raise SSHChannelException(f'Timed out: {e.__str__()}')
        except paramiko.ssh_exception.AuthenticationException as e:
            raise SSHChannelException(f'Auth problem: {e.__str__()}')
        except FileNotFoundError:
            raise SSHChannelException(f'Key file not found.')
        except paramiko.ssh_exception.SSHException as e:
            raise SSHChannelException(f'SSH Error: {e.__str__()}')

    def __execute_command(self, cmd: str, elevated=False, stdin=None):
        text = cmd
        if elevated:
            text = f"sudo -S bash -c \' {cmd} \'"
        sin, sout, serr = self.client.exec_command(text)
        used = False
        if elevated:
            sin.write(self.password + '\n')
            sin.flush()
            used = True
        if stdin is not None:
            for line in stdin:
                sin.write(line + '\n')
                sin.flush()
            used = True
        if used:
            sin.close()
        return sin, sout, serr

    def generate_output(self, listener, sout, serr):
        while not sout.channel.exit_status_ready() or not serr.channel.exit_status_ready():
            if (line := sout.readline().strip()) != '':
                listener(f'OUT: {line}')
            if (line := serr.readline().strip()) != '':
                listener(f'ERR: {line}')
        if (line := sout.readline().strip()) != '':
            listener(f'OUT: {line}')
        if (line := serr.readline().strip()) != '':
            listener(f'ERR: {line}')


    def rollback_command(self, cmd: SSHCommand, listener=None) -> bool:
        if cmd.rollback is None:
            return True
        sin, sout, serr = self.__execute_command(cmd.rollback, elevated=cmd.elevated, stdin=cmd.stdin)
        if listener is not None:
            self.generate_output(listener, sout, serr)
        if sout.channel.recv_exit_status() != 0:
            return False
        return True

    def execute_command(self, cmd: SSHCommand, listener=None) -> bool:
        sin, sout, serr = self.__execute_command(cmd.cmd, elevated=cmd.elevated, stdin=cmd.stdin)
        if listener is not None:
            self.generate_output(listener, sout, serr)
        if sout.channel.recv_exit_status() != 0:
            return False
        return True

    def check_command(self, cmd: SSHCommand) -> bool:
        if cmd.test is None:
            return False
        sin, sout, serr = self.__execute_command(cmd.test, elevated=cmd.elevated, stdin=cmd.stdin)
        data = sout.read().decode()
        if TEST_SUCCESS in data:
            return True
        elif TEST_FAIL in data:
            return False
        else:
            raise ValueError(f'Test for command {cmd} failed to return an expected value.')