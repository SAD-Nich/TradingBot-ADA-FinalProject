#%%
import MetaTrader5 as MT
import pandas as pd
import time
from datetime import datetime


MT.initialize()
login = 69120408
password = 'cq1ppuvf'
server = 'MetaQuotes-Demo'
MT.login(login, password, server)
account = MT.account_info()

ticker = 'USDJPY'
quantity = 0.01
positions = MT.positions_get()

def buy_order(ticker, quantity):
    request={
    "action": MT.TRADE_ACTION_DEAL,
    "symbol": ticker,
    "volume": quantity,
    "type": MT.ORDER_TYPE_BUY,
    "price": MT.symbol_info_tick("USDJPY").ask,
    "type_time": MT.ORDER_TIME_GTC,
    "type_filling": MT.ORDER_FILLING_IOC,
}
    order = MT.order_send(request)
    return order

def sell_order(ticker, quantity):
    request={
    "action": MT.TRADE_ACTION_DEAL,
    "symbol": ticker,
    "volume": quantity,
    "type": MT.ORDER_TYPE_SELL,
    "price": MT.symbol_info_tick("USDJPY").bid,
    "type_time": MT.ORDER_TIME_GTC,
    "type_filling": MT.ORDER_FILLING_IOC,
    }
    order = MT.order_send(request)

def close_order(position):
    request={
    "action": MT.TRADE_ACTION_DEAL,
    "position": position.ticket,
    "symbol": position.symbol,
    "volume": position.volume,
    "magic": 100,
    "deviation": 20,
    "type": MT.ORDER_TYPE_SELL if position.type == 0 else MT.ORDER_TYPE_BUY,
    "price": MT.symbol_info_tick(position.symbol).bid if position.type == 0 else MT.symbol_info_tick(position.symbol).ask,
    "type_time": MT.ORDER_TIME_GTC,
    "type_filling": MT.ORDER_FILLING_IOC,
    }
    order = MT.order_send(request)

def close_position():
    for position in positions:
        close_order(position)

for i in range(100):
    ohlc = pd.DataFrame(MT.copy_rates_range('USDJPY',MT.TIMEFRAME_M1,datetime(2023,12,12),datetime.now()))
    ohlc['time']=pd.to_datetime(ohlc['time'],unit='s')
    print(ohlc)

    current_close = list(ohlc[-1:]['close'])[0]
    last_close = list(ohlc[-2:]['close'])[0]
    last_high = list(ohlc[-2:]['high'])[0]
    last_low = list(ohlc[-2:]['low'])[0]

    long_condition = current_close > last_high
    short_condition = current_close < last_low
    close_long = current_close < last_close
    close_short = current_close > last_close
    no_positions = len(MT.positions_get()) == 0

    already_buy = False
    already_sell = False

    try:
        already_sell = MT.positions_get()[0]._asdict()['type']==1
        already_buy = MT.positions_get()[0]._asdict()['type']==0
    except:
        pass

    if long_condition:
        if no_positions:
            buy_order(ticker, quantity)
            print('Buy Position Placed')
        if already_sell:
            close_position()
            print('Sell Position Closed')
            time.sleep(1)
            buy_order(ticker, quantity)
            print('Buy Position Placed')
        
    if short_condition:
        if no_positions:
            sell_order(ticker,quantity)
            print('Sell Position Placed')
        if already_buy:
            close_position()
            print('Buy Position Closed')
            time.sleep(1)
            sell_order(ticker, quantity)
            print('Sell Position Placed')

    try:
        already_sell = MT.positions_get()[0]._asdict()['type']==1
        already_buy = MT.positions_get()[0]._asdict()['type']==0
    except:
        pass

    if close_long and already_buy:
        close_position()
        print('Buy Position Closed Without Entry')
    if close_short and already_sell:
        close_position()
        print('Sell Position Closed Without Entry')

    already_buy = False
    already_sell = False
    time.sleep(60)
