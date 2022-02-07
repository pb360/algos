#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-
# imports
#
#

"""
This script creates a websocket connection to binance and listens and records all trades for relevant tickers
"""
from data import config
from utils import check_if_file_in_directory, send_email, get_data_file_path, convert_date_format


import os
import pandas as pd
import sys
import signal
import subprocess
import threading
import traceback
import time
from twisted.internet import task, reactor


# local imports
sys.path.append('/Users/paul/Documents/Monkey/algo2')
sys.path.append('/Users/paul/Documents/Monkey/algo2/sams_binance_api')
from sams_binance_api.binance.client import Client
from sams_binance_api.binance.websockets import BinanceSocketManager


# ### variable definitions
#
#
START_TIME = time.time()
params = config.params
lock = threading.Lock() # locks other threads from writing to daily trade file

# global variables used in various functions
this_scripts_process_ID = os.getpid()
conn_key = 0 ### used to close binance connections... is int, need one to start so zero
last_msg_time = time.time() + 1.5
consecutive_error_messages = 0
message_counter = 0   # for debug only


# directories
repo_dir = params['dirs']['repo_dir']
data_dir = params['dirs']['data_dir']
book_data_dir  = params['dirs']['book_data_dir']
live_trade_data_dir  = params['dirs']['live_trade_data_dir']
trade_data_dir = params['dirs']['trade_data_dir']

# api keys
api_key = params['keys']['data_key_1']
secret_key = params['keys']['data_secret_1']

# parameters about investment universe
coins_tracked = params['universe']['coins_tracked']
tick_collection_list = params['universe']['tick_collection_list']

# binance client
client = Client(
    api_key = api_key,
    api_secret = secret_key,
    requests_params = None,
    tld='us'  # ###PAUL this is for the country... need to set that for sure.... careful on other exchanges
)

# initiate client instance
bm = BinanceSocketManager(client)


def lock_thread_append_to_file(file_path, new_line):
    """locks file so no other thread from this script may write to it

    ###PAUL TODO: make a decorator so that BTC_USDT isnt fighting ETH_BTC for a lock

    inputs:
        file_path (str): string from root directory to file
        new_line (str): to append to file

    out:
        none
    """
    lock.acquire() # thread must aquire lock to write to file
    # in this section, only one thread can be present at a time.
    with open(file_path, "a") as f:
        f.write(new_line)
    os.chmod(file_path, 0o777)
    lock.release()


def rename_temp_to_live_file(temp_file_path, live_file_path):
    """lock thread so live file may be deleted, and temp file renamed to live file
    ###PAUL this is an idea if speed becomes a problem, NOT USED CURRENTLY
    """
    lock.acquire()
    os.remove(live_file_path)
    os.rename(temp_file_path, live_file_path)
    lock.release()


def make_new_trade_observation_for_trade_file(trade_info):
    new_line = str(trade_info['E'] / 1000) + ',' \
               + str(trade_info['s']) + ',' \
               + str(trade_info['t']) + ',' \
               + str(trade_info['p']) + ',' \
               + str(trade_info['q']) + ',' \
               + str(trade_info['b']) + ',' \
               + str(trade_info['a']) + ',' \
               + str(trade_info['T'] / 1000) + ',' \
               + str(trade_info['m']) + '\n'
    return new_line

# ###PAUL delete this if uncommenting doesn't break anything in systemd job
# def make_new_trade_observation_for_df(trade_info):
#     """NOT USED left here as it provides lavels for what each of the message parameters is in the function above
#     """
#
#     new_line_dict = {'msg_time':        trade_info['E'] / 1000, # times come in microseconds
#                      'ticker':          trade_info['s'],
#                      'trade_id':        trade_info['t'],
#                      'price':           trade_info['p'],
#                      'quantity':        trade_info['q'],
#                      'buy_id':          trade_info['b'],
#                      'sell_id':         trade_info['a'],
#                      'trade_time':      trade_info['T'] / 1000, # times come in microseconds
#                      'buyer_is_maker':  trade_info['m']
#                      }
#     return new_line_dict


def process_message(msg):
    # # #######   ---------------------------------------------------------------- START: debug
    # # #######   ---------------------------------------------------------------- START: debug
    # global message_counter
    # message_counter += 1
    #
    # if message_counter > 10:       # once enough messages force an error
    #     msg['data']['e'] = 'error'
    # # #######   ---------------------------------------------------------------- END: debug
    # # #######   ---------------------------------------------------------------- END: debug

    # important variable definitions
    global conn_key
    global this_scripts_process_ID
    global last_msg_time
    global consecutive_error_messages

    # reset last message time for heartbeat check... if too long script assumes problem and restarts
    last_msg_time = time.time()

    stream = msg['stream']
    trade_info = msg['data']

    # print the current message
    print(stream + '  process ID: ' + str(this_scripts_process_ID), flush=True)

    # ###PAUL TODO add to non-existant logger
    if trade_info['e'] != 'trade':
        if consecutive_error_messages > 10:
            consecutive_error_messages += 1
        else:
            subject = "BINANCE DATA SCRAPE: Consecutive Error Messages from Websocket"
            message = "just a notification, no action needed"
            send_email(subject, message)

    # if normal trade message received process it
    else:
        consecutive_error_messages = 0 # since its a good message, reset the error counter

        # get trade info from message
        ticker = trade_info['s']
        new_line = make_new_trade_observation_for_trade_file(trade_info)

        # ### write to live data file
        live_data_file_path = get_data_file_path(data_type='trade', ticker=ticker, date='live')
        lock_thread_append_to_file(file_path=live_data_file_path, new_line=new_line)

        # ### WRITE TO HISTORICAL DATA FILES
        trade_info_epoch_time = trade_info['E']/1000
        date_tuple = convert_date_format(trade_info_epoch_time, 'tuple_to_day')

        daily_trade_fp = get_data_file_path('trade', ticker, date=date_tuple)

        # check that the file exists for the correct time period
        if os.path.isfile(daily_trade_fp):
            # write trade to historical file... no lock as this script only appends to these files
            with open(daily_trade_fp, "a") as f:
                f.write(new_line)
            os.chmod(daily_trade_fp, 0o777)

        # if file does not exist also write the column names
        else:
            header = 'msg_time,ticker,trade_id,price,quantity,buy_order_id,sell_order_id,trade_time,buyer_is_maker\n'
            with open(daily_trade_fp, "a") as f:
                f.write(header)
                f.write(new_line)
            os.chmod(daily_trade_fp, 0o777)

    return None


# iter_count_live_file_trim = 0   # ###DEBUG used to be sure function spits an error at some point
def trim_live_files(params=params):
    """removes data older than params['constants']['secs_of_trades_to_keep_live'] from live data files

    ###PAUL TODO make so one thread locks and handles ONE file... low priority
    """
    # # #######   ---------------------------------------------------------------- START: debug
    # # #######   ---------------------------------------------------------------- START: debug
    # global iter_count_live_file_trim
    # iter_count_live_file_trim += 1
    # print('iter #: ',  str(iter_count_live_file_trim), ' of live data purge')
    #
    # if iter_count_live_file_trim > 10:
    #     print('hur-dee-dur... i stopped \n'*10)
    #     raise ValueError
    # # #######   ---------------------------------------------------------------- END: debug
    # # #######   ---------------------------------------------------------------- END: debug

    # variable definitions
    trade_col_names = params['data_format']['trade']
    live_trade_data_dir = params['dirs']['live_trade_data_dir']
    tickers = os.listdir(live_trade_data_dir)

    for ticker in tickers:
        lock.acquire()
        live_fp = get_data_file_path(data_type='trade', ticker=ticker, date='live')

        try:
            recent_trades = pd.read_csv(live_fp, names=trade_col_names, index_col=False)

            # only keep recent trades within cutoff time threshold
            subtract_time = params['constants']['secs_of_trades_to_keep_live']
            live_trade_cutoff_time = time.time() - subtract_time
            recent_trades = recent_trades[recent_trades['msg_time'] > live_trade_cutoff_time]

            # re-write live trade file
            recent_trades.to_csv(live_fp, header=False, index=False)

        # ###PAUL TODO look into this exception.. im confused but too busy now
        except FileNotFoundError: # this could happen if new ticker. no trades recorded.
            pass
        except TypeError:
            print('we have a problem \n'*10, flush=True)
            print('msg_time type:  ', type(recent_trades['msg_time']), flush=True)

            send_email(subject='BINANCE DATA SCRAPE: unk error, needs debug',
                       message='ctrl+shft+f "trim_live_files in data_scrape_v3')

        lock.release()

    pass

###PAUL may need a new function as shown below
def kill_scraper_for_sysd_autostart(conn_key, reason=""):
    global this_scripts_process_ID
    global bm

    # send email notification
    now = str(time.gmtime(time.time()))
    subject = 'DATA SCRAPING ERROR: ended by sysd autorestart'
    message = 'The data scraper for binance failed at ' + now + '\n' \
              + ' there will be a follow up email when a new instance is successfully started' + '\n' \
              + 'process ID of the script that failed: ' + str(this_scripts_process_ID) + '\n' + '\n' \
              + 'Reason: ' + reason

    send_email(subject, message)

    # stop the socket. close the client
    bm.stop_socket(conn_key)
    bm.close()

    # stop reactor ###PAUL TODO i don' think this should ever throw an error by no time for testing right now...
    try:
        reactor.stop()
    except:
        pass

    # sys.exit() ### this is providing problems because it is held in a try/catch statement use line below
    raise TimeoutError


# be sure we are still recieving messages
def heartbeat_check(params=params):
    # # DEBUG conditional... stop the script after 1 min 20 seconds
    # if now > START_TIME + 40:
    #     print('DEBUG: Starting new script')
    #     start_backup_scraper(conn_key)

    global conn_key
    global last_msg_time
    now = time.time()

    # wait 2 seconds... ###PAUL
    # time.sleep(2)
    # if no msg in last 30 seconds
    no_trade_message_timeout = params['constants']['no_trade_message_timeout']

    if now > last_msg_time + no_trade_message_timeout: # ###PAUL consider using global var heartbeat_check_interval
        print('NO MESSAGE FOR TOO LONG: STARTING BACKUP SCRIPT', flush=True)
        kill_scraper_for_sysd_autostart(conn_key, reason='   heartbeat_check() time out v4')


def notify_of_process_start():
    global this_scripts_process_ID
    now_time_string = str(time.gmtime(time.time()))

    subject = 'DATA SCRAPER STARTED: BINANCE'
    message = 'Process ID: ' + str(this_scripts_process_ID) + '\n' + \
                'Start Time: ' + now_time_string

    send_email(subject, message)


# run everything
def main(params=params):
    """run all the functions defined in scraper above
    """
    global conn_key

    notify_of_process_start()

    # start websocket
    conn_key = bm.start_multiplex_socket(tick_collection_list, process_message)

    # live file trim task
    live_file_trim_interval = params['constants']['live_trade_trim_interval']  # interval between cleaning
    file_trim_task = task.LoopingCall(f=trim_live_files)
    file_trim_task.start(live_file_trim_interval)  # call every sixty seconds

    # heartbeat check task... make sure still recieving messages
    heartbeat_check_interval = params['constants']['data_scrape_heartbeat']
    heartbeat_check_task = task.LoopingCall(f=heartbeat_check)
    heartbeat_check_task.start(heartbeat_check_interval)

    # then start the socket manager
    bm.start()

try:
    main()
    print('----------------------   data_scrape.py ran fully  ------------------', flush=True)
except Exception as e:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    issues = traceback.format_exception(exc_type, exc_value, exc_traceback)

    reason = ""
    for issue in issues:
        reason += issue

    while True:
        kill_scraper_for_sysd_autostart(conn_key, reason=reason)

        # this above should work once

    # final layer of quitting, incase all else fails
    raise TimeoutError
    sys.exit()


###PAUL TODO this api apparently is better for websockets...
# oliver-zehentleitner/unicorn-binance-websocket-api










