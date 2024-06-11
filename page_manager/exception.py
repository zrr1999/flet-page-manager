from __future__ import annotations


class PageException(Exception):
    pass


class PageRestartException(Exception):
    pass


class PageCrash(PageException):
    pass
