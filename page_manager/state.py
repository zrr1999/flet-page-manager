from pydantic import dataclasses
import flet as ft


@dataclasses.dataclass
class StateBase:
    running_pages: list[ft.Page] = dataclasses.field(default_factory=dict)
