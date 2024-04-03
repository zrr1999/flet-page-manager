from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..state import StateBase

if TYPE_CHECKING:
    from ..manager import PageManager


class PageBase[StateT: StateBase]:
    async def init(self, page: ft.Page, pm: PageManager[StateT]):
        pm.state.running_pages.append(page)
        await page.window_center_async()

    async def build(self, page: ft.Page, pm: PageManager[StateT]):
        raise NotImplementedError

    async def __call__(self, page: ft.Page, pm: PageManager[StateT]):
        await self.init(page, pm)
        await self.build(page, pm)
