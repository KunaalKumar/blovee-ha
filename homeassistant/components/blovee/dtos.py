from attr import dataclass


@dataclass
class BloveeDevice:
    name: str
    model: str
    mac: str
    err: str
    is_on: bool
    brightness: int
