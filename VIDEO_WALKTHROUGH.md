# Suggested 4-5 minute screen-recording walkthrough

0:00-0:40 — Introduce the question: compare six stocks over January 2015 to July
2018 and identify 20/50-session moving-average crossings using SQL. Show six CSVs.

0:40-1:30 — Open analysis.sql. Explain stock/date primary key, ISO dates, complete
window counts, AVG OVER and LAG. Explain why the first full average is not a cross.

1:30-2:20 — Show Overview. TVS and Eicher lead raw price growth. Explain why the
large TCS and Infosys discontinuities mean these are not total investment returns.
Show the corrected Infosys raw change of -30.91%.

2:20-3:00 — Open Stock explorer. Select Bajaj Auto and show close plus both MAs.
Describe a BUY crossing and a SELL crossing. Filter dates without recomputing MAs.

3:00-4:10 — Open SQL playground. Load and run signal counts. Then run:
SELECT * FROM signals WHERE stock='Bajaj Auto' AND trade_date='2018-06-21';
Show the BUY result. Run the large daily moves example and download results.

4:10-5:00 — Open the PDF. Explain findings, data quality and raw-price limitations.
Conclude that adjusted data and realistic next-session execution assumptions are
needed before evaluating a trading strategy. Do not claim profitable execution.
