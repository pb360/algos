#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-

# ###PAUL_refractor
# ###PAUL_refractor
"""
after getting the bot running on /algos/ services
pairs_tracked --> tickers_traded_universial
- This logic implies that the FOREIGN ticker = UNIVERSIAL ticker
-                         and      US ticker = EXCHANGE   ticker
- this will be the new nomenclature: ^^^^^^^^^^^^^^^^^^^^^^^^^^
----> convert_pair_foreign_to_us(foreign_ticker) --> convert_pair_universial_to_exchange(universial_t)
----> convert_pair_us_to_foreign(us_ticker)      --> convert_pair_exchange_to_universial(exchange_t)
"""
# ###PAUL_refractor
# ###PAUL_refractor

# ### portfolio name
#
#
port_name = 'sma_v1_equal_dist'
exchange = 'binance_us'  # ###PAUL should this be inherited from params?
data_exchange = 'binance_foreign'

iter_count = 0  # counter for place_order_on_signals

# ### imports
#
#

# ### time zone change... this must happen first and utils must be imported first
# ### time zone change... this must happen first and utils must be imported first
import os
import time

os.environ['TZ'] = 'UTC'
time.tzset()
# ### time zone change... this must happen first and utils must be imported first
# ### time zone change... this must happen first and utils must be imported first


# import ast
# import concurrent.futures
#
# import datetime
# from decimal import Decimal
# import json
# import math
# import numpy as np
# import os
import pandas as pd
# import platform
# import plotly
# from plotly.subplots import make_subplots
# import plotly.graph_objects as go
# import re
# import signal
# import sys
# import time
from twisted.internet import task, reactor
# from typing import Union

# local imports
#
#
import config
from utils import *

sys.path.append('/mnt/algos/ext_packages/sams_binance_api')  # # path containing sams binance api

from binance.client import Client
from binance.websockets import BinanceSocketManager

# time the script from start to first trade
START_TIME = time.time()
this_scripts_process_ID = os.getpid()

# ### definitions
#
#
params = config.params
# params['port_name'] = port_name  # ###PAUL_refractor i dont think this works under the remodel
op_sys = params['constants']['os']

# #
# ##
# ### for deployment only
# assert(exchange in params['systemd_control']['active_data_exchanges']) << see below for correct line
# assert(port_name in params['active_services']['ports'].keys())
# ###
# ##
# #


# ### API things
#
#
api_key = params['keys']['protonmail_sub_acct_key']
secret_key = params['keys']['protonmail_sub_acct_secret']

### create client to pair with binance
client = Client(
    api_key=api_key,
    api_secret=secret_key,
    requests_params=None,
    tld='us'  ### paul this is for the country... need to set that for sure.... careful on other exchanges
)

# ### utility constants
#
#
prices_dtype_dict = params['data_format'][exchange]['price_name_and_type']
order_filters_names_type_dict = params['data_format'][exchange]['order_filters_name_type']

tickers_foreign_to_us_dict = params['universe'][exchange]['tickers_foreign_to_us_dict']
tickers_us_to_foreign_dict = params['universe'][exchange]['tickers_us_to_foreign_dict']

# ###PAUL_refractor...
pairs_tracked = params['universe'][exchange]['pairs_tracked']
pairs_tracked = params['universe'][exchange]['tickers_traded']  # ###PAUL_refractor... temp soln
# ###PAUL_refractor the above line just gives the tickers I want for now. this is the biggest refractor
# ###PAUL_refractor adjustment... it will need attention later


# ###PAUL_refractor. delete this later... or reconsider how its handled
if exchange == 'binance_us':
    try:
        # editing pairs_tracked
        pairs_tracked.remove('XRPUSDT')
        pairs_tracked.remove('XRPBTC')
    except ValueError as e:
        print('---- XRP not in list of tickers so no removal', flush=True)
        print(e, flush=True)

for ticker_t in pairs_tracked:
    btc_quote_bool = re.search('BTC$', ticker_t)  # checks that BTC is the ending of the ticker

    # remove all bitcoin denominated tickers from trading
    if btc_quote_bool != None:
        pairs_tracked.remove(ticker_t)  # remove if match

# ### Global Variables
#
#
actions_dict = dict()  # {ticker: one_of --> ['buy_again', 'buy', 'neutural', 'sell', 'sell_again']}
whose_turn_dict = dict()  # whose_turn is it is {ticker: ['buy' or 'sell']}
prices_dfs_dict = dict()  # {ticker: price_df}
short_term_prices_dict = dict()  # {ticker: price_df}
last_prices_dict = dict()  # {ticker: most_recent_price}
signal_dfs_dict = dict()  # {ticker: signal}  # ###PAUL all vari's standard except this one
# ###PAUL_refractor: should also update how prices are made. only care about prices on the exchange that
# ###PAUL_refractor: is being traded.. the signal may come from elsewhere but where orders placed matters

port_value = 0  # total port value (in USD denomination)
port_usd = 0  # USD currently in the portfolio (available for purchasing stuff)
port_allocation_dict = dict()  # prortion value each ticker gets - ex: {'BTCUSDT':0.75, 'ETHUSDT':0.25}

# value held (in base asset) ----  formatted:  {'free':free, 'locked':locked, 'total':total}
# NOTE: doesnt consider quote/pair/multi tickers with same base, just all merged in one
port_holdings_dict = dict()

# each is structured bag_dict[ticker][base, base_in_quote, AND quote]
bag_max_dict = dict()  # max value of port for ticker if all in the quote or itself - uses allocation_dict
bag_actual_dict = dict()  # what we really got
bag_desired_dict = dict()  # what we want

order_open_dict = {}  # contains all open orders, backed up live in  ./data/<port_name>/open_orders.csv


# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------


def directory_check_for_portfolio_data(params):
    """ checks that the directory setup for the current portfolio is correct
    if needed it will create a directory in ./data/<port_name> with other necessary thing in it.
    """

    # create portfolio orders dir:         ./data/<exchange>/<port_name>   ...if its not there yet
    port_path = get_data_file_path(data_type='port_folder',
                                   pair=None,
                                   date='live',
                                   port=port_name,
                                   exchange=exchange,
                                   )

    dirs_needed_for_order_data = [port_path, port_path + 'closed/', ]
    for ticker in pairs_tracked:
        dirs_needed_for_order_data.append(port_path + 'closed/' + ticker + '/')

    for dir_path in dirs_needed_for_order_data:
        check_if_dir_exists_and_make(dir_path)

    fps_needed = [port_path + 'last_check.txt',
                  port_path + 'open_orders.csv',
                  port_path + 'whose_turn.csv', ]
    for fp in fps_needed:
        if not os.path.isfile(fp):
            with open(fp, 'x'):
                pass

    return None


# initialize actions dict --> {'ticker': 'neutural'}
def initialize_actions_dicts():
    global actions_dict

    for ticker in pairs_tracked:
        actions_dict[ticker] = 'neutural'

    return None


# initialize allocation dict
def initialize_port_allocation_dict(method='default'):
    """ initialized the proportion of assets in the trading account that go to each ticker """
    global port_allocation_dict

    if method == 'default':
        port_allocation_dict['ADAUSDT'] = 0.0
        port_allocation_dict['BNBUSDT'] = 0.0
        port_allocation_dict['BTCUSDT'] = 0.25
        port_allocation_dict['DOGEUSDT'] = 0.25
        port_allocation_dict['ETHUSDT'] = 0.25
        port_allocation_dict['LINKUSDT'] = 0.25
        port_allocation_dict['LTCUSDT'] = 0.0
        port_allocation_dict['XLMUSDT'] = 0.0

    if method == 'all BTC':
        for ticker in pairs_tracked:
            if ticker == 'BTCUSDT':
                port_allocation_dict[ticker] = 1
            else:
                port_allocation_dict[ticker] = 0

    return None


# initial get for prices
def get_initial_prices_batch():
    """get prices from historical files.. calculate metrics, populate signal_df_dict

    output
        None: edits prices_dfs_dict as a global variable


    ###PAUL there is a huge problem with this function... its prices are not coming in up to date.
    ###PAUL its super weird and i have no clue what is going on with it... looking into now because kindof
    ###PAUL crucial error
    """
    global prices_dfs_dict
    global pairs_tracked
    global short_term_prices_dict

    for ticker in pairs_tracked:
        # get_data will retrieve the last 24 hours of prices from written price files
        prices = get_data(data_type='price', pair=ticker, date='live', exchange=data_exchange)  # gets 24 hours

        # fill in annoying missing data
        prices.fillna(method='ffill', inplace=True)
        prices.fillna(method='bfill', inplace=True)
        prices.fillna(method='ffill', inplace=True)
        prices_dfs_dict[ticker] = prices

        # fill the short term prices dict (used for secondary orders)
        # clean prices_older than 10 mins... (for now)
        cutoff_time = datetime.datetime.now() + datetime.timedelta(minutes=-10)
        keep_mask = prices.index > cutoff_time
        short_term_prices_dict[ticker] = prices_dfs_dict[ticker][keep_mask].copy(deep=True)

        # get vwap and mid_ewm prices... used to place orders for scam wicks
        short_term_prices_dict[ticker]['mid_vwap'] = (short_term_prices_dict[ticker]['buy_vwap'] +
                                                      short_term_prices_dict[ticker]['sell_vwap']) / 2
        short_term_prices_dict[ticker]['mid_ewm'] = short_term_prices_dict[ticker]['mid_vwap'].ewm(alpha=0.6).mean()

    return None


# ###PAUL_refractor_round_2... will want to make a get_signal(ticker) function and loop over that
def get_initial_signal_batch(params=params):
    """create signals from initial price batch

    output
        None: edits signal_dfs_dict inplace
    """
    global prices_dfs_dict
    global signal_dfs_dict

    for ticker in pairs_tracked:
        prices = prices_dfs_dict[ticker]

        sma_short = prices['buy_vwap'].rolling(window=3400 * 3).mean().fillna(method='bfill')[-1]
        sma_long = prices['buy_vwap'].rolling(window=3400 * 10).mean().fillna(method='bfill')[-1]

        # buy if shorter SMA is bigger than longer SMA
        if sma_short > sma_long:
            signal_dfs_dict[ticker] = 1

        # sell if shorter SMA smaller than longer SMA
        if sma_short < sma_long:
            signal_dfs_dict[ticker] = -1

    return None


def get_ticker_filters_dict_binance_us(ticker_exchange):
    """get order filters such as PRICE_FILTER, LOT_SIZE, etc... so orders will go through cleanly

    returns: order_parameters_dict cointaining the following keys
        baseAssetPrecision  ---- max precision to place base asset order
        quoteAssetPrecision ---- max precision to place quote asset order
        tickSize            ---- increments of price that limit orders may be placed in the quote asset
        minQty              ---- smallest amount of base asset purchasable
        maxQty              ---- largest amount of base asset purchasable
        stepSize            ---- change in step size of asset orders
        minNotional         ---- smallest order allowed by cost in quote asset
    """
    order_params_dict = dict()
    order_params_dict['ticker_us'] = ticker_exchange  # ###PAUL_refractor... 'ticker_us' --> 'ticker_exchange'

    info = client.get_symbol_info(ticker_exchange)

    # base asset: (BTC in BTC_USDT)
    order_params_dict['baseAsset'] = info['baseAsset']
    order_params_dict['baseAssetPrecision'] = info['baseAssetPrecision']

    # quote asset: (USDT in BTC_USDT)
    order_params_dict['quoteAsset'] = info['quoteAsset']
    order_params_dict['quoteAssetPrecision'] = info['quoteAssetPrecision']

    filters = info['filters']

    for f in filters:
        if f['filterType'] == 'PRICE_FILTER':
            # tick size: increment of change allowed in quote asset price of order
            order_params_dict['minPrice'] = f['minPrice']
            order_params_dict['maxPrice'] = f['maxPrice']
            order_params_dict['tickSize'] = f['tickSize']

        # lot size work: min, max, step_size
        if f['filterType'] == 'LOT_SIZE':
            order_params_dict['minQty'] = f['minQty']
            order_params_dict['maxQty'] = f['maxQty']
            order_params_dict['stepSize'] = f['stepSize']

        # minimum purchase in quote asset quantity
        if f['filterType'] == 'MIN_NOTIONAL':
            order_params_dict['minNotional'] = f['minNotional']

        # minimum purchase in quote asset quantity
        if f['filterType'] == 'MARKET_LOT_SIZE':
            order_params_dict['marketMinQty'] = f['minQty']
            order_params_dict['marketMaxQty'] = f['maxQty']
            order_params_dict['marketStepSize'] = f['stepSize']

    if 'SPOT' not in info['permissions']:
        print('looks like trading not allowed on this asset \n ... investigate further', flush=True)
        raise TypeError

    return order_params_dict


def make_ticker_info_df():
    """makes DataFrame, indexed by standard binance ticker with columns:
        'ticker_us', 'baseAsset', 'baseAssetPrecision', 'quoteAsset', 'quoteAssetPrecision',
        'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty', 'stepSize', 'minNotional',
        'marketMinQty', 'marketMaxQty', 'marketStepSize'
    """

    global ticker_info_df

    ticker_entry_list = []

    # note that the ticker index for the DF is the standard binance ticker (USDT)... ticker_us is another col
    for ticker in pairs_tracked:
        ticker_us = tickers_foreign_to_us_dict[ticker]  # ###PAUL_refractor... ticker_us --> ticker_exchange
        filters_dict = get_ticker_filters_dict_binance_us(
            ticker_us)  # ###PAUL_refractor... ticker_us --> ticker_exchange
        filters_dict['ticker'] = ticker  # ###PAUL_refractor... ticker --> ticker_universal
        ticker_entry_list.append(filters_dict)

    ticker_info_df = pd.DataFrame.from_records(ticker_entry_list, index='ticker')
    ticker_info_df = ticker_info_df.astype(dtype=order_filters_names_type_dict)


def update_prices(ticker, params=params):
    """TODO: eventually update from short term price DFs ###PAUL
    """

    # ###PAUL_update not sure if the below is needed as it runs so well without without it but
    # ###PAUL_update maybe needed in the long run
    """
    need to make it so that the update price function includes seconds with no transaction 
    """

    global exchange
    global data_exchange
    global prices_dfs_dict

    latest_price_written = max(prices_dfs_dict[ticker].index)

    # get all the new trades
    # ###PAUL_refractor... wrong exchange cause dealing with binance prices.. dont know how to handle rn
    live_trades = get_live_trades_data(ticker, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = convert_trades_df_to_prices(live_trades, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = live_prices[live_prices.index > latest_price_written]

    # merge the new prices with the old prices.
    prices_dfs_dict[ticker] = pd.concat([prices_dfs_dict[ticker], live_prices])

    # clean prices_older than 24 hr... probably wont need more for informed decision making (for now)
    cutoff_time = datetime.datetime.now() + datetime.timedelta(hours=-24)
    keep_mask = prices_dfs_dict[ticker].index > cutoff_time
    prices_dfs_dict[ticker] = prices_dfs_dict[ticker][keep_mask]

    # fill NaNs (only happens when is missing information so this is needed at this step each update)
    prices_dfs_dict[ticker].fillna(method='ffill', inplace=True)
    prices_dfs_dict[ticker].fillna(method='bfill', inplace=True)


def update_all_prices(params=params):
    global pairs_tracked

    for ticker in pairs_tracked:
        update_prices(ticker)

    return None


def update_short_term_prices(ticker, params=params):
    """updates the short term prices... the file reading in this may take a bit extra timme, for stability
    for now this is seperate from update prices... eventually should be combined with update prices as to
    not need to generate prices from live trades twice
    """

    global data_exchange
    global short_term_prices_dict

    ##############################################################################################
    ##############################################################################################
    ##############################################################################################
    try:
        latest_price_written = max(short_term_prices_dict[ticker].index)
    except:
        import pdb; pdb.set_trace()
    ##############################################################################################
    ##############################################################################################
    ##############################################################################################

    # get all the new trades
    # ###PAUL_refractor... wrong exchange cause dealing with binance prices.. dont know how to handle rn
    live_trades = get_live_trades_data(ticker, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = convert_trades_df_to_prices(live_trades, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = live_prices[live_prices.index > latest_price_written]

    # merge the new prices with the old prices.
    short_term_prices_dict[ticker] = pd.concat([prices_dfs_dict[ticker], live_prices])

    # clean prices_older than 24 hr... probably wont need more for informed decision making (for now)
    cutoff_time = datetime.datetime.now() + datetime.timedelta(minutes=-10)
    keep_mask = short_term_prices_dict[ticker].index > cutoff_time
    short_term_prices_dict[ticker] = short_term_prices_dict[ticker][keep_mask]

    # fill NaNs (only happens when is missing information so this is needed at this step each update)
    short_term_prices_dict[ticker].fillna(method='ffill', inplace=True)
    short_term_prices_dict[ticker].fillna(method='bfill', inplace=True)

    # recently added
    short_term_prices_dict[ticker]['mid_vwap'] = (short_term_prices_dict[ticker]['buy_vwap'] +
                                                  short_term_prices_dict[ticker]['sell_vwap']) / 2
    short_term_prices_dict[ticker]['mid_ewm'] = short_term_prices_dict[ticker]['mid_vwap'].ewm(alpha=0.6).mean()

    return None


def update_all_short_term_prices(params=params):
    global pairs_tracked

    for ticker in pairs_tracked:
        update_short_term_prices(ticker)

    return None


def update_signals(params=params):
    # first update the prices
    update_all_prices()
    update_all_short_term_prices()

    # declare globals for this scope
    global prices_dfs_dict
    global signal_dfs_dict

    for ticker in pairs_tracked:
        prices = prices_dfs_dict[ticker]

        sma_short = prices['buy_vwap'].rolling(window=3400 * 3).mean().fillna(method='bfill')[-1]
        sma_long = prices['buy_vwap'].rolling(window=3400 * 10).mean().fillna(method='bfill')[-1]

        # buy if shorter SMA is bigger than longer SMA
        if sma_short > sma_long:
            signal_dfs_dict[ticker] = 1

        # sell if shorter SMA smaller than longer SMA
        if sma_short < sma_long:
            signal_dfs_dict[ticker] = -1

    return None


def initialize_bag_dicts():
    global bag_max_dict
    global bag_actual_dict
    global bag_desired_dict

    for ticker in pairs_tracked:
        bag_max_dict[ticker] = {'base': 0, 'base_in_quote': 0, 'quote': 0}
        bag_actual_dict[ticker] = {'base': 0, 'base_in_quote': 0, 'quote': 0}
        bag_desired_dict[ticker] = {'base': 0, 'base_in_quote': 0, 'quote': 0}


def update_port_holdings_and_value():
    '''updates the global variables listed at the top of the function
    note the differientation between holdings and bags
        - holdings is EVERYTHING in the account
        - bags are things that are tradable according to tickers tracked
        - value is determined from bags, holdings are not included and must be manually traded

    TODO: this function gets holdings of ALL tickers, not all tickers are tracked right now some
     optimization needs to be done its not worth adding all tickers to track.. will take longer and more compute
    '''

    global short_term_prices_dict
    global last_prices_dict

    global port_value
    global port_usd
    global port_holdings_dict
    global port_allocation_dict

    global bag_max_dict
    global bag_actual_dict

    ###PAUL errored out here

    # update port holdings    ---- note: it gets all holdable assets on binance us
    try:
        bag_list = client.get_account()[
            'balances']  # returns list of dicts: {'asset': 'BTC', 'free': '0.18', 'locked': '0.0'}
    except TimeoutError as e:
        print('\n \n ###PAUL_ReadTimeout error here happened \n \n ', flush=True)  # ###PAUL eventually figure this out
        print('Exception Trace 1', flush=True)
        print(e, flush=True)
        print('\n \n \n', flush=True)
        pass

    for bag in bag_list:
        ticker = bag['asset']
        free = float(bag['free'])
        locked = float(bag['locked'])
        total = free + locked

        # will add tickers outside of portfolio's control to bag list... these don't contribute value to the port..
        port_holdings_dict[ticker] = {'free': free, 'locked': locked, 'total': total}

    # update port value   ---- note: only considers the ticker's traded in the portfolio value
    port_value_t = 0
    for ticker in pairs_tracked:  # ###PAUL_refractor pairs_tracked --> tickers_traded_universal
        # get the base asset of each ticker
        base_asset = ticker_info_df.loc[ticker]['baseAsset']  # ###PAUL_refractor. df indexed by universal tickers

        # get qty and value of base asset held for each ticker
        last_price = float(short_term_prices_dict[ticker].iloc[-1:]['mid_ewm'])
        last_prices_dict[ticker] = last_price
        base_asset_qty = port_holdings_dict[base_asset]['total']
        asset_value = last_price * base_asset_qty

        # update actual bags dict
        bag_actual_dict[ticker]['base'] = base_asset_qty
        bag_actual_dict[ticker]['base_in_quote'] = asset_value

        port_value_t += asset_value

    port_value_t += port_holdings_dict['USD']['total']  # tack on the USD value... not a ticker tracked
    port_value = port_value_t

    # must do these after the new total value is assessed
    for ticker in pairs_tracked:
        last_price = last_prices_dict[ticker]

        # get dollars for actual bags dict by subtracting value held from proportion of portfolio for ticker
        total_value_for_ticker = port_allocation_dict[ticker] * port_value

        # figure out how many dollars are left for ticker (can be negative this means were holding too much)
        quote_value_of_ticker_bag = last_price * bag_actual_dict[ticker]['base']
        bag_actual_dict[ticker]['quote'] = total_value_for_ticker - quote_value_of_ticker_bag

        # update all of max bag dict
        #
        # ###PAUL_refractor... generalize the base_asset as a variable
        #
        bag_max_dict[ticker]['base'] = total_value_for_ticker / last_price
        bag_max_dict[ticker]['base_in_quote'] = total_value_for_ticker
        bag_max_dict[ticker]['quote'] = total_value_for_ticker


def update_desired_bags(action, ticker):
    """called in place_orders_on_signal()
    ###PAUL_refractor... maybe needed for place_secondary orders?
    ###PAUL_tag1 ---- longer term consideration... desired_bags more complex than in or out
    ###PAUL_tag1 ---- also considering using funds that aren't being utilized for a more bullish asset.
    """

    global bag_max_dict
    global bag_desired_dict

    if action == 'buy' or action == 'buy_again':
        bag_desired_dict[ticker]['base'] = bag_max_dict[ticker]['base']
        bag_desired_dict[ticker]['base_in_quote'] = bag_max_dict[ticker]['base_in_quote']
        bag_desired_dict[ticker]['quote'] = 0

    if action == 'sell' or action == 'sell_again':
        bag_desired_dict[ticker]['base'] = 0
        bag_desired_dict[ticker]['base_in_quote'] = 0
        bag_desired_dict[ticker]['quote'] = bag_max_dict[ticker]['quote']


def initialize_whose_turn_dict():
    global last_prices_dict
    global port_holdings_dict
    global whose_turn_dict
    global ticker_info_df

    for ticker in pairs_tracked:
        baseAsset = ticker_info_df.loc[ticker]['baseAsset']
        value_of_hold = last_prices_dict[ticker] * port_holdings_dict[baseAsset]['total']

        if value_of_hold < 25:
            whose_turn_dict[ticker] = 'buy'
        else:
            whose_turn_dict[ticker] = 'sell'

    return None


# make stuff thats gotta be made
directory_check_for_portfolio_data(params)
make_ticker_info_df()
initialize_bag_dicts()

initialize_port_allocation_dict()
initialize_actions_dicts()
get_initial_prices_batch()
get_initial_signal_batch()
update_all_prices()
update_all_short_term_prices()
update_signals()
update_port_holdings_and_value()
initialize_whose_turn_dict()

print('---- initial variables created', flush=True)


#
# ###PAUL_tag2
# """
# there was a problem with prices being too sparce and being filled in weird when using binance_us
# as the price maker... a few things
# ---> check that binance_us prices are being made nice and properly
# --->  figure out the issue becuase this will come up when it becomes time to trading lower liquidity assets
#       in an automated manner
# """
# ###PAUL_tag2
#


# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------


def determine_buy_or_sell():
    """ the primary benefit of this function is to see whether we have a buy or sell that has been determined
    and then to up the priority of that order if it needs it.


    output:
        actions_dict (dict): {'BTCUSDT':'buy',  'XRPUSDT':'sell'}
    """
    global actions_dict
    global pairs_tracked
    global signals_dfs_dict
    global whose_turn_dict

    actions_dict = dict()

    for ticker in pairs_tracked:
        whose_turn = whose_turn_dict[ticker]
        signal_int = signal_dfs_dict[ticker]  # -1 = sell    1 = buy

        # BUY condition met
        if signal_int == 1:
            if whose_turn == 'buy':
                actions_dict[ticker] = 'buy'
                whose_turn_dict[ticker] = 'sell'
            else:  # the buy condition was met before but the order has not been filled
                actions_dict[ticker] = 'buy_again'

        # SELL condition met
        elif signal_int == -1:
            if whose_turn == 'sell':
                actions_dict[ticker] = 'sell'
                whose_turn_dict[ticker] = 'buy'
            else:  # the sell condition was met, but it is not sell's turn yet.
                actions_dict[ticker] = 'sell_again'

                # NEITHER buy or sell condition met
        else:
            actions_dict[ticker] = 'neutural'

    return actions_dict


def make_order_observation_csv_line(orderId, order_info_dict):
    """returns a string to go in live order tracking file
    """

    new_live_order_line = str(orderId) + ',' \
                          + str(order_info_dict['ticker']) + ',' \
                          + str(order_info_dict['clientOrderId']) + ',' \
                          + str(order_info_dict['placedTime']) + ',' \
                          + str(order_info_dict['price']) + ',' \
                          + str(order_info_dict['origQty']) + ',' \
                          + str(order_info_dict['executedQty']) + ',' \
                          + str(order_info_dict['cummulativeQuoteQty']) + ',' \
                          + str(order_info_dict['side']) + ',' \
                          + str(order_info_dict['status']) + ',' \
                          + str(order_info_dict['ord_type']) + ',' \
                          + str(order_info_dict['updateTime']) + '\n'

    return new_live_order_line


def process_placed_order(placed_order_res):
    """makes live order observation from placed order response.. note there are subtle differences between
    a placed order response and a get_or der response which is an update on an already placed orders.py
    for more see the update from
    """
    global exchange
    global port_name
    global order_open_dict
    global tickers_us_to_foreign_dict

    # used as primary key among orders (not sure if this or clientOrderId best practice...)
    ticker = placed_order_res['symbol']
    foreign_ticker = tickers_us_to_foreign_dict[ticker]

    orderId = placed_order_res['orderId']
    order_time = placed_order_res['transactTime']

    order_info_dict = dict()

    order_info_dict['ticker'] = foreign_ticker  # ###PAUL_refractor
    # order_info_dict['orderId']              = placed_order_res['orderId'] # put lower for dictionary return
    order_info_dict['clientOrderId'] = placed_order_res['clientOrderId']
    order_info_dict['placedTime'] = placed_order_res['transactTime']
    order_info_dict['price'] = placed_order_res['price']
    order_info_dict['origQty'] = placed_order_res['origQty']
    order_info_dict['executedQty'] = placed_order_res['executedQty']
    order_info_dict['cummulativeQuoteQty'] = placed_order_res['cummulativeQuoteQty']
    order_info_dict['side'] = placed_order_res['side']
    order_info_dict['status'] = placed_order_res['status']
    order_info_dict['ord_type'] = placed_order_res['type']
    order_info_dict['updateTime'] = placed_order_res['transactTime']

    # add the new order to the dictionary tracking open orders
    order_open_dict[(orderId, foreign_ticker)] = order_info_dict

    # ### write the order to the live files
    #
    open_order_fp = get_data_file_path(data_type='order',
                                       pair='None',
                                       date='live',
                                       port=port_name,
                                       exchange=exchange)

    new_live_order_line = make_order_observation_csv_line(orderId, order_info_dict)

    with open(open_order_fp, "a") as f:
        f.write(new_live_order_line)
    os.chmod(open_order_fp, 0o777)  # needed for when running on systemd

    return orderId, foreign_ticker, order_info_dict


def place_order(B_or_S, ticker, o_type, base_qty, price=None, order_id=None):
    """places an orders.py

    input:
        ticker (str): 'BTCUSDT'... use ticker tracked NOT the USA ticker, it will convert it
        o_type (str): 'limit' only supported now, in future maybe, market and more...
        B_or_S (str): 'buy' or 'sell'
        base_qty (float): amount of base asset to buy (i.e. BTC in BTCUSDT )
        quote_qty (float): same functionality as base_qty, but for quote... NOT YET SUPPORTED
        price (float): price of base asset in quote asset terms

    returns:
        ???? not sure need:
        order ID to track the order status, maybe more
    """

    if ticker not in pairs_tracked:  # ###PAUL_refractor
        raise KeyError

    info = ticker_info_df.loc[ticker]

    # string used to place order on ticker
    ticker_us = info['ticker_us']  # ###PAUL_refractor ticker_exchange

    # requirements on the base asset
    base_qty = round_step_size(quantity=base_qty, step_size=info['stepSize'])

    if base_qty < info['minQty'] or base_qty > info['maxQty']:
        raise ValueError

        # price requirements
    price = round_step_size(quantity=price, step_size=info['tickSize'])

    if price < info['minPrice'] or price > info['maxPrice']:
        raise ValueError

    # notional requirements (makes sure that the order is large enough in terms of quote asset)
    if price * base_qty < info['minNotional']:
        print('    Price: ' + str(price), flush=True)
        print('    base_qty: ' + str(base_qty), flush=True)
        print("    info['minNotional']: " + str(info['minNotional']), flush=True)

        return 'order not placed MIN_NOTIONAL issue '

    if o_type == 'limit':
        print('Limit Order:  ' + B_or_S + ' ' + str(base_qty) + ' ' + ticker_us + ' for $' + str(price), flush=True)
        if B_or_S == 'buy':
            order_res = client.order_limit_buy(symbol=ticker_us,
                                               quantity=base_qty,
                                               price=price
                                               )

        if B_or_S == 'sell':
            order_res = client.order_limit_sell(symbol=ticker_us,
                                                quantity=base_qty,
                                                price=price
                                                )

    else:
        print('Error: order type not supported', flush=True)
        raise TypeError

    process_placed_order(order_res)

    return order_res


def write_closed_order(orderId, ticker, order_info_dict):
    """writes order that has closed to a file of orders for that ticker
    """

    global order_open_dict
    global params

    header = 'orderId,ticker,clientOrderId,placedTime,price,origQty,executedQty,cummulativeQuoteQty,side,status,ord_type,updateTime\n'
    new_line = make_order_observation_csv_line(orderId, order_info_dict)

    #     print('###PAUL_debug_spot_1', flush=True)
    daily_trade_fp = get_data_file_path('closed_order', ticker, date='live', port=port_name, exchange=exchange)
    #     print('###PAUL_debug_spot_2', flush=True)

    # check that the file exists for the correct time period
    file_existed = os.path.isfile(daily_trade_fp)
    with open(daily_trade_fp, "a") as f:
        if file_existed == False:  # then new file, write header
            f.write(header)
        f.write(new_line)
    os.chmod(daily_trade_fp, 0o777)

    #     print('###PAUL_debug_spot_3', flush=True)

    return None


def remove_order_from_open_tracking(tuple_key):
    """serves 3 primary purposes:  1.) removes order from ./data/orders/open/open_orders.csv
                                   2.) writes the order to the ticker's / day's closed order file
                                   3.) removes order from global tracking dictionary
    """

    global order_open_dict

    orderId, foreign_ticker = tuple_key

    order_info_dict = order_open_dict[(orderId, foreign_ticker)]
    ticker_us = order_info_dict['ticker']

    # ### remove order from open order tracking file
    #
    open_order_fp = get_data_file_path(data_type='order', pair=None, date='live', port=port_name, exchange=exchange)

    with open(open_order_fp, 'r') as f:
        lines = f.readlines()

    # rewrite file without the orderId in it
    with open(open_order_fp, "w") as f:
        for line in lines:
            if str(orderId) not in line[:15]:
                f.write(line)

    # ### write to closed order files
    write_closed_order(orderId, ticker_us, order_info_dict)

    # ### remove order from dictionary... must do last, info here used to write to closed order file
    #
    del order_open_dict[(orderId, foreign_ticker)]

    return None


def close_order(order_id_tuple):
    global tickers_foreign_to_us_dict

    orderId, foreign_ticker = order_id_tuple
    ticker_us = convert_pair_foreign_to_us(foreign_ticker, exchange)

    tuple_key = (orderId, foreign_ticker)

    # cancel the order
    try:
        order_res = client.cancel_order(symbol=ticker_us, orderId=orderId)
        remove_order_from_open_tracking(tuple_key)

    except Exception as e:
        print('order cancel attempted, it seems order was filled: ', flush=True)
        print('    symbol: ' + ticker_us + '  orderId: ' + str(orderId) + '\n \n \n', flush=True)
        print(e, flush=True)
        print('\n \n \n ', flush=True)

    return None


def update_most_recent_order_check_file(params):
    fp = get_data_file_path(data_type='last_order_check',
                            pair=None, date='live',
                            port=port_name,
                            exchange=exchange)

    now = str(time.time())

    with open(fp, 'w') as f:
        f.write(now)
    os.chmod(fp, 0o777)

    return None


def check_for_closed_orders():
    """checks if any of the open orders being tracked are now closed and removes them from tracking
    TODO: need to add order fills to tracking consider ./data/orders/filled/  (filled being a new dir)
    """

    global order_open_dict

    # get open orders from exchange
    open_orders_res_list = client.get_open_orders()

    # put list of keys: tuples (orderId, Ticker) from exchange collected
    open_orders_on_exchange = []
    for res in open_orders_res_list:
        ticker = convert_pair_us_to_foreign(res['symbol'], exchange)  # ###PAUL_refractor
        orderId = res['orderId']
        tup = (orderId, ticker)

        open_orders_on_exchange.append(tup)

    # loop through the open_order_dict, remove entry if the order is not in the orders on the exchange
    keys_to_delete = []
    for key in order_open_dict:
        if key not in open_orders_on_exchange:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        remove_order_from_open_tracking(key)

    return None


def place_orders_on_signal(params):
    """
    """
    global iter_count

    global actions_dict

    global port_value
    global port_holdings_dict
    global port_allocation_dict

    global ticker_info_df

    global bag_max_dict
    global bag_actual_dict
    global bag_desired_dict

    update_signals()  # also includes update to long and short term prices

    # get desired action for ticker
    actions_dict = determine_buy_or_sell()

    # want update holdings and value as near as placing new orders as possible... this cancels open orders
    update_port_holdings_and_value()

    for ticker in pairs_tracked:  # ###PAUL_refractor... tickers_traded_universal

        us_ticker = tickers_foreign_to_us_dict[ticker]
        # place buy/sell order
        action = actions_dict[ticker]

        # most actions should be neutral... save time by passing on other actions if neutral
        if action == 'neutural':
            continue

        update_desired_bags(action, ticker)  # bag for ticker to  {0, max_bag_for_ticker} based on allocation

        actual_base_in_quote_value = bag_actual_dict[ticker]['base_in_quote']
        desired_base_in_quote_value = bag_desired_dict[ticker]['base_in_quote']

        diff = desired_base_in_quote_value - actual_base_in_quote_value

        # if diff to small, we dont do anything
        ###PAUL this only works IF QUOTE IS IN DOLLARS..
        ###PAUL once trading in other quotes need to figure out another way to go about this
        if -25 < diff and diff < 25:
            continue  # skips to next iteration of for loop

        print('###PAUL_debug ---- diff > 25', flush=True)  ###PAUL_debug

        # info needed whether buying or selling
        last_price_df_t = short_term_prices_dict[ticker].iloc[-1:]
        mid_vwap = float(last_price_df_t['mid_vwap'])
        mid_ewm = float(last_price_df_t['mid_ewm'])

        # need to update holdings before this selling... there is a delay,
        # however, updating each ticker individually is too many API requests...
        # this means just catch the error on the order... yes this same problem can apply to the buys
        # need to find the specific type of error and see what happens.. lets go sell too much btc

        ###PAUL TODO: should add order book info on prices to this to take advantage of scan wicks
        # this means buying at the scam price if lower than the above, vise versa selling
        if diff >= 25:  # we are buying
            print('###PAUL_debug ---- should be buying', flush=True)
            current_dollar_holdings = port_holdings_dict['USD']['free']

            buy_dollars = min(diff, current_dollar_holdings)  # cant buy more than i have

            if action == 'buy':
                B_or_S = 'buy'
                price = min(mid_vwap, mid_ewm)  # want to buy for cheaper since not high priority
                qty = buy_dollars / price * 0.98

            else:  # more urgent option... or for some reason have too little (crash and re-boot)
                B_or_S = 'buy'
                price = max(mid_vwap, mid_ewm)  # max cause on buy again we really want the asset
                qty = buy_dollars / price * 0.98

        if diff <= -25:  # we are selling
            print('###PAUL_debug ---- should be selling', flush=True)
            baseAsset = ticker_info_df.loc[ticker]['baseAsset']
            baseAsset_holdings = port_holdings_dict[baseAsset]['free']
            sell_dollars = min(-diff, min(mid_vwap, mid_ewm) * baseAsset_holdings)

            if action == 'sell':
                B_or_S = 'sell'
                price = max(mid_vwap, mid_ewm)  # max cause want the highest price on non-urgent sell
                qty = 0.98 * (sell_dollars / price)

            else:  # more urgent (sell again or if we have too much unintentionally - a reboot for example)
                B_or_S = 'sell'
                price = min(mid_vwap, mid_ewm)  # min... want to get rid of it on urgent sells
                qty = 0.98 * (sell_dollars / price)

        total_order_value = qty * price

        if total_order_value < 11:
            print(' ----->>>>  total_order_value too small  value is: ' + str(total_order_value), flush=True)
            continue

        try:

            order_higher_priority = False
            order_open_for_ticker = False
            keys_to_close = []

            # ###PAUL_refractor... this could (should?) be built more DRY
            for key in order_open_dict.keys():
                _, order_ticker = key
                if ticker == order_ticker:
                    print('ticker match for order', flush=True)
                    order_open_for_ticker = True

                    old_price = float(order_open_dict[key]['price'])
                    if B_or_S == 'buy' and price > old_price or B_or_S == 'sell' and price < old_price:
                        print("order qualifying condition ---- " + B_or_S + '  ask was  ' + str(old_price)
                              + '  updated to:   ' + str(price),
                              flush=True)
                        order_higher_priority = True
                        keys_to_close.append(key)

            for key in keys_to_close:
                print('Closing order: ' + str(key), flush=True)
                close_order(key)  # keep this here unless

            print('###PAUL_debug: order_open_for_ticker:  ' + str(order_open_for_ticker) + '\n'
                  + '  ----  order_higher_priority :' + str(order_higher_priority),
                  flush=True)
            ###PAUL expecting an error here. if order is filled between the time the order_open_dict is checked
            ###PAUL this point then the attempt to close should fail... the try catch is to enable this


        except RuntimeError as e:
            print('ERROR PLACING ORDER', flush=True)
            print('    ###PAUL it appears an order was filled between the time the closed orders were ', flush=True)
            print('    ###PAUL checked for and the time it was attempted to be closed', flush=True)
            print('    ###PAUL this is just a warning which seems to be the cleanest way to handle right now \n \n',
                  flush=True)
            print(e, flush=True)
            print('\n \n \n', flush=True)
            continue  # want to continue so no order is placed as its been filled

        #         print('closing order to update to higher priority', flush=True)
        #         close_order(key)

        # if  order_higher_priority  or no   order_open_for_ticker  then order
        if order_higher_priority == True or order_open_for_ticker == False:
            print('LIMIT ORDER ---- ' + B_or_S + ' - ' + str(qty) + ' - ' + ticker
                  + ' for $' + str(price) + ' ---- port_name: ' + port_name, flush=True)
            order_res = place_order(B_or_S=B_or_S,
                                    ticker=ticker,
                                    o_type='limit',
                                    base_qty=qty,
                                    price=price
                                    )

            print(order_res, flush=True)
            process_placed_order(order_res)

    check_for_closed_orders()  # stops tracking orders that were closed any way (filled, bot, or manual)

    # only update the portfolios most recent update time if this function runs to fruition
    update_most_recent_order_check_file(params)

    if iter_count % 10 == 0:
        print('ALGOS - LIVE BOT - iter: ' + str(iter_count) + ' ---- port: ' + port_name
              + ' ---- exchange: ' + exchange, flush=True)
    iter_count += 1

    return None


def place_signal_on_orders_exception_catch():
    # try:
    place_orders_on_signal(params)
    # except Exception as e:
    #     print('\n \n ALGOS - LIVE BOT - TOP LEVEL ERROR! \n \n', flush=True)
    #     print(e, flush=True)
    #     print('\n \n \n', flush=True)
    #     send_email(subject='live bot notebook failed',
    #                message='the error was: ' + str(e),)


def main():
    signal_based_order_interval = params['active_services']['ports']['sma_v1_equal_dist']['signal_based_order_interval']
    place_orders_on_signal_task = task.LoopingCall(f=place_signal_on_orders_exception_catch)
    place_orders_on_signal_task.start(signal_based_order_interval)

    reactor.run()
    return None


# try:
main()
print('ALGOS ---- LIVE BOT ---- ran fully ------------------------ \n', flush=True)
# except Exception as e:
#     print('\n \n ALGOS - LIVE BOT - MAIN LEVEL ERROR! \n ' + str(e) + '\n \n', flush=True)
