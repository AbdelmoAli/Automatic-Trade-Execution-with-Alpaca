import sqlite3
import config

# empties the stock_strategy 

connection = sqlite3.connect( config.DB_FILE )
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""DELETE FROM stock_strategy""")

connection.commit()