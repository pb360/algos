# ### imports
#
#

# ### time zone change... this must happen first and utils must be imported first
import os
import time

os.environ['TZ'] = 'UTC'
time.tzset()
# ### time zone change... this must happen first and utils must be imported first

import pandas as pd
from twisted.internet import task, reactor


# local imports
#
#
import config
params = config.params

from utils import *

# ###PAUL_del
# ###PAUL this will likely be replaced by ccxt so pass on consideration for this for now.
# sys.path.append('/mnt/algos/ext_packages/sams_binance_api')  # # path containing sams binance api

# from binance.client import Client
# from binance.websockets import BinanceSocketManager


import ccxt


# time the script from start to first trade
START_TIME = time.time()
this_scripts_process_ID = os.getpid()

# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split

# ### portfolio specific information
#
#
port_name = 'sma_v2_8020_KDA_NOIA'
exchange = 'kucoin'  # ###PAUL should this be inherited from params?
data_exchange = 'kucoin'

# all pairs to be considered in portfolio... in universal symbol format
pairs_traded = ['KDA-USDT', 'NOIA-USDT']

# ### API things
#
#
api_key = params['keys']['kucoin']['algostrading0123456789']['trade_1']['key']
secret_key = params['keys']['kucoin']['algostrading0123456789']['trade_1']['secret']
kucoin_passphrase = params['keys']['kucoin']['algostrading0123456789']['trade_1']['passphrase']


# ###PAUL probably want this to be based off exchange
kucoin = ccxt.kucoin({'apiKey': api_key,
                      'secret': secret_key,
                      'password': kucoin_passphrase})

# #
# ##
# ### for systemd deployment only
# assert(exchange in params['systemd_control']['active_exchanges'])
# assert(port_name in params['systemd_control']['active_ports'])
# ###
# ##
# #


# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split


# ### definitions
#
#
iter_count = 0  # counter for decision cycles  i.e.   place_order_on_signals()

# params['port_name'] = port_name  # ###PAUL no need to put this here... for now leave out and remove if can
op_sys = params['constants']['os']


# ### utility constants... these should be constant on a exchange basis (for crypto)
#
#
prices_dtype_dict = params['data_format'][exchange]['price_name_and_type']
order_filters_names_type_dict = params['data_format'][exchange]['order_filters_name_type']

# ### Global Variables
#
#
prices_dfs_dict = dict()  # {pair: price_df}
short_term_prices_dict = dict()  # {pair: price_df}
last_prices_dict = dict()  # {pair: most_recent_price}

# in order of how derived from prices each is
signal_dfs_dict = dict()  # {pair: signal}  # ###PAUL all vari's standard except this one
actions_dict = dict()  # {pair: one_of --> ['buy_again', 'buy', 'neutural', 'sell', 'sell_again']}
whose_turn_dict = dict()  # whose_turn is it is {pair: ['buy' or 'sell']}


# ### state of holdings / portfolio
#
#
port_value = 0  # total port value (in USD denomination)
port_usd = 0  # USD currently in the portfolio (available for purchasing stuff)
port_allocation_dict = dict()  # prortion value each pair gets - ex: {'BTCUSDT':0.75, 'ETHUSDT':0.25}

# value held (in base asset) ----  formatted:  {'free':free, 'locked':locked, 'total':total}
# NOTE: doesnt consider pairs with same base, just all merged in one
port_holdings_dict = dict()

# each is structured bag_dict[pair][base, base_in_quote, AND quote]
bag_max_dict = dict()  # max value of port for pair if all in the quote or itself - uses allocation_dict
bag_actual_dict = dict()  # what we really got
bag_desired_dict = dict()  # what we want

order_open_dict = {}  # contains all open orders, backed up live in  ./data/<port_name>/open_orders.csv


# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split


# %%time


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
    for pair in pairs_traded:
        dirs_needed_for_order_data.append(port_path + 'closed/' + pair + '/')

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


# initialize actions dict --> {'pair': 'neutural'}
def initialize_actions_dicts():
    global actions_dict

    for pair in pairs_traded:
        actions_dict[pair] = 'neutural'

    return None


# initialize allocation dict
def initialize_port_allocation_dict(method='default'):
    """ initialized the proportion of assets in the trading account that go to each pair """
    global port_allocation_dict
    global pairs_traded

    if method == 'default':
        port_allocation_dict['ADA-USDT'] = 0.0
        port_allocation_dict['BNB-USDT'] = 0.0
        port_allocation_dict['BTC-USDT'] = 0.25
        port_allocation_dict['DOGE-USDT'] = 0.25
        port_allocation_dict['ETH-USDT'] = 0.25
        port_allocation_dict['LINK-USDT'] = 0.25
        port_allocation_dict['LTC-USDT'] = 0.0
        port_allocation_dict['XLM-USDT'] = 0.0

    if method == 'all BTC':
        for pair in pairs_traded:
            if pair == 'BTC-USDT':
                port_allocation_dict[pair] = 1
            else:
                port_allocation_dict[pair] = 0

    if method == 'uniform':
        num_pairs = len(pairs_traded)

        for pair in pairs_traded:
            port_allocation_dict[pair] = 1 / num_pairs

    if method == 'markowitz':
        raise RuntimeError

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

    global pairs_traded
    global prices_dfs_dict
    global short_term_prices_dict

    for pair in pairs_traded:
        # get_data will retrieve the last 24 hours of prices from written price files
        prices = get_data(data_type='price', pair=pair, date='live', exchange=data_exchange)  # gets 24 hours

        # fill in annoying missing data
        prices.fillna(method='ffill', inplace=True)
        prices.fillna(method='bfill', inplace=True)
        prices.fillna(method='ffill', inplace=True)
        prices_dfs_dict[pair] = prices

        # fill the short term prices dict (used for secondary orders)
        # clean prices_older than 10 mins... (for now)
        cutoff_time = datetime.datetime.now() + datetime.timedelta(minutes=-10)
        keep_mask = prices.index > cutoff_time
        short_term_prices_dict[pair] = prices_dfs_dict[pair][keep_mask].copy(deep=True)

        # get vwap and mid_ewm prices... used to place orders for scam wicks
        short_term_prices_dict[pair]['mid_vwap'] = (short_term_prices_dict[pair]['buy_vwap'] +
                                                    short_term_prices_dict[pair]['sell_vwap']) / 2
        short_term_prices_dict[pair]['mid_ewm'] = short_term_prices_dict[pair]['mid_vwap'].ewm(alpha=0.6).mean()

    return None


# ###PAUL universal exchange interaction refactor needed
def get_pair_filters_dict_binance_us(universal_symbol):
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

    global exchange

    exchange_symbol = convert_pair(universal_symbol, in_exchange='universal', out_exchange=exchange)

    order_params_dict = dict()
    order_params_dict['exchange_symbol'] = exchange_symbol

    info = client.get_symbol_info(exchange_symbol)

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
        print('looks like trading not allowed on this asset \n ... investigate further')
        raise TypeError

    return order_params_dict


# ###PAUL universal exchange interaction refactor needed
def make_pair_info_df():
    """makes DataFrame, indexed by column "universal_symbol" with columns:
        'exchange_symbol', 'baseAsset', 'baseAssetPrecision', 'quoteAsset', 'quoteAssetPrecision',
        'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty', 'stepSize', 'minNotional',
        'marketMinQty', 'marketMaxQty', 'marketStepSize'
    """

    global pair_info_df

    pair_entry_list = []

    for pair in pairs_traded:
        filters_dict = get_pair_filters_dict_binance_us(pair)
        filters_dict['universal_symbol'] = pair  # add on the universal
        pair_entry_list.append(filters_dict)

    pair_info_df = pd.DataFrame.from_records(pair_entry_list, index='universal_symbol')
    pair_info_df = pair_info_df.astype(dtype=order_filters_names_type_dict)


def update_prices(pair, params=params):
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

    latest_price_written = max(prices_dfs_dict[pair].index)

    # get all the new trades
    # ###PAUL_refractor... wrong exchange cause dealing with binance prices.. dont know how to handle rn
    live_trades = get_live_trades_data(pair, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = convert_trades_df_to_prices(live_trades, exchange=data_exchange)  # ###PAUL_refractor
    live_prices = live_prices[live_prices.index > latest_price_written]

    # merge the new prices with the old prices.
    prices_dfs_dict[pair] = pd.concat([prices_dfs_dict[pair], live_prices])

    # clean prices_older than 24 hr... probably wont need more for informed decision making (for now)
    cutoff_time = datetime.datetime.now() + datetime.timedelta(hours=-24)
    keep_mask = prices_dfs_dict[pair].index > cutoff_time
    prices_dfs_dict[pair] = prices_dfs_dict[pair][keep_mask]

    # fill NaNs (only happens when is missing information so this is needed at this step each update)
    prices_dfs_dict[pair].fillna(method='ffill', inplace=True)
    prices_dfs_dict[pair].fillna(method='bfill', inplace=True)


def update_all_prices(params=params):
    global pairs_traded

    for pair in pairs_traded:
        update_prices(pair)

    return None


def update_short_term_prices(pair, params=params):
    """updates the short term prices... the file reading in this may take a bit extra timme, for stability
    for now this is seperate from update prices... eventually should be combined with update prices as to
    not need to generate prices from live trades twice
    """

    global exchange
    global short_term_prices_dict

    latest_price_written = max(short_term_prices_dict[pair].index)

    # get all the new trades
    # ###PAUL this is a dirty fix... after initializing the short term prices on the data exchange
    # ###PAUL i switch them to "exchange" the trading exchange...
    live_trades = get_live_trades_data(pair, exchange=exchange)  # ###PAUL_refractor
    live_prices = convert_trades_df_to_prices(live_trades, exchange=exchange)  # ###PAUL_refractor
    live_prices = live_prices[live_prices.index > latest_price_written]

    # merge the new prices with the old prices.
    short_term_prices_dict[pair] = pd.concat([prices_dfs_dict[pair], live_prices])

    # clean prices_older than 10 minutes... no need for more on the short term
    cutoff_time = datetime.datetime.now() + datetime.timedelta(minutes=-10)
    keep_mask = short_term_prices_dict[pair].index > cutoff_time
    short_term_prices_dict[pair] = short_term_prices_dict[pair][keep_mask]

    # fill NaNs (only happens when is missing information so this is needed at this step each update)
    short_term_prices_dict[pair].fillna(method='ffill', inplace=True)
    short_term_prices_dict[pair].fillna(method='bfill', inplace=True)

    # recently added
    short_term_prices_dict[pair]['mid_vwap'] = (short_term_prices_dict[pair]['buy_vwap'] +
                                                short_term_prices_dict[pair]['sell_vwap']) / 2
    short_term_prices_dict[pair]['mid_ewm'] = short_term_prices_dict[pair]['mid_vwap'].ewm(alpha=0.6).mean()

    return None


def update_all_short_term_prices(params=params):
    global pairs_traded

    for pair in pairs_traded:
        update_short_term_prices(pair)

    return None


def update_signals(params=params):
    """also handles initialization of the signals dictionary
    """

    # first update the prices
    update_all_prices()
    update_all_short_term_prices()

    # declare globals for this scope
    global pairs_traded
    global prices_dfs_dict
    global signal_dfs_dict

    for pair in pairs_traded:
        prices = prices_dfs_dict[pair]

        sma_short = prices['buy_vwap'].rolling(window=3400 * 2).mean().fillna(method='bfill')[-1]
        sma_long = prices['buy_vwap'].rolling(window=3400 * 8).mean().fillna(method='bfill')[-1]

        # buy if shorter SMA is bigger than longer SMA
        if sma_short > sma_long:
            signal_dfs_dict[pair] = 1

        # sell if shorter SMA smaller than longer SMA
        if sma_short < sma_long:
            signal_dfs_dict[pair] = -1

    return None


def initialize_bag_dicts():
    global pairs_traded
    global bag_max_dict
    global bag_actual_dict
    global bag_desired_dict

    for pair in pairs_traded:
        bag_max_dict[pair] = {'base': 0, 'base_in_quote': 0, 'quote': 0}
        bag_actual_dict[pair] = {'base': 0, 'base_in_quote': 0, 'quote': 0}
        bag_desired_dict[pair] = {'base': 0, 'base_in_quote': 0, 'quote': 0}


def update_port_holdings_and_value():
    '''updates the global variables listed at the top of the function
    note the differientation between holdings and bags
        - holdings is EVERYTHING in the account
        - bags are things that are tradable according to pairs tracked
        - value is determined from bags, holdings are not included and must be manually traded

    TODO: this function gets holdings of ALL pairs, not all pairs are tracked right now some
     optimization needs to be done its not worth adding all pairs to track.. will take longer and more compute
    '''

    global pairs_traded

    global short_term_prices_dict
    global last_prices_dict

    global port_value
    global port_usd
    global port_holdings_dict
    global port_allocation_dict

    global bag_max_dict
    global bag_actual_dict

    # update port holdings    ---- note: it gets all holdable assets on binance us

    #     try:

    bag_list = client.get_account()[
        'balances']  # returns list of dicts: {'asset': 'BTC', 'free': '0.18', 'locked': '0.0'}

    #     except TimeoutError as e:
    #         print('\n \n ###PAUL_ReadTimeout error here happened \n \n ')  # ###PAUL eventually figure this out
    #         print('Exception Trace 1')
    #         print(e)
    #         print('/n /n /n')
    #         pass

    # loop adds pairs outside of portfolio's control to bag list... these don't contribute value to the port value
    for bag in bag_list:
        ticker = bag['asset']  # actual one sided ticker  i.e. BTC
        free = float(bag['free'])
        locked = float(bag['locked'])
        total = free + locked

        #         universal_symbol = convert_pair(exchange_symbol, in_exchange=exchange, out_exchange='universal')
        port_holdings_dict[ticker] = {'free': free, 'locked': locked, 'total': total}

    # update port value   ---- note: only considers the pair's traded in the portfolio value
    port_value_t = 0

    for pair in pairs_traded:
        # get the base asset of each pair
        base_asset = pair_info_df.loc[pair]['baseAsset']

        # get qty and value of base asset held for each pair
        last_price = float(short_term_prices_dict[pair].iloc[-1:]['mid_ewm'])
        last_prices_dict[pair] = last_price
        base_asset_qty = port_holdings_dict[base_asset]['total']
        asset_value = last_price * base_asset_qty

        # update actual bags dict
        bag_actual_dict[pair]['base'] = base_asset_qty
        bag_actual_dict[pair]['base_in_quote'] = asset_value

        port_value_t += asset_value

    port_value_t += port_holdings_dict['USD']['total']  # tack on the USD value... not a pair tracked
    port_value = port_value_t

    # must do these after the new total value is assessed
    for pair in pairs_traded:
        last_price = last_prices_dict[pair]

        # get dollars for actual bags dict by subtracting value held from proportion of portfolio for pair
        total_value_for_pair = port_allocation_dict[pair] * port_value

        quote_value_of_pair_bag = last_price * bag_actual_dict[pair]['base']
        bag_actual_dict[pair]['quote'] = total_value_for_pair - quote_value_of_pair_bag

        # update all of max bag dict
        #
        # ###PAUL_refractor... generalize the base_asset as a variable
        #
        bag_max_dict[pair]['base'] = total_value_for_pair / last_price
        bag_max_dict[pair]['base_in_quote'] = total_value_for_pair
        bag_max_dict[pair]['quote'] = total_value_for_pair


def update_desired_bags(action, pair):
    """called in place_orders_on_signal()
    ###PAUL_refractor... maybe needed for place_secondary orders?
    ###PAUL_tag1 ---- longer term consideration... desired_bags more complex than in or out
    ###PAUL_tag1 ---- also considering using funds that aren't being utilized for a more bullish asset.
    """

    global bag_max_dict
    global bag_desired_dict

    if action == 'buy' or action == 'buy_again':
        bag_desired_dict[pair]['base'] = bag_max_dict[pair]['base']
        bag_desired_dict[pair]['base_in_quote'] = bag_max_dict[pair]['base_in_quote']
        bag_desired_dict[pair]['quote'] = 0

    if action == 'sell' or action == 'sell_again':
        bag_desired_dict[pair]['base'] = 0
        bag_desired_dict[pair]['base_in_quote'] = 0
        bag_desired_dict[pair]['quote'] = bag_max_dict[pair]['quote']

    ###PAUL_todo TODO make whose turn correct in case of a reboot. no reason to trade on startup if not needed.


def initialize_whose_turn_dict():
    global last_prices_dict
    global port_holdings_dict
    global whose_turn_dict
    global pair_info_df

    for pair in pairs_traded:
        baseAsset = pair_info_df.loc[pair]['baseAsset']
        value_of_hold = last_prices_dict[pair] * port_holdings_dict[baseAsset]['total']

        if value_of_hold < 25:
            whose_turn_dict[pair] = 'buy'
        else:
            whose_turn_dict[pair] = 'sell'

    return None


# make stuff thats gotta be made
directory_check_for_portfolio_data(params)
make_pair_info_df()
initialize_bag_dicts()

initialize_port_allocation_dict(method='uniform')
initialize_actions_dicts()
get_initial_prices_batch()
# get_initial_signal_batch()
update_all_prices()
update_all_short_term_prices()
update_signals()
update_port_holdings_and_value()
initialize_whose_turn_dict()

print('Done')

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


# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split


def update_actions_dict():
    """ the primary benefit of this function is to see whether we have a buy or sell that has been determined
    and then to up the priority of that order if it needs it.


    output:
        actions_dict (dict): {'BTCUSDT':'buy',  'XRPUSDT':'sell'}
    """
    global actions_dict
    global pairs_traded
    global signals_dfs_dict
    global whose_turn_dict

    actions_dict = dict()

    for pair in pairs_traded:
        whose_turn = whose_turn_dict[pair]
        signal_int = signal_dfs_dict[pair]  # -1 = sell    1 = buy

        # BUY condition met
        if signal_int == 1:
            if whose_turn == 'buy':
                actions_dict[pair] = 'buy'
                whose_turn_dict[pair] = 'sell'
            else:  # the buy condition was met before but the order has not been filled
                actions_dict[pair] = 'buy_again'

        # SELL condition met
        elif signal_int == -1:
            if whose_turn == 'sell':
                actions_dict[pair] = 'sell'
                whose_turn_dict[pair] = 'buy'
            else:  # the sell condition was met, but it is not sell's turn yet.
                actions_dict[pair] = 'sell_again'

                # NEITHER buy or sell condition met
        else:
            actions_dict[pair] = 'neutural'

    return actions_dict


def make_order_observation_csv_line(orderId, order_info_dict):
    """returns a string to go in live order tracking file
    """

    new_live_order_line = str(orderId) + ',' \
                          + str(order_info_dict['symbol']) + ',' \
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

    # used as primary key among orders (not sure if this or clientOrderId best practice...)
    pair = placed_order_res['symbol']
    universal_symbol = convert_pair(pair, in_exchange=exchange, out_exchange='universal')

    orderId = placed_order_res['orderId']
    order_time = placed_order_res['transactTime']

    order_info_dict = dict()

    order_info_dict['symbol'] = universal_symbol
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
    order_open_dict[(orderId, universal_symbol)] = order_info_dict

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

    return orderId, universal_symbol, order_info_dict


def place_order(B_or_S, pair, o_type, base_qty, price=None, order_id=None):
    """places an orders.py

    input:
        pair (str): 'BTCUSDT'... use universal_symbol tracked NOT the USA universal_symbol, it will convert it
        o_type (str): 'limit' only supported now, in future maybe, market and more...
        B_or_S (str): 'buy' or 'sell'
        base_qty (float): amount of base asset to buy (i.e. BTC in BTCUSDT )
        quote_qty (float): same functionality as base_qty, but for quote... NOT YET SUPPORTED
        price (float): price of base asset in quote asset terms

    returns:
        ???? not sure need:
        order ID to track the order status, maybe more
    """

    if pair not in pairs_traded:  # ###PAUL  not sure what I wanted to be doing here
        raise KeyError

    # ### verify constraints met for order... stepSize and tickSize should be only ones affected
    #
    #
    info = pair_info_df.loc[pair]

    # most important / relevant checks
    base_qty = round_step_size(quantity=base_qty, step_size=info['stepSize'])
    price = round_step_size(quantity=price, step_size=info['tickSize'])

    # exchange rules
    if base_qty < info['minQty'] or base_qty > info['maxQty']:
        raise ValueError

    if price < info['minPrice'] or price > info['maxPrice']:
        raise ValueError

    # ###PAUL would like to get rid of the below and raise a ValueError also
    # notional requirements (makes sure that the order is large enough in terms of quote asset)
    if price * base_qty < info['minNotional']:
        print('    Price: ' + str(price) + '\n')
        print('    base_qty: ' + str(base_qty) + '\n')
        print("    info['minNotional']: " + str(info['minNotional']) + '\n')

        return 'order not placed MIN_NOTIONAL issue '

    # ### place order
    #
    #
    # string used to place order on pair on the exchange
    exchange_symbol = info['exchange_symbol']

    if o_type == 'limit':
        print('placing order')
        print('Limit Order:  ' + B_or_S + ' ' + str(base_qty) + ' ' + exchange_symbol + ' for $' + str(price))

        if B_or_S == 'buy':
            order_res = client.order_limit_buy(symbol=exchange_symbol,
                                               quantity=base_qty,
                                               price=price
                                               )

        if B_or_S == 'sell':
            order_res = client.order_limit_sell(symbol=exchange_symbol,
                                                quantity=base_qty,
                                                price=price
                                                )

    else:
        print('Error: order type not supported')
        raise TypeError

    process_placed_order(order_res)

    return order_res


def write_closed_order(orderId, pair, order_info_dict):
    """writes order that has closed to a file of orders for that pair
    """

    global order_open_dict
    global params

    header = 'orderId,ticker,clientOrderId,placedTime,price,origQty,executedQty,cummulativeQuoteQty,side,status,ord_type,updateTime\n'
    new_line = make_order_observation_csv_line(orderId, order_info_dict)

    daily_trade_fp = get_data_file_path('closed_order', pair, date='live', port=port_name, exchange=exchange)

    # check that the file exists for the correct time period
    file_existed = os.path.isfile(daily_trade_fp)
    with open(daily_trade_fp, "a") as f:
        if file_existed == False:  # then new file, write header
            f.write(header)
        f.write(new_line)
    os.chmod(daily_trade_fp, 0o777)

    return None


def remove_order_from_open_tracking(tuple_key):
    """serves 3 primary purposes:  1.) removes order from ./data/orders/open/open_orders.csv
                                   2.) writes the order to the pair's / day's closed order file
                                   3.) removes order from global tracking dictionary
    """

    global order_open_dict

    orderId, universal_symbol = tuple_key
    order_info_dict = order_open_dict[(orderId, universal_symbol)]

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
    write_closed_order(orderId, universal_symbol, order_info_dict)

    # ### remove order from dictionary... must do last, info here used to write to closed order file
    #
    del order_open_dict[(orderId, universal_symbol)]

    return None


def close_order(order_id_tuple):
    orderId, universal_symbol = order_id_tuple
    exchange_symbol = convert_pair(universal_symbol, in_exchange='universal', out_exchange=exchange)

    tuple_key = (orderId, universal_symbol)

    # cancel the order
    try:
        order_res = client.cancel_order(symbol=exchange_symbol, orderId=orderId)
        remove_order_from_open_tracking(tuple_key)

        print('closed order: ')
        print(order_res)

    except Exception as e:
        print('order cancel attempted, it seems order was filled: ')
        print('    symbol: ' + exchange_symbol + '  orderId: ' + str(orderId) + '/n /n /n')
        print(e)
        print('/n /n /n ')

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


def check_opens_and_close_lower_priority_orders(B_or_S, price, pair):
    """goes over all the open orders for the set of API keys and if the new order
    """

    global order_open_dict

    order_higher_priority = False
    order_open_for_pair = False
    keys_to_close = []

    # ###PAUL_refractor... this could (should?) be built more DRY
    for key in order_open_dict.keys():
        _, order_pair = key
        if pair == order_pair:
            print('pair match for order')
            order_open_for_pair = True

            old_price = float(order_open_dict[key]['price'])
            if B_or_S == 'buy' and price > old_price or B_or_S == 'sell' and price < old_price:
                print("order qualifying condition ---- " + B_or_S + '  ask was  ' + str(old_price)
                      + '  updated to:   ' + str(price))
                order_higher_priority = True
                keys_to_close.append(key)

    for key in keys_to_close:
        close_order(key)

    return order_higher_priority, order_open_for_pair


# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split


###PAUL... should orders be checked for before every order attempt?
def check_for_closed_orders():
    """checks if any of the open orders being tracked are now closed and removes them from tracking
    TODO: need to add order fills to tracking consider ./data/orders/filled/  (filled being a new dir)
    """

    global order_open_dict

    # get open orders from exchange
    open_orders_res_list = client.get_open_orders()

    # put list of keys: tuples (orderId, universal_symbol) from exchange collected
    open_orders_on_exchange = []
    for res in open_orders_res_list:
        exchange_symbol = res['symbol']
        universal_symbol = convert_pair(exchange_symbol, in_exchange=exchange, out_exchange='universal')

        orderId = res['orderId']
        tup = (orderId, universal_symbol)

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

    global pair_info_df

    global bag_max_dict
    global bag_actual_dict
    global bag_desired_dict

    update_signals()  # also includes update to long and short term prices

    # get desired action for pair
    actions_dict = update_actions_dict()

    # want update holdings and value as near as placing new orders as possible... this cancels open orders
    update_port_holdings_and_value()

    for pair in pairs_traded:

        exchange_symbol = convert_pair(pair, in_exchange='universal', out_exchange=exchange)

        # place buy/sell order
        action = actions_dict[pair]

        # most actions should be neutral... save time by passing on other actions if neutral
        if action == 'neutural':
            continue

        update_desired_bags(action, pair)  # bag for pair to  {0, max_bag_for_pair} based on allocation

        actual_base_in_quote_value = bag_actual_dict[pair]['base_in_quote']
        desired_base_in_quote_value = bag_desired_dict[pair]['base_in_quote']

        diff = desired_base_in_quote_value - actual_base_in_quote_value

        # if diff to small, we dont do anything
        ###PAUL this only works IF QUOTE IS IN DOLLARS..
        ###PAUL once trading in other quotes need to figure out another way to go about this
        if -25 < diff and diff < 25:
            continue  # skips to next iteration of for loop

        # info needed whether buying or selling
        last_price_df_t = short_term_prices_dict[pair].iloc[-1:]
        mid_vwap = float(last_price_df_t['mid_vwap'])
        mid_ewm = float(last_price_df_t['mid_ewm'])

        # need to update holdings before this selling... there is a delay,
        # however, updating each pair individually is too many API requests...
        # this means just catch the error on the order... yes this same problem can apply to the buys
        # need to find the specific type of error and see what happens.. lets go sell too much btc

        ###PAUL TODO: should add order book info on prices to this to take advantage of scan wicks
        # this means buying at the scam price if lower than the above, vise versa selling
        if diff >= 25:  # we are buying
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
            baseAsset = pair_info_df.loc[pair]['baseAsset']
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
            continue

        #         try:

        order_higher_priority, order_open_for_pair = check_opens_and_close_lower_priority_orders(B_or_S,
                                                                                                 price,
                                                                                                 pair)

        ###PAUL expecting an error here. if order is filled between the time the order_open_dict is checked
        ###PAUL this point then the attempt to close should fail... the try catch is to enable this

        #         except RuntimeError as e:
        #             print('ERROR PLACING ORDER')
        #             print('    ###PAUL it appears an order was filled between the time the closed orders were ')
        #             print('    ###PAUL checked for and the time it was attempted to be closed')
        #             print('    ###PAUL this is just a warning which seems to be the cleanest way to handle right now /n /n')
        #             print(e)
        #             print('/n /n /n')
        #             continue  # want to continue so no order is placed as its been filled

        #         print('closing order to update to higher priority')
        #         close_order(key)

        # if  order_higher_priority  or no   order_open_for_pair  then order
        if order_higher_priority == True or order_open_for_pair == False:
            print('LIMIT ORDER ---- ' + B_or_S + ' - ' + str(qty) + ' - ' + pair
                  + ' for $' + str(price) + ' ---- port_name: ' + port_name)
            order_res = place_order(B_or_S=B_or_S,
                                    pair=pair,
                                    o_type='limit',
                                    base_qty=qty,
                                    price=price
                                    )
            print('order_res:  ')
            print(order_res)
            process_placed_order(order_res)

    check_for_closed_orders()  # stops tracking orders that were closed any way (filled, bot, or manual)

    # only update the portfolios most recent update time if this function runs to fruition
    update_most_recent_order_check_file(params)

    if iter_count % 10 == 0:
        print('ALGOS - LIVE BOT - iter: ' + str(iter_count) \
              + ' ---- port: ' + port_name \
              + ' ---- exchange: ' + exchange)

    iter_count += 1

    return None

# def place_signal_on_orders_exception_catch():
#     try:
#         place_orders_on_signal(params)
#     except Exception as e:
#         print('/n /n ALGOS - LIVE BOT - TOP LEVEL ERROR! /n /n')
#         print(e)
#         print('/n /n /n')
#         send_email(subject = 'live bot notebook failed',
#                    message = 'the error was: ' + str(e)
#                   )

# signal_based_order_interval = params['constants']['signal_based_order_interval']
# place_orders_on_signal_task = task.LoopingCall(f=place_signal_on_orders_exception_catch)
# place_orders_on_signal_task.start(signal_based_order_interval)





# cell_split
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split  ----------------------------------------------------------------------------------------
# cell_split
