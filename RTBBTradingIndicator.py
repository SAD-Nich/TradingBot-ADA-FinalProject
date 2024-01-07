import pandas as pd
import pandas_ta as ta
import numpy as np
import MetaTrader5 as MT
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime
from backtesting import Strategy, Backtest

MT.initialize()
login = 69120408
password = 'cq1ppuvf'
server = 'MetaQuotes-Demo'
MT.login(login, password, server)
account = MT.account_info()

indices = pd.DataFrame(MT.copy_rates_range('USDJPY', MT.TIMEFRAME_D1,datetime(2013,12,29),datetime(2023,12,30)))
indices = indices[indices.high!=indices.low]
indices.reset_index(drop=True)
indices['time']=pd.to_datetime(indices['time'],unit='s')

dfRT = pd.DataFrame()
dfRT['Time']= indices['time']
dfRT['Open']= indices['open']
dfRT['High']= indices['high']
dfRT['Low']= indices['low']
dfRT['Close'] = indices['close']
dfRT['Volume'] = indices['tick_volume']

dfRT['EMA']=ta.ema(indices.close, length=200)
dfRT['EMA2']=ta.ema(indices.close, length=150)
dfRT['RSI']=ta.rsi(indices.close, length=12)
my_bbands = ta.bbands(indices.close, length=14, std=2.0)
#my_bbands[0:100]
dfRT=dfRT.join(my_bbands)
dfRT.dropna(inplace=True)
dfRT.reset_index(inplace=True, drop=True)

def addemasignal(df):
    emasignal = [0]*len(df)
    for i in range(0, len(df)):
        if df.EMA2[i]>df.EMA[i]:
            emasignal[i]=2
        elif df.EMA2[i]<df.EMA[i]:
            emasignal[i]=1
    df['EMASignal'] = emasignal
addemasignal(dfRT)

def addorderslimit(df, percent):
    ordersignal=[0]*len(df)
    for i in range(1, len(df)): #EMASignal of previous candle!!! modified!!!
        if  df.Close[i]<=df['BBL_14_2.0'][i] and df.EMASignal[i]==2:
            ordersignal[i]=df.Close[i]-df.Close[i]*percent
        elif df.Close[i]>=df['BBU_14_2.0'][i] and df.EMASignal[i]==1:
            ordersignal[i]=df.Close[i]+df.Close[i]*percent
    df['ordersignal']=ordersignal
    
addorderslimit(dfRT, 0.000)

def pointposbreak(x):
    if x['ordersignal']!=0:
        return x['ordersignal']
    else:
        return np.nan
dfRT['pointposbreak'] = dfRT.apply(lambda row: pointposbreak(row), axis=1)

dfpl = dfRT.copy()
fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
                open=dfpl['Open'],
                high=dfpl['High'],
                low=dfpl['Low'],
                close=dfpl['Close']),
                go.Scatter(x=dfpl.index, y=dfpl.EMA, line=dict(color='orange', width=2), name="EMA"),
                go.Scatter(x=dfpl.index, y=dfpl.EMA2, line=dict(color='yellow', width=2), name="EMA2"),        
                go.Scatter(x=dfpl.index, y=dfpl['BBL_14_2.0'], line=dict(color='blue', width=1), name="BBL"),
                go.Scatter(x=dfpl.index, y=dfpl['BBU_14_2.0'], line=dict(color='blue', width=1), name="BBU")])

fig.add_scatter(x=dfpl.index, y=dfpl['pointposbreak'], mode="markers",
                marker=dict(size=6, color="Black"),
                name="Signal")
fig.update_xaxes(rangeslider_visible=False)
fig.update_layout(autosize=False, width=600, height=600,margin=dict(l=50,r=50,b=100,t=100,pad=4), paper_bgcolor="white")
fig.show()

def SIGNAL():
    return dfpl.ordersignal

class MyStrat(Strategy):
    initsize = 0.9
    mysize = initsize
    def init(self):
        super().init()
        self.signal = self.I(SIGNAL)

    def next(self):
        super().next()
        TPSLRatio = 2
        perc = 0.02
        
        if len(self.trades)>0:
            if self.data.index[-1]-self.trades[-1].entry_time>=10:
                self.trades[-1].close()
            if self.trades[-1].is_long and self.data.RSI[-1]>=75:
                self.trades[-1].close()
            elif self.trades[-1].is_short and self.data.RSI[-1]<=25:
                self.trades[-1].close()
        
        if self.signal!=0 and len(self.trades)==0 and self.data.EMASignal==2:  
            sl1 = min(self.data.Low[-1],self.data.Low[-2])*(1-perc)
            tp1 = self.data.Close[-1]+(self.data.Close[-1] - sl1)*TPSLRatio
            self.buy(sl=sl1, tp=tp1, size=self.mysize)
        
        elif self.signal!=0 and len(self.trades)==0 and self.data.EMASignal==1:         
            sl1 = sl1 = max(self.data.High[-1],self.data.High[-2])*(1+perc)
            tp1 = self.data.Close[-1]-(sl1 - self.data.Close[-1])*TPSLRatio
            self.sell(sl=sl1, tp=tp1, size=self.mysize)

bt = Backtest(dfpl, MyStrat, cash=1000, margin=1/15, commission=.000)
stat = bt.run()
bt.plot()
print(stat)
print(dfpl)