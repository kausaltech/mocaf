from enum import Enum, auto


class EmissionUnit(Enum):
    G = auto()
    KG = auto()


class TimeResolution(Enum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()
    YEAR = auto()
