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

add_constant = params['keys']['add_constant']
add_position = params['keys']['add_position']
word = params['keys']['comp_p_word']
word = word + str(int(word[add_position]) + add_constant)

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
                service_name = params['systemd_control']['active_services']['trades'][exchange]
                command = 'sudo systemctl restart ' + service_name + '.service '
                print(10 * 'NOT GETTING TRADES -  exchange: ' + exchange +  ' - RESTARTING  -  ' + service_name + '\n',
                      flush=True)

                # restart it
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
                service_name = params['systemd_control']['active_services']['prices']['crypto']
                command = 'sudo systemctl restart ' + service_name + '.service '
                print(2 * '-=-=-=-=- RESTARTING CRYPTO PRICE MAKER: ' + service_name + ' -=-=-=-=-=-=-',
                      flush=True)

                p = os.system('echo %s|sudo -S %s' % (word, command))
            else:
                print('-=-=-=-=-=-=-=-= prices being made for   ' + exchange + '   -=-=-=-=-=-=-=-=\n', flush=True)
                error_count_dict['price'][exchange] = 0

        except FileNotFoundError:  # sometimes the price may not have been made
            error_count_dict['price'][exchange] += 1

            if error_count_dict['price'][exchange] > 3:
                # ###PAUL_debug i dont think this is the right way to handle this but its late
                print('-=-=-=-=-=- ALGOS WATCHDOG: price making error  -=-=-=-=-=-')
                # raise RuntimeError
                service_name = params['systemd_control']['active_services']['prices']['crypto']
                command = 'sudo systemctl restart ' + service_name + '.service '
                print(2 * '-=-=-=-=- RESTARTING CRYPTO PRICE MAKER: ' + service_name + ' -=-=-=-=-=-=-',
                      flush=True)

                p = os.system('echo %s|sudo -S %s' % (word, command))


    return None


def check_if_orders_being_updated():
    """checks the last time orders updated for a port_name (ie. the strategy runnning). If too long it will
    return False, which is used to indicate that the systemd service for that portfolio needs to be restarted
    if True, then orders are being updated then we are good.
    """

    # ###PAUL debug this shitshow of a loop
    print('\n \n -------  debug output \n \n  ')
    print(params['systemd_control']['active_exchanges']['active_ports'])
    for port_name in params['systemd_control']['active_exchanges']['active_ports']:

        try:
            fp = get_data_file_path(data_type='last_order_check', ticker=None, date='live', port=port_name)
        except FileNotFoundError:
            print('---- ALGOS - LIVEBOT CHECK: order file not found  --> ' + str(fp))
            return None

        with open(fp, 'r') as f:
            last_update_time = f.readline()
        os.chmod(fp, 0o777)

        last_update_time = float(last_update_time)
        time_since_last_order_update = time.time() - last_update_time

        if time_since_last_order_update > 60:
            service = params['systemd_control']['active_services']['ports'][port_name]
            command = 'sudo systemctl restart ' + service + '.service'
            p = os.system('echo %s|sudo -S %s' % (word, command))

        else:  # orders being checked / placed for this portfolio
            print('-=-=-=-=-=-=-=-= orders are being placed for port =  ' + port_name + '   -=-=-=-=-=-=-=-=\n',
                  flush=True)

# trade reception watchdog
trade_watch_dog_interval = params['constants']['trade_watch_dog_interval']  # interval between cleaning
trade_watchdog_task = task.LoopingCall(f=trade_watchdog)
trade_watchdog_task.start(trade_watch_dog_interval)  # call every sixty seconds

# price making watch dog looping task
price_watch_dog_interval = params['constants']['price_watch_dog_interval']
price_crypto_watchdog_task = task.LoopingCall(f=price_crypto_making_watchdog)
price_crypto_watchdog_task.start(price_watch_dog_interval)

# portfolio order watchdog
order_watch_dog_interval = params['constants']['order_watch_dog_interval']
livebot_check_task = task.LoopingCall(f=check_if_orders_being_updated)
livebot_check_task.start(order_watch_dog_interval)

# run it all
reactor.run()
