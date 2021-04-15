import sqlite3
import config
import alpaca_trade_api as tradeapi
import datetime as date
from datetime import date
import json

# TODO: add notification by mail when something is bought

#SQL initialisation
connection = sqlite3.connect( config.DB_FILE )
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

# We retrieve the id of the breakout strategy
cursor.execute("""
    SELECT id from strategy where name = 'opening_range_breakout'
""")
strategy_id = cursor.fetchone()['id']

# We retrieve all the stocks that the user wants breakout applied to.
cursor.execute("""
    SELECT symbol, name FROM stock
    JOIN stock_strategy ON stock.id=stock_strategy.stock_id
    WHERE stock_strategy.strategy_id = ?
""", (strategy_id,) )
stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]

# We define the starting and ending time 
cursor.execute("""select max(date) from stock_price""")
current_date=cursor.fetchone()[0]
start_minute_bar = f"{current_date}T09:30:00-05:00"
end_minute_bar = f"{current_date}T09:45:00-05:00"

# Connect to Alpaca API
api = tradeapi.REST( config.API_KEY, config.SECRET_KEY, base_url=config.BASE_URL )

# Retrieve all the orders of the given day
orders = api.list_orders(status='all',after=start_minute_bar)
existing_orders = [order.symbol for order in orders]

messages=[]
#Apply the strategy to all symbols
for symbol in symbols:
    
    minute_bars = api.get_barset(symbol,'minute', limit=1000, start=start_minute_bar, end=end_minute_bar)

    # defining the variables
    opening_range_low = float('inf')
    opening_range_high = 0
    for bar in minute_bars[symbol]:
        opening_range_low=min(opening_range_low,bar.l)
        opening_range_high=max(opening_range_high,bar.h)
    opening_range = opening_range_high - opening_range_low

    # Since the free Alpaca tier is sometimes incomplete, we disregard the stocks that dont have enough data (no data between 9:30 and 45 for example)
    if opening_range==-float("inf"): 
        print(f'not enough data on {symbol}.')
        symbols.remove(symbol)
        continue

    elif opening_range<0.02: #Alpace doesn't allow to take profit with less than 0.01 per share
        print(f'not enough momentum on {symbol}.')
        symbols.remove(symbol)
        continue
    
    # We retrieve all data that starts after 9:45
    minute_bars = api.get_barset(symbol,'minute', limit=1000, start=end_minute_bar)
    for bar in minute_bars[symbol]:
        
        # if the price is greater than the opening_range and it has not been purchased on the same day, we 
        # submit a bracket order
        if bar.c>opening_range_high and symbol not in existing_orders:
            limit_price = int(bar.c)
            
            messages.append(f"placing buy order for {symbol} at {limit_price}, closed above {opening_range_high} at{bar.t} ")
            print(f"placing buy order for {symbol} at {limit_price}, closed above {opening_range_high} at{bar.t} ")

            api.submit_order(
                symbol=symbol,
                qty=10,
                side='buy',
                type='limit',
                time_in_force='gtc',
                order_class='bracket',
                limit_price=limit_price,
                take_profit=dict(
                    limit_price=limit_price+opening_range
                ),
                stop_loss=dict(
                    stop_price=limit_price-opening_range,
                )
            )
            break # we only allow one buy per day 