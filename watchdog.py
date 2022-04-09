#!/home/paul/miniconda3/envs/crypto_data_scrape/bin/python3 -u
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

device_name = params['device_info']['device_name']

# set the error count for each exchange to 0
for ex in params['exchanges']:
    error_count_dict['trade'][ex] = 0
    error_count_dict['price'][ex] = 0


# used a few times to restart services, good because it allows for mode switching easily for manual updates
def restart_service(service, script, pword=word, mode='hard_restart'):

    send_email(subject='WATCHDOG UPDATE: ' + service + ' ---- restart',
               message=('restarting: \n'
                        + '---- service: ' + service
                        + '---- script: ' + script),
               script=script)

    if mode == 'restart':
        command = 'sudo systemctl restart ' + service + '.service'
        p = os.system('echo %s|sudo -S %s' % (pword, command))

    if mode == 'hard_restart':
        command = 'sudo chmod u+x ' + script \
                  + '&& sudo systemctl stop ' + service + '.service ' \
                  + '&& sudo systemctl daemon-reload' \
                  + '&& sudo systemctl enable ' + service + '.service' \
                  + '&& sudo systemctl restart ' + service + '.service'

        p = os.system('echo %s|sudo -S %s' % (pword, command))

    return None


def trade_watchdog():
    """checks if we are getting trades and will hard reset the trade datascrape service
    """

    print("-=-=-=-=-=-=-=-= ALGOS WATCHDOG: ------------ CHECKING TRADES -=-=-=-=-=-=-=-=\n", flush=True)

    for exchange in params['systemd_control']['active_data_exchanges']:
        # if exchange == 'kucoin':
        #     import pdb; pdb.set_trace()

        # keep this here, bottom line needed for top
        service = params['systemd_control']['active_services']['trades'][exchange]['service']
        script = params['systemd_control']['active_services']['trades'][exchange]['script']
        restart_notification_string = 3 * ('NOT GETTING TRADES - exchange: ' + exchange + ' - RESTARTING  -  ' + service + '\n')

        try:
            check_ticker = params['systemd_control']['ticker_to_check_trades'][exchange]
            no_trade_time = params['systemd_control']['no_trade_time'][exchange]
            trades = get_live_trades_data(check_ticker, exchange=exchange)
            time_since_last_btc_trade = time.time() - trades.iloc[-1]['trade_time']

            # if exchange == 'kucoin':
            #     import pdb; pdb.set_trace()

            if time_since_last_btc_trade > no_trade_time:  # restart systemd service

                # restart it
                print(restart_notification_string, flush=True)
                restart_service(service, script)

            else:
                error_count_dict['trade'][exchange] = 0
                print("-=-=-=-=-=-=-=-= ALGOS WATCHDOG: trades being received for     " + exchange + "    -=-=-=-=-=\n",
                      flush=True)

        # some exchanges are slow, so we will give 3 checks untill we force a restart
        except (FileNotFoundError, IndexError):
            error_count_dict['trade'][exchange] += 1
            if error_count_dict['trade'][exchange] > 3:
                # restart it
                print('-=-=-=-=-=-=-=-= ALGOS WATCHDOG: max ERROR count for exchange: ' + exchange, flush=True)
                print(restart_notification_string, flush=True)
                restart_service(service, script)


    return None


def price_crypto_making_watchdog():
    """checks if we are making prices from trades and will hard reset orders.py service
    """

    global error_count_dict

    print('-=-=-=-=-=-=-=-= ALGOS WATCHDOG: ------------ CHECKING PRICES -=-=-=-=-=-=-=-=\n', flush=True)
    for exchange in params['systemd_control']['active_data_exchanges']:
        try:
            check_ticker = params['systemd_control']['ticker_to_check_trades'][exchange]
            prices = get_data(data_type='prices', ticker=check_ticker, exchange=exchange)

            # get most recent BTC trade (or whatever is the highest frequency)
            most_recent_trade_timestamp = pd.to_datetime(prices.index[-1])

            # calculate unix datetime
            epoch_msg_time = (most_recent_trade_timestamp - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
            seconds_since_last_msg = time.time() - epoch_msg_time

            if seconds_since_last_msg > params['systemd_control']['no_trade_time'][exchange]:
                service = params['systemd_control']['active_services']['prices']['crypto']['service']
                script = params['systemd_control']['active_services']['prices']['crypto']['script']
                print(2 * '-=-=-=-=- RESTARTING CRYPTO PRICE MAKER: ' + service + ' -=-=-=-=-=-=-',
                      flush=True)

                # restart it
                restart_service(service, script)

            else:
                print('-=-=-=-=-=-=-=-= ALGOS WATCHDOG prices being made for    ' + exchange + '    -=-=-=-=-=-=-=-=\n',
                      flush=True)
                error_count_dict['price'][exchange] = 0

        except FileNotFoundError:  # sometimes the price may not have been made ... weird stuff happens...
            error_count_dict['price'][exchange] += 1

            if error_count_dict['price'][exchange] > 3:
                # ###PAUL_debug i dont think this is the right way to handle this but its late
                print('-=-=-=-=-=- ALGOS WATCHDOG: price making ERROR  -=-=-=-=-=-', flush=True)
                # raise RuntimeError
                service = params['systemd_control']['active_services']['prices']['crypto']['service']
                script = params['systemd_control']['active_services']['prices']['crypto']['script']
                print(2 * '-=-=-=-=- ALGOS - RESTARTING CRYPTO PRICE MAKER: ' + service + ' -=-=-=-=-=-=-',
                      flush=True)

                # restart service
                restart_service(service, script)

    return None


def check_if_orders_being_updated():
    """checks the last time orders updated for a port_name (ie. the strategy runnning). If too long it will
    return False, which is used to indicate that the systemd service for that portfolio needs to be restarted
    if True, then orders are being updated then we are good.
    """

    print('-=-=-=-=-=-=-=-= ALGOS WATCHDOG: ------------ CHECKING LIVE BOTS -=-=-=-=-=-=-=-=\n', flush=True)

    active_ports = params['systemd_control']['active_ports']

    if len(active_ports) == 0:
        print('-=-=-=-=-=-=-=-= no bots running on ---- ' + device_name)
    for port_name in active_ports:
        exchange = params['systemd_control']['active_services']['ports'][port_name]['exchange']
        service = params['systemd_control']['active_services']['ports'][port_name]['service']
        script = params['systemd_control']['active_services']['ports'][port_name]['script']

        try:
            fp = get_data_file_path(data_type='last_order_check',
                                    ticker=None,
                                    date='live',
                                    port=port_name,
                                    exchange=exchange)
        except FileNotFoundError:
            print(2 * '\n ---- ALGOS - LIVEBOT CHECK: order file not found  --> \n' + str(fp), flush=True)
            print('---- PROBLEM: last_order_check not found for port ---- ' + port_name, flush=True)
            return None

        with open(fp, 'r') as f:
            last_update_time = f.readline()
        os.chmod(fp, 0o777)

        last_update_time = float(last_update_time)
        time_since_last_order_update = time.time() - last_update_time

        if time_since_last_order_update > 60:
            print(2 * '-=-=-=-=- ALGOS - RESTARTING LIVE BOT: ' + service + ' -=-=-=-=-=-=-',
                  flush=True)

            # restart it
            restart_service(service, script)

        else:  # orders being checked / placed for this portfolio
            print('-=-=-=-=-=-=-=-= ALGOS WATCHDOG:   port   ' + port_name + '  ---- is active on   ' + exchange
                  + '   -=-=-=-=-=\n',
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
