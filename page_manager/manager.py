from __future__ import annotations

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Awaitable, Callable

import flet as ft
from flet import AppView
from loguru import logger

from .pages import PageBase
from .state import StateBase
from .utils import get_free_port


class PageManager[StateT: StateBase]:
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
        state: StateT,
        *,
        view: AppView = AppView.FLET_APP,
        assets_dir: str = "public",
    ) -> None:
        self.state = state
        self.page_count: int = 0
        self.page_tasks: list[asyncio.Task] = []
        self.background_tasks: list[asyncio.Task] = []
        self.loop = asyncio.get_running_loop()
        self.executor = ThreadPoolExecutor()

        self.view = view
        self.assets_dir = assets_dir

    def run_task[OutputT](self, handler: Callable[..., Awaitable[OutputT]], *args):
        assert asyncio.iscoroutinefunction(handler)
        return asyncio.run_coroutine_threadsafe(handler(*args), self.loop)

    def run_thread(self, handler: Callable[..., Any], *args):
        self.loop.call_soon_threadsafe(self.loop.run_in_executor, self.executor, handler, *args)

    async def cancel_tasks(self, tasks: list[asyncio.Task]):
        for task in tasks:
            if not task.done():
                try:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    self.logger.info("PageManager: Task canceled")
                except Exception as e:
                    self.logger.error(f"PageManager: Error canceling task - {e}")

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
                break

        await self.cancel_tasks(self.page_tasks)
        await self.cancel_tasks(self.background_tasks)
        self.logger.info("PageManager: All tasks have been canceled, exiting...")

    def open_page(self, name: str, *, port: int = 0):
        if name not in PageManager.page_mapping:
            logger.error(f"Page `{name}` not found")
            return
        if port == 0:
            port = get_free_port()
        logger.info(f"PageManager: Opening page `{name}` on port {port}")
        page_obj = PageManager.page_mapping[name]()
        self.page_count += 1

        task = asyncio.create_task(
            ft.app_async(
                target=partial(page_obj, pm=self),
                view=self.view,
                port=port,
                assets_dir=self.assets_dir,
            )
        )
        self.page_tasks.append(task)

    async def restart(self, name: str, *, port: int = 0):
        # TODO
        await self.cancel_tasks(self.page_tasks)
        await self.cancel_tasks(self.background_tasks)
        self.page_count = 0
        self.page_tasks = []
        self.background_tasks = []
        await self.run(name, port=port)

    async def start(self, name: str, *, port: int = 0):
        # TODO
        await self.run(name, port=port)

    async def close(self):
        # TODO
        for p in self.state.running_pages:
            p.window_destroy()
