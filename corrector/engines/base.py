from dataclasses import dataclass


@dataclass
class EngineStatus:
    name: str
    available: bool
    note: str = ""
