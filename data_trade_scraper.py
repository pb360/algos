import sys
sys.path.insert(0, "..")

from algos.config import params
from algos.utils import (
    init_ch_client,
    init_ccxt_client,
    async_wait_for_next_execution,
)

import argparse
import asyncio
import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Data trade scraper for different exchanges.")
    parser.add_argument("--exchange", type=str, help="The exchange to scrape data from")
    return parser.parse_args()


class TradeProcessor:
    def __init__(self, ch_client, ccxt_client, params):
        self.ch_client = ch_client
        self.ccxt_client = ccxt_client
        self.params = params
        self.exchange = params["state"]["exchange"]
        self.symbols = self.params["active_services"]["trade_collect"]["exchanges"][self.exchange]
        self.trade_db_write_delay = self.params["active_services"]["trade_collect"]["trade_db_write_delay"]
        self.trade_process_interval = self.params["active_services"]["trade_collect"]["trade_process_interval"]

        self.accumulated_trades = []

    async def fetch_and_accumulate_trades_for_symbol(self, symbol):
        """Fetch and accumulate trades for a single symbol."""
        while True:  # You might want some condition to exit this loop
            try:
                trades = await self.ccxt_client.watch_trades(symbol)
                self.accumulated_trades.extend(trades)
            except Exception as e:
                print(f"Error watching trades for {symbol}: {e}", flush=True)
                raise

    async def fetch_and_accumulate_trades(self):
        if self.exchange in ["kraken"]:  # These don't support watch_trades_for_symbols
            tasks = [self.fetch_and_accumulate_trades_for_symbol(symbol) for symbol in self.symbols]
            await asyncio.gather(*tasks)
        else:
            while True:
                try:
                    trades = await self.ccxt_client.watch_trades_for_symbols(symbols=self.symbols)
                    self.accumulated_trades.extend(trades)
                except Exception as e:
                    print(f"Critical error occurred with CCXT client: {e}", flush=True)
                    raise  # Reraise the exception to exit the script

    async def process_trade_data(self):
        ch_formatted_trades = []
        print(f"exchange: {self.exchange} had {len(self.accumulated_trades)} in the last minute", flush=True)
        for trade in self.accumulated_trades:
            if trade["id"] is None:
                trade["id"] = "NA"
            # trade = {'timestamp': datetime.datetime.utcfromtimestamp(int(trade['timestamp']/1000)),  # ###PAUL TODO: gon need to verify this
            trade = {
                "timestamp": datetime.datetime.utcfromtimestamp(
                    trade["timestamp"] / 1000
                ),  # ###PAUL TODO: gon need to verify this
                "exchange": self.exchange,
                "symbol": trade["symbol"],
                "id": trade["id"],
                "price": trade["price"],
                "amount": trade["amount"],
                "buyer_is_taker": 1 if trade["side"] == "buy" else 0,
            }

            ch_formatted_trades.append(trade)

        try:  # for a clickhouse timeout error
            self.ch_client.execute(
                "INSERT INTO algos_db.Trades VALUES ",
                ch_formatted_trades,
                types_check=True,
            )
        except Exception as e:
            print(f"Critical error: \n\n {e} \n\n", flush=True)
            raise  # Reraise the exception to exit the script

    async def process_trades_periodically(self):
        while True:
            await async_wait_for_next_execution(delay_seconds=self.trade_db_write_delay, interval=self.trade_process_interval)
            if self.accumulated_trades:  # if list isn't empty, process it
                await self.process_trade_data()
                self.accumulated_trades.clear()


async def main():
    args = parse_args()
    exchange = args.exchange
    params["state"] = {"exchange": exchange}

    api_key_names = params["active_services"]["trade_collect"]["api_keys"][exchange]

    ch_client = init_ch_client()
    ccxt_client = init_ccxt_client(exchange=params["state"]["exchange"], type="pro", api_key_names=api_key_names)

    # symbols=['BTC/USDT', 'KDA/USDT', 'ETH/USDT',  'LINK/USDT', 'ROSE/USDT', 'ICP/USDT', 'AVAX/USDT', 'SOL/USDT', 'BNB/USDT', 'DOGE/USDT', 'GRT/USDT', ]
    processor = TradeProcessor(ch_client, ccxt_client, params)

    # Run fetching and processing tasks concurrently4
    fetch_task = asyncio.create_task(processor.fetch_and_accumulate_trades())
    process_task = asyncio.create_task(processor.process_trades_periodically())

    # Wait for both tasks to complete (in this case, they won't because they run forever)
    await asyncio.gather(fetch_task, process_task)


if __name__ == "__main__":
    asyncio.run(main())
