from src.app.demos.ai_bi.nlq.enums import ChartType


def typify_chart_type(s: str) -> ChartType:
    s = s.upper()
    if s in ChartType.__members__:
        return ChartType[s]
    else:
        raise ValueError(f"Invalid chart type: {s}")
