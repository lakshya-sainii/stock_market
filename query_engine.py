"""Bounded, read-only SQL execution for the local playground."""
import sqlite3,time
from pathlib import Path
import pandas as pd
DB=Path(__file__).resolve().parent/'stock_market.db'

def run_query(sql,limit=5000,seconds=5):
    con=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
    con.set_authorizer(lambda action,*args: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
    deadline=time.monotonic()+seconds
    con.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
    try:
        cur=con.execute(sql)
        if cur.description is None: raise ValueError('Enter a SELECT query.')
        rows=cur.fetchmany(limit+1)
        return pd.DataFrame(rows[:limit],columns=[c[0] for c in cur.description]),len(rows)>limit
    finally: con.close()
