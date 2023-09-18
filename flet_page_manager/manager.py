from __future__ import annotations
import flet as ft
from flet import AppView
import asyncio
from typing import TYPE_CHECKING, TypeVar, Generic
from loguru import logger
import sys
from .exception import PageException

if TYPE_CHECKING:
    from .pages import PageBase

    StateT = TypeVar("StateT")


class PageManager(Generic[StateT]):
    logger = logger

    page_mapping: dict[str, type[PageBase]] = {}

    @staticmethod
    def register_page(name: str | None = None):
        def _register_page(page_cls: type[PageBase]):
            PageManager.page_mapping[name or page_cls.__name__] = page_cls
            return page_cls

        return _register_page

    @staticmethod
    def set_level(level: str | int):
        logger.remove(0)
        logger.add(sys.stdout, level=level)

    def __init__(
        self,
        *,
        view: AppView = AppView.FLET_APP,
        assets_dir: str = "public",
        state: StateT | None = None,
    ) -> None:
        self.state = state
        self.page_count: int = 0
        self.page_tasks: list[asyncio.Task] = []
        self.background_tasks: list[asyncio.Task] = []

        self.view: AppView = view
        self.assets_dir = assets_dir

    async def run(self, name: str, *, port: int = 0):
        self.open_page(name, port=port)
        while self.page_count > 0:
            try:
                await asyncio.sleep(0.1)
                for task in self.page_tasks:
                    if task.done():
                        self.page_count -= 1
                        self.page_tasks.remove(task)
                        await task

                for task in self.background_tasks:
                    if task.done():
                        self.background_tasks.remove(task)
                        await task

            except KeyboardInterrupt:
                for task in self.page_tasks:
                    task.cancel()
                    self.logger.info("PageManager: Page task canceled")
                break

        for task in self.background_tasks:
            task.cancel()
            self.logger.info("PageManager: Background task canceled")

    def open_page(self, name: str, *, port: int = 0):
        if name not in PageManager.page_mapping:
            raise PageException(f"Page {name} not found")
        page_obj = PageManager.page_mapping[name]()
        self.page_count += 1

        async def _page_func_async(page: ft.Page):
            await page_obj(page, self)

        task = asyncio.create_task(
            ft.app_async(
                target=_page_func_async,
                view=self.view,
                port=port,
                assets_dir=self.assets_dir,
            )
        )
        self.page_tasks.append(task)
