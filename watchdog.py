#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-

# ### time zone change... this must happen first and utils must be imported first
# ### time zone change... this must happen first and utils must be imported first
import os 
import time
os.environ['TZ'] = 'UTC'
time.tzset()
# ### time zone change... this must happen first and utils must be imported first
# ### time zone change... this must happen first and utils must be imported first

# ### imports 
# 
#
from twisted.internet import task, reactor

# ### local imports
from utils import * 

params = config.params

error_count_dict = {'trade':0,
                    'price':0,
                   }

def trade_watchdog():
    """checks if we are getting trades and will hard reset the trade datascrape service
    """
    print(2*"-=-=-=-=-=-=-=-= algo 2 update: Watch Dogging If Were Getting Trades -=-=-=-=-=-=-=-=\n", flush=True)

    try:
        trades = get_live_trades_data('BTCUSDT')
        time_since_last_btc_trade = time.time() - trades.iloc[-1]['trade_time']

        if time_since_last_btc_trade > 20: # restart systemd service
            print(10*"NOT GETTING TRADES: ATTEMPTING TO RESTART datascrape_v4 \n", flush=True)
            word = params['keys']['comp_p_word']
            word = word + str(int(word[4]) + 8)

            command = 'sudo systemctl restart binance_datascrape_v4.service '
            p = os.system('echo %s|sudo -S %s' % (word, command))

        error_count_dict['trade'] = 0

    except FileNotFoundError:  # sometimes the price may not have been made
        error_count_dict['trade'] += 1

        if error_count_dict['trade'] > 5:
            print('-=-=-=-=-=- ALGO2 WATCHDOG: Errored in trade recording watchdog -=-=-=-=-=-')
            raise RuntimeError

    return None

def price_making_watchdog():
    """chceks if we are making prices from trades and will hard reset orders.py service
    """

    global error_count_dict

    print(2 * '-=-=-=-=-=- algo 2 update: Watch Dogging If Prices Being Made From Trades -=-=-=-=-=\n', flush=True)

    try:
        prices = get_data(data_type='prices', ticker='BTCUSDT')

        # create test data
        most_recent_trade_timestamp = pd.to_datetime(prices.index[-1])

        # calculate unix datetime
        epoch_msg_time = (most_recent_trade_timestamp - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')

        seconds_since_last_msg = time.time() - epoch_msg_time

        if seconds_since_last_msg > 60:
            print(3*'-=-=-=-=-=-=-=-=-=- RESTARTING PRICE MAKER: No Price Update For Too Long -=-=-=-=-=-=-=-=-=- ')
            word = params['keys']['comp_p_word']
            word = word + str(int(word[4]) + 8)

            command = 'sudo systemctl restart binance_orders.service '
            p = os.system('echo %s|sudo -S %s' % (word, command))

        error_count_dict['price'] = 0

    except FileNotFoundError: # sometimes the price may not have been made
        error_count_dict['price'] += 1

        if error_count_dict['price'] > 5:
            print('-=-=-=-=-=- ALGO2 WATCHDOG: Errored in price making watchdog -=-=-=-=-=-')
            raise RuntimeError

    return None

def check_if_orders_being_updated(port_name):
    """checks the last time orders updated for a port_name (ie. the strategy runnning). If too long it will
    return False, which is used to indicate that the systemd service for that portfolio needs to be restarted
    if True, then orders are being updated then we are good.
    """

    fp = get_data_file_path(data_type='last_order_check', ticker=None, date='live', port=port_name)

    with open(fp, 'r') as f:
        last_update_time = f.readline()
    os.chmod(fp, 0o777)

    last_update_time = float(last_update_time)
    time_since_last_order_update = time.time() - last_update_time

    if time_since_last_order_update < 60:
        return True
    else:
        return False

def check_sma_v1_ordering():
    status = check_if_orders_being_updated('sma_v1')

    if status == True: # then orders are being updated
        return None
    elif status == False: # then orders are not being updated
        print(3 * '-=-=-=-=-=-=-=-=-=- RESTARTING LIVE BOT: sma_v1 -=-=-=-=-=-=-=-=-=- ')
        word = params['keys']['comp_p_word']
        word = word + str(int(word[4]) + 8)

        command = 'sudo systemctl restart algo2_live_bot_sma_v1.service'
        p = os.system('echo %s|sudo -S %s' % (word, command))

    return None


# trade reception watchdog
trade_watch_dog_interval = params['constants']['trade_watch_dog_interval']  # interval between cleaning
trade_watchdog_task      = task.LoopingCall(f=trade_watchdog)
trade_watchdog_task.start(trade_watch_dog_interval)  # call every sixty seconds

# price making watch dog looping task
price_watch_dog_interval = params['constants']['price_watch_dog_interval']
price_watchdog_task      = task.LoopingCall(f=price_making_watchdog)
price_watchdog_task.start(price_watch_dog_interval)

# making sure that orders based on signals are being considered for given strategies... if too many eventually change the structure here
# order_watch_dog_interval     = params['constants']['order_watch_dog_interval']
# livebot_sma_v1_watchdog_task = task.LoopingCall(f=check_sma_v1_ordering)
# livebot_sma_v1_watchdog_task.start(order_watch_dog_interval)

# run it all
reactor.run()

