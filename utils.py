#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-

# ### imports
#
#
import os
import time

# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

import sys

sys.path.append('/mnt/algos/')

import datetime
import dateutil
from decimal import Decimal
import math
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np
import os
import pandas as pd
# import pandas.api.types  # not sure if needed but added from notebook so ill keep dis here for now
import re
import smtplib
from typing import Union

# local packages

import config

# ### variable definitions
#
#
params = config.params


def convert_date_format(date, output_type):
    """takes a date in a given format and returns it in another

    input AND output formats:
        tuple_to_day        ---- ('2021', '01', '31')  ---- entries maybe int or str, leading zero not required
        tuple_to_sec        ---- ('2021', '01', '31', '13', '22', '59')   ---- same format type as above
        datetime.date       ---- datetime.date(2021, 1, 9, 20)
        datetime.datetime   ---- datetime.datetime(2021, 1, 9, 20, 46, 33, 377164)
        np.datetime64       ----
        string_to_day       ---- "2021-01-31"
        string_to_sec       ---- "2021-01-31 13:55:01"
        tuple_day_int       ---- (2021, 1, 31)   tuple entries may be int or str
        tuple_sec_int       ---- (2021, 1, 31, 13, 22, 59)   tuple entries may be int or str
        timestamp           ---- ###PAUL this needs to be added

    """
    ### input type for first conditional, output type for second
    if isinstance(date, tuple):
        # make sure the tuple entries are int... this converts to a list of ints
        date = [int(x) for x in date]

        # tuple to day resolution... ie: [2021, 01, 31]
        if len(date) == 3:
            year, month, day = date
            if output_type == 'datetime' or output_type == 'datetime.date':
                return datetime.date(year=year, month=month, day=day)
            if output_type == 'tuple_to_day':
                y, m, d = str(date[0]), str(date[1]), str(date[2])
                return (y, m, d)

        # tuple to sec  resolution... ie: [2021, 01, 31, 23, 59, 1]
        if len(date) == 6:
            year, month, day, hour, minute, second = date
            if output_type == 'datetime' or output_type == 'datetime.datetime':
                return datetime.date(year=year, month=month, day=day, hour=hour, minute=minute, second=second)

        print("###PAUL make    tuple     to desired output work please", flush=True)

    if isinstance(date, datetime.date) or isinstance(date, datetime.datetime):
        if output_type == 'epoch':
            return test_date.timestamp()
        if output_type == 'string_long':
            return date.strftime('%Y-%m-%d %H:%M:%S')
        if output_type == 'string_short':
            return date.strftime('%Y-%m-%d')
        if output_type == 'tuple_to_day' or output_type == "tuple_to_second":
            year = date.strftime('%Y')
            month = date.strftime('%m')
            day = date.strftime('%d')
            hour = date.strftime('%H')
            minute = date.strftime('%M')
            second = date.strftime('%S')
            if output_type == 'tuple_to_day':
                return (year, month, day)
            if output_type == 'tuple_to_sec':
                return (year, month, day, hour, minute, second)
            if output_type == 'datetime.date' or output_type == 'datetime.datetime' or output_type == 'datetime':
                return date


    # paul convert epoch time to various formats
    elif isinstance(date, int) or isinstance(date, float):
        if output_type == 'tuple_to_day':
            year = time.strftime('%Y', time.localtime(date))
            month = time.strftime('%m', time.localtime(date))
            day = time.strftime('%d', time.localtime(date))

            date_tuple = (year, month, day)
            return date_tuple

    # convert string to various formats
    elif isinstance(date, str):
        if len(date) == 19:  ### i.e. 2020-01-08 22:55:32
            print("###PAUL make    string_to_sec     to desired output work please", flush=True)

        if len(date) == 10:  ### i.e. 2020-01-08
            if output_type == 'datetime' or output_type == 'datetime.date':
                return dateutil.parser.isoparse(date).date()
            if output_type == 'tuple_to_day':
                y, m, d = date[0:4], date[5:7], date[8:11]
                return (y, m, d)

            else:
                print(' string to date time does not work yet... get on it if you needful', flush=True)

    else:
        print('cant do that yet', flush=True)
        raise TypeError


def check_if_file_in_directory(file, directory):
    """check if file in directory... returns boolean
    inputs:
        file (str): name of file
        directory (str): path to directory
    outputs:
        boolean: True or False
    """
    file_list = os.listdir(directory)
    if file in file_list:
        return True
    else:
        return False


def send_email(subject, message, script=None, to='paulboehringer0989@gmail.com', params=params):
    """sends an email from my protonmail to the
    input:
        subject (str): subject for email
        message (str): message for email
        params (dict): params dict used repo wide

    output:
        None: sends an email. Nothing is returned
    """
    # pull variables out of params
    try:
        port_number = params['constants']['email_port']
        sender_email = params['keys']['mail_user']
        email_password = params['keys']['mail_password']

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to

        msg['Subject'] = subject
        begin_message_str = 'email from script ---- ' + str(script) \
                            + ' \n \n running on  ----  ' + params['device_info']['device_name'] + '\n \n'

        message = begin_message_str + message
        msg.attach(MIMEText(message))

        mailserver = smtplib.SMTP('127.0.0.1', port_number)
        mailserver.login(sender_email, email_password)
        mailserver.sendmail('paulboehringer@protonmail.com', 'paulboehringer0989@gmail.com', msg.as_string())
        mailserver.quit()
    except Exception as e:
        print('---- an email failed to send \n the error will print out below \n \n \n ', flush=True)
        print(e, flush=True)
        print('\n \n \n', flush=True)
        pass

    return True


def get_last_line_of_file(filepath, filesize='large'):
    """gets the last line of a file.. see link for second way to do it
    https://stackoverflow.com/questions/46258499/read-the-last-line-of-a-file-in-python
    """

    if not os.path.isfile(filepath):
        print('FileNotFoundError: ' + filepath + 'in get_last_line_of_file()')
        raise FileNotFoundError

    if filesize == 'small':
        with open(filepath) as f:
            for line in f:
                pass
            last_line = line

    if filesize == 'large':
        # if the file is one line this method will fail, revert to small file method
        try:
            with open(filepath, 'rb') as f:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
                last_line = f.readline().decode()
        # turns out the file was one line
        except OSError:
            print(2 * ('file too short for the long method ---- ' + filepath + '\n'), flush=True)
            # if the file is empty then this try except will hit
            try:
                with open(filepath) as f:
                    for line in f:
                        pass
                    last_line = line
            except NameError as e:
                print(e, flush=True)
                print('\n \n this file is empty  \n ', flush=True)
                raise FileExistsError

    return last_line


def make_date_suffix(date, file_type='.csv'):
    """ makes as suffix for file paths of the form: "----2020-12-31.csv"

    input
        date (tuple):     (year, month, day) such as (2021, 01, 31)... leading zeros not required

        file_type (str):  '.csv',  '.pickle',   ect..
    """

    # if live is sent to this function we likely want the file for today...
    if date == 'live' or date == 'open':
        date = convert_date_format(time.time(), 'tuple_to_day')

    if type(date) != tuple:
        date = convert_date_format(date, 'tuple_to_day')

    year, month, day = date
    year = str(year)
    month = str(month)
    day = str(day)

    if len(month) == 1:
        month = '0' + month
    if len(day) == 1:
        day = '0' + day

    suffix = '----' + year + '-' + month + '-' + day + file_type

    return suffix


def convert_symbol(symbol, in_exchange, out_exchange, params=params):
    # try:

    if out_exchange == 'universal':
        if in_exchange == 'universal':
            print('asking to convert pair from universal to universal')
            raise SyntaxWarning
        else:
            return params['universe']['universal']['to_universal'][in_exchange][symbol]

    if out_exchange != 'universal':
        if in_exchange == 'universal':
            universal_pair = symbol
        else:
            universal_pair = params['universe']['universal']['to_universal'][in_exchange][symbol]

        try:
            return params['universe']['universal']['from_universal'][out_exchange][universal_pair]

        except KeyError:
            # handle the case of tether pairs from exchanges that also have a separate USD (non tether quote)
            if 'ether' in universal_pair:
                universal_pair = universal_pair.replace('ether', '')  # for tether, not ETH
                return params['universe']['universal']['from_universal'][out_exchange][universal_pair]
            else:  # there is a problem
                raise KeyError


def get_data_file_path(data_type, pair, date='live', port=None, exchange=None, pair_mode='asis', params=params):
    """returns string of filepath to requested datafile

    :param port: (str) naming the portfolio strategy for orders and preformance data
    inputs
        data_type (str): options ----  ['price', 'trade', 'order', 'book']  ----
            TODO add live order which means all open orders
            TODO daily data files  add support for book eventually
        pair (str):    pair  ---- 'BTCUSDT'
        date (tuple):    (year, month, day) such as (2021, 01, 31) ---- TODO make other time formats work
    """

    live_data_dir = params['dirs']['live_data_dir']  # still used
    port_data_dir = params['dirs']['port_data_dir']  # still used

    # ###PAUL_todo: once data is saved under universal names the conditional is needed, should be done every time
    if pair_mode == 'asis':  # pair given in exchange's format
        pass
    elif pair_mode == 'universal':
        pair = convert_symbol(pair, in_exchange='universal', out_exchange=exchange, params=params)

    fp = None

    if date != 'pair_folder':
        suffix = make_date_suffix(date)

    # first handle if date is live... if not we attempt to convert it if not a tuple
    if date == 'live' or date == 'open':

        # ### live kept data
        #
        #
        if data_type == 'trade' or data_type == 'trades' or data_type == 'price' or data_type == 'prices':
            if exchange is None:
                return IOError
            elif data_type == 'trade' or data_type == 'trades':
                fp = live_data_dir + 'trades_live/' + exchange + '/' + pair + '/' \
                     + exchange + '_' + pair + '_live_trades.csv'

            # ###PAUL this should be handled one day... maybe return just the price file for time.time()
            elif data_type == 'price' or data_type == 'prices':
                fp = live_data_dir + pair + '/' + pair + '_live_trades.csv'

        # ### portfolio data
        #
        #
        if data_type == 'orders' or data_type == 'order' or data_type == 'open_orders' \
                or data_type == 'whose_turn' or data_type == 'last_order_check' \
                or data_type == 'port' or data_type == 'port_folder' or data_type == 'port_path' \
                or data_type == 'closed_order' or data_type == 'closed_orders' or data_type == 'orders_closed':
            # if port not provided can't get any of these
            if port is None:
                return IOError
            elif data_type == 'orders' or data_type == 'order' or data_type == 'open_orders':
                fp = port_data_dir + exchange + '/' + port + '/open_orders.csv'
            elif data_type == 'whose_turn':
                fp = port_data_dir + exchange + '/' + port + '/whose_turn.csv'
            elif data_type == 'last_order_check':
                fp = port_data_dir + exchange + '/' + port + '/last_check.txt'
            elif data_type == 'port' or data_type == 'port_folder' or data_type == 'port_path':
                fp = port_data_dir + exchange + '/' + port + '/'
            elif data_type == 'closed_order' or data_type == 'closed_orders' or data_type == 'orders_closed':
                fp = port_data_dir + exchange + '/' + port + '/closed/' + pair + '/' \
                     + 'orders----' + pair + '----' + suffix

    # # ### if not exactly passed as a tuple of form ("2021", "01", "31") attempt conversion
    # if ~isinstance(date, tuple):
    #     date = convert_date_format(date=date, output_type='tuple_to_day')

    elif date == 'pair_folder':  # just gets the pair's folder.. will direct to folder of dates for data type
        if exchange is not None:
            if data_type == 'price' or data_type == 'prices':
                fp = live_data_dir + 'price/' + exchange + '/' + pair + '/'
            elif data_type == 'trade' or data_type == 'trades':
                fp = live_data_dir + 'trades_daily/' + exchange + '/' + pair + '/'
            elif data_type == 'book':
                fp = live_data_dir + 'book_daily/' + exchange + '/' + pair + '/'
        elif port is not None:
            if data_type == 'order_closed':
                fp = port_data_dir + exchange + '/' + port + '/closed/' + pair + '/' \
                     + 'orders----' + pair + '----' + suffix
        else:
            return IOError

    elif date != 'live':  # date is actually supplied

        # live maintained data (historical, but still folder is managed in real time)
        if exchange is not None and port is None:
            if data_type == 'price' or data_type == 'prices':
                fp = live_data_dir + 'price/' + exchange + '/' + pair \
                     + '/prices----' + exchange + '_' + pair + suffix
            elif data_type == 'trade' or data_type == 'trades':
                fp = live_data_dir + 'trades_daily/' + exchange + '/' + pair \
                     + '/trades----' + exchange + '_' + pair + suffix
            elif data_type == 'book':
                fp = live_data_dir + 'book/' + exchange + '/' + pair \
                     + '/book----' + exchange + '_' + pair + suffix

        # port related data
        elif port is not None:
            if data_type == 'order' or data_type == 'orders' or data_type == 'closed_orders':
                ffp = port_data_dir + exchange + '/' + port + '/closed/' + pair + '/' \
                      + 'orders----' + pair + '----' + suffix
        else:
            return IOError

    if fp is not None:
        return fp
    else:
        print('Nothing in data file path function matched the request', flush=True)
        print('the request was:', flush=True)
        print('    data_type=' + str(data_type) + ', pair=' + str(pair) + ', date=' + str(date) \
              + ', port=' + str(port) + ', exchange=' + str(exchange), flush=True)
        return IOError


def get_live_trades_data(pair, exchange, params=params):
    """gets dataframe of live data... most recent trades for last 10 mins

    input
        - pair (str): pair for data.       e.x.:  btcusdt
    returns
        - trades (pd.DataFrame): trades for last 10 minutes
    """
    col_dtype_dict = params['data_format'][exchange]['trade_name_and_type']
    fp = get_data_file_path(data_type='trade', pair=pair, date='live', exchange=exchange)

    return pd.read_csv(fp,
                       header=0,  # ignore col_names... dont treat as data
                       names=col_dtype_dict.keys(),  # name of columns
                       dtype=col_dtype_dict,  # data type of cols
                       index_col='msg_time'
                       )


def get_date_range(start_date, end_date, output_type='datetime.datetime'):
    """makes list from start_date to end date

    inputs:
        start_date (datetime.datetime):
        end_date (datetime.datetime):
        output_type (str)

    outputs:
        date_list (list): containing datetime.datetime objects.... unless output_type specified otherwise
    """

    date_list = []
    delta = end_date - start_date  # as timedelta

    for i in range(delta.days + 1):
        date_i = start_date + datetime.timedelta(days=i)

        if output_type != 'datetime.datetime':
            date_i = convert_date_format(date=date_i, output_type=output_type)

        date_list.append(date_i)

    return date_list


def get_data(data_type,
             pair,
             params=params,
             date=None,
             start_date=None,
             end_date=None,
             duration=None,
             port=None,
             exchange=None,
             fill_in=True
             ):
    """master data retriving function

    input:
        data_type (str): 'price'  OR  'trade
        date (tuple): options:
        date: datetime.datetime
        start_date (tuple): ('2021', '01', '31') will work... all others not gaurenteed
    """

    # handle timing requests  ###PAUL TODO make this part of get_date_range function

    # convert any dates to datetime as we do relative calculations with them
    if start_date is not None:
        start_date = convert_date_format(start_date, 'datetime')
    if end_date is not None:
        end_date = convert_date_format(end_date, 'datetime')
    if start_date is None and end_date is None and date is None:
        date = 'live'

    # ### set start and end date according to input
    #
    # if date live --> get last 24 hours of data
    if date == 'live':
        if duration is None:  # this means look back one day... we take the last 24 hours of data when live no duration
            duration = datetime.timedelta(days=1)
        end_date = datetime.date.fromtimestamp(time.time())
        start_date = end_date - duration

    # only a date provided --> get that day or data
    elif date is not None:
        if type(date) != datetime.date or type(date) != datetime.datetime:
            date = convert_date_format(date, 'datetime')
        start_date = date
        end_date = date

    # only start date given --> use start_date  AND  duration argument
    elif start_date is not None and end_date is None:
        if duration is None:
            end_date = start_date  # do this because only return start_date's data
        else:
            end_date = start_date + datetime.timedelta(duration)
        if end_date > datetime.date.fromtimestamp(time.time()):
            end_date = datetime.date.fromtimestamp(time.time())

    # only end date given --> use end_date  and  duration argument
    elif end_date is not None and start_date is None:
        if duration is None:
            start_date = end_date  # do this because only return start_date's data
        else:
            start_date = end_date - datetime.timedelta(duration)
        if end_date > datetime.date.fromtimestamp(time.time()):
            end_date = datetime.date.fromtimestamp(time.time())

    # if start and end are provided --> use as given
    elif start_date is not None and end_date is not None:
        pass

    # something wrong about the date request to this function. Its not worth trying to handle
    else:
        print('I cant handle the dates as given', flush=True)
        raise DateError

    if data_type == 'price' or data_type == 'prices':
        col_dtype_dict = params['data_format'][exchange]['price_name_and_type']

    if data_type == 'trade' or data_type == 'trades':
        col_dtype_dict = params['data_format'][exchange]['trade_name_and_type']

    # for now these must get fed in as datetime
    date_list = get_date_range(start_date, end_date)

    idx = 0

    for data_date in date_list:
        fp = get_data_file_path(data_type, pair, data_date, port, exchange, params=params)

        try:
            if idx == 0:
                # pdb.set_trace()
                data = pd.read_csv(fp,
                                   header=0,  # ignore col_names... dont treat as data
                                   # names=col_dtype_dict.keys(),     # name of columns
                                   # dtype=col_dtype_dict,            # data type of cols
                                   index_col='msg_time'
                                   )
            if idx > 0:
                # pdb.set_trace()
                data_t = pd.read_csv(fp,
                                     header=0,  # ignore col_names... dont treat as data
                                     # names=col_dtype_dict.keys(),  # name of columns
                                     # dtype=col_dtype_dict,  # data type of cols
                                     index_col='msg_time'
                                     )

                data = pd.concat([data, data_t])
        except FileNotFoundError:
            print('---- file missing: ' + fp, flush=True)
            continue

        idx += 1  # cant enumerate... only increase count if the file is found, otherwise breaks if first file not there

    # convert index_col "YYYY-MM-DD HH:MM:SS" to pd.datetime AFTER price read... trade data is epoch time int, so OK
    if data_type == 'price':
        data.index = pd.to_datetime(data.index)
        data.drop_duplicates(inplace=True)
        data.dropna(inplace=True)
        data.sort_index(inplace=True)

        # fill in missing observations using this dictionary
        observation_dict = {'buyer_is_maker': 0, 'buyer_is_taker': 0, 'buy_vol': 0, 'sell_vol': 0,
                            'buy_base_asset': 0, 'sell_base_asset': 0, 'buy_vwap': np.nan, 'sell_vwap': np.nan}

        empty_ts = pd.Series(data=pd.date_range(start=min(data.index), end=max(data.index), freq='s'))
        mask = empty_ts.isin(data.index)
        mask = ~mask
        missing_times = empty_ts[mask]
        missing_data = pd.DataFrame(observation_dict, index=missing_times)

        if fill_in == True:
            data = pd.concat([data, missing_data])

        # sort everything with the missing enteries filled in as 0
        data.sort_index(inplace=True)

        # and fill in the NaNs from the missing enteries
        data.fillna(method='ffill', inplace=True)
        data.fillna(method='bfill', inplace=True)
        data.fillna(method='ffill', inplace=True)

    return data


def convert_trades_df_to_prices(trades, exchange='standard_trade_format'):
    """reads CSV of trades. converts to prices in some interval

    input :
        trades (pd.dataframe): trades df output by utils.get_live_trades_data()
        exchange (str): helps tell the format
    """

    if exchange == 'standard_trade_format' or exchange in ['binance', 'binanceus', 'kucoin']:
        trades.index = pd.to_datetime(trades.index, unit='s')
        trades['buyer_is_maker'] = trades['buyer_is_maker'].astype('int')
        trades['buyer_is_taker'] = trades['buyer_is_maker'].map({0: 1, 1: 0})
        trades['buy_vol'] = trades['quantity'] * trades['buyer_is_maker']
        trades['sell_vol'] = trades['quantity'] * trades['buyer_is_taker']
        trades['buy_base_asset'] = trades['price'] * trades['buy_vol']
        trades['sell_base_asset'] = trades['price'] * trades['sell_vol']

        trades.drop(columns=['buy_order_id', 'sell_order_id', 'trade_time', 'trade_id'], inplace=True)
        prices = trades.groupby(pd.Grouper(freq='s')).sum()

        prices['buy_vwap'] = prices['buy_base_asset'] / prices['buy_vol']
        prices['sell_vwap'] = prices['sell_base_asset'] / prices['sell_vol']

        prices.drop(columns=['price', 'quantity'], inplace=True)

        # fill in VWAP NaN's due to volume being 0 in a second...
        prices.fillna(method='ffill', inplace=True)
        prices.fillna(method='bfill', inplace=True)
        prices.fillna(method='ffill', inplace=True)

        if exchange == ' kucoin':
            print(3 * 'kucoin not yet supported \n', flush=True)
            raise FileExistsError

        return prices


def trim_data_frame_by_time(df,
                            method='most_recent',
                            days=0,
                            hours=0,
                            minutes=0,
                            seconds=0,
                            millieseconds=0,
                            relative_to_now=False
                            ):
    """trims a dataframe.. for example 'most_recent' hour or 'least_recent' hour of trades

    output (pd.DataFrame): df given, but now trimmed
    ###PAUL dumb, also need the ability to do this from this point in time.. prolly not worth implementing yet
    """
    if method == 'most_recent':
        days = -days
        hours = -hours
        minutes = -minutes
        seconds = -seconds
        millieseconds = -millieseconds

    time_delta = datetime.timedelta(days=days,
                                    hours=hours,
                                    minutes=minutes,
                                    seconds=seconds,
                                    milliseconds=millieseconds
                                    )

    if relative_to_now == True:
        cutoff_time = datetime.datetime.now() + time_delta
    else:
        cutoff_time = max(df.index) + time_delta
    #
    drop_mask = df.index > cutoff_time
    df = df[drop_mask]

    return df


def make_day_of_prices_from_day_of_trades(pair, date, exchange, params=params):
    """makes prices historical price csv using trades.

    input:
        pair
        date
        params
    """

    if type(date) != tuple:
        date = convert_date_format(date, 'tuple_to_day')

    trades = get_data(data_type='trade', pair=pair, date=date, exchange=exchange)
    prices = convert_trades_df_to_prices(trades)
    prices_fp = get_data_file_path(data_type='prices', pair=pair, date=date, exchange=exchange)
    check_if_dir_exists_and_make(fp=prices_fp)
    prices.to_csv(prices_fp)

    return None


def remake_price_files(start_date=None, end_date=None, exchange=None, symbol_mode='native_exchange', params=params):
    """scans the trade history directory for each pair and remakes the price file

    input:
        params (dict): standard params as defined in ./data/config.py
        start_date (tuple): earliest date to start making prices for (inclusive)... other formats may work
        end_date (tuple): latest date to make prices for (inclusive)... other formats may work
    """

    symbol_and_date_errored = []
    symbols_tracked = params['universe'][exchange]['symbols_tracked']

    # try converting the start_date and end_date
    if start_date is not None:
        start_date = convert_date_format(start_date, 'datetime.date')

    if end_date is not None:
        end_date = convert_date_format(end_date, 'datetime.date')

    for symbol in symbols_tracked:

        if symbol_mode == 'native_exchange':
            symbol = convert_symbol(symbol=symbol, in_exchange=exchange, out_exchange='universal')

        # get dir of trade data for that pair
        daily_trade_exchange_symbol_level_dir = get_data_file_path(data_type='trade',
                                              pair=symbol,
                                              date='pair_folder',
                                              exchange=exchange,
                                              params=params, )

        trs = os.listdir(daily_trade_exchange_symbol_level_dir)

        # identify dates with trading data`
        re_date_str = "([0-9]{4}\-[0-9]{2}\-[0-9]{2})"
        dates = [re.search(re_date_str, tr).group(0) for tr in trs]

        for date in dates:
            # two formats needed for the date from the trade file name
            file_date_tup = convert_date_format(date, 'tuple_to_day')
            file_dt = convert_date_format(date, 'datetime.date')

            # assume we don't remake the price file, only if conditions are met
            make_pair_date_prices = False

            # no start or end date --> make everything
            if start_date == None and end_date == None:
                make_pair_date_prices = True

                # only start_date provided
            elif start_date is not None and end_date is None:
                if start_date <= file_dt:
                    make_pair_date_prices = True

            # only end_date provided
            elif start_date is None and end_date is not None:
                if file_dt <= end_date:
                    make_pair_date_prices = True

            # both start_date and end_date were provided
            else:
                if start_date <= file_dt and file_dt <= end_date:
                    make_pair_date_prices = True

            try:
                if make_pair_date_prices:
                    make_day_of_prices_from_day_of_trades(symbol, file_date_tup, exchange)
                    print('MADE:     pair:  ' + symbol + '  date: ' + date + '  exchange: ' + exchange, flush=True)

            except:
                print("  ERRORED \n  ERRORED \n  ERRORED \n  ERRORED \n  ERRORED \n  ERRORED \n ", flush=True)
                print('errored on:   pair:  ' + symbol + '  date: ' + date + '  exchange: ' + exchange, flush=True)
                symbol_and_date_errored.append((symbol, date))

    return symbol_and_date_errored


def find_runs(x):
    """Find runs of consecutive items in an array.
    input:
        x (np.array)

    output:
        run_values (np.array):   value of run
        run_starts (np.array):   index where the run starts
        run_lengths (np.array):  how long the run is (how many times value repeats in a row)
    """

    # ensure array
    x = np.asanyarray(x)
    if x.ndim != 1:
        raise ValueError('only 1D array supported')
    n = x.shape[0]

    # handle empty array
    if n == 0:
        return np.array([]), np.array([]), np.array([])

    else:
        # find run starts
        loc_run_start = np.empty(n, dtype=bool)
        loc_run_start[0] = True
        np.not_equal(x[:-1], x[1:], out=loc_run_start[1:])
        run_starts = np.nonzero(loc_run_start)[0]

        # find run values
        run_values = x[loc_run_start]

        # find run lengths
        run_lengths = np.diff(np.append(run_starts, n))

        return run_values, run_starts, run_lengths


def make_alternating_buy_sell_signal(buy_idxs, sell_idxs, signal_shape):
    """if signal may appear as buy, sell, sell, sell, buy   --transform-->   buy, sell, buy

    input:
        buy_idxs = np.array([0,  500])

        sell_idxs = np.array([110, 300])

        signal_shape = ex: (100000,.)  ###PAUL would be good if multi-dim capable... later things

    output:
        signal  = np.array([1, 0, 0, ..., 0, -1, 0, ..., 0, 1])

    """

    i_in_sell_idxs = 0  # sell idx in queue to be compared to buy_idx
    signal = np.zeros(signal_shape)  # 1 for buy,  -1 for sell,    0 for no action

    for i, buy_idx in enumerate(buy_idxs):
        if i > 5:
            break

        whose_turn = 'buy'  # cant sell something you dont own
        sell_idx = sell_idxs[i_in_sell_idxs]  # set sell_idx for the loop

        if buy_idx < sell_idx:  # set a buy by flipping a zero in signal at the position of buy_idx's value
            if whose_turn == 'buy':  # skip the next sell_idx
                signal[buy_idx] == 1
                whose_turn = 'sell'

            else:  # it is not buys turn yet, go to next buy_idx, see if time for a sell yet
                continue

        if sell_idx < buy_idx:  # set a sell in signal with a -1 at position sell_idx's value
            if whose_turn == 'sell':
                signal[sell_idx] == -1
                whose_turn = 'buy'
            else:  # not sell's turn yet.. move to next sell_idx position and wait for buy
                i_in_sell_idxs += 1

    return signal


def round_step_size(quantity: Union[float, Decimal], step_size: Union[float, Decimal]) -> float:
    """Rounds a given quantity to a specific step size
    :param quantity: required
    :param step_size: required
    :return: decimal
    """
    precision: int = int(round(-math.log(step_size, 10), 0))
    return float(round(quantity, precision))


def round_decimals_up(number: float, decimals: int = 2):
    """
    Returns a value rounded up to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.ceil(number)

    factor = 10 ** decimals
    return math.ceil(number * factor) / factor


def round_decimals_down(number: float, decimals: int = 2):
    """
    Returns a value rounded down to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.floor(number)

    factor = 10 ** decimals
    return math.floor(number * factor) / factor


def check_if_dir_exists_and_make(dir=None, fp=None):

    # check if directory heading to file exists, if not make all required on the way
    if dir is not None:
        if os.path.isdir(dir) == False:
            os.makedirs(dir)

    if fp is not None:
        fp_dirname = os.path.dirname(fp)
        if os.path.isdir(fp_dirname) == False:
            os.makedirs(fp_dirname)

    return None


def reverse_dictionary(d):
    """takes a dictionary and flips the keys and values
    """
    new_dict = {}

    for key in d.keys():
        value = d[key]
        new_dict[value] = key

    return new_dict


def check_if_file_make_dirs_then_write_append_line(file_path, new_line, header=None, thread_lock=False):
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