#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-
# imports
#
#

"""
This script creates a websocket connection to binance and listens and records all trades for relevant tickers
on or around 2/20/2022 the repo was migrated from algo2 --> algos allowing for easier data collection
the data for 'tickers_tracked': ['ADAUSDT', 'ADABTC', 'BNBUSDT', 'BNBBTC', 'BTCUSDT', 'BTCBTC', 'DOGEUSDT', 'ETHUSDT',
 'ETHBTC', 'LINKUSDT', 'LINKBTC', 'LTCUSDT', 'LTCBTC', 'XLMUSDT', 'XRPUSDT', 'XRPBTC', ] goes back much earlier


 other tickers' data collection starts after
"""

# ### imports
#
#
import os
import time
# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

import asyncio
import nest_asyncio
import pandas as pd
import sys  # ###PAUL_del_later_if_not_needed
import threading
import traceback
from twisted.internet import task, reactor

# ### local imports
#
#
import config
from utils import send_email, get_data_file_path, convert_date_format

# needed to let the package to see itself for interior self imports
sys.path.append('/mnt/algos/ext_packages/kucoin_python_sdk')
from kucoin.client import Market
from kucoin.client import WsToken
from kucoin.ws_client import KucoinWsClient


# ### variable definitions
#
#
START_TIME = time.time()

# ### kucoin market data client # ###PAUL test if the below line is needed
client = Market(url='https://api.kucoin.com')

# configs
params = config.params

exchange = 'kucoin'  # exchange we are collecting data for
params['exchange'] = exchange

lock = threading.Lock()  # locks other threads from writing to daily trade file

# global variables used in various functions
this_scripts_process_ID = os.getpid()
last_msg_time = time.time() + 1.5
consecutive_error_messages = 0
message_counter = 0  # for debug only


# parameters about investment universe
coins_tracked = params['universe'][exchange]['coins_tracked']
tickers_tracked = params['universe'][exchange]['tickers_tracked']
tick_collection_list = params['universe'][exchange]['tick_collection_list']


def lock_thread_append_to_file(file_path, new_line):
    """locks file so no other thread from this script may write to it

    ###PAUL TODO: make a decorator so that BTC_USDT isnt fighting ETH_BTC for a lock

    inputs:
        file_path (str): string from root directory to file
        new_line (str): to append to file

    out:
        none
    """
    global lock

    lock.acquire()  # thread must aquire lock to write to file
    # in this section, only one thread can be present at a time.
    with open(file_path, "a") as f:
        f.write(new_line)
    os.chmod(file_path, 0o777)
    lock.release()


def make_new_trade_observation_for_trade_file(trade_info):
    # columns = 'msg_time,ticker,trade_id,price,quantity,buy_order_id,sell_order_id,trade_time,buyer_is_maker\n'

    side = trade_info['side']
    if side == 'buy':
        buyer_is_maker = True
        buyer_order_id = trade_info['takerOrderId']
        seller_order_id = trade_info['makerOrderId']
    elif side == 'sell':
        buyer_is_maker = False
        buyer_order_id = trade_info['makerOrderId']
        seller_order_id = trade_info['takerOrderId']
    else:
        raise ValueError

    new_line = str(time.time()) + ',' \
               + str(trade_info['symbol']) + ',' \
               + str(trade_info['tradeId']) + ',' \
               + str(trade_info['price']) + ',' \
               + str(trade_info['size']) + ',' \
               + str(buyer_order_id) + ',' \
               + str(seller_order_id) + ',' \
               + str(float(trade_info['time']) / 1000 / 1000 / 1000) + ',' \
               + str(buyer_is_maker) + '\n'
    return new_line


def check_if_file_make_dirs_then_write(file_path, new_line, header=None, thread_lock=False):
    # check that the file exists for the correct time period
    if os.path.isfile(file_path):
        if thread_lock == True:
            lock_thread_append_to_file(file_path, new_line)
        if thread_lock == False:
            # write trade to historical file... no lock as this script only appends to these files
            with open(file_path, "a") as f:
                f.write(new_line)
            os.chmod(file_path, 0o777)

    else:  # file does not exist
        # check if directory heading to file exists, if not make all required on the way
        fp_dirname = os.path.dirname(file_path)
        if os.path.isdir(fp_dirname) == False:
            os.makedirs(fp_dirname)

        # write the new line, and header if requestd
        with open(file_path, "a") as f:
            if header is not None:
                f.write(header)
            f.write(new_line)
        os.chmod(file_path, 0o777)


async def process_message(msg):
    # # #######   ---------------------------------------------------------------- START: debug
    # # #######   ---------------------------------------------------------------- START: debug
    # global message_counter
    # message_counter += 1
    #
    # if message_counter > 10:       # once enough messages force an error
    #     msg['data']['e'] = 'error'
    # # #######   ---------------------------------------------------------------- END: debug
    # # #######   ---------------------------------------------------------------- END: debug

    global conn_key
    global exchange
    global last_msg_time
    global this_scripts_process_ID
    global consecutive_error_messages


    # reset last message time for heartbeat check... if too long script assumes problem and restarts
    last_msg_time = time.time()
    print(msg, flush=True)

    topic = msg['topic']
    trade_info = msg['data']

    # print the current message
    # print('kucoin' + str(topic) + '  process ID: ' + str(this_scripts_process_ID), flush=True)

    # ###PAUL_todo  TODO add to non-existant logger
    if 'trade' not in msg['subject']:
        if consecutive_error_messages > 10:
            consecutive_error_messages += 1
        else:
            subject = "BINANCE DATA SCRAPE: Consecutive Error Messages from Websocket"
            message = "just a notification, no action needed"
            send_email(subject, message)

    # if normal trade message received process it
    else:
        consecutive_error_messages = 0  # since its a good message, reset the error counter

        # get trade info from message
        ticker = trade_info['symbol']
        new_line = make_new_trade_observation_for_trade_file(trade_info)

        # ### write to live data file
        live_data_file_path = get_data_file_path(data_type='trade', ticker=ticker, date='live', exchange=exchange)

        check_if_file_make_dirs_then_write(file_path=live_data_file_path, new_line=new_line, thread_lock=True)

        # ### WRITE TO HISTORICAL DATA FILES
        trade_info_epoch_time = (float(trade_info['time']) / 1000 / 1000 / 1000)
        date_tuple = convert_date_format(trade_info_epoch_time, 'tuple_to_day')
        daily_trade_fp = get_data_file_path('trade', ticker, date=date_tuple, exchange=exchange)
        header = 'msg_time,ticker,trade_id,price,quantity,buy_order_id,sell_order_id,trade_time,buyer_is_maker\n'

        check_if_file_make_dirs_then_write(file_path=daily_trade_fp, new_line=new_line, header=header)

        # print('processed one message', flush=True)

    return None


# iter_count_live_file_trim = 0   # ###DEBUG used to be sure function spits an error at some point
async def trim_live_files(params=params):
    """removes data older than params['constants']['secs_of_trades_to_keep_live'] from live data files

    ###PAUL TODO make so one thread locks and handles ONE file... low priority
    """
    # # #######   ---------------------------------------------------------------- START: debug
    # # #######   ---------------------------------------------------------------- START: debug
    # global iter_count_live_file_trim
    # iter_count_live_file_trim += 1
    # print('iter #: ',  str(iter_count_live_file_trim), ' of live data purge', flush=True)
    #
    # if iter_count_live_file_trim > 10:
    #     print('hur-dee-dur... i stopped \n'*10, flush=True)
    #     raise ValueError
    # # #######   ---------------------------------------------------------------- END: debug
    # # #######   ---------------------------------------------------------------- END: debug

    # variable definitions
    global exchange
    global tickers_tracked

    trade_col_names = params['data_format'][exchange]['trade_col_name_list']

    for ticker in tickers_tracked:
        lock.acquire()
        live_fp = get_data_file_path(data_type='trade', ticker=ticker, date='live', exchange=exchange)

        try:
            recent_trades = pd.read_csv(live_fp, names=trade_col_names, index_col=False)

            # only keep recent trades within cutoff time threshold
            subtract_time = params['constants']['secs_of_trades_to_keep_live']
            live_trade_cutoff_time = time.time() - subtract_time
            recent_trades = recent_trades[recent_trades['msg_time'] > live_trade_cutoff_time]

            # re-write live trade file
            recent_trades.to_csv(live_fp, header=False, index=False)

        # happens auto for new tickers
        except FileNotFoundError:
            print('debug 1: FileNotFoundError: ' + str(live_fp) , flush=True)
            pass
        except TypeError as e:
            print('we have a problem \n' * 10, flush=True)
            print('msg_time type:  ', type(recent_trades['msg_time']), flush=True)

            send_email(subject='BINANCE DATA SCRAPE: error in trim live files',
                       message='ctrl+shft+f "trim_live_files in data_scrape_v3 \n error below \n ' + str(e) )

        lock.release()

    pass


def notify_of_process_start():
    global this_scripts_process_ID
    now_time_string = str(time.gmtime(time.time()))

    subject = 'DATA SCRAPER STARTED: BINANCE'
    message = 'Process ID: ' + str(this_scripts_process_ID) + '\n' + \
              'Start Time: ' + now_time_string

    send_email(subject, message)


# websocket connection
async def main():
    notify_of_process_start()

    # is public
    client = WsToken()

    ws_client = await KucoinWsClient.create(None, client, process_message, private=False)

    # documentation showing how to format request ---- https://docs.kucoin.com/#match-execution-data
    subscribe_string = '/market/match:'
    for tick in tick_collection_list:
        subscribe_string = subscribe_string + tick + ','
    subscribe_string = subscribe_string[:-1]

    await ws_client.subscribe(subscribe_string)
    while True:
        await trim_live_files(params=params)
        await asyncio.sleep(60, loop=loop)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
