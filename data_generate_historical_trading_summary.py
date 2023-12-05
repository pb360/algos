"""gets data from eaors trades database
don't run without verifying carefully, messed with some underlying functionality since building this
"""
import sys

sys.path.insert(0, '..')  # for local imports from the top directory

from algos.utils import (convert_date_format,
                         get_trades_data,
                         convert_trades_df_to_trading_summary,
                         fill_trading_summary_interpolating_missing_minutes,
                         push_trading_summary_to_clickhouse, )

import datetime
import pandas as pd


def query_trades_each_day_make_trading_summary_push_to_clickhouse(exchange,
                                                                  start_date,
                                                                  end_date,
                                                                  pairs_list,
                                                                  pair=None,
                                                                  backup_pair=None,
                                                                  ):
    """
    input:
    pairs_list [(pair, backup_pair), ...] ---- or use one pair and backup_pair
    """

    if type(start_date) != datetime.datetime:
        convert_date_format(start_date, 'datetime')
    if type(end_date) != datetime.datetime:
        convert_date_format(end_date, 'datetime')

    date_range_arr = pd.date_range(start=start_date, end=end_date, freq='D')

    missing_dates_filled = []
    failed_dates = []

    if pair != None:
        pairs_list = [(pair, backup_pair)]

    for pair, backup_pair in pairs_list:
        for i in range(date_range_arr.shape[0] - 1):
            iter_start_date = date_range_arr[i]
            iter_end_date = date_range_arr[i + 1]
            if i % 5 == 0:
                print(f"iter {i} ---- {pair} for ---- {iter_start_date} --> iter_end_date: {iter_end_date}")

            try:
                trades = get_trades_data(exchange=exchange,
                                         symbol=pair,
                                         start_date=iter_start_date,
                                         end_date=iter_end_date,
                                         source='EAORS')

                if type(trades) == int or trades.shape[0] < 100:
                    if trades == 0:
                        print(f"    - no trades for iter_start_date: {iter_start_date} --> iter_end_date: "
                              f"{iter_end_date}")

                    trades = get_trades_data(exchange=exchange,
                                             symbol=backup_pair,
                                             start_date=iter_start_date,
                                             end_date=iter_end_date,
                                             source='EAORS')

                    if type(trades) == int or trades.shape[0] < 100:
                        raise ValueError

                    missing_dates_filled.append((iter_start_date, iter_end_date))

                trading_summary = convert_trades_df_to_trading_summary(trades, exchange_format='EAORS')
                trading_summary = fill_trading_summary_interpolating_missing_minutes(trading_summary)

                push_trading_summary_to_clickhouse(trading_summary, exchange, pair)

                if trading_summary.shape[0] < 1440:
                    import pdb
                    pdb.set_trace()

            except:
                print(f"    - failed on {iter_start_date} --> iter_end_date: {iter_end_date}")
                failed_dates.append((iter_start_date, iter_end_date))

    return failed_dates


if __name__ == "__main__":
    # ### TRADES --> TRADING_SUMMARY (fill with BTC-USDT trading summary for periods where TUSD data wasn't available)
    #
    #
    exchange = 'binance'
    # pair = f"BTC-USDT"
    # backup_pair = f"BTC-USDT"
    pairs_list = [('BTC-USDT', 'BTC-USDT'), ('BTC-TUSD', 'BTC-USDT'),
                  ('ETH-USDT', 'ETH-USDT'), ('ETH-TUSD', 'ETH-USDT'), ]
    start_date = datetime.datetime(2023, 7, 1)
    end_date = datetime.datetime(2023, 8, 14)

    failed_dates = query_trades_each_day_make_trading_summary_push_to_clickhouse(exchange=exchange,
                                                                                 pairs_list=pairs_list,
                                                                                 start_date=start_date,
                                                                                 end_date=end_date,
                                                                                 pair=None,
                                                                                 backup_pair=None,
                                                                                 )
