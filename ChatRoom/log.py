# -*- coding: utf-8 -*-
from datetime import datetime

class Log():

    def __init__(self, show=0):
        """ init """
        self.switch(show)

    def _log_noshow(self, *args, **kwargs):
        pass

    def switch(self, show):
        if show == None:
            self.log = self._log_noshow
            self.log_info = self._log_noshow
        elif show == "INFO":
            self.log = self._log_noshow
            self.log_info = print
        else:
            # DEBUG
            self.log = print
            self.log_info = print

    def log_info_format(self, title, info, err=False):
        if err:
            self.log_info("{0} | \033[0;36;41m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))
        else:
            self.log_info("{0} | \033[0;36;42m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))

    def log_format(self, title, info, err=False):
        if err:
            self.log("{0} | \033[0;36;41m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))
        else:
            self.log("{0} | \033[0;36;42m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))
