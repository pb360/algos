import os
import time
import sys

# ### i like to make these things happen first despite convention 
os.environ['TZ'] = 'UTC'
time.tzset()
# sys.path.insert(0, '/home/paul/src')
sys.path.insert(0, '..')

from algos.utils import init_ch_client, get_secret
from ccxt.pro import binanceus
import asyncio
import dotenv
import ccxt
from clickhouse_driver import Client as CH_Client
from collections import defaultdict
import datetime

ch_client = init_ch_client()


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
                 'buyer_is_taker': 1 if trade['side'] == 'buy' else 0 
                }
        ch_formatted_trades.append(trade)

    ch_client.execute('INSERT INTO algos_db.Trades VALUES ',
                      ch_formatted_trades, 
                      types_check=True,
                     )
    
async def process_trades_periodically(processing_interval, ch_client):
    while True:
        if accumulated_trades:  # Check if there are trades to process
            await process_trade_data(accumulated_trades, ch_client, exchange='binance_us')  # ###PAUL TODO: don't specify exchange for collection here. 
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
        # ###PAUL TODO, this list should be in config, likely needs to go under machine specific, don't want multiple machines running collection (yet)
        # TODO: outline reconcialiation to make sure that 
        trades = await ccxt_binanceus.watch_trades_for_symbols(symbols=['BTC/USDT', 'KDA/USDT', 'ETH/USDT',  'LINK/USDT', 'ROSE/USDT', 'ICP/USDT', 'AVAX/USDT',
                                                                        'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'GRT/USDT', ])
        accumulated_trades.extend(trades)

if __name__ == "__main__":
    asyncio.run(main())

    # # ### NOTE: to run in a notebook instead of using the __main__ convention the below structure is needed (at the top level after definitions) 
    # # ##
    # # #
    # # List to store accumulated trades
    # accumulated_trades = []

    # # Start trade collection tasks for each exchange
    # collection_tasks = []
    # for exchange, symbols in exchange_symbols.items():
    #     # Create an exchange client instance for each exchange
    #     exchange_client = create_exchange_client(exchange)  # Replace with actual client creation logic
    #     task = asyncio.create_task(collect_trades(exchange_client, exchange, symbols, accumulated_trades))
    #     collection_tasks.append(task)

    # # Start processing task
    # processing_interval = 10  # Process trades every 10 seconds
    # processing_task = asyncio.create_task(process_trades_periodically(processing_interval, ch_client, accumulated_trades))

    # # Run the event loop
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(asyncio.gather(*collection_tasks, processing_task))