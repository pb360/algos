import os
import time
import sys

# ### i like to make these things happen first despite convention 
os.environ['TZ'] = 'UTC'
time.tzset()
# sys.path.insert(0, '/home/paul/src')

print(f"this isn't printing \n" * 10)
print(os.getcwd() )
print(f"\n" * 10)


sys.path.insert(0, '..')

from algos.utils import get_secret
from ccxt.pro import binanceus
import asyncio
import dotenv
import ccxt
from clickhouse_driver import Client as CH_Client
from collections import defaultdict
import datetime

ch_client = CH_Client(host=get_secret('CH_ALGOS_DB_HOST'),
                      port=int(get_secret('CH_ALGOS_DB_PORT')),
                      user=get_secret('CH_ALGOS_DB_USER'),
                      password=get_secret('CH_ALGOS_DB_PASSWORD'), 
                      database=get_secret('CH_ALGOS_DB_DATABASE'))


# Connect to Binance
ccxt_binanceus = binanceus({
    'apiKey': get_secret('BINANCE_DATA_1_PUBLIC'),
    'secret': get_secret('BINANCE_DATA_1_PRIVATE'),
})

# List to store accumulated trades
accumulated_trades = []
processing_interval = 10  # Process trades every 10 seconds

async def process_trade_data(trades, ch_client, exchange):
    
    ch_formatted_trades = []
    print(len(trades)) 
    for trade in trades: 
        # trade = {'timestamp': datetime.datetime.utcfromtimestamp(int(trade['timestamp']/1000)),  # ###PAUL TODO: gon need to verify this 
        trade = {'timestamp': datetime.datetime.utcfromtimestamp(trade['timestamp']/1000),  # ###PAUL TODO: gon need to verify this 
                 'exchange': exchange,
                 'symbol': trade['symbol'],
                 'id': trade['id'], 
                 'price': trade['price'],
                 'amount': trade['amount'],
                 'side': 1 if trade['side'] == 'buy' else 0 
                }
        ch_formatted_trades.append(trade)

    ch_client.execute('INSERT INTO algos_db.Trades VALUES ',
                      ch_formatted_trades, 
                      types_check=True,
                     )
    
async def process_trades_periodically(processing_interval, ch_client):
    while True:
        if accumulated_trades:  # Check if there are trades to process
            await process_trade_data(accumulated_trades, ch_client, exchange='binance')
            accumulated_trades.clear()  # Clear the list after processing
        await asyncio.sleep(processing_interval)

# # List to store accumulated trades
# accumulated_trades = []

# # Start processing task
# processing_interval = 10  # Process trades every 10 seconds
# processing_task = asyncio.create_task(process_trades_periodically(processing_interval, ch_client))

# # Main loop to collect trades indefinitely
# while True:
#     trades = await ccxt_binanceus.watch_trades_for_symbols(symbols=['BTC/USDT', 'KDA/USDT', 'ETH/USDT', 'LINK/USDT', 'ROSE/USDT'] )
#     accumulated_trades.extend(trades)


async def main():
    processing_task = asyncio.create_task(process_trades_periodically(processing_interval, ch_client))
    while True:
        trades = await ccxt_binanceus.watch_trades_for_symbols(symbols=['BTC/USDT', 'KDA/USDT', 'ETH/USDT', 'LINK/USDT', 'ROSE/USDT'])
        accumulated_trades.extend(trades)

if __name__ == "__main__":
    asyncio.run(main())