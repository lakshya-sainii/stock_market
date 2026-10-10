# Stock Market Analysis + Streamlit SQL Playground

## Run in VS Code (Windows)
1. Extract the ZIP completely. Open the extracted `Stock_Market_Project` folder in VS Code.
2. Open Terminal > New Terminal. Use Python 3.10 or newer.
3. Run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501.
Keep the terminal open. Press Ctrl+C to stop. No API key, SQL Server connection,
or separate EDA application is needed. The packaged SQLite database is ready.
If `python` is not recognized on Windows, try `py` in both commands.

## Rebuild analysis
```powershell
python build_database.py
```
This reads all six source CSVs, validates types and unique stock/date keys,
executes `analysis.sql`, and regenerates the database and CSV result tables.
Restart Streamlit after rebuilding so cached dashboard data refreshes.
Python imports data and displays SQL outputs; the analysis is implemented in SQL.
The importer preserves source blanks as NULL and never imputes them.

## Deliverables
- `analysis.sql`: schema, 9 reusable analysis views, and 12 numbered query tasks.
- `Stock_Market_Insights.pdf`: evidence, charts, interpretation and limitations.
- `app.py`: overview, stock chart, live SQL editor and downloads.
- `stock_market.db`: populated SQLite database with 5,334 source observations.
- `data/`: unchanged six input CSVs; prices and turnover are in INR.
- `results/`: exported SQL outputs for checking and submission.
- `query_engine.py`: restricted query runner, row cap and time budget.
- `build_database.py`: reproducible CSV import and SQL execution.
- `validate_project.py`: independent calculations and query safety checks.
- `VIDEO_WALKTHROUGH.md`: suggested narration for recording your demonstration.

## SQL compatibility
The delivered SQL uses SQLite 3.25+ window functions and is tested with Python's
SQLite engine. It is not directly executable in SSMS/MySQL without translation.
To run the SQL manually, open `stock_market.db` in a SQLite client and execute
`analysis.sql`. Running the script on an empty database creates empty views;
load data with `build_database.py` first. The app's editor accepts single read-only
SELECT/WITH queries, not schema edits. Standard SQLite functions are available.

## Definitions and limitations
- One row = one stock on one observed trading date, 2015-01-01 to 2018-07-31.
- Simple moving averages use 20/50 observations, including today's close.
- Only full windows are accepted. No synthetic signal on the first full window.
- BUY: MA20 crosses from <= MA50 to > MA50. SELL is the reverse.
- HOLD means no new event, not a persistent long position. WARMUP covers 50 rows.
- Signals can only be known after the close. Counts are not executed trades.
- Raw price changes exclude dividends and corporate-action adjustments. The
  supplied approximately 50% discontinuities distort changes and risk measures.
- Within-year changes use the first and last available close inside each year,
  not previous-year closing prices; 2018 ends in July.
- This is a historical classroom analysis; the playground is live query execution,
  not a current market feed. No investment recommendation or profitability claim.
- The reference PPTX lists a video as another submission component. Record your
  own screen demonstration using the included walkthrough. No video is included.

## Technical reference
https://docs.streamlit.io/develop/api-reference
