#!/home/paul/miniconda3/envs/binance/bin/python3 -u
# -*- coding: utf-8 -*-
# ### imports
#
#
import os
import time
# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

import datetime
import pandas as pd
import sys
from twisted.internet import task, reactor

# local imports
#
#
import config
from utils import *  # import utils first for time zone considerations

# ### variable declarations
#
#
START_TIME = time.time()
params = config.params


# ###PAUL_temp ---- should loop over this eventually
# ###PAUL_temp ---- should loop over this eventually
# ###PAUL_temp ---- should loop over this eventually
exchange = 'binance_foreign'
# ###PAUL_temp ---- should loop over this eventually
# ###PAUL_temp ---- should loop over this eventually
# ###PAUL_temp ---- should loop over this eventually


# investment universe from params
tickers_tracked = params['universe'][exchange]['tickers_tracked']


def add_prices_from_live_trade_data(ticker, exchange):
    """checkes the live trade file and will append trades to days file

    currently some trades from the day before will end up in the next days file
    there will be some overlap such that the last trades are in the next days file
    """

    # get trades
    try:
        trades = get_live_trades_data(ticker, exchange)

        # if there are no trades for ticker's live file skip for this round (else it errors)
        if trades.shape[0] == 0:
            return None
    except:
        print('Errored here once for some reason I could not figure out so have try except case here too...', flush=True)
        sys.stdout.flush()
        return None

    prices = convert_trades_df_to_prices(trades)
    prices = prices.iloc[:-1]   # remove last second as this second could still be happening

    now = time.time()
    price_fp = get_data_file_path(data_type='price', ticker=ticker, date=now)

    try:
        last_line = get_last_line_of_file(price_fp)
        latest_time_price_written = last_line[:19]  # date will always be 19 characters...

        # indicates no trades since start of day. header written, but no prices. else should be "YYYY-MM..."
        if latest_time_price_written == 'msg_time,buyer_is_m':
            prices.to_csv(price_fp, header=None, mode='a')
        else:
            latest_time_price_written = pd.to_datetime(latest_time_price_written)
            prices = prices[prices.index > latest_time_price_written]
            prices.to_csv(price_fp, header=None, mode='a')

    # if no price file has been written for this ticker yet today
    except FileNotFoundError:

        # ### first handle the rest of the data from yesterday's trades
        #
        #
        yesterday_price_fp = get_data_file_path(data_type='price', ticker=ticker, date=now-24*60*60)

        # get datetime variable that is exactly midnight
        dt = datetime.datetime.fromtimestamp(now)
        dt = dt - datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
        # if the scraper was not running yesterday. this file also does not exist..
        try:
            # get last time of of price from yesterday
            last_line = get_last_line_of_file(yesterday_price_fp)
            # date will always be 19 characters...  if ever issue see how i handled it in above try portion
            latest_time_price_written = pd.to_datetime(last_line[:19])

            yesterdays_prices = prices[prices.index > latest_time_price_written]
            yesterdays_prices = yesterdays_prices[yesterdays_prices.index < dt]

        # if yesterday prices don't exist, just pass on writing anything
        except FileNotFoundError:
            pass
        # create file and with first observed prices today
        prices = prices[prices.index > dt]
        prices.to_csv(price_fp)


def add_prices_to_all_tickers():
    ST = time.perf_counter()

    for ticker in tickers_tracked:
        add_prices_from_live_trade_data(ticker)

    ET = time.perf_counter()
    TT = ET - ST

    print('price_files_updated ---- iter time: ' + str(TT))
    sys.stdout.flush()


def main(params=params):
    price_add_interval = params['constants']['make_prices_from_trades_interval']
    add_prices_task = task.LoopingCall(f=add_prices_to_all_tickers)
    add_prices_task.start(price_add_interval)
    reactor.run()


main()
