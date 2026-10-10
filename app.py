from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from query_engine import run_query
from build_database import build,DB,ROOT

st.set_page_config(page_title='MarketScope | SQL Lab',layout='wide')
st.markdown('''<style>.stApp{background:#0b1020;color:#e7edf7}h1,h2,h3{letter-spacing:-.035em}div[data-testid="stMetric"]{background:#151e33;padding:18px;border-radius:12px;border:1px solid #26334b}</style>''',unsafe_allow_html=True)
if not DB.exists(): build()
@st.cache_data
def load(name):
    with sqlite3.connect(DB) as c: return pd.read_sql_query(f'SELECT * FROM {name}',c)
summary=load('stock_summary')
st.sidebar.title('MarketScope')
st.sidebar.caption('Historical research / SQL laboratory')
page=st.sidebar.radio('Workspace',['Overview','Stock explorer','SQL playground','Method & downloads'])
st.sidebar.info('01 Jan 2015 - 31 Jul 2018\n\nLive SQL execution on the supplied historical data. No live market feed.')
st.title(page)
st.caption('Six Indian stocks. Every analytical metric is calculated in SQL.')
if page=='Overview':
    a,b,c,d=st.columns(4)
    a.metric('Stocks','6');b.metric('Price observations','5,334');c.metric('Sessions per stock','889');d.metric('Crossover events',int(summary.buy_events.sum()+summary.sell_events.sum()))
    st.warning('Raw prices: TCS and Infosys contain approximately 50% one-day discontinuities. Corporate-action adjustments and dividends are unavailable.')
    fig=px.bar(summary.sort_values('raw_price_change_pct'),x='raw_price_change_pct',y='stock',orientation='h',color='raw_price_change_pct',color_continuous_scale=['#ed6a7a','#61d8be'],labels={'raw_price_change_pct':'Raw close change (%)','stock':''})
    fig.update_layout(template='plotly_dark',height=380,coloraxis_showscale=False,paper_bgcolor='#0b1020',plot_bgcolor='#0b1020')
    st.plotly_chart(fig,width='stretch')
    st.subheader('Signals at the end of the sample')
    st.dataframe(summary[['stock','start_close','end_close','raw_price_change_pct','buy_events','sell_events','regime','last_event_date','last_event']].round(2),hide_index=True,width='stretch')
    st.caption('BUY / SELL are 20/50-session crossover labels. They are not tested trades or current recommendations.')
elif page=='Stock explorer':
    stock=st.selectbox('Stock',summary.stock.tolist())
    data,_=run_query("SELECT * FROM signals WHERE stock='"+stock+"' ORDER BY trade_date")
    data['trade_date']=pd.to_datetime(data.trade_date)
    date_range=st.date_input('Display dates',(data.trade_date.min().date(),data.trade_date.max().date()),min_value=data.trade_date.min().date(),max_value=data.trade_date.max().date())
    if len(date_range)==2:
        data=data[(data.trade_date.dt.date>=date_range[0])&(data.trade_date.dt.date<=date_range[1])]
    if data.empty: st.info('No trading observations in this range. Choose other dates.')
    else:
        fig=go.Figure()
        for col,label,color in [('close_price','Close','#dbe6f6'),('ma20','20-session MA','#61d8be'),('ma50','50-session MA','#b5a4ff')]:
            fig.add_trace(go.Scatter(x=data.trade_date,y=data[col],name=label,line=dict(color=color)))
        for signal,color,symbol in [('BUY','#61d8be','triangle-up'),('SELL','#ed6a7a','triangle-down')]:
            part=data[data.signal==signal]
            fig.add_trace(go.Scatter(x=part.trade_date,y=part.close_price,mode='markers',name=signal,marker=dict(color=color,symbol=symbol,size=11)))
        fig.update_layout(template='plotly_dark',height=480,yaxis_title='Raw price (INR)',paper_bgcolor='#0b1020',plot_bgcolor='#0b1020')
        st.plotly_chart(fig,width='stretch')
        st.caption('Moving averages use full history before the display filter. Warm-up values remain blank.')
        st.dataframe(data.sort_values('trade_date',ascending=False).round(2),hide_index=True,width='stretch')
        st.download_button('Download displayed observations',data.to_csv(index=False),'stock_observations.csv','text/csv')
elif page=='SQL playground':
    examples={
      'Stock performance':'SELECT stock, start_close, end_close, ROUND(raw_price_change_pct,2) AS raw_change_pct FROM stock_summary ORDER BY raw_price_change_pct DESC;',
      'Buy and sell counts':'SELECT * FROM signal_counts;',
      'Latest signals':'SELECT * FROM latest_signals;',
      'Bajaj signal on a date':"SELECT * FROM signals WHERE stock='Bajaj Auto' AND trade_date='2018-06-21';",
      'Large daily moves':'SELECT stock,trade_date,daily_change_pct FROM price_metrics WHERE ABS(daily_change_pct)>=20;',
      'Master price table':'SELECT * FROM master_prices ORDER BY trade_date DESC LIMIT 25;',
      'Data quality':'SELECT * FROM quality_audit;',
      'Annual analysis':'SELECT * FROM annual_summary ORDER BY stock,year;'}
    choice=st.selectbox('Example query',list(examples))
    if 'sql' not in st.session_state: st.session_state.sql=examples[choice]
    if st.button('Load example'): st.session_state.sql=examples[choice]
    sql=st.text_area('SQL editor',key='sql',height=210)
    st.caption('SQLite syntax • One SELECT/WITH query • 5,000-row preview limit • 5-second execution budget. Dashboard filters do not affect this editor.')
    if st.button('Run SQL',type='primary'):
        try:
            df,truncated=run_query(sql)
            st.session_state.query_result=(df,truncated)
            st.success(f'{len(df):,} rows returned')
        except Exception as e:
            st.session_state.pop('query_result',None)
            st.error(f'Query could not run: {e}')
    if 'query_result' in st.session_state:
        df,truncated=st.session_state.query_result
        if truncated: st.warning('Result truncated to 5,000 rows. Add filters to retrieve a smaller result.')
        st.dataframe(df,hide_index=True,width='stretch')
        st.download_button('Download result CSV',df.to_csv(index=False),'query_results.csv','text/csv')
    with st.expander('Tables, views and columns'):
        with sqlite3.connect(DB) as con:
            for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"):
                columns=[r[1] for r in con.execute(f'PRAGMA table_info({name})')]
                st.markdown(f'**{name}**');st.code(', '.join(columns),language=None)
else:
    st.subheader('Method')
    st.write('Raw daily close prices are ordered chronologically per stock. SQL window functions calculate trailing 20- and 50-observation simple moving averages. BUY and SELL identify crossings; HOLD means no new crossing. The first 50 observations are marked WARMUP for signals because no previous full pair exists.')
    st.write('Price change = 100 × (last close / first close − 1). Drawdown = 100 × (close / previous running peak − 1). Neither measure adjusts for corporate actions or dividends. No strategy backtest or future performance claim is made.')
    st.subheader('Project files')
    for name in ['analysis.sql','Stock_Market_Insights.pdf','README.md']:
        path=ROOT/name
        if path.exists(): st.download_button(f'Download {name}',path.read_bytes(),name)
    st.caption('Technical reference: https://docs.streamlit.io/develop/api-reference')
