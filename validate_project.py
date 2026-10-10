from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from query_engine import run_query
ROOT=Path(__file__).resolve().parent

def validate():
    with sqlite3.connect(ROOT/'stock_market.db') as con:
        prices=pd.read_sql_query('SELECT * FROM stock_prices ORDER BY stock,trade_date',con)
        actual=pd.read_sql_query('SELECT * FROM signals ORDER BY stock,trade_date',con)
        assert len(prices)==5334 and not prices.duplicated(['stock','trade_date']).any()
        assert con.execute('SELECT COUNT(*) FROM master_prices').fetchone()[0]==889
        assert con.execute('SELECT SUM(ohlc_issues+invalid_close+negative_activity) FROM quality_audit').fetchone()[0]==0
        for stock,g in prices.groupby('stock'):
            a=actual[actual.stock==stock]
            m20=g.close_price.rolling(20).mean();m50=g.close_price.rolling(50).mean()
            assert np.allclose(a.ma20,m20,equal_nan=True)
            assert np.allclose(a.ma50,m50,equal_nan=True)
            spread=m20-m50;prev=spread.shift()
            expected=np.select([m50.isna()|prev.isna(),(spread>0)&(prev<=0),(spread<0)&(prev>=0)],['WARMUP','BUY','SELL'],default='HOLD')
            assert (expected==a.signal).all()
    assert run_query('SELECT COUNT(*) n FROM stock_prices')[0].iloc[0,0]==5334
    assert run_query('SELECT * FROM stock_prices')[1]
    assert run_query('SELECT * FROM stock_prices WHERE 1=0')[0].empty
    for sql in ['DELETE FROM stock_prices',"ATTACH DATABASE ':memory:' AS other",'DROP VIEW signals','SELECT 1; SELECT 2;','SELECT * FROM missing_table']:
        try: run_query(sql)
        except (sqlite3.Error,ValueError): pass
        else: raise AssertionError('Expected rejection: '+sql)
    try:
        run_query('WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t) SELECT SUM(x) FROM t',seconds=.01)
    except sqlite3.OperationalError: pass
    else: raise AssertionError('Execution limit failed')
    print('PASS: SQL windows/signals agree with independent calculations for all 5,334 rows; quality, query results, write protection and timeout checked.')
if __name__=='__main__': validate()
