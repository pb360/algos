#!/home/paul/miniconda3/envs/binance/bin/python3 -u
# -*- coding: utf-8 -*-

# ### imports
#
#
import os
import time

os.environ['TZ'] = 'UTC'
time.tzset()

from twisted.internet import task, reactor

# ### local imports
#
#
from utils import *

params = config.params

error_count_dict = {'trade': {},
                    'price': {},
                    }

# set the error count for each exchange to 0
for ex in params['exchanges']:
    error_count_dict['trade'][ex] = 0
    error_count_dict['price'][ex] = 0


def trade_watchdog():
    """checks if we are getting trades and will hard reset the trade datascrape service
    """

    print(2 * "-=-=-=-=-=-=-=-= ALGOS WATCHDOG: checking if we are GETTING TRADES -=-=-=-=-=-=-=-=\n", flush=True)

    for exchange in params['systemd_control']['active_exchanges']:
        try:
            check_ticker = params['systemd_control']['ticker_to_check_trades'][exchange]
            trades = get_live_trades_data(check_ticker, exchange=exchange)
            time_since_last_btc_trade = time.time() - trades.iloc[-1]['trade_time']

            if time_since_last_btc_trade > 30:  # restart systemd service
                pword = params['keys']['comp_p_word']
                add_constant = params['keys']['add_constant']
                add_position = params['keys']['add_position']

                print(10 * "NOT GETTING TRADES: ATTEMPTING TO RESTART datascrape_v4 \n", flush=True)
                word = pword
                word = word + str(int(word[add_position]) + add_constant)

                service_name = params['systemd_control']['active_services']['trade'][exchange]
                command = 'sudo systemctl restart ' + service_name + '.service '
                p = os.system('echo %s|sudo -S %s' % (word, command))
            else:
                error_count_dict['trade'][exchange] = 0
                print("-=-=-=-=-=-=-=-= trades being received for   " + exchange + "   -=-=-=-=-=-=-=-=\n", flush=True)

        except FileNotFoundError:  # sometimes the price may not have been made
            error_count_dict['trade'][exchange] += 1

            if error_count_dict['trade'][exchange] > 3:
                print('-=-=-=-=-=- ALGO2 WATCHDOG: Errored in trade recording watchdog -=-=-=-=-=-', flush=True)
                raise RuntimeError

    return None


def price_crypto_making_watchdog():
    """checks if we are making prices from trades and will hard reset orders.py service
    """

    global error_count_dict

    print(2 * '-=-=-=-=-=-=-=-= ALGOS WATCHDOG: checking if we are MAKING PRICES -=-=-=-=-=-=-=-=\n', flush=True)
    for exchange in params['systemd_control']['active_exchanges']:
        try:
            check_ticker = params['systemd_control']['ticker_to_check_trades'][exchange]
            prices = get_data(data_type='prices', ticker=check_ticker, exchange=exchange)

            # get most recent BTC trade (or whatever is the highest frequency)
            most_recent_trade_timestamp = pd.to_datetime(prices.index[-1])

            # calculate unix datetime
            epoch_msg_time = (most_recent_trade_timestamp - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
            seconds_since_last_msg = time.time() - epoch_msg_time

            if seconds_since_last_msg > 35:
                print(2 * '-=-=-=-=-=-=- RESTARTING CRYPTO PRICE MAKER: No Price Update For Too Long -=-=-=-=-=-=-',
                      flush=True)

                pword = params['keys']['comp_p_word']
                add_constant = params['keys']['add_constant']
                add_position = params['keys']['add_position']

                word = pword
                word = word + str(int(word[add_position]) + add_constant)

                service_name = params['systemd_control']['prices']['crypto']
                command = 'sudo systemctl restart ' + service_name + '.service '
                p = os.system('echo %s|sudo -S %s' % (word, command))
            else:
                print('-=-=-=-=-=-=-=-= prices being made for   ' + exchange + '   -=-=-=-=-=-=-=-=\n', flush=True)
                error_count_dict['price'][exchange] = 0

        except FileNotFoundError:  # sometimes the price may not have been made
            error_count_dict['price'][exchange] += 1

            if error_count_dict['price'][exchange] > 3:
                # ###PAUL_debug i dont think this is the right way to handle this but its late
                print('-=-=-=-=-=- ALGOS WATCHDOG: price making error  -=-=-=-=-=-')
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

    if status == True:  # then orders are being updated
        return None
    elif status == False:  # then orders are not being updated
        print(3 * '-=-=-=-=-=-=-=-=-=- RESTARTING LIVE BOT: sma_v1 -=-=-=-=-=-=-=-=-=- ')
        word = params['keys']['comp_p_word']
        word = word + str(int(word[4]) + 8)

        command = 'sudo systemctl restart algo2_live_bot_sma_v1.service'
        p = os.system('echo %s|sudo -S %s' % (word, command))

    return None


# trade reception watchdog
trade_watch_dog_interval = params['constants']['trade_watch_dog_interval']  # interval between cleaning
trade_watchdog_task = task.LoopingCall(f=trade_watchdog)
trade_watchdog_task.start(trade_watch_dog_interval)  # call every sixty seconds

# price making watch dog looping task
price_watch_dog_interval = params['constants']['price_watch_dog_interval']
price_crypto_watchdog_task = task.LoopingCall(f=price_crypto_making_watchdog)
price_crypto_watchdog_task.start(price_watch_dog_interval)

# making sure that orders based on signals are being considered for given strategies... if too many eventually change the structure here
# order_watch_dog_interval     = params['constants']['order_watch_dog_interval']
# livebot_sma_v1_watchdog_task = task.LoopingCall(f=check_sma_v1_ordering)
# livebot_sma_v1_watchdog_task.start(order_watch_dog_interval)

# run it all
reactor.run()
