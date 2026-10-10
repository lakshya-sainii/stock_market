"""Import the six source CSVs; execute SQL analysis; export SQL result tables."""
from pathlib import Path
from datetime import datetime
import csv, sqlite3, json
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'stock_market.db'
STOCKS = ['Bajaj Auto','Eicher Motors','Hero Motocorp','Infosys','TCS','TVS Motors']

def build():
    con = sqlite3.connect(DB)
    sql = (ROOT/'analysis.sql').read_text()
    con.executescript(sql.split('DROP VIEW')[0])
    counts = {}
    with con:
        con.execute('DELETE FROM stock_prices')
        for stock in STOCKS:
            with (ROOT/'data'/f'{stock}.csv').open(newline='',encoding='utf-8-sig') as f:
                rows = list(csv.reader(f)); data=[]
            for r in rows[1:]:
                date=datetime.strptime(r[0],'%d-%B-%Y').date().isoformat()
                values=[float(x) if x.strip() else None for x in r[1:]]
                for i in [5,6,8]:
                    if values[i] is not None: values[i]=int(values[i])
                data.append((stock,date,*values))
            con.executemany('INSERT INTO stock_prices VALUES ('+','.join('?'*14)+')',data)
            counts[stock]=len(data)
    con.executescript(sql)
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    queries={name:f'SELECT * FROM {name}' for name in ['quality_audit','stock_summary','signal_counts','latest_signals','annual_summary','master_prices']}
    queries['large_moves']='SELECT stock,trade_date,prev_close,close_price,daily_change_pct FROM price_metrics WHERE ABS(daily_change_pct)>=20 ORDER BY ABS(daily_change_pct) DESC'
    for name,q in queries.items():
        cur=con.execute(q)
        with (out/f'{name}.csv').open('w',newline='') as f:
            w=csv.writer(f); w.writerow([x[0] for x in cur.description]); w.writerows(cur)
    integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
    con.close()
    print(json.dumps({'imported':counts,'integrity':integrity},indent=2))
if __name__=='__main__': build()
