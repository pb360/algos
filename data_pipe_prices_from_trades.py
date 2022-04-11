#!/home/paul/miniconda3/envs/crypto_data_scrape/bin/python3 -u
# -*- coding: utf-8 -*-
# ### imports
#
#
import os
import time
# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()
import pandas as pd
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


def check_if_head_dir_if_no_make_path(fp):
    """if /path/to/ doesn't exist in /whole/ for fp='whole/path/to/file.txt' it makes /path/ and /to/ folders
     accordingly so that 'file.txt' can be written as the directory path now exists
    """

    fp_dirname = os.path.dirname(fp)
    if os.path.isdir(fp_dirname) == False:
        os.makedirs(fp_dirname)

    return None


def add_prices_from_live_trade_data(ticker, exchange):
    """checkes the live trade file and will append trades to days file
    """

    # get trades
    # try:
    # print(ticker)

    # import pdb; pdb.set_trace()

    # if exchange == 'kucoin':
        # import pdb;
        # pdb.set_trace()

    trades = get_live_trades_data(ticker, exchange)



    # if there are no trades for ticker's live file skip for this round (else it errors)
    if trades.shape[0] == 0:
        return None
    # except:
    #     print('\n \n \n errored here once ---- could not figure ---- try except here too ###PAUL_debug later \n \n \n',
    #           flush=True)
    #     return None

    prices = convert_trades_df_to_prices(trades)
    prices = prices.iloc[:-1]  # remove last second as this second could still be happening

    now = time.time()  # must use timestamp as requesting date="live"
    price_fp = get_data_file_path(data_type='price', ticker=ticker, date=now, exchange=exchange)

    if os.path.isfile(price_fp):
        last_line = get_last_line_of_file(price_fp)



        latest_time_price_written = last_line[:19]  # date will always be 19 characters...

        # indicates no trades since start of day. header written, but no prices. else should be "YYYY-MM..."
        if latest_time_price_written == 'msg_time,buyer_is_m':
            prices.to_csv(price_fp, header=None, mode='a')
        # a price is included in the file, get all prices after
        else:
            latest_time_price_written = pd.to_datetime(latest_time_price_written)
            prices = prices[prices.index > latest_time_price_written]
            prices.to_csv(price_fp, header=None, mode='a')

    else:  # price_fp not an existing file
        print('\n \n ---- making file to start the day --> fp =  ' + str(price_fp) + ' \n', flush=True)

        # ### first handle the rest of the data from yesterday's trades
        #
        #
        # get datetime variable that is exactly midnight
        dt = datetime.datetime.fromtimestamp(now)
        dt = dt - datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)


        yesterday_price_fp = get_data_file_path(data_type='price',
                                                ticker=ticker,
                                                date=now - 24 * 60 * 60,
                                                exchange=exchange)

        yesterdays_prices = prices[prices.index < dt]
        check_if_head_dir_if_no_make_path(yesterday_price_fp)

        try:
            latest_time_price_written = get_last_line_of_file(yesterday_price_fp)[:19]   # isolate 19 char date YYYY-MM...

            # yesterday could have no trades.. if this happens then we still make file, but dont have early cutoff
            if latest_time_price_written != 'msg_time,buyer_is_m':
                latest_time_price_written = pd.to_datetime(latest_time_price_written)
                yesterdays_prices = yesterdays_prices[yesterdays_prices.index > latest_time_price_written]

            yesterdays_prices.to_csv(yesterday_price_fp, header=None, mode='a')

        except FileNotFoundError:
            yesterdays_prices.to_csv(yesterday_price_fp)

        # create file and with first observed prices today after we finished updating yesterday's prices

        # cutoff prices so they start at midnight and
        prices = prices[prices.index > dt]
        check_if_head_dir_if_no_make_path(price_fp)  # make any dirs if needed (new tickers, etc...)
        prices.to_csv(price_fp)
    return None


def add_prices_to_all_tickers(exchange):
    # print(exchange)
    ST = time.perf_counter()

    # investment universe from params
    tickers_tracked = params['universe'][exchange]['tickers_tracked']



    # import pdb; pdb.set_trace()




    for ticker in tickers_tracked:
        add_prices_from_live_trade_data(ticker, exchange)

    ET = time.perf_counter()
    TT = ET - ST

    print('price_files_updated for ---- ' + str(exchange) + ' ---- iter time: ' + str(TT), flush=True)


def add_prices_for_all_exchanges():
    ST = time.perf_counter()

    global params
    exchanges = params['systemd_control']['active_services']['prices'].keys()

    # import pdb; pdb.set_trace()

    for exchange in exchanges:
        add_prices_to_all_tickers(exchange)

    ET = time.perf_counter()
    TT = ET - ST

    print('\n' + 'price updates for all exchanges ---- took: ' + str(TT) + '\n', flush=True)

    return None


def main(params=params):
    price_add_interval = params['constants']['make_prices_from_trades_interval']
    add_prices_task = task.LoopingCall(f=add_prices_for_all_exchanges)
    add_prices_task.start(price_add_interval)
    reactor.run()


main()
