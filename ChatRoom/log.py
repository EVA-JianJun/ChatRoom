# -*- coding: utf-8 -*-

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