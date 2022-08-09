from enum import Enum, auto


class EmissionUnit(Enum):
    G = auto()
    KG = auto()


class TimeResolution(Enum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()
    YEAR = auto()


class Disease(Enum):
    ALL_CAUSE_MORTALITY = auto()
    CARDIOVASCULAR = auto()
    DEMENTIA = auto()


class PrizeLevel(Enum):
    BRONZE = 'bronze'
    SILVER = 'silver'
    GOLD = 'gold'
