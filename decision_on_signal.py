import sys
sys.path.insert(0, '..')  # for local imports from the top directory
sys.path.insert(0, '../..')  # for local imports from the top directory

from algos.decision import (make_requests_dict,
                            actions_to_bull_or_bear_dict,
                            update_state_dict, 
                            decide_live, )
from algos.utils import (check_if_dir_exists_and_make,
                         query_trading_summary,
                         query_signal_by_name,
                         read_json_to_dict, )
from src.util import get_logger, get_secret

import ccxt
import datetime
from datetime import timedelta
import numpy as np
import pandas as pd
import pickle
import time

# ### hard coded solutions which should be finalized and then handled better
exchange = 'binance'
symbol = 'BTC-USDT'
pairs_traded = ['BTC-TUSD']
assets_in_port = {'BTC', 'TUSD'}  # ###PAUL TODO: generate this off pairs traded list?
client = ccxt.binance({'apiKey': get_secret("BINANCE_API_KEY_1"), 'secret': get_secret("BINANCE_SECRET_KEY_1")})

mins_between_decision_check = 1
signal_name = f"prod_1____BTC_USDT_trades_only_data"
signal_make_delay = 50  # seconds
decision_params = {'fee': 0.01,
 'max_workers': 70,
 'cool_down': 15,
 'threshold': -0.09999999999999998,
 'pred_dist': 0.25,
 'price_dist': 0.0185,
 'stop_limit': 0.045,
 'overrides': ['stop_limit'],
 'any_two': [],
 'to_neutral_threshold': 0.375,
 'to_neutral_pred_dist': 0.14999999999999997,
 'to_neutral_price_dist': 0.0022500000000000003,
 'to_neutral_stop_limit': 0.0205,
 'to_neutral_overrides': ['stop_limit'],
 'to_neutral_any_two': []}


# #### STARTUP LOGIC
#
#
port_path = f"/opt/shared/crypto/algos/data/live/{signal_name}/"
dir_existed = check_if_dir_exists_and_make(dir=port_path)
if dir_existed is False:
    first_time_signal = True
    port_value = 100.0  # create as a float
    port_allocation_dict = {'BTC-TUSD': 1.0}
if not first_time_signal:
    # get all the stuff that is needed from state_dict and what not
    try:
        state_dict_fp = f"{port_path}state_dict.json"
        state_dict = read_json_to_dict(fp=state_dict_fp)
        port_value = state_dict['port_value']
        port_allocation_dict = state_dict['port_allocation_dict']
    except FileNotFoundError:
        first_time_signal = True

if first_time_signal:
    state_dict = {}
    update_state_dict(state_dict=state_dict, action='start', MODE='live')

# ###PAUL THESE SHOULD PROBABLY ALL GO IN STATE DICT (AS ITS EASIER TO RE-READ ESPECIALLY AS PORT VALUE CHANGES


# each is structured bag_dict[pair][base, base_in_quote, AND quote]
bag_max_dict = dict()  # max value of port for pair if all in the quote or itself - uses allocation_dict
bag_actual_dict = dict()  # what we really got
bag_desired_dict = dict()  # what we want



def make_symbol_filters_dict(universal_symbol, market_info_dicts, exchange):
    """
    universal_symbol (str): Ex: BTC-USDT
    info (dict): result of ccxt_client.fetch_markets()
    exchange (str):  exchange (being traded, not data)   Ex: binanceus
    """

    filters_dict = {}

    # ###PAUL TODO... not needed but this functionlaity will ne needed
    # exchange_symbol = convert_symbol(universal_symbol, in_exchange='universal', out_exchange=exchange)
    exchange_symbol = universal_symbol  # TEMP_FIX

    for d in market_info_dicts:
        if d['id'] == exchange_symbol:
            symbol_dict = d

    filters_dict['universal_symbol'] = universal_symbol
    filters_dict['id'] = symbol_dict['id']
    filters_dict['base'] = symbol_dict['base']
    filters_dict['precision_amount'] = symbol_dict['precision']['amount']
    filters_dict['quote'] = symbol_dict['quote']
    filters_dict['precision_price'] = symbol_dict['precision']['price']

    limits_price_min = symbol_dict['limits']['price']['min']
    if limits_price_min is None:
        limits_price_min = 0
    filters_dict['limits_price_min'] = limits_price_min

    limits_price_max = symbol_dict['limits']['price']['max']
    if limits_price_max is None:
        limits_price_max = 10e6
    filters_dict['limits_price_max'] = limits_price_max

    filters_dict['limits_amount_min'] = symbol_dict['limits']['amount']['min']
    filters_dict['limits_amount_max'] = symbol_dict['limits']['amount']['max']
    filters_dict['limits_cost_min'] = symbol_dict['limits']['cost']['min']
    filters_dict['limits_cost_max'] = symbol_dict['limits']['cost']['max']

    # precision numbers for these exchanges given in terms of # of decimals must --> tick size
    if exchange in ['binance', 'binanceus']:
        # swap_from_int_to_ticksize = True
        filters_dict['precision_amount'] = 1 / 10 ** filters_dict['precision_amount']
        filters_dict['precision_price'] = 1 / 10 ** filters_dict['precision_price']

    return filters_dict


def make_pair_info_df():
    """makes DataFrame, indexed by column "universal_symbol" with columns:
        'exchange_symbol', 'baseAsset', 'baseAssetPrecision', 'quoteAsset', 'quoteAssetPrecision',
        'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty', 'stepSize', 'minNotional',
        'marketMinQty', 'marketMaxQty', 'marketStepSize'
    """

    global pair_info_df
    global client

    pair_entry_list = []

    markets = client.fetch_markets()

    for symbol in pairs_traded:
        filters_dict = make_symbol_filters_dict(universal_symbol=symbol,
                                                market_info_dicts=markets,
                                                exchange=exchange)
        pair_entry_list.append(filters_dict)

    pair_info_df = pd.DataFrame.from_records(pair_entry_list, index='universal_symbol')
    pair_info_df = pair_info_df.astype(dtype=order_filters_names_type_dict)


def get_opening_portfolio():
    """funky start for this portfolio (probably want to rely on state dictionary)
    """


# ### LIVE LOOPING
#
iter_count = 0
num_decisions = 0
now = pd.to_datetime(datetime.datetime.now())
next_time_to_decide = (now.floor('min') + timedelta(seconds=signal_make_delay)).to_pydatetime()

while True:
    if iter_count % 10 == 0 or iter_count < 5:
        print(f"check for signal update iter # {iter_count}")
    iter_count += 1

    now = pd.to_datetime(datetime.datetime.now())

    if now > next_time_to_decide:
        if num_decisions % 10 == 0:
            print(
                f"update iter #: {num_decisions} ---- updates {signal_make_delay} second after the start of every minute")
        num_decisions += 1

        last_decision_time = state_dict['last_decision_time']
        trading_summary = query_trading_summary(exchange, symbol, start_date=last_decision_time, end_date=None)
        signal = query_signal_by_name(signal_name, start_date=last_decision_time, end_date=None)
        time_to_decide_till = min(trading_summary.index[-1], signal.index[-1])

        vwap = trading_summary['vwap'][trading_summary.index <= time_to_decide_till]
        signal = signal[signal.index <= time_to_decide_till]


        triggered_actions, state_dict = \
            decide_live(state_dict, signal, vwap, requests_dict, debug_triggers=False, max_transacts=10_000)
        next_time_to_decide = next_time_to_decide + timedelta(minutes=mins_between_decision_check)

    time.sleep(1)

