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
            self.log_debug = self._log_noshow
            self.log_info = self._log_noshow
        elif show == "INFO":
            self.log_debug = self._log_noshow
            self.log_info = print
        else:
            # DEBUG
            self.log_debug = print
            self.log_info = print

    def log_info_format(self, title, info):
        self.log_info("{0} | \033[0;36;42m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))

    def log_info_format_err(self, title, info):
        self.log_info("{0} | \033[0;36;41m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))

    def log_info_warning_format(self, title, info):
        self.log_info("{0} | \033[0;36;44m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))

    def log_debug_format(self, title, info):
        self.log_debug("{0} | \033[0;36;42m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))

    def log_debug_format_err(self, title, info):
        self.log_debug("{0} | \033[0;36;41m{1:^25}\033[0m | {2}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), title, info))
