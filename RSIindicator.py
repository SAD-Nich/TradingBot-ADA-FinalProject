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

indices = pd.DataFrame(MT.copy_rates_range('USDJPY', MT.TIMEFRAME_M5,datetime(2023,6,30),datetime(2023,8,30)))
indices=indices[indices['tick_volume']!=0]
indices.isna().sum()
indices.reset_index(drop=True, inplace=True)
indices['time']=pd.to_datetime(indices['time'],unit='s')

df = pd.DataFrame()
df['Time']= indices['time']
df['Open']= indices['open']
df['High']= indices['high']
df['Low']= indices['low']
df['Close'] = indices['close']
df['Volume'] = indices['tick_volume']

df["EMA"] = ta.ema(df.Close, length=50)
df["RSI"] = ta.rsi(df.Close, length=3)
a=ta.adx(df.High, df.Low, df.Close, length=5)
df['ADX']=a['ADX_5']
df['ATR']= df.ta.atr()

emasignal = [0]*len(df)
backcandles = 8

for row in range(backcandles, len(df)):
    upt = 1
    dnt = 1
    for i in range(row-backcandles, row+1):
        if df.High[i]>=df.EMA[i]:
            dnt=0
        if df.Low[i]<=df.EMA[i]:
            upt=0
    if upt==1 and dnt==1:
        emasignal[row]=3
    elif upt==1:
        emasignal[row]=2
    elif dnt==1:
        emasignal[row]=1

df['EMAsignal'] = emasignal

RSIADXSignal = [0] * len(df)
for row in range(0, len(df)):
    RSIADXSignal[row] = 0
    if df.EMAsignal[row]==1 and df.RSI[row]>=80 and df.ADX[row]>=30:
        RSIADXSignal[row]=1
    if df.EMAsignal[row]==2 and df.RSI[row]<=20 and df.ADX[row]>=30:
        RSIADXSignal[row]=2

df['RSIADXSignal']=RSIADXSignal

CandleSignal = [0] * len(df)
for row in range(1, len(df)):
    CandleSignal[row] = 0
    if (RSIADXSignal[row]==1 or RSIADXSignal[row-1]==1) and (df.Open[row]>df.Close[row]):# and df.Close[row]<df.Close[row-1]):
        CandleSignal[row]=1
    if (RSIADXSignal[row]==2 or RSIADXSignal[row-1]==2) and (df.Open[row]<df.Close[row]):# and df.Close[row]>df.Close[row-1]):
        CandleSignal[row]=2
    if RSIADXSignal[row-1]==1 and df.Open[row]>df.Close[row] and df.Close[row]<min(df.Close[row-1], df.Open[row-1]):
        CandleSignal[row]=1
    if RSIADXSignal[row-1]==2 and df.Open[row]<df.Close[row] and df.Close[row]>max(df.Close[row-1], df.Open[row-1]):
        CandleSignal[row]=2

df['TotSignal']=CandleSignal

def pointpos(x):
    if x['TotSignal']==1:
        return x['High']+1e-4
    elif x['TotSignal']==2:
        return x['Low']-1e-4
    else:
        return np.nan

df['pointpos'] = df.apply(lambda row: pointpos(row), axis=1)

dfpl = df
fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
                open=dfpl['Open'],
                high=dfpl['High'],
                low=dfpl['Low'],
                close=dfpl['Close']),
                go.Scatter(x=dfpl.index, y=dfpl.EMA, line=dict(color='red', width=1), name="EMA")])

fig.add_scatter(x=dfpl.index, y=dfpl['pointpos'], mode="markers",
                marker=dict(size=5, color="Black"),
                name="Signal")
fig.show()

SLSignal = [0] * len(df)
SLbackcandles = 3
for row in range(SLbackcandles, len(df)):
    mi=1e10
    ma=-1e10
    if df.TotSignal[row]==1:
        for i in range(row-SLbackcandles, row+1):
            ma = max(ma,df.High[i])
        SLSignal[row]=ma
    if df.TotSignal[row]==2:
        for i in range(row-SLbackcandles, row+1):
            mi = min(mi,df.Low[i])
        SLSignal[row]=mi
        
df['SLSignal']=SLSignal

def SIGNAL():
    return dfpl.TotSignal

class MyStrat(Strategy):
    initsize = 0.02
    mysize = initsize
    def init(self):
        super().init()
        self.signal1 = self.I(SIGNAL)

    def next(self):
        super().next()
        slatr = 1.3*self.data.ATR[-1]
        TPSLRatio = 1.3

        if self.signal1==2 and len(self.trades)==0:   
            sl1 = self.data.Close[-1] - slatr
            tp1 = self.data.Close[-1] + slatr*TPSLRatio
            self.buy(sl=sl1, tp=tp1, size=self.mysize)
        
        elif self.signal1==1 and len(self.trades)==0:         
            sl1 = self.data.Close[-1] + slatr
            tp1 = self.data.Close[-1] - slatr*TPSLRatio
            self.sell(sl=sl1, tp=tp1, size=self.mysize)

bt = Backtest(dfpl, MyStrat, cash=1000, margin=1/500, commission=.00)
stat = bt.run()
print(stat)
bt.plot()