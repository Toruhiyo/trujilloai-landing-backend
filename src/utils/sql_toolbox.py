import sqlparse


def is_valid_sql_query(s: str) -> bool:
    try:
        return bool(sqlparse.parse(s))
    except Exception:
        return False
