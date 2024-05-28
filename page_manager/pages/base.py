from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..state import StateBase

if TYPE_CHECKING:
    from ..manager import PageManager


class PageBase[StateT: StateBase]:
    def init(self, page: ft.Page, pm: PageManager[StateT]):
        pm.state.running_pages.append(page)
        page.window_center()

    def build(self, page: ft.Page, pm: PageManager[StateT]):
        raise NotImplementedError("Page must implement build method")

    def __call__(self, page: ft.Page, pm: PageManager[StateT]):
        self.init(page, pm)
        self.build(page, pm)
