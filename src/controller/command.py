from dataclasses import dataclass

@dataclass
class SSHCommand:
    cmd: str
    desc: str
    test: str | None = None
    rollback: str | None = None
    elevated: bool = False
    stdin: tuple | None = None


TEST_SUCCESS = 'CMD_SUCCESS'
TEST_FAIL = 'CMD_FAILURE'
