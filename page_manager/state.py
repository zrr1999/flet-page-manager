from __future__ import annotations

import flet as ft
from pydantic import dataclasses


class Config:
    arbitrary_types_allowed = True


@dataclasses.dataclass(config=Config)
class StateBase:
    running_pages: list[ft.Page] = dataclasses.Field(default_factory=list)
