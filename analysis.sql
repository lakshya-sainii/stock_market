-- STOCK MARKET ANALYSIS | SQLite 3.25+ | raw supplied prices, INR
-- Run: python build_database.py (loads CSVs, executes this file, exports results).
-- Or open stock_market.db in SQLite and execute this file. Not T-SQL/MySQL.
-- All analytic calculations below are SQL. Python only imports and presents.
-- Re-runnable: replaces derived views only, preserves stock_prices.
CREATE TABLE IF NOT EXISTS stock_prices (
 stock TEXT NOT NULL, trade_date TEXT NOT NULL,
 open_price REAL NOT NULL, high_price REAL NOT NULL, low_price REAL NOT NULL,
 close_price REAL NOT NULL CHECK(close_price > 0), wap REAL,
 shares INTEGER, trades INTEGER, turnover REAL, deliverable_quantity INTEGER,
 delivery_pct REAL, spread_high_low REAL, spread_close_open REAL,
 PRIMARY KEY(stock, trade_date)
);
DROP VIEW IF EXISTS stock_summary;
DROP VIEW IF EXISTS signal_counts;
DROP VIEW IF EXISTS latest_signals;
DROP VIEW IF EXISTS master_prices;
DROP VIEW IF EXISTS quality_audit;
DROP VIEW IF EXISTS annual_summary;
DROP VIEW IF EXISTS price_metrics;
DROP VIEW IF EXISTS signals;
DROP VIEW IF EXISTS moving_averages;

-- Q1: Full history coverage and OHLC consistency.
CREATE VIEW quality_audit AS
SELECT stock, COUNT(*) observations, MIN(trade_date) first_date, MAX(trade_date) last_date,
 SUM(CASE WHEN close_price IS NULL OR close_price<=0 THEN 1 ELSE 0 END) invalid_close,
 SUM(CASE WHEN low_price>high_price OR open_price<low_price OR open_price>high_price
 OR close_price<low_price OR close_price>high_price THEN 1 ELSE 0 END) ohlc_issues,
 SUM(CASE WHEN shares<0 OR trades<0 OR turnover<0 THEN 1 ELSE 0 END) negative_activity
FROM stock_prices GROUP BY stock;

-- Q2: Trailing 20/50 OBSERVATION moving averages (not calendar days).
-- Require complete windows; first 49 observations have no 50-day average.
CREATE VIEW moving_averages AS
SELECT stock,trade_date,close_price,
 CASE WHEN COUNT(*) OVER w20=20 THEN AVG(close_price) OVER w20 END ma20,
 CASE WHEN COUNT(*) OVER w50=50 THEN AVG(close_price) OVER w50 END ma50
FROM stock_prices
WINDOW w20 AS (PARTITION BY stock ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
 w50 AS (PARTITION BY stock ORDER BY trade_date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW);

-- Q3: Crossover EVENTS. A persistent above/below regime is not a new signal.
-- BUY: current ma20>ma50, prior ma20<=ma50. SELL is the reverse.
-- First valid MA pair does not create a synthetic crossover.
CREATE VIEW signals AS
WITH lagged AS (
 SELECT *,LAG(ma20-ma50) OVER(PARTITION BY stock ORDER BY trade_date) prev_spread
 FROM moving_averages)
SELECT *,CASE WHEN ma50 IS NULL OR prev_spread IS NULL THEN 'WARMUP'
 WHEN ma20>ma50 AND prev_spread<=0 THEN 'BUY'
 WHEN ma20<ma50 AND prev_spread>=0 THEN 'SELL' ELSE 'HOLD' END signal,
 CASE WHEN ma50 IS NULL THEN 'WARMUP' WHEN ma20>ma50 THEN 'ABOVE'
 WHEN ma20<ma50 THEN 'BELOW' ELSE 'EQUAL' END regime
FROM lagged;

-- Q4: Raw close changes, running peak drawdown and normalized price.
CREATE VIEW price_metrics AS
WITH p AS (
 SELECT *, LAG(close_price) OVER(PARTITION BY stock ORDER BY trade_date) prev_close,
 MAX(close_price) OVER(PARTITION BY stock ORDER BY trade_date ROWS UNBOUNDED PRECEDING) running_peak,
 FIRST_VALUE(close_price) OVER(PARTITION BY stock ORDER BY trade_date) first_close
 FROM stock_prices)
SELECT *,100.0*(close_price/prev_close-1) daily_change_pct,
 100.0*(close_price/running_peak-1) drawdown_pct,
 100.0*close_price/first_close normalized_close FROM p;

-- Q5: Signal frequency (not completed trades or strategy profitability).
CREATE VIEW signal_counts AS
SELECT stock,SUM(signal='BUY') buy_events,SUM(signal='SELL') sell_events,
 SUM(signal='HOLD') hold_days,SUM(signal='WARMUP') warmup_days
FROM signals GROUP BY stock;

-- Q6: Latest observation, current regime and last crossover.
CREATE VIEW latest_signals AS
SELECT s.stock,s.trade_date,s.close_price,s.ma20,s.ma50,s.regime,s.signal,
 (SELECT x.trade_date FROM signals x WHERE x.stock=s.stock AND x.signal IN ('BUY','SELL')
 ORDER BY x.trade_date DESC LIMIT 1) last_event_date,
 (SELECT x.signal FROM signals x WHERE x.stock=s.stock AND x.signal IN ('BUY','SELL')
 ORDER BY x.trade_date DESC LIMIT 1) last_event
FROM signals s WHERE s.trade_date=(SELECT MAX(trade_date) FROM signals WHERE stock=s.stock);

-- Q7: Whole-sample raw price change, drawdown and trading activity.
CREATE VIEW stock_summary AS
WITH endpoints AS (
 SELECT stock,MIN(trade_date) start_date,MAX(trade_date) end_date,COUNT(*) observations,
 MIN(drawdown_pct) max_drawdown_pct,AVG(turnover) avg_daily_turnover,
 AVG(shares) avg_daily_shares,AVG(delivery_pct) avg_delivery_pct,
 MIN(daily_change_pct) worst_day_pct,MAX(daily_change_pct) best_day_pct
 FROM price_metrics GROUP BY stock)
SELECT e.*,a.close_price start_close,b.close_price end_close,
 100.0*(b.close_price/a.close_price-1) raw_price_change_pct,
 c.buy_events,c.sell_events,l.regime,l.last_event_date,l.last_event
FROM endpoints e JOIN stock_prices a ON a.stock=e.stock AND a.trade_date=e.start_date
JOIN stock_prices b ON b.stock=e.stock AND b.trade_date=e.end_date
JOIN signal_counts c ON c.stock=e.stock JOIN latest_signals l ON l.stock=e.stock;

-- Q8: Within-year first-to-last observed raw close changes.
-- 2015 and 2018 are boundary periods; these are not annual total returns.
CREATE VIEW annual_summary AS
WITH bounds AS (
 SELECT stock,SUBSTR(trade_date,1,4) year,MIN(trade_date) first_date,MAX(trade_date) last_date
 FROM stock_prices GROUP BY stock,SUBSTR(trade_date,1,4))
SELECT b.*,a.close_price first_close,z.close_price last_close,
 100.0*(z.close_price/a.close_price-1) within_year_change_pct
FROM bounds b JOIN stock_prices a ON a.stock=b.stock AND a.trade_date=b.first_date
JOIN stock_prices z ON z.stock=b.stock AND z.trade_date=b.last_date;

-- Q9: Date-aligned master table; keep only dates shared by all six stocks.
CREATE VIEW master_prices AS
SELECT trade_date,
 MAX(CASE WHEN stock='Bajaj Auto' THEN close_price END) bajaj_auto,
 MAX(CASE WHEN stock='Eicher Motors' THEN close_price END) eicher_motors,
 MAX(CASE WHEN stock='Hero Motocorp' THEN close_price END) hero_motocorp,
 MAX(CASE WHEN stock='Infosys' THEN close_price END) infosys,
 MAX(CASE WHEN stock='TCS' THEN close_price END) tcs,
 MAX(CASE WHEN stock='TVS Motors' THEN close_price END) tvs_motors
FROM stock_prices GROUP BY trade_date HAVING COUNT(DISTINCT stock)=6;

SELECT * FROM quality_audit;
SELECT * FROM stock_summary ORDER BY raw_price_change_pct DESC;
SELECT * FROM latest_signals;
SELECT * FROM annual_summary ORDER BY stock,year;
-- Q10: Flag discontinuities for review; do not infer corporate actions.
SELECT stock,trade_date,prev_close,close_price,daily_change_pct
FROM price_metrics WHERE ABS(daily_change_pct)>=20 ORDER BY ABS(daily_change_pct) DESC;
-- Q11: One-date Bajaj signal lookup; change the ISO date as needed.
SELECT trade_date,close_price,ma20,ma50,signal FROM signals
WHERE stock='Bajaj Auto' AND trade_date='2018-06-21';
-- Q12: Largest turnover sessions for each stock.
WITH ranked AS (SELECT stock,trade_date,turnover,
 ROW_NUMBER() OVER(PARTITION BY stock ORDER BY turnover DESC) rank
 FROM stock_prices)
SELECT * FROM ranked WHERE rank<=3 ORDER BY stock,rank;
