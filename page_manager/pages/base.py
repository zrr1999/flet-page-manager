from __future__ import annotations
import flet as ft
from ..manager import PageManager


class PageBase:
    async def init(self, page: ft.Page, pm: PageManager):
        await page.window_center_async()

    async def build(self, page: ft.Page, pm: PageManager):
        raise NotImplementedError

    async def __call__(self, page: ft.Page, pm: PageManager):
        await self.init(page, pm)
        await self.build(page, pm)
