import sqlite3, config
import alpaca_trade_api as tradeapi

# SQL init
connection = sqlite3.connect('app.db')
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

# Select all stocks
cursor.execute("""SELECT id, symbol, name FROM stock""")
rows = cursor.fetchall()

symbols = []
stock_dict = {}
for row in rows:
    symbol = row['symbol']
    symbols.append(symbol)
    stock_dict[symbol] = row['id']

# Connect to API
api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.BASE_URL)

# The start date, we don't want to request all historical prices
cursor.execute("""select max(date) from stock_price""")
current_date=cursor.fetchone()[0]
start_day_bar = f"{current_date}T09:30:00-05:00"

chunk_size = 200 # max allowed chunk in Alpaca
for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i:i+chunk_size]
    barsets = api.get_barset(symbol_chunk, 'day', start=start_day_bar)

    for symbol in barsets:
        print(f"processing symbol {symbol}")
        for bar in barsets[symbol]:
            stock_id = stock_dict[symbol]
            
            #check if the price is already in the database
            count=cursor.execute("""SELECT count(*) FROM stock_price WHERE 
            stock_id = """+str(stock_id)+""" AND date = """ +str(bar.t.date()) )
            if count == 0:
                cursor.execute("""
                INSERT INTO stock_price (stock_id, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (stock_id, bar.t.date(), bar.o, bar.h, bar.l, bar.c, bar.v))
                print("done")

connection.commit()