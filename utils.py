import sys
sys.path.insert(0, "..")

from algos.config import params


from copy import deepcopy
import dotenv
import asyncio
from clickhouse_driver import Client as CH_Client
import datetime
from datetime import timedelta
import dateutil
from decimal import Decimal
import dotenv
import json
import importlib
import lttb
import os
import math
import numpy as np
import pandas as pd
from pandas.tseries.offsets import Minute
import pickle
import pytz
import re
import requests
from typing import Union


dotenv.load_dotenv()  # ###PAUL TODO: do i want to move this somewhere into the params hook? 
data_dir = params['dirs']['data_dir']


def get_secret(key):
    if key not in os.environ:
        raise KeyError(f"Key {key} not found!")
    return os.environ[key]


def init_ch_client(send_receive_timeout=120*60, max_execution_time=120*60): 
    ch_client = CH_Client(host=get_secret('CH_ALGOS_DB_HOST'),
                      port=int(get_secret('CH_ALGOS_DB_PORT')),
                      user=get_secret('CH_ALGOS_DB_USER'),
                      password=get_secret('CH_ALGOS_DB_PASSWORD'), 
                      database=get_secret('CH_ALGOS_DB_DATABASE'),
                      settings={
                                    'send_receive_timeout': send_receive_timeout,  # Timeout in seconds for send/receive operations
                                    'max_execution_time': max_execution_time     # Maximum execution time for a query
                                })
    
    return ch_client
    
    
def init_ccxt_client(exchange='binance_us', type='standard', api_key_names=('pubic', 'private')):
    """
    """

    # Mapping configuration for exchanges
    exchange_config = {
        'binance_us': { 
            'module': 'binanceus',
            'credentials': {
                'apiKey': get_secret(api_key_names[0]),
                'secret': get_secret(api_key_names[1]),
            }
        },

        'kraken': {
            'module': 'kraken',
            'credentials': {
                'apiKey': get_secret(api_key_names[0]),
                'secret': get_secret(api_key_names[1]),
            }
        }

    }

    # Validate exchange
    if exchange not in exchange_config:
        raise ValueError(f"Exchange {exchange} not supported!!!")

    # Determine module base based on type
    module_base = "ccxt" if type == 'standard' else "ccxt.pro"

    # Dynamic import based on exchange and type
    module_name = exchange_config[exchange]['module']
    module = importlib.import_module(f"{module_base}.{module_name}")

    # Access the class from the module dynamically
    # The class name is assumed to be the same as `module_name` with the first letter capitalized
    # class_name = module_name.capitalize()
    if hasattr(module, module_name):
        CCXT_Client = getattr(module, module_name)
    else:
        raise AttributeError(f"Class {class_name} not found in module {module_base}.{module_name}")

    # Initialize and return the client
    credentials = exchange_config[exchange]['credentials']
    ccxt_client = CCXT_Client(credentials)

    return ccxt_client


def wait_for_next_execution(delay_seconds, interval='1min'):
    """Waits until the next execution time, which is the start of the next minute plus a delay.
    
    Note, may want to make functionality to not do something every minute. 
    """

    if interval == '1min':
        # Calculate the next minute mark after the current time plus delay
        next_execution_time = (pd.to_datetime(datetime.datetime.now()).floor('min') \
                            + timedelta(minutes=1) \
                            + timedelta(seconds=delay_seconds)
                            ).to_pydatetime()
        
        # Wait until the next execution time
        while datetime.datetime.now() < next_execution_time:
            time.sleep(0.5)  # Sleep in short intervals to stay responsive
    
    return next_execution_time


async def async_wait_for_next_execution(delay_seconds, interval='1min'):
    """ Asynchronously waits until the start of the next minute plus a specified delay.
    """
    
    if interval == '1min':
        now = datetime.datetime.now()
        next_execution_time = (now + timedelta(minutes=1)).replace(second=0, microsecond=0) \
                               + timedelta(seconds=delay_seconds) 
    
        while datetime.datetime.now() < next_execution_time:
            await asyncio.sleep(1) 

    return next_execution_time


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
            if output_type in ['datetime.date']:
                return datetime.date(year=year, month=month, day=day)
            if output_type in ['datetime', 'datetime.datetime']:
                return datetime.datetime(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            if output_type == 'tuple_to_day':
                y, m, d = str(date[0]), str(date[1]), str(date[2])
                return (y, m, d)
            if output_type in ['pandas', 'pd.datetime']:  # ###PAUL TODO: (datetime should imply to millisecond, which is microsecond in datetime)
                return pd.to_datetime(datetime.date(year=year, month=month, day=day))
            if output_type in ['string_short', 'string_to_day', 'string', 'str']:
                date = datetime.date(year=year, month=month, day=day)
                return date.strftime('%Y-%m-%d')
            if output_type in ['suffix']:
                date = make_date_suffix(date, file_type='.csv')
        # tuple to sec  resolution... ie: [2021, 01, 31, 23, 59, 1]
        if len(date) == 6:
            year, month, day, hour, minute, second = date
            if output_type == 'datetime' or output_type == 'datetime.datetime':
                return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
            if output_type in ['pandas', 'pd.datetime']:
                return pd.to_datetime(datetime.datetime(year=year, month=month, day=day,
                                                        hour=hour, minute=minute, second=second))
            if output_type == 'string_long':
                return date.strftime('%Y-%m-%d %H:%M:%S')

        print("###PAUL make    tuple     to desired output work please", flush=True)

    elif isinstance(date, datetime.date) or isinstance(date, datetime.datetime):
        if output_type == 'epoch':
            return date.timestamp()
        elif output_type in ['string_long', 'string_to_second', 'string']:
            return date.strftime('%Y-%m-%d %H:%M:%S')
        elif output_type in ['string_short', 'string_to_day', ]:
            return date.strftime('%Y-%m-%d')
        elif output_type == 'tuple_to_day' or output_type == "tuple_to_second":
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
        elif output_type == 'pandas':
            return date
        else:
            print(f"datetime conversion to output_type {output_type} from type: {type(date)} is not implemented")
            raise NotImplementedError

    elif isinstance(date, np.datetime64):
        if output_type in ['string_short', 'string_to_day', 'string']:
            # ### NOTE: if numpy goes to nanosecond precision MUST convert to pandas, so just do all the time...
            date = pd.to_datetime(str(date))
            return date.strftime('%Y-%m-%d')

    elif isinstance(date, int) or isinstance(date, float):
        # make the tuple because it is useful for many output types
        year = time.strftime('%Y', time.gmtime(date))
        month = time.strftime('%m', time.gmtime(date))
        day = time.strftime('%d', time.gmtime(date))
        hour = time.strftime('%H', time.gmtime(date))
        min = time.strftime('%M', time.gmtime(date))
        sec = time.strftime('%S', time.gmtime(date))

        tuple_to_day = (year, month, day)
        tuple_to_second = (year, month, day, hour, min, sec)

        if output_type == 'tuple_to_day':
            return tuple_to_day
        elif output_type == 'tuple_to_second':
            return tuple_to_second
        elif output_type in ['pandas', 'pd.datetime']:
            return convert_date_format(tuple_to_second, output_type='pandas')
        else:
            print(f"request for output type: {output_type} not supported for input type: {type(date)}", flush=True)
            raise NotImplementedError

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


# ###PAUL TODO: EAORS considerations
def convert_symbol(symbol, in_exchange, out_exchange, params=params):
    # try:

    # ### special handling of weird use cases
    #
    #
    # here ccxt returns 'BTC-USD' as a universal symbol
    if re.search('USD$', symbol) != None and in_exchange == 'universal' and \
            out_exchange in ['binanceus']:
        symbol += 'T'

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

        # try:
        return params['universe']['universal']['from_universal'][out_exchange][universal_pair]

        # except KeyError:
        #     import pdb;
        #     pdb.set_trace()
        #     # handle the case of tether pairs from exchanges that also have a separate USD (non tether quote)
        #     if 'ether' in universal_pair:
        #         universal_pair = universal_pair.replace('ether', '')  # for tether, not ETH
        #         return params['universe']['universal']['from_universal'][out_exchange][universal_pair]
        #     else:  # there is a problem
        #         raise KeyError


def get_date_list(start_date, end_date, output_type='datetime.datetime', step_size='day'):
    """makes list from start_date to end date

    inputs:
        start_date (datetime.datetime):
        end_date (datetime.datetime):
        output_type (str)

    outputs:
        date_list (list): containing datetime.datetime objects.... unless output_type specified otherwise
    """

    start_date = convert_date_format(date=start_date, output_type=output_type)
    end_date = convert_date_format(date=end_date, output_type=output_type)

    date_list = []
    delta = end_date - start_date  # as timedelta

    for i in range(delta.days + 1):
        date_i = start_date + datetime.timedelta(days=i)

        if output_type != 'datetime.datetime':
            date_i = convert_date_format(date=date_i, output_type=output_type)

        date_list.append(date_i)

    return date_list


# ###PAUL TODO: arg, exchange_format, should be depricated. Everything handled via CCXT 
def convert_trades_df_to_trading_summary(trades):
    """reads CSV of trades. converts to prices in some interval

    input :
        trades (pd.dataframe): trades df output by utils.get_live_trades_data()
        exchange (str): helps tell the format
    """

    """ 
    logic for conversion of which side the trade was on... this is the link for the binance documentation.
    https://developers.binance.com/docs/binance-trading-api/spot#recent-trades-list
    going off this and the line ```"False if trade["m"] else True,``` in  `algos_db/src/data/exchanges/binance_data`
    if side==True in the table algos_db.Trades the seller is the price maker for the trade
    """

    try:
        trades.set_index('timestamp', inplace=True)
    except KeyError:
        if trades.index.name == 'timestamp':
            pass
        else:
            raise KeyError

    try:
        opens = trades['price'].groupby(pd.Grouper(freq='min')).first()
    except:
        import pdb; 
        pdb.set_trace() 

    highs = trades['price'].groupby(pd.Grouper(freq='min')).max()
    lows = trades['price'].groupby(pd.Grouper(freq='min')).min()
    closes = trades['price'].groupby(pd.Grouper(freq='min')).last()

    # override name to be desired col name, currently is "price"
    opens.name = 'open';
    highs.name = 'high';
    lows.name = 'low';
    closes.name = 'close';

    ohlc_df = pd.concat([opens, highs, lows, closes], axis=1)

    trades['buyer_is_maker'] = trades['buyer_is_taker'].map({0: 1, 1: 0})
    trades['buy_base_vol'] = trades['amount'] * trades['buyer_is_maker']
    trades['sell_base_vol'] = trades['amount'] * trades['buyer_is_taker']
    trades['buy_quote_vol'] = trades['buy_base_vol'] * trades['price']
    trades['sell_quote_vol'] = trades['sell_base_vol'] * trades['price']
    trades['total_quote_vol'] = trades['buy_quote_vol'] + trades['sell_quote_vol']
    trades.rename(mapper={'amount': 'total_base_vol'}, axis='columns', inplace=True)

    trades = trades.drop(columns=['exchange', 'symbol', 'price', 'id'])

    # Add one minute offset... otherwise summary comes for the beginning of the minute
    trades.index += Minute(1)
    ohlc_df.index += Minute(1)
    summation_price_data = trades.groupby(pd.Grouper(freq='min')).sum()

    trading_summary = pd.concat([ohlc_df, summation_price_data], axis=1)

    trading_summary['buy_vwap'] = trading_summary['buy_quote_vol'] / trading_summary['buy_base_vol']
    trading_summary['sell_vwap'] = trading_summary['sell_quote_vol'] / trading_summary['sell_base_vol']
    trading_summary['vwap'] = trading_summary['total_quote_vol'] / trading_summary['total_base_vol']

    # fill in VWAP NaN's due to volume being 0 in a second...
    trading_summary.ffill(inplace=True)
    trading_summary.bfill(inplace=True)
    trading_summary.ffill(inplace=True)

    return trading_summary


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
    

def check_df_for_missing_data_and_no_activity(df, freq='min', gap_len=60, col='total_base_vol', no_activity_val=0):
    """ currently built for trading summary given how it fills in a datafame with predetermined observations... 

    # ###PAUL TODO: support freq=None ---- return abnormal intervals where there is no data for long period comparitive to dataset  
    # ###PAUL TODO: build support for pd.series (don't think i want to go into numpy support for this function )
    """

    # get start and end of df
    start_pd_dti = df.index[0]
    end_pd_dti = df.index[-1]

    # make DatetimeIndex containing every period in interval via pandas
    continuous_index = pd.date_range(start=start_pd_dti, end=end_pd_dti, freq=freq)

    # find gaps longer than `gap_len`
    data_in_continuous_series = continuous_index.isin(df.index)
    vals_missing, start_idxs_for_runs, lens_missing = find_runs(data_in_continuous_series)
    false_runs_mask = vals_missing == False  # False, means that its not in the continuous price index, i.e. missing
    missing_long_run_mask = lens_missing > gap_len
    long_missing_runs_mask = np.logical_and(false_runs_mask, missing_long_run_mask)
    start_idxs_missing = start_idxs_for_runs[long_missing_runs_mask]
    lens_missing = lens_missing[long_missing_runs_mask]

    # get start and end of peiords where data is missing
    start_end_tuple_list_missing = []
    for start_idx, run_len in zip(start_idxs_missing, lens_missing):
        start_dti = df.index[start_idx - 1]
        end_dti = df.index[start_idx + run_len + 1]
        start_end_tuple_list_missing.append((start_dti, end_dti))

    # no activity periods ---- EX: looking for no volume on a trading summmary 
    no_activity_series = df[col] == 0
    no_activity_series = no_activity_series.reindex(continuous_index, fill_value=no_activity_val)
    # ###PAUL TODO: in the case that the df is not continuous the below line will add indicies from the df not in the continuous index
    # no_activity_series = reindexed_series.reindex(df.index.union(continuous_index))
    run_values, start_idxs_for_runs, run_lens = find_runs(no_activity_series)
    no_vol_runs = run_values == True
    no_activity_long_run_mask = run_lens > gap_len
    long_no_vol_runs_mask = np.logical_and(no_vol_runs, no_activity_long_run_mask)
    no_activity_run_start_idxs = start_idxs_for_runs[long_no_vol_runs_mask]
    no_activity_run_lens = run_lens[long_no_vol_runs_mask]

    # get (start, end) datetimeindex's for no activity run periods. 
    start_end_tuple_list_no_vol = []
    for start_idx, run_len in zip(no_activity_run_start_idxs, no_activity_run_lens):
        start_dti = df.index[start_idx - 1]
        end_dti = df.index[start_idx + run_len + 1]
        start_end_tuple_list_no_vol.append((start_dti, end_dti))

    missing_and_no_activity_info = \
        {
            'missing_info': \
                {
                    'start_idxs_missing': start_idxs_missing,
                    'lens_missing': lens_missing,
                    'start_end_tuple_list_missing': start_end_tuple_list_missing,
                },
            'no_activity_info': \
                {
                    'no_activity_run_start_idxs': no_activity_run_start_idxs,
                    'no_activity_run_lens': no_activity_run_lens,
                    'start_end_tuple_list_no_vol': start_end_tuple_list_no_vol,
                },
        }

    # # ###PAUL TODO:  printouts removed from above, consider verbose option or simple deletion 
    # if long_missing_runs_mask.sum() > 0:
    #     print(f"- RUNS OVER AN HOUR NOT IN IDX {long_missing_runs_mask.sum()} \n" * 3, flush=True)
    # if long_no_vol_runs_mask.sum() > 0:
    #     print(f"- RUNS OVER AN HOUR WITH NO VOLUME {long_no_vol_runs_mask.sum()} \n" * 3, flush=True)

    return missing_and_no_activity_info


def get_trades_data(exchange, symbol, date=None, start_date=None, end_date=None, ch_client=None):
    """ get trades data from various intenral db sources...
    need a start_date... maybe fix this later...
    input:
    """

    if ch_client is None: 
        ch_client = init_ch_client()

    if date is not None:  # only getting trades for one day  
        
        date_str = convert_date_format(date, 'string')
        query = f"""
                SELECT *
                FROM algos_db.Trades
                WHERE
                    exchange = '{exchange}'
                    AND symbol = '{symbol}'
                    AND toDate(timestamp) = toDate('{date_str}')
                ORDER BY timestamp;
                """
    else: 
        # note in all cases -- not inclusive on the end in order to have no overlap of trades gathered when rolling
        if end_date is not None and start_date is not None:
            end_date_string = convert_date_format(end_date, output_type='string')
            start_date_string = convert_date_format(start_date, output_type='string')
            query_date_str_1 = f"""WITH 
                                    toDateTime('{start_date_string}') as startdate,
                                    toDateTime('{end_date_string}') as enddate"""
            query_date_str_2 = """AND timestamp > startdate
                                AND timestamp <= enddate"""
        elif end_date is None and start_date is not None:
            start_date_string = convert_date_format(start_date, output_type='string')
            query_date_str_1 = f"WITH toDateTime('{start_date_string}') as startdate"
            query_date_str_2 = """AND timestamp > startdate"""
        elif end_date is not None and start_date is None:
            query_date_str_1 = f"WITH toDateTime('{end_date_string}') as enddate"
            query_date_str_2 = """AND timestamp <= enddate"""

        query = f"""
        {query_date_str_1}
        SELECT *
        FROM algos_db.Trades
        WHERE
            exchange = '{exchange}'
            AND symbol='{symbol}'
            {query_date_str_2}
        ORDER BY timestamp;
        """

    # print(f"{query}")
    trades = ch_client.query_dataframe(query)

    try:
        trades.set_index('timestamp', inplace=True)  # replace counting index with time
    except KeyError:
        return 0  # this means there were no trades in the requested interval

    return trades


def downsample_pd_series(series, downsample_n=500_000):
    len_series = series.shape[0]
    counting_idx = np.arange(len_series)
    downsampled_arr = np.array([counting_idx, series]).T
    downsampled_arr = lttb.downsample(downsampled_arr, n_out=downsample_n)

    ilocs = downsampled_arr.T[0, :].astype('int')
    values = downsampled_arr.T[1, :]
    dtis = series.index[ilocs]

    downsampled_series = pd.Series(data=values, index=dtis)

    return downsampled_series, ilocs


# ###PAUL change name of this, and consider moving, I just wanted it out of the notebook
# ###PAUL_RTI_CHECK____
def preprocess_data(df, pct_nan):
    """
        Remove columns with more than 'pct_nan' missing values.

        :pct_nan: frequency threshold to remove signal.
    """
    df_nan = df.apply(lambda x: x.isna().mean())
    keep_col = df_nan[df_nan < 0.05].index
    df = df[keep_col]
    return df


# ###PAUL change name of this, and consider moving, I just wanted it out of the notebook
# ###PAUL this would be a useful function also... but it needs a fequency input , actually already have this built...
#         TODO: may want to apply printed feature making code to this, yes... do this
def preprocessing(df, pct_nan, signal_transformation):
    """ See init method for parameters description.
    """
    df = preprocess_data(df, pct_nan=pct_nan)
    df.fillna(method="ffill", inplace=True)
    df.fillna(method="bfill", inplace=True)
    df.fillna(method="ffill", inplace=True)

    if signal_transformation == "diff":
        df = df.diff()
    elif signal_transformation == "return":
        df = df.pct_change()
    elif signal_transformation == "MA":
        window = 24 if self.freq == "hour" else 30
        df = df - df.rolling(window).mean()
    elif signal_transformation == "z_score":  # ###PAUL look into adding this, may need to employ a max_cut
        window = 30
        df = (df - df.rolling(window).mean()) / df.rolling(window).std()
    df = preprocess_data(df, pct_nan=pct_nan)

    df.fillna(method="ffill", inplace=True)
    df.fillna(method="bfill", inplace=True)
    df.fillna(method="ffill", inplace=True)

    return df


def get_data_file_path(data_type, pair, date='live', port=None, signal=None, exchange=None, pair_mode='asis',
                       params=params):
    """returns string of filepath to requested datafile

    :param port: (str) naming the portfolio strategy for orders and preformance data
    inputs
        data_type (str): options ----  ['price', 'trade', 'order', 'book']  ----
            TODO add live order which means all open orders
            TODO daily data files  add support for book eventually
        pair (str):    pair  ---- 'BTCUSDT'
        date (tuple):    (year, month, day) such as (2021, 01, 31) ---- TODO make other time formats work
    """

    live_data_dir = params['dirs']['live_data_dir']
    ports_data_dir = params['dirs']['ports_data_dir']

    # ###PAUL_todo: once data is saved under universal names the conditional is needed, should be done every time
    if pair_mode == 'asis':  # pair given in exchange's format
        pass
    elif pair_mode == 'universal':
        pair = convert_symbol(pair, in_exchange='universal', out_exchange=exchange, params=params)

    fp = None

    if date != 'path':
        suffix = make_date_suffix(date)

    # TODO: keep this method of keeping data live around... if fast responses eventually desired that system >>>
    # first handle if date is live... if not we attempt to convert it if not a tuple
    if date in {'live'}:
        if data_type in {'trade', 'trades', 'price', 'prices'}:
            live_data_dir = "THIS MOVED TO"  # TODO a reminder for later... trades and prices should be in database
            # TODO: would be good to migrate this functionality to a broader `get_data()`
            if exchange is None:
                return IOError
            elif data_type in {'trade', 'trades'}:
                fp = live_data_dir + 'trades_live/' + exchange + '/' + pair + '/' \
                     + exchange + '_' + pair + '_live_trades.csv'
            elif data_type == 'price' or data_type == 'prices':
                fp = live_data_dir + pair + '/' + pair + '_live_prices.csv'

        # ### portfolio data
        #
        #
        if data_type in {'state_dict', 'orders', 'order', 'open_orders', 'whose_turn', 'last_order_check',
                         'port', 'port_folder', 'port_path', 'closed_order', 'closed_orders', 'orders_closed'}:
            if port is None and signal is None:
                print(f"---- need a `port` or `signal`  name for this data_type = {data_type}")
                return IOError
            elif data_type in {'port', 'port_folder', 'port_path'}:
                fp = ports_data_dir + port + '/'
            elif data_type in {'state_dict'}:
                if port is not None:
                    fp = ports_data_dir + port + '/state_dict.pickle'
                elif signal is not None:
                    fp = live_data_dir + 'signals/' + signal + '/state_dict.pickle'
                else:
                    print(f"need to provide a port or signal to get a state_dict")
                    raise ValueError
            elif data_type in {'open_orders', 'orders_open', 'open', }:
                fp = ports_data_dir + port + '/orders/' + exchange + '/open_orders.csv'
            elif data_type in {'closed_order', 'closed_orders', 'orders_closed', 'closed', }:
                fp = ports_data_dir + port + '/orders/' + exchange + '/closed/' + pair + '/' \
                     + 'orders----' + pair + '----' + suffix
            elif data_type in {'last_order_check', }:
                fp = ports_data_dir + port + '/last_check.txt'
            else:
                fp = None

    # desired ordering...   /  <port_name
    # >  /  <data_type>  /
    #                                              ^^^ orders (open
    # # ### if not exactly passed as a tuple of form ("2021", "01", "31") attempt conversion
    #     date = convert_date_format(date=date, output_type='tuple_to_day')

    elif date == 'path':  # just gets the pair's folder.. will direct to folder of dates for data type
        if exchange is not None:
            if data_type == 'price' or data_type == 'prices':
                fp = live_data_dir + 'price/' + exchange + '/' + pair + '/'
            elif data_type == 'trade' or data_type == 'trades':
                fp = live_data_dir + 'trades_daily/' + exchange + '/' + pair + '/'
            elif data_type == 'book':
                fp = live_data_dir + 'book_daily/' + exchange + '/' + pair + '/'
            elif port is not None:
                if data_type in {'closed_order', 'closed_orders', 'orders_closed', 'closed', }:
                    fp = ports_data_dir + port + '/orders/' + exchange + '/closed/'
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


def check_if_dir_exists_and_make(dir=None, fp=None):
    """acts the same if dir or fp passed, will make the dir or fp
    returns True if directory already existed, False if it did not """

    # check if directory heading to file exists, if not make all required on the way
    if dir is None:
        if fp is not None:
            dir = os.path.dirname(fp)
        else:
            print(f"must provide dir or fp")
            raise ValueError

    if os.path.isdir(dir) == False:
        dir_existed = False
        os.makedirs(dir)
    else:
        dir_existed = True

    return dir_existed


def check_if_file_make_dirs_then_write_append_line(file_path, new_line, header=None):
    # check that the file exists for the correct time period
    if os.path.isfile(file_path):
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

    return


# # ###PAUL these were horrible, but done in a rush. its only meant for framework results... which has been totally
# restructured. once the pipeline is known later (hopefully today) we can put this together.
# # `signal_dict` can all go in 1 dictionary pickled, but the framework results can not
# # the model needs to be saved at a separate path meaning this kind of functionality is needed
# def wrap_up_framework_results_and_model(prices, results_name, model, framework_results, one_run_params):
#     """ ###PAUL TODO: move one_run_params into framework_results
#     """
#     framework_results_fp = f"{data_dir}pickled_framework_results/{results_name}"
#
#     saved_model_fp = f"{data_dir}saved_models/{results_name}"
#
#
#     # ###PAUL THE BELOW SHOULD BE MOVED INTO FUNCTIONALITY IN UTILS for `make_signal_df()` and `make_transacts_df()`
#     # ###PAUL THE BELOW SHOULD BE MOVED INTO FUNCTIONALITY IN UTILS for `make_signal_df()` and `make_transacts_df()`
#     # # ### making signal_df
#     # #
#     # signal_df = pd.DataFrame(framework_results['signal'])
#     # signal_df.columns = ['signal_smoothed']
#     # signal_df = pd.concat([prices.loc[signal_df.index]['vwap'], signal_df], axis=1)
#     # signal_df['port_val'] = framework_results['port_value_ts']
#     # signal_df['signal_not_smoothed'] = framework_results['preds']
#     # signal_df.to_pickle(f"{framework_results_dir_path}preformance_df.pickle")
#     # # ### saving transactions in convenient df form
#     # #
#     # transacts_df = pd.DataFrame.from_records(framework_results['transacts_list'], index='datetime')
#     # transacts_df.to_pickle(f"{framework_results_dir_path}transacts_df.pickle")
#
#
#     # ### wrapping up one_run_params.... for future reproducability
#     #
#     one_run_params_fp = f"{framework_results_dir_path}one_run_params.pickle"
#     with open(one_run_params_fp, 'wb') as f:
#         pickle.dump(one_run_params, f)
#
#
# def read_wrapped_framework_results(results_name):
#     """ unwraps / reads all the results for a certain model run ---- the following are supported
#         "2023_03_22____4_precent_peaks____test_period"
#         "2023_03_22____4_precent_peaks____validation_period"
#     """
#
#     framework_results_dir_path = f"{data_dir}framework_results/{results_name}/"
#     transacts_df = pd.read_pickle(f"{framework_results_dir_path}transacts_df.pickle")
#     signal_df = pd.read_pickle(f"{framework_results_dir_path}preformance_df.pickle")
#
#     # ### wrapping up all model results object for future analysis
#     #
#     framework_results_fp = f"{framework_results_dir_path}framework_results.pickle"
#     with open(framework_results_fp, 'rb') as f:
#         framework_results = pickle.load(f)  # protocol=pickle.HIGHEST_PROTOCOL
#
#     # ### wrapping up one_run_params.... for future reproducability
#     #
#     one_run_params_fp = f"{framework_results_dir_path}one_run_params.pickle"
#     with open(one_run_params_fp, 'rb') as f:
#         one_run_params = pickle.load(f)
#
#     return one_run_params, framework_results, signal_df, transacts_df


def cut_two_pd_dti_objects_to_matching_dtis(dti_obj_1, dti_obj_2):
    """force two pandas objects (pd.Series or pd.DataFrame to have the same date time index
    """

    start_dt = max(min(dti_obj_1.index), min(dti_obj_2.index))
    end_dt = min(max(dti_obj_1.index), max(dti_obj_2.index))
    dti_obj_1 = dti_obj_1.loc[start_dt:end_dt]
    dti_obj_2 = dti_obj_2.loc[start_dt:end_dt]

    indicies_equal = dti_obj_1.index.equals(dti_obj_2.index)
    if indicies_equal != True:
        print(f"observations missing from one pandas object")
        raise IndexError

    return dti_obj_1, dti_obj_2


def fill_missing_minutes(dataframe, freq='1min', verbose=False):
    """ looks at the dataframe and fills in the missing observations with NaNs
    """

    dataframe = dataframe.sort_index()
    expected_index = pd.date_range(start=dataframe.index[0], end=dataframe.index[-1], freq=freq)
    num_expected = expected_index.shape[0]
    missing_minutes = expected_index[~expected_index.isin(dataframe.index)]
    missing_data = pd.DataFrame(index=missing_minutes)
    missing_data = missing_data.assign(**{col: np.nan for col in dataframe.columns})
    num_missing = missing_data.shape[0]
    dataframe = pd.concat([dataframe, missing_data])
    dataframe = dataframe.sort_index()
    p_missing = num_missing / num_expected

    if verbose:
        print(f"number of expected enteries: {num_expected} \n"
              f"number of expected enteries: {num_expected} \n"
              f"proportion of enteries missing: {p_missing} \n"
              f"")

    return dataframe


def fill_trading_summary(trading_summary, out_cols=None):
    """ function specific to `trading_summary` dataframe becasue some columns fill with zeros other interpolated
    """

    zero_cols = ['total_base_vol', 'buyer_is_maker',
                 'buyer_is_taker', 'buy_base_vol', 'sell_base_vol', 'buy_quote_vol',
                 'sell_quote_vol', 'total_quote_vol', ]

    interpolate_cols = ['open', 'high', 'low', 'close', 'buy_vwap', 'sell_vwap', 'vwap']

    # used if a supset of trading summary is given to this function (for example only the vwap col)
    out_cols = list(trading_summary.columns)
    zero_cols = [item for item in zero_cols if item in out_cols]
    interpolate_cols = [item for item in interpolate_cols if item in out_cols]

    trading_summary = fill_missing_minutes(dataframe=trading_summary)  # add missing observations to trading summary
    trading_summary[zero_cols] = trading_summary[zero_cols].fillna(0)
    trading_summary[interpolate_cols] = trading_summary[interpolate_cols].interpolate()
    trading_summary[interpolate_cols] = trading_summary[interpolate_cols].ffill()
    trading_summary[interpolate_cols] = trading_summary[interpolate_cols].bfill()

    return trading_summary


def fill_trading_summary_interpolating_missing_minutes(trading_summary):
    """designed to take one day of a `trading_summary` and fill in any missing minutes

    because of the strucutre of how trading summaries are made day by day (on a historical basis) for 2021-03-13 it assumes that
    the first observation should be 2021-03-13 00:01:00 and last should be 2021-03-14 00:00:00
    it then makes the `full_index` of every minute in that time span where the rows are NaNs then filled by a custom fulling function
    """
    # Extract the day from the first row
    day = trading_summary.index[0].date()

    # Create datetime index for the entire day, starting from 00:01:00
    full_index = pd.date_range(start=pd.Timestamp(day) + pd.Timedelta(minutes=1),
                               end=pd.Timestamp(day) + pd.Timedelta(days=1),
                               freq='min')

    # Reindex the DataFrame with the full index, filling missing rows with NaN
    trading_summary = trading_summary.reindex(full_index)
    trading_summary = fill_trading_summary(trading_summary)

    return trading_summary


def push_trading_summary_to_clickhouse(trading_summary, exchange, symbol, overwrite_mode='python_side', output='quiet', ch_client=None):
    """ ###PAUL TODO: in push_trading_summary_to_clickhouse() make sure that duplicate rows aren't being pushed
    (probably best to make a parameter overwrite defaulted to True) to ensure the new row has
    a unique ['timestamp ticker, exchange] combo
    """
    if ch_client is None: 
        ch_client = init_ch_client()

    table = 'algos_db.TradingSummary' # ###PAUL TODO: eventually want to use the new overwrite hook for
    # TODO: trades and signals too, will need to handle unique identifiers for each table...
    # TODO:
    trading_summary = fill_trading_summary(trading_summary=trading_summary)
    check_minute_integrity(dataframe=trading_summary)

    trading_summary['exchange'] = exchange
    trading_summary['symbol'] = symbol
    trading_summary.index.name = 'timestamp'

    trading_summary = trading_summary.astype({'buyer_is_maker': int, 'buyer_is_taker': int})

    existing_dates = from_table_get_existing_dates_in_series(ch_client,
                                                             table=table,
                                                             exchange=exchange,
                                                             symbol=symbol,
                                                             series=trading_summary, )

    if overwrite_mode == 'python_side':
        idxs_to_drop = []
        for idx in trading_summary.index:
            if idx.to_pydatetime() in existing_dates:
                idxs_to_drop.append(idx)
    if overwrite_mode == 'in_clickhouse':
        delete_observations(exchange=exchange, symbol=symbol, datetimes=existing_dates, table=table)

    if output == 'verbose':
        print(f"there were {len(idxs_to_drop)} duplicates prevented from being entered ---- "
              f" grouped by  [timestamp, exchange, symbol]")
    trading_summary = trading_summary.drop(idxs_to_drop)

    trading_summary['time_created'] = datetime.datetime.now(pytz.UTC)
    num_rows_entered = ch_client.execute("INSERT INTO algos_db.TradingSummary VALUES",
                                         trading_summary.reset_index().to_dict('records'))

    return num_rows_entered


def make_day_of_trading_summary_push_to_db(exchange, symbol, date, overwrite_mode='python_side', ch_client=None): 
    """
    """
    
    if ch_client is None: 
        ch_client = init_ch_client()

    trades = get_trades_data(exchange=exchange, symbol=symbol, date=date)

    if not isinstance(trades, pd.DataFrame) or trades.empty:
            print(f""" there were no trades for exchange: {exchange} -- symbol: {symbol} -- on date: {date} """)
            raise Warning
            return 0 
        
    trading_summary = convert_trades_df_to_trading_summary(trades)

    push_trading_summary_to_clickhouse(trading_summary=trading_summary,
                                        exchange=exchange, 
                                        symbol=symbol, 
                                        overwrite_mode=overwrite_mode, 
                                        ch_client=ch_client)

    return trading_summary


def make_trading_summary_from_trades_in_batches(exchange, 
                                                symbol, 
                                                date=None, 
                                                start_date=None, 
                                                end_date=None, 
                                                freq='W', 
                                                overwrite_mode='python_side', 
                                                ch_client=None):
    """ make and get trading summary for long period of time

    only useful when adding new assets as trades table can not be queried over long
    periods of time because they can take too much memory. This will query in intervals of `freq` and combine the
    TradingSummary table which can be 1000x smaller than the trades table for the same time period.

    input:
        freq (str): step size to go by, see: https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
    """

    if end_date is not None and start_date is None:
        raise ValueError  # ###PAUL TODO:  don't want to support going forever forward, need to reconclie this view with date='live' option... i like live 
    
    if start_date is not None:
        start_date = convert_date_format(start_date, output_type='pandas')  # outputs a Timestanp
    if end_date is not None:
        end_date = convert_date_format(end_date, output_type='pandas')  # outputs a Timestanp
    else:  # if end date is none we want thru live ---- add a minute past now to ensure all minute prices grabbed
        # ###PAUL TODO: check if dev2 / eu-dev are in UTC time
        now = time.time() + 60
        end_date = convert_date_format(now, output_type='pandas')

    date_range_arr = pd.date_range(start=start_date, end=end_date, freq=freq)

    # setup iter start and end date for loop 
    iter_start_date = date_range_arr[0]
    date_range_arr = date_range_arr[1:]

    num_iterations = date_range_arr.shape[0]
    df_list = []

    for iter_count, date in enumerate(date_range_arr):
        iter_end_date = date
        if iter_count % 10 == 0:
            print(
                f"""    make trading_summary for {symbol} on {exchange} ----
                iter: {iter_count + 1} of {num_iterations} ---- start: {iter_start_date}  --  end: {iter_end_date}""",
                flush=True)

        trades = get_trades_data(exchange=exchange,
                                 symbol=symbol,
                                 start_date=iter_start_date,
                                 end_date=iter_end_date,)

        if not isinstance(trades, pd.DataFrame) or trades.empty:
            # This handles both cases:  when trades is 0     or    its empty
            continue
        else:
            trading_summary = convert_trades_df_to_trading_summary(trades)
            df_list.append(trading_summary)
            iter_start_date = iter_end_date

    if len(df_list) != 0:
        all_trading_summary = pd.concat(df_list)

        pre_cleaned_nans = all_trading_summary.isna().sum().sum()
        all_trading_summary = all_trading_summary[~all_trading_summary.index.duplicated(keep='first')]
        all_trading_summary = fill_trading_summary(all_trading_summary)
        all_trading_summary = all_trading_summary[~all_trading_summary.index.duplicated(keep='first')]
        post_cleaned_nans = all_trading_summary.isna().sum().sum()

        print(f" - final data clean ---- pre_cleaned_nans: {pre_cleaned_nans} "
              f"                    ---- post_cleaned_nans {post_cleaned_nans}",
              flush=True)
    else:
        print(f"no data for request to make a summary of trading ")
        return 0  # no data for

    push_trading_summary_to_clickhouse(trading_summary=all_trading_summary, 
                                       exchange=exchange, 
                                       symbol=symbol, 
                                       overwrite_mode=overwrite_mode,
                                       ch_client=ch_client)

    return all_trading_summary


def check_minute_integrity(dataframe, verbose=False):
    # Ensure DataFrame is sorted by DateTimeIndex
    dataframe = dataframe.sort_index()

    # Generate the expected DateTimeIndex with minute frequency
    expected_index = pd.date_range(start=dataframe.index[0], end=dataframe.index[-1], freq='1min')

    # Compare the expected index with the DataFrame's DateTimeIndex
    if dataframe.index.equals(expected_index):
        if verbose:
            print("The DataFrame's DateTimeIndex includes every minute.")
    else:
        print("The DataFrame's DateTimeIndex is missing minute(s).")
        raise ValueError

    return None


def create_trading_summary_table():
    query = """
            create table if not exists algos_db.TradingSummary
            (
                timestamp date,  -- summary metrics for the close of the minute
                symbol VARCHAR(32),
                exchange VARCHAR(32),
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                total_base_vol FLOAT,
                buyer_is_maker int,
                buyer_is_taker int,
                buy_base_vol FLOAT,
                sell_base_vol FLOAT,
                buy_quote_vol FLOAT,
                sell_quote_vol FLOAT,
                total_quote_vol FLOAT,
                buy_vwap FLOAT,
                sell_vwap FLOAT,
                vwap FLOAT
            )
            ENGINE  = MergeTree()
            ORDER BY timestamp;
        """

    ch_client = init_ch_client()
    ch_client.execute(query)


def from_table_get_existing_dates_in_series(ch_client, table, exchange, symbol, series):
    """assumes the series has a sorted datetime index"""

    str_start = series.index[0].strftime("%Y-%m-%d %H:%M:%S")
    str_end = series.index[-1].strftime("%Y-%m-%d %H:%M:%S")

    # get existing data in the date range with matching
    query = f"""SELECT timestamp
                FROM {table}
                WHERE exchange = '{exchange}' 
                    AND symbol = '{symbol}'
                    AND timestamp BETWEEN '{str_start}' AND '{str_end}' """
    existing_dates = ch_client.execute(query)
    existing_dates = set([_[0] for _ in existing_dates])

    return existing_dates


def delete_observations(ch_client, table, exchange, symbol, datetimes, ):
    """will delete observations from a given table given [exchange, symbol, datetimes, table]

    input:
        exchange (str):
        symbol (str):
        datestimes (set): from `from_table_get_existing_dates_in_series(ch_client, table, exchange, symbol, series)`
        table (str): name of the table ---- EX: 'algos_db.TradingSummary
    """

    datetime_strs = [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in datetimes]
    datetime_list_str = ', '.join(f"'{dt_str}'" for dt_str in datetime_strs)
    delete_query = f"""DELETE FROM {table}
                       WHERE exchange = '{exchange}'
                           AND symbol = '{symbol}'
                           AND timestamp IN ({datetime_list_str})"""
    ch_client.execute(delete_query)


def get_binance_data_zip_file(save_path, market, data_type, symbol, year, month, day=None, interval=None, unzip=True):
    """downloads the zip file for binance data based on given input
    """

    base_url = "https://data.binance.vision"

    # Validate and normalize market and data_type
    if market.lower() not in ["spot", "futures"]:
        raise ValueError("Invalid market. It must be either 'spot' or 'futures'")
    market = market.lower()

    if data_type.lower() not in ["klines", "trades"]:
        raise ValueError("Invalid data type. It must be either 'klines' or 'trades'")
    data_type = data_type.lower()

    # Make sure month and day are two digits
    month = str(month).zfill(2)

    # Check if day is provided
    if day is not None:
        frequency = "daily"
        day = str(day).zfill(2)
    else:
        frequency = "monthly"
        day = ""

    # Construct the URL based on the data type
    if data_type == "klines":
        if interval is None:
            raise ValueError("Interval must be provided for klines data")
        filename = f"{symbol}-{interval}-{year}-{month}{day}.zip"
        url = f"{base_url}/data/{market}/{frequency}/klines/{symbol}/{interval}/{filename}"
    elif data_type == "trades":
        filename = f"{symbol}-trades-{year}-{month}-{day}.zip"
        url = f"{base_url}/data/{market}/{frequency}/trades/{symbol}/{filename}"

    # Full path for the zip file
    zip_filepath = os.path.join(save_path, filename)

    # Download the file
    print(f"Downloading {filename} to {zip_filepath}...")
    response = requests.get(url, stream=True)
    with open(zip_filepath, 'wb') as fd:
        for chunk in response.iter_content(chunk_size=1024):
            fd.write(chunk)

    # # If unzip is True, extract the zip file and load the data into a pandas DataFrame
    # if unzip:
    #     csv_filepath = zip_filepath.replace(".zip", ".csv")
    #     print(f"Extracting {zip_filepath}...")
    #     with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
    #         zip_ref.extractall(save_path)
    #     print(f"Loading {csv_filepath} into a pandas DataFrame...")
    #     df = pd.read_csv(csv_filepath)
    #     return df

    return zip_filepath


def update_trading_summary_table(exchange='binance', symbol='BTC-USDT', output='quiet', overwrite_mode='python_side', ch_client=None):
    """ gets the last time in the trading summary table and then makes the trading summary table up to the current point
    # ###PAUL TODO: remove default values from this... I dont like that they are here. It seems like it could lead to issues
    """
    if ch_client is None: 
        ch_client = init_ch_client()

    query = f""" SELECT MAX(timestamp)
                 FROM algos_db.TradingSummary
                 WHERE symbol = '{symbol}' 
                    AND exchange = '{exchange}';"""
    last_trading_summary_datetime = ch_client.execute(query)[0][0] - timedelta(minutes=60)  # ###PAUL_del_later ---- the time delta is not needed but we use it to ensure overwrite in push is working correctly

    trades_df = get_trades_data(exchange=exchange, symbol=symbol, start_date=last_trading_summary_datetime, end_date=None)

    if isinstance(trades_df, pd.DataFrame):
        new_trading_summary_info = convert_trades_df_to_trading_summary(trades_df)
        new_trading_summary_info = new_trading_summary_info[new_trading_summary_info.index > last_trading_summary_datetime]
    elif trades_df == 0:
        return None

    if new_trading_summary_info.shape[0] != 0:
        push_trading_summary_to_clickhouse(trading_summary=new_trading_summary_info, 
                                           exchange=exchange, 
                                           symbol=symbol, 
                                           overwrite_mode=overwrite_mode, 
                                           output='quiet',
                                           ch_client=ch_client,)


def get_query_date_strings(start_date, end_date):
    """ start_date < timestamp   &&  timestamp <= end_date   ----  non-inclusive then inclusive points in the timespan

    """
    if end_date is not None and start_date is None:
        print(f"warninng: running query with no start or end. could take awhile and memory overload")
        query_date_str_1 = f""
        query_date_str_2 = f""

    if start_date is not None:
        start_date = convert_date_format(start_date, output_type='pandas')  # outputs a Timestamp

    if end_date is not None:
        end_date = convert_date_format(end_date, output_type='pandas')  # outputs a Timestamp
    else:  # if end date is none we want thru live ---- add a minute past now to ensure all minute prices grabbed
        now = time.time() + 60  # ran into issues having this directly in fn input below ..?
        end_date = convert_date_format(now, output_type='pandas')

    # note in all cases -- not inclusive on the end in order to have no overlap of trades gathered when rolling
    # not inclusive on start because we want all times greater when querying last_decision_time=last_decision_time
    if end_date is not None and start_date is not None:
        end_date_string = convert_date_format(end_date, output_type='string')
        start_date_string = convert_date_format(start_date, output_type='string')
        query_date_str_1 = f"""WITH 
                                       toDateTime('{start_date_string}') as startdate,
                                       toDateTime('{end_date_string}') as enddate"""
        query_date_str_2 = """AND timestamp > startdate
                                  AND timestamp <= enddate"""
    elif end_date is None and start_date is not None:
        start_date_string = convert_date_format(start_date, output_type='string')
        query_date_str_1 = f"WITH toDateTime('{start_date_string}') as startdate"
        query_date_str_2 = """AND timestamp > startdate"""
    elif end_date is not None and start_date is None:
        end_date_string = convert_date_format(end_date, output_type='string')
        query_date_str_1 = f"WITH toDateTime('{end_date_string}') as enddate"
        query_date_str_2 = """AND timestamp <= enddate"""

    return query_date_str_1, query_date_str_2


def query_trading_summary(exchange, symbol, start_date, end_date, columns='all', ch_client=None):
    """ queries trading summary table
    ###PAUL TODO: the start/end date handling in this came from two functions, can be merged and cleaned
    """

    query_date_str_1, query_date_str_2 = get_query_date_strings(start_date, end_date)

    # preprocessing on symbol, amber data format is -->  f"btc_usdt"   vs   the EAORS -->  f"BTC-USDT"
    symbol = symbol.upper().replace('_', '-')  # needed for trade queries (keep for now though)

    if columns == 'all':
        cols_str = f"*"
    else:
        if 'timestamp' not in columns:
            columns.append('timestamp')
        cols_str = ', '.join([str(elem) for elem in columns if isinstance(elem, str)])

    query = f"""
        {query_date_str_1}
        SELECT {cols_str}
        FROM algos_db.TradingSummary
        WHERE
            exchange = '{exchange}'
            AND symbol='{symbol}'
            {query_date_str_2}
        ORDER BY timestamp;
            """

    if ch_client == None:
        print(f"warning -- clickhouse client set to none in utils.py `query_trading_summary()`\n"*3)
        ch_client = init_ch_client()

    trading_summary = ch_client.query_dataframe(query)

    try:
        trading_summary = trading_summary.set_index('timestamp')  # replace counting index with time
    except KeyError:
        return 0  # this means there were no trades in the requested interval

    return trading_summary


def get_signal_id(signal_name, ):
    """gets the `signal_id` (int) for a given `signal_name`, option to add signal_id if there is one"""
    ch_client = init_ch_client()
    query = f"""SELECT signal_id FROM algos_db.AlgosSignalNames WHERE signal_name = '{signal_name}';"""
    signal_id = ch_client.execute(query)
    assert (len(signal_id) <= 1)
    signal_id = False if signal_id == [] else signal_id[0][0]

    return signal_id


def add_signal_name_to_foreign_key_table(signal_name):
    """inserts a signal name into algos_db.AlgosSignalNames if it is not there already, otherwise raises an error
    returns the signal_id that now corresponds to that signal_name
    """

    signal_id = get_signal_id(signal_name, )
    if signal_id is not False:
        raise ValueError(f"Signal name '{signal_name}' already exists in SignalNames.")
    else:
        ch_client = init_ch_client()
        signal_id = ch_client.execute('SELECT max(signal_id) FROM algos_db.AlgosSignalNames')[0][0]
        signal_id = signal_id + 1
        ch_client.execute(f"""INSERT INTO algos_db.AlgosSignalNames (signal_id, signal_name) VALUES""",
                          [(signal_id, signal_name)])

        return signal_id


def bulk_insert_signal_observations(signal_name, signal):

    print(f"dont want this to work without adding the logic to add trading summary which checks "
          f"for matching existing times we have observations for (should add a keep or replace mode) ")
    raise NotImplementedError

    # need signal as a dataframe (if it comes as a series convert it)
    if type(signal) == pd.Series:
        signal = pd.DataFrame(signal, columns=['value'])
        signal.index.name = 'timestamp'

    ch_client = init_ch_client()

    query = f"SELECT signal_id FROM algos_db.AlgosSignalNames WHERE signal_name = '{signal_name}'"
    signal_id = ch_client.execute(query)[0][0]  # comes as [(1,)]

    if signal_id:  # the above query returns False if there is no signal name matching
        signal['signal_id'] = signal_id
        num_rows_entered = ch_client.execute("INSERT INTO algos_db.AlgosSignals VALUES",
                                             signal.reset_index().to_dict('records'))
    else:
        print(f"Signal name {signal_name} does not exist in SignalNames.")

    return num_rows_entered


def query_signal_by_name(signal_name, start_date=None, end_date=None):
    ch_client = init_ch_client()

    query = f"SELECT signal_id FROM algos_db.AlgosSignalNames WHERE signal_name = '{signal_name}'"
    signal_id = ch_client.execute(query)[0][0]  # comes as [(1,)]

    query_date_str_1, query_date_str_2 = get_query_date_strings(start_date, end_date)
    query = f"""
        {query_date_str_1}
        SELECT timestamp, value
        FROM algos_db.AlgosSignals
        WHERE signal_id = '{signal_id}'
        {query_date_str_2}
        ORDER BY timestamp;
        """

    # query = f"""
    #     {query_date_str_1}
    #     SELECT timestamp, value
    #     FROM algos_db.AlgosSignals AS s
    #     JOIN algos_db.AlgosSignalNames AS sn ON s.signal_id = sn.signal_id
    #     {query_date_str_2}
    #     AND sn.signal_name = '{signal_name}'
    #     ORDER BY timestamp;
    #     """

    # print(f"{query}")
    signal = ch_client.query_dataframe(query)

    try:
        signal = signal.set_index('timestamp')  # replace counting index with time
        # signal = pd.DataFrame(signal, columns=['timestamp', 'value'])
    except KeyError:
        return 0  # this means there were no trades in the requested interval

    return signal


def get_latest_signal_timestamp(signal_name):
    ch_client = init_ch_client()

    return timestamp


def update_signals_table(signal, signal_name=None, signal_id=None, overwrite=False, ch_client=None):
    """ gets the last time in the trading summary table and then makes the trading summary table up to the current point
    # ###PAUL TODO: add overwrite argument which overwrites a signal
    """
    signal.columns = ['value']
    signal.index.name = 'timestamp'  # sometimes it comes as 'datetime' if not in the live pipeline
    # TODO: are we comfortable with this ugly index renaming fix???

    if ch_client is None:
        print(f"warning ch_client set to None in `update_signals_table` \n *3")
        ch_client = init_ch_client()

    if signal_id is None:
        signal_id = get_signal_id(signal_name)

    query = f"""SELECT MAX(timestamp) FROM algos_db.AlgosSignals WHERE signal_id={signal_id};"""
    latest_signal_timestamp = ch_client.execute(query)[0][0]

    if overwrite is False:
        signal_to_push = signal[signal.index > latest_signal_timestamp]
        signal_to_push = pd.DataFrame(signal_to_push, columns=['value'])
        signal_to_push['signal_id'] = signal_id
    else:  # ###PAUL TODO:  handle this with the same pattern (made a function for this for trading_summary (& trades?)
        raise NotImplementedError

    num_rows_entered = ch_client.execute("INSERT INTO algos_db.AlgosSignals VALUES",
                                         signal_to_push.reset_index().to_dict('records'))

    return num_rows_entered


def write_dict_to_json(dict_obj, fp):
    with open(fp, 'w') as file:
        json.dump(dict_obj, file)


def read_json_to_dict(fp):
    with open(fp, 'r') as file:
        dict_obj = json.load(file)
    return dict_obj


def remove_duplicates_from_trading_summary():
    """removes duplicates from trading summary in clickhouse based on input parameters"""

    query = """ALTER TABLE algos_db.TradingSummary DELETE WHERE (timestamp, exchange, symbol) IN (
    SELECT timestamp, exchange, symbol
    FROM (
            SELECT timestamp, exchange, symbol
            FROM algos_db.TradingSummary
            GROUP BY timestamp, exchange, symbol
            HAVING count(*) > 1
            ));"""

    ch_client = init_ch_client()
    ch_client.execute(query)


def round_step_size(quantity: Union[float, Decimal], step_size: Union[float, Decimal]) -> float:
    """Rounds a given quantity to a specific step size
    :param quantity: required
    :param step_size: required
    :return: decimal
    """
    precision: int = int(round(-math.log(step_size, 10), 0))
    return float(round(quantity, precision))


def get_mutual_min_max_datetimes(pandas_objects):
    # Initialize min_date and max_date with the values of the first DataFrame
    min_date = pandas_objects[0].index.min()
    max_date = pandas_objects[0].index.max()

    # Iterate over the pandas objects and update min_date and max_date
    for df in pandas_objects[1:]:
        current_min = df.index.min()
        current_max = df.index.max()

        # If the current min date is later than the overall min date, update min_date
        if current_min > min_date:
            min_date = current_min

        # If the current max date is earlier than the overall max date, update max_date
        if current_max < max_date:
            max_date = current_max

    # Check if there is any overlap
    if min_date > max_date:
        print("There is no overlap in dates among the provided dataframes.")
        return None, None

    return min_date, max_date


def deduplicate_df_on_index_only(df):
    df = df.reset_index()
    df = df.drop_duplicates(subset='index')
    df = df.set_index('index')

    return df


# ### DATA UTILS    TODO: consider including these things in a data_utils.py at the top level
def insert_trades(ccxt_trades): 
    """list of  trades, the historical fetch_trades() has format 
        {   'amount': 0.00654,
            'cost': 285.8708556,
            'datetime': '2023-12-07T16:51:43.789Z',
            'fee': None,
            'fees': [],
            'id': '25243312',
            'info': {'M': True,
                    'T': '1701967903789',
                    'a': '25243312',
                    'f': '26655598',
                    'l': '26655598',
                    'm': True,
                    'p': '43711.14000000',
                    'q': '0.00654000'},
            'order': None,
            'price': 43711.14,
            'side': 'sell',
            'symbol': 'BTC/USDT',
            'takerOrMaker': None,
            'timestamp': 1701967903789,
            'type': None}
        # ###PAUL TODO: figure out optimal way to work formatting into config. 
    """

    if type(ccxt_trades) == pd.DataFrame: 
          cc    

    for trade in ccxt_trades: 

        trade = {'timestamp': trade['datetime'],  # ###PAUL TODO: gon need to verify this 
                 'id': trade['id'], 
                 'price': trade['price'],
                 'amount': trade['amount'],
                 'buyer_is_taker': 1 if trade['side'] == 'buy' else 0 
        }

        data_tuple = tuple(data_dict.values())

    data_tuples = [tuple(d[col] for col in columns_order) for d in data_dicts]
