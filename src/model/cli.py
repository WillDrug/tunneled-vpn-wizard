from .baseframe import BaseFrame
from logging import getLogger, StreamHandler, Formatter, DEBUG
from sys import stdout


class LogFrame(BaseFrame):
    def __init__(self, root, controller):
        self.controller = controller  # ignoring super call and Tk inheritance.
        logger = getLogger('vpn-wizard')
        logger.setLevel(DEBUG)
        handler = StreamHandler(stream=stdout)
        handler.setFormatter(Formatter("%(asctime)s|%(name)s|%(levelname)s|%(funcName)s:%(lineno)d|%(message)s"))
        logger.addHandler(handler)
        self.logger = logger

    def log_line(self, text):
        self.logger.info(text)
