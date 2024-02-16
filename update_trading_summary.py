import sys
sys.path.insert(0, "..")

from algos.config import params
from algos.utils import (
    init_ch_client,
    wait_for_next_execution,
    update_trading_summary_table,
)

import datetime
from datetime import timedelta
import time
import pandas as pd


def main():
    ch_client = init_ch_client()

    trade_collect = params["active_services"]["trade_collect"]
    summary_process_delay = trade_collect["summary_process_delay"]
    trade_process_interval = trade_collect["trade_process_interval"]
    pairs_by_exchange = trade_collect["exchanges"]

    num_updates = -1

    while True:
        _ = wait_for_next_execution(delay_seconds=summary_process_delay, interval=trade_process_interval)

        for exchange in pairs_by_exchange.keys():
            num_updates += 1
            if num_updates % 10 == 0:
                print(
                    f"update iter #: {num_updates} ---- updates {summary_process_delay} seconds after the start of every minute",
                    flush=True,
                )

            for pair in pairs_by_exchange[exchange]:
                try:
                    print(f"    - pair: {pair} ---- exchange: {exchange}")
                    update_trading_summary_table(exchange=exchange, symbol=pair, ch_client=ch_client)
                except Exception as e:
                    print(f"highest level exception in `update_trading_summary`")
                    print(f"{e}")


if __name__ == "__main__":
    main()


print("in update_trading_summary.py somehow got to the end of the script")
