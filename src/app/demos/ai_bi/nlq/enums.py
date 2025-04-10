from src.utils.typification.base_enum import BaseEnum


class Unit(BaseEnum):
    USD = "USD"
    EUR = "EUR"
    MM = "MM"
    KG = "KG"
    PCS = "PCS"
    PERCENT = "PERCENT"


class ChartType(BaseEnum):
    BAR = "BAR"
    LINE = "LINE"
    AREA = "AREA"
    PIE = "PIE"
    KPI = "KPI"
