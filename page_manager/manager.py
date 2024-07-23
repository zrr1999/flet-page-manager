from __future__ import annotations

import asyncio
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
from typing import Any, Awaitable, Callable, Iterable

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
    def register_page(
        name: str | None = None,
    ) -> Callable[[type[PageBase[StateT]]], type[PageBase[StateT]]]:
        def _register_page(page_cls: type[PageBase[StateT]]) -> type[PageBase[StateT]]:
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
        self.view = view
        self.assets_dir = assets_dir

        self.page_count: int = 0
        self.page_tasks: list[asyncio.Task[Any]] = []
        self.backgroud_futures: list[Future[Any]] = []
        self.need_restart: bool = False
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor()

    def run_task[**InputT, RetT](
        self,
        handler: Callable[InputT, Awaitable[RetT]],
        *args: InputT.args,
        **kwargs: InputT.kwargs,
    ) -> Future[RetT]:
        assert asyncio.iscoroutinefunction(handler)
        task = asyncio.run_coroutine_threadsafe(handler(*args, **kwargs), self.loop)
        self.backgroud_futures.append(task)
        return task

    def run_thread[**InputT](
        self, handler: Callable[InputT, Any], *args: InputT.args, **kwargs: InputT.kwargs
    ):
        self.loop.call_soon_threadsafe(
            self.loop.run_in_executor, self.executor, partial(handler, *args, **kwargs)
        )

    async def cancel_tasks(self, tasks: Iterable[asyncio.Task[Any]]):
        wrapped_tasks: list[asyncio.Task[Any]] = []
        for task in tasks:
            if not task.done():
                task.cancel()
                self.logger.info(f"PageManager: Task {task.get_name()} canceled")
                wrapped_tasks.append(task)
        await asyncio.gather(*wrapped_tasks, return_exceptions=True)

    async def cancel_futures(self, futures: Iterable[Future[Any]]):
        wrapped_futures: list[asyncio.Future[Any]] = []

        for future in futures:
            if not future.done():
                future.cancel()
                self.logger.info("PageManager: Future canceled")
                wrapped_futures.append(asyncio.wrap_future(future))

        await asyncio.gather(*wrapped_futures, return_exceptions=True)

    async def check_page_count(self):
        while self.page_count > 0 and not self.need_restart:
            for task in self.page_tasks:
                await asyncio.sleep(0.1)
                if task.done():
                    self.page_count -= 1
                    self.page_tasks.remove(task)
        await self.cancel_tasks(asyncio.all_tasks() - {asyncio.current_task()})
        self.executor.shutdown(cancel_futures=True)
        self.executor = ThreadPoolExecutor()
        self.logger.info("PageManager: Event loop stopped, exiting...")

    def open_page(self, name: str, *, port: int = 0):
        if name not in PageManager.page_mapping:
            logger.error(f"Page `{name}` not found")
            return
        if port == 0:
            port = get_free_port()
        page_obj = PageManager.page_mapping[name]()
        self.page_count += 1
        task = self.loop.create_task(
            ft.app_async(
                target=partial(page_obj, pm=self),
                view=self.view,
                port=port,
                assets_dir=self.assets_dir,
            )
        )
        self.page_tasks.append(task)
        logger.info(f"PageManager: Opening page `{name}` on port http://127.0.0.1:{port}")

    def restart(self):
        self.need_restart = True

    def start(self, name: str, *, port: int = 0):
        while True:
            self.open_page(name, port=port)
            self.loop.run_until_complete(self.check_page_count())
            if not self.need_restart:
                break
            logger.info("PageManager: Restarting...")
            # TODO: port should be reused, but port already in use
            port = get_free_port()
            self.need_restart = False
        self.loop.close()

    async def close(self):
        # TODO
        for p in self.state.running_pages:
            p.window_destroy()
