from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
import config,sqlite3
from fastapi.templating import Jinja2Templates
from datetime import date

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# home page
@app.get("/")
def index(request: Request):
    stock_filter = request.query_params.get('filter', False) # filter of stocks, non necessary

    # sql init
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    
    if stock_filter == 'new_closing_highs':
        cursor.execute(""" 
        select * from (
            select symbol, name, stock_id, max(close), date
            from stock_price join stock on stock.id = stock_price.stock_id
            group by stock_id
            order by symbol
        ) where date = (select max(date) from stock_price) """)
    
    elif stock_filter == 'new_closing_lows':
        cursor.execute(""" 
        select * from (
            select symbol, name, stock_id, min(close), date
            from stock_price join stock on stock.id = stock_price.stock_id
            group by stock_id
            order by symbol
        ) where date = (select max(date) from stock_price) """)

    else:
        cursor.execute("""
        SELECT id, symbol, name from stock ORDER BY symbol
        """)
    
    rows = cursor.fetchall()
    connection.commit()

    return templates.TemplateResponse("index.html",{"request":request, "stocks":rows})

# stock detail page
@app.get("/stock/{symbol}")
def stock_detail(request: Request, symbol):
    # sql init
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    # retrieve all available strategies
    cursor.execute("""
        SELECT * FROM strategy""")
    strategies = cursor.fetchall()
    
    # select id, name and symbol of a stock
    cursor.execute("""
        SELECT id, symbol, name from stock WHERE symbol = ?
    """, (symbol,))
    row = cursor.fetchone() 

    # select all available daily data of the stock
    cursor.execute(""" SELECT * FROM stock_price WHERE stock_Id=? ORDER BY date DESC""", (row['id'],))
    bars = cursor.fetchall()

    connection.commit()

    # we return the stock name/symbol + historical day prices + different available strategies
    return templates.TemplateResponse("stock_detail.html",{"request":request, "stock":row, "bars": bars, "strategies": strategies})

# what happens when we submit apply strategy
@app.post("/apply_strategy")
def apply_strategy(strategy_id: int = Form(...), stock_id: int = Form(...)):
    connection = sqlite3.connect( config.DB_FILE )
    cursor = connection.cursor()

    # we add the stock_id and the strategy_id to stock_strategy table
    cursor.execute("""
        INSERT INTO stock_strategy (stock_id, strategy_id) VALUES (?, ?)
    """, (stock_id, strategy_id))

    connection.commit()
    
    return RedirectResponse( url=f"/strategy/{strategy_id}", status_code=303)

# page with stocks that the strategy_id is applied to
@app.get("/strategy/{strategy_id}")
def strategy(request: Request, strategy_id: int):
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # retrieve strategy name to be displayed on the page
    cursor.execute(""" 
        SELECT id, name
        FROM strategy
        WHERE id = ? """, (strategy_id,))
    strategy = cursor.fetchone()


    cursor.execute("""
        SELECT symbol, name
        FROM stock JOIN stock_strategy on stock_strategy.stock_id = stock.id
        WHERE strategy_id = ? """, (strategy_id,))
    
    # all the stocks that we apply strategy to
    stocks = cursor.fetchall()

    return templates.TemplateResponse("strategy.html", {"request": request, "stocks": stocks, "strategy": strategy})