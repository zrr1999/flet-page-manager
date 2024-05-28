from __future__ import annotations

import flet as ft
from pydantic import BaseModel, Field


class StateBase(BaseModel, arbitrary_types_allowed=True):
    running_pages: list[ft.Page] = Field(default_factory=list)
