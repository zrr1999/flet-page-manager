from pydantic import dataclasses
import flet as ft


class Config:
    arbitrary_types_allowed = True


@dataclasses.dataclass(config=Config)
class StateBase:
    running_pages: list[ft.Page] = dataclasses.Field(default_factory=list)
