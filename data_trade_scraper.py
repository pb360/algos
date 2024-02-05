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


class TradeProcessor:

    def __init__(self, symbols, ch_client, ccxt_client):
        self.symbols = symbols
        self.ch_client = ch_client
        self.ccxt_client = ccxt_client
        self.accumulated_trades = []
        self.processing_interval = 10  # TODO: put in configs 
        self.exchange = 'binance_us'
    
    async def fetch_and_accumulate_trades(self):
        while True:
            try:
                trades = await self.ccxt_client.watch_trades_for_symbols(symbols=self.symbols)
                self.accumulated_trades.extend(trades)
            except Exception as e:
                print(f"Critical error occurred with CCXT client: {e}", flush=True)
                raise   # Reraise the exception to exit the script
            
    async def process_trade_data(self):
        
        ch_formatted_trades = []
        print(len(self.accumulated_trades), flush=True) 
        for trade in self.accumulated_trades: 
            # trade = {'timestamp': datetime.datetime.utcfromtimestamp(int(trade['timestamp']/1000)),  # ###PAUL TODO: gon need to verify this 
            trade = {'timestamp': datetime.datetime.utcfromtimestamp(trade['timestamp']/1000),  # ###PAUL TODO: gon need to verify this 
                    'exchange': self.exchange,
                    'symbol': trade['symbol'],
                    'id': trade['id'], 
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'buyer_is_taker': 1 if trade['side'] == 'buy' else 0 
                    }
            ch_formatted_trades.append(trade)

        try: # for a clickhouse timeout error 
            self.ch_client.execute('INSERT INTO algos_db.Trades VALUES ',
                            ch_formatted_trades, 
                            types_check=True, )
        except Exception as e:
            print(f"Critical error occurred: {e}", flush=True)
            raise   # Reraise the exception to exit the script
    
    async def process_trades_periodically(self):
        while True:
            if self.accumulated_trades:
                await self.process_trade_data()
                self.accumulated_trades.clear()
            await asyncio.sleep(self.processing_interval)


async def main():

    ch_client = init_ch_client()
    ccxt_client = binanceus({
        'apiKey': get_secret('BINANCE_DATA_1_PUBLIC'),
        'secret': get_secret('BINANCE_DATA_1_PRIVATE'),
    })

    symbols=['BTC/USDT', 'KDA/USDT', 'ETH/USDT',  'LINK/USDT', 'ROSE/USDT', 'ICP/USDT', 'AVAX/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'GRT/USDT', ]
    
    processor = TradeProcessor(symbols, ch_client, ccxt_client)
    
    # Run fetching and processing tasks concurrently
    fetch_task = asyncio.create_task(processor.fetch_and_accumulate_trades())
    process_task = asyncio.create_task(processor.process_trades_periodically())
    
    # Wait for both tasks to complete (in this case, they won't because they run forever)
    await asyncio.gather(fetch_task, process_task)

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