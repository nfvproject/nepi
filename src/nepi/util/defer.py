class Defer:
    class NONE:
        pass
    
    def __init__(self, ojetwait):
        self.__ojet = Defer.NONE
        self.__ojetwait = ojetwait
    def __getattr__(self, attr):
        if attr in ('_Defer__ojet', '_Defer__ojetwait', '_get'):
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError, attr
        else:
            if self.__ojet is Defer.NONE:
                self.__ojet = self.__ojetwait()
            return getattr(self.__ojet, attr)
    def __setattr__(self, attr, value):
        if attr in ('_Defer__ojet', '_Defer__ojetwait'):
            self.__dict__[attr] = value
        else:
            if self.__ojet is Defer.NONE:
                self.__ojet = self.__ojetwait()
                self.__ojetwait = None
            return setattr(self.__ojet, attr, value)
    def _get(self):
        if self.__ojet is Defer.NONE:
            self.__ojet = self.__ojetwait()
        return self.__ojet

    def __nonzero__(self):
        return bool(self._get())
    
