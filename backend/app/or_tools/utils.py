from datetime import datetime

def make_dt(y: int, m: int, d: int, h: int = 0, minute: int = 0) -> datetime:
    return datetime(y, m, d, h, minute)