from dataclasses import dataclass

@dataclass
class Tag:
    name: str
    block: bool
    table: bool
