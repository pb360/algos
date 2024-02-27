""" this module contains functionality that should only be utilized by live services

things here maybe useful for debugging... specifically `load_cached_state_dict()`

assumption of operating this bot
-  inventory managment ---- assumes this bot is the only one touch any of the symbols in the pairs traded
- `params`     ---- is for settings and constants that will never change during the operation of the portfolio
- `state_dict` ---- for things whose state change ---- managed activley by the service utilizing the `state_dict`
"""

import sys
sys.path.insert(0, "..")

from algos.config import params
from algos.decision import decide_live
from algos.utils import (
    convert_date_format,
    get_data_file_path,
    check_if_dir_exists_and_make,
    convert_symbol,
    query_trading_summary,
    query_signal_by_name,
    round_by_step_or_decimal,
)

from copy import deepcopy
from ccxt.base.errors import InsufficientFunds
import datetime
import dotenv
import math
import os
import pandas as pd
import pickle
import time

dotenv.load_dotenv()


# ### functions that affect `params`
#
#
def directory_check_for_portfolio_data(params):
    """checks that the directory setup for the current portfolio is correct
    if needed it will create a directory in ./data/<port_name> with other necessary thing in it.
    """

    paths_needed = []
    fps_needed = []

    # create portfolio orders dir:         ./data/<exchange>/<port_name>   ...if its not there yet
    port_path = get_data_file_path(
        data_type="port_folder",
        pair=None,
        date="live",
        port=params["port"]["port_name"],
        exchange=None,
    )

    paths_needed.append(port_path)
    fps_needed.extend(
        [
            port_path + "last_check.txt",
            port_path + "open_orders.csv",
        ]
    )

    for exchange in params["port"]["exchanges"]:
        exchange_open_order_fp = get_data_file_path(
            data_type="open_orders",
            pair=None,
            date="live",
            port=params["port"]["port_name"],
            exchange=exchange,
        )
        exchange_closed_order_dir = get_data_file_path(
            data_type="closed_orders",
            pair=None,
            date="path",
            port=params["port"]["port_name"],
            exchange=exchange,
        )

        fps_needed.append(exchange_open_order_fp)
        paths_needed.append(exchange_closed_order_dir)

        for pair in params["port"]["pairs_traded"]:
            paths_needed.append(port_path + "orders/" + exchange + "/closed/" + pair + "/")

    # MAKE PATHS AND FILES
    for needed_path in paths_needed:
        check_if_dir_exists_and_make(needed_path)
    for fp in fps_needed:
        if not os.path.isfile(fp):
            with open(fp, "x"):
                pass

    return None


def make_symbol_filters_dict(universal_symbol, market_info_dicts, params):
    """
    universal_symbol (str): Ex: BTC-USDT
    info (dict): result of ccxt_client.fetch_markets()
    """

    filters_dict = {}

    exchange_symbol = convert_symbol(universal_symbol, in_exchange="universal", out_exchange=params["port"]["exchange"])

    for d in market_info_dicts:
        if d["id"] == exchange_symbol:
            symbol_dict = d

    filters_dict["universal_symbol"] = universal_symbol
    filters_dict["id"] = symbol_dict["id"]
    filters_dict["base"] = symbol_dict["base"]
    filters_dict["precision_amount"] = symbol_dict["precision"]["amount"]
    filters_dict["quote"] = symbol_dict["quote"]
    filters_dict["precision_price"] = symbol_dict["precision"]["price"]

    limits_price_min = symbol_dict["limits"]["price"]["min"]
    if limits_price_min is None:
        limits_price_min = 0
    filters_dict["limits_price_min"] = limits_price_min

    limits_price_max = symbol_dict["limits"]["price"]["max"]
    if limits_price_max is None:
        limits_price_max = 10e6
    filters_dict["limits_price_max"] = limits_price_max

    filters_dict["limits_amount_min"] = symbol_dict["limits"]["amount"]["min"]
    filters_dict["limits_amount_max"] = symbol_dict["limits"]["amount"]["max"]
    filters_dict["limits_cost_min"] = symbol_dict["limits"]["cost"]["min"]
    filters_dict["limits_cost_max"] = symbol_dict["limits"]["cost"]["max"]

    # precision numbers for these exchanges given in terms of # of decimals must --> tick size
    if params["port"]["exchange"] in ["binance", "binanceus"]:
        # swap_from_int_to_ticksize = True
        filters_dict["precision_amount"] = 1 / 10 ** filters_dict["precision_amount"]
        filters_dict["precision_price"] = 1 / 10 ** filters_dict["precision_price"]

    return filters_dict


def make_pair_info_df(ccxt_client, state_dict, params):
    """puts`pair_info_df` in `params` ---- filled with useful info for exchange interaction

    indexed by column "universal_symbol" with columns listed below
    - columns:
        ['exchange_symbol', 'baseAsset', 'baseAssetPrecision', 'quoteAsset', 'quoteAssetPrecision',
        'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty', 'stepSize', 'minNotional',
        'marketMinQty', 'marketMaxQty', 'marketStepSize']

    TODO: support multi exchange
    """

    pair_entry_list = []

    markets = ccxt_client.fetch_markets()

    for symbol in params["port"]["pairs_traded"]:
        filters_dict = make_symbol_filters_dict(universal_symbol=symbol, market_info_dicts=markets, params=params)
        pair_entry_list.append(filters_dict)

    params["pair_info_df"] = pd.DataFrame.from_records(pair_entry_list, index="universal_symbol")
    order_filters_names_type_dict = params["data_format"][params["port"]["exchange"]]["order_filters_name_type"]
    params["pair_info_df"] = params["pair_info_df"].astype(dtype=order_filters_names_type_dict)


def get_set_of_assets_in_port(params):
    """makes `set_of_assets_in_port` and puts it in params"""

    set_of_assets_in_port = set()
    for pair in params["port"]["pairs_traded"]:
        base = params["pair_info_df"].loc[pair]["base"]
        quote = params["pair_info_df"].loc[pair]["quote"]
        set_of_assets_in_port.add(base)
        set_of_assets_in_port.add(quote)

    params["port"]["set_of_assets_in_port"] = set_of_assets_in_port


def get_primary_pricing_pair_per_asset(params):
    """a dictionary of assets in port keyed with the primary pair to use for pricing the value of that asset

    ###PAUL_usd_denomination TODO: unified true USD denomination work to be done here
        * TODO: make a DF for `assets_in_port` (differently indexed than pair_info_df which is done by pair)
        * TODO: this could go in `state_dict` as I think I want to keep prices here...

        TODO: BIG NOTE IN CAPS TO GRAB ATTENTION, I DON'T LIKE THAT THIS NEEDS ACTIVE ADJUSTMENT ON A PER PORTFOLIO BASIS
        THINGS THAT NEED THIS KINDOF ATTENTION SHOULD BE HOUSED SOLELY IN CONFIGS WITH SPARING EXCEPTIONS 
    """

    params["port"]["pricing_pair_per_asset"] = {}

    for symbol in params["port"]["set_of_assets_in_port"]:
        if symbol in {"BTC", "ETH", "BNB", "XRP", "ADA", "LTC", "LINK", "XLM", "DOGE", "KDA"}:
            params["port"]["pricing_pair_per_asset"][symbol] = symbol + "/USDT"
        elif symbol in ["TUSD", "USDT", "USD"]:
            # ###PAUL TODO: consider tracking stable prices... likely want an "oracle" vs basing on exchange's trading
            params["port"]["pricing_pair_per_asset"][symbol] = "STABLE"

# ### functions for `state_dict`
#
#
# initialize positions dict --> {'pair': 'neutral'}
def initialize_positions_dict(state_dict, params):
    state_dict["desired_position"] = {}

    for pair in params["port"]["pairs_traded"]:
        state_dict["desired_position"][pair] = "neutral"


# initialize allocation dict
def initialize_port_allocation_dict(state_dict, params):
    """initialized the proportion of assets in the trading account that go to each pair"""

    method = params["port"]["inventory_method"]
    port_allocation_dict = {}

    if method == "default":
        port_allocation_dict["ADA-USDT"] = 0.0
        port_allocation_dict["BNB-USDT"] = 0.0
        port_allocation_dict["BTC-USDT"] = 0.25
        port_allocation_dict["DOGE-USDT"] = 0.25
        port_allocation_dict["ETH-USDT"] = 0.25
        port_allocation_dict["LINK-USDT"] = 0.25
        port_allocation_dict["LTC-USDT"] = 0.0
        port_allocation_dict["XLM-USDT"] = 0.0

    elif method == "all BTC":
        for pair in params["port"]["pairs_traded"]:
            # if pair == 'BTC-USDT':
            if pair == "BTC-TUSD":
                port_allocation_dict[pair] = 1
            else:
                port_allocation_dict[pair] = 0
    elif method in {"stochastic_rebalance", "uniform"}:
        num_pairs = len(params["port"]["pairs_traded"])
        for pair in params["port"]["pairs_traded"]:
            port_allocation_dict[pair] = 1 / num_pairs
    elif method == "markowitz":
        raise NotImplementedError
    else:
        raise ValueError

    # UPDATE `state_dict`
    state_dict["port_allocation_dict"] = port_allocation_dict


def initialize_bag_dicts(state_dict, params):
    state_dict["bag_max"] = {}
    state_dict["bag_actual"] = {}
    state_dict["bag_desired"] = {}

    for pair in params["port"]["pairs_traded"]:
        state_dict["bag_max"][pair] = {"base": 0, "base_in_quote": 0, "quote": 0}
        state_dict["bag_actual"][pair] = {"base": 0, "base_in_quote": 0, "quote": 0}
        state_dict["bag_desired"][pair] = {"base": 0, "base_in_quote": 0, "quote": 0}


def initalize_last_time_checked(state_dict, params):
    state_dict["last_time_checked"] = {}
    for pair in params["port"]["pairs_traded"]:
        state_dict["last_time_checked"][pair] = 0


def cache_state_dict(state_dict, params):
    keys = params.keys()

    # ###PAUL TODO: consider making `port` vs `signal` a function argument, I could imagine updating both or having
    #         TODO: both fees in the top level of params, overall relying on params like this is ugly to me
    if "port" in keys:
        state_dict_fp = get_data_file_path(
            data_type="state_dict",
            pair="None",
            date="live",
            port=params["port"]["port_name"],
            exchange=params["port"]["exchange"],
            params=params,
        )
    if "signal" in keys:
        state_dict_fp = get_data_file_path(
            data_type="state_dict",
            pair="None",
            date="live",
            # port=params['port']['port_name'],
            signal=params["signal_name"],
            # exchange=params['port']['exchange'],
            params=params,
        )

    check_if_dir_exists_and_make(fp=state_dict_fp)
    pickle.dump(state_dict, open(state_dict_fp, "wb"))


def load_cached_state_dict(params):
    """state_dict ---- conta9ins pieces of live functionality that are changed by the script while params contains static things

    personal note: this was initially and solely utilized in the historical decision algorithm.
                   when implementing live version, also needed there but for persistance between restarts needed
                   to pickle. This pattern is needed for more than just frameworks (also signals... but I could see
                   it useful to extend to data collection (for various sources, especially of transformations are needed)
    """

    keys = params.keys()
    if "port" in keys:
        state_dict_fp = get_data_file_path(
            data_type="state_dict",
            pair="None",
            date="live",
            port=params["port"]["port_name"],
            exchange=params["port"]["exchange"],  # TODO: multi exchange???
            params=params,
        )

    if "signal" in keys:
        state_dict_fp = get_data_file_path(
            data_type="state_dict",
            pair="None",
            date="live",
            signal=params["signal_name"],
            params=params,
        )

    with open(state_dict_fp, "rb") as f:
        state_dict = pickle.load(f)
    return state_dict


def update_trading_summary(pair, trading_summaries, state_dict, params, ch_client=None):
    """also handles initialization of the `trading_summaries` dictionary"""

    last_check_pd_dti = convert_date_format(state_dict["last_time_checked"][pair], "pandas")
    min_start_date = convert_date_format((2018, 6, 1), "pandas")
    start_date = max(last_check_pd_dti, min_start_date)
    trading_summary = query_trading_summary(
        exchange=params["port"]["exchange"], symbol=pair, start_date=start_date, end_date=None, ch_client=ch_client
    )

    # merge the new prices with the old prices
    trading_summaries[pair] = trading_summary



def trading_summary_collection_check(trading_summaries, state_dict, params):
    all_pairs_empty = True
    for pair in params["port"]["pairs_traded"]:
        if trading_summaries[pair].shape[0] > 0:
            all_pairs_empty = False

    if all_pairs_empty:
        try:
            state_dict["consecutive_all_pair_empty"] += 1
        except KeyError:
            state_dict["consecutive_all_pair_empty"] = 0
        print(
            f"    - `all_pairs_empty` ---- leaving to see if it happens # ###PAUL_del_later \n"
            f"       state_dict['consecutive_all_pair_empty'] ---- {state_dict['consecutive_all_pair_empty']}\n" * 5
        )
        if state_dict["consecutive_all_pair_empty"] > 5:
            print(f"state_dict['consecutive_all_pair_empty'] is over the limit!!!!!!")
            import ipdb
            ipdb.set_trace()
            
    else:
        state_dict["consecutive_all_pair_empty"] = 0


def update_trading_summaries(trading_summaries, state_dict, params, ch_client=None):
    for pair in params["port"]["pairs_traded"]:
        update_trading_summary(pair, trading_summaries, state_dict, params, ch_client=ch_client)

    trading_summary_collection_check(trading_summaries, state_dict, params)


def update_signals(signal_dfs_dict, state_dict, params):
    """also handles initialization of the `signal_dfs_dict`"""

    for pair in params["port"]["pairs_traded"]:
        last_decision_time = state_dict["last_time_checked"][pair]  # TODO: multi exchange
        last_decision_time = convert_date_format(last_decision_time, "pandas")
        signal_name = params["active_services"]["ports"][params["port"]["port_name"]]["signal_name"]
        new_signal = query_signal_by_name(signal_name, start_date=last_decision_time, end_date=None)
        # TODO: neaten up later... theres a better way to do the below
        cutoff_time = datetime.datetime.now() + datetime.timedelta(hours=-240)
        signal_dfs_dict[pair] = new_signal[new_signal.index > cutoff_time]


def get_usd_value_of_port_holdings_and_positions(trading_summaries, ch_client, state_dict, params):
    """updates `state_dict` with this iterations `port_value` and `positions`"""

    port_value_running_sum = 0
    positions_list = []
    for symbol in params["port"]["set_of_assets_in_port"]:
        # gets holdings for that base asset / ticker
        state_dict["port_holdings_dict"][symbol] = state_dict["account_balances"][symbol]  
        pricing_pair = params["port"]["pricing_pair_per_asset"][symbol]

        if pricing_pair == "STABLE":  # ###PAUL_usd_denomination  # TODO: stables, stables, stables
            state_dict["last_prices_by_symbol_in_usd"][symbol] = float(1)
        else:

            try:
                symbol_price_in_quote = trading_summaries[pricing_pair]["vwap"].iloc[-1]  # TODO: dont hard code 'vwap'
            except:
                import pdb;      # ###PAUL TODO: DELETE LATER
                pdb.set_trace()  # ###PAUL TODO: DELETE LATER
    
            state_dict["last_prices_by_pair_in_quote"][pricing_pair] = symbol_price_in_quote

            quote_price_in_usd = 1  # ###PAUL_usd_denomination # TODO: stables, stables, stables
            symbol_in_usd = symbol_price_in_quote * quote_price_in_usd
            state_dict["last_prices_by_symbol_in_usd"][symbol] = symbol_in_usd

        last_price = state_dict["last_prices_by_symbol_in_usd"][symbol]
        qty = state_dict["port_holdings_dict"][symbol]["total"]
        ts = convert_date_format(time.time(), "pandas")

        # get strategy specific thing for the row in the positions table, add asset specific stuff here
        position = deepcopy(params["port"]["positions_table_info"])
        position.update(
            {
                "timestamp": ts,
                "leg_group_id": int(ts.timestamp() * 1000),
                "instrument": symbol,
                "size": qty,
                "mid_price": last_price,  # ###PAUL_usd_denomination TODO: i think this is okay to go
                "currency_price": 1,
                "currency_name": "USD",
            }
        )
        positions_list.append(position)

        qty = state_dict["port_holdings_dict"][symbol]["total"]
        asset_value = last_price * qty
        port_value_running_sum += asset_value

    # insert positions df into bob's table
    positions_df = pd.DataFrame(positions_list)
    ch_client.execute(
        "INSERT INTO algos_db.Positions VALUES ",
        positions_df.reset_index().to_dict("records"),
        types_check=True,
    )

    state_dict["port_value"] = port_value_running_sum
    state_dict["positions_df"] = positions_df  # ###PAUL TODO: update this on a per pair basis in the for loop above, this means 
    # ###PAUL TODO: that the positions won't be overridden in the case that that a new trading summary hasn't been seen for a pair 


def update_bag_dicts(state_dict, ch_client, params):
    """updates desired bags"""

    # TODO: need to account for having a base asset shared among two pairs - EX: ETH-TUSD, ETH-BTC,
    # TODO: the quote asset is already "handled" because its derived from `value_for_pair` and `value_of_base`
    for pair in params["port"]["pairs_traded"]:
        base = params["pair_info_df"].loc[pair]["base"]
        quote = params["pair_info_df"].loc[pair]["quote"]
        qty_base = state_dict["account_balances"][base]["total"]
        base_priced_in_quote = state_dict["last_prices_by_pair_in_quote"][pair]
        base_priced_in_usd = state_dict["last_prices_by_symbol_in_usd"][base]
        quote_priced_in_usd = state_dict["last_prices_by_symbol_in_usd"][quote]
        total_usd_for_pair = state_dict["port_allocation_dict"][pair] * state_dict["port_value"]

        # ### MAX BAG update
        #
        max_quote_qty_for_pair = total_usd_for_pair / quote_priced_in_usd
        # TODO: (BELOW) # should be `base_priced_in_usd` but cant do till have TUSD price correct (BELOW)
        max_base_qty_for_pair = total_usd_for_pair / base_priced_in_quote
        #
        state_dict["bag_max"][pair]["base"] = max_base_qty_for_pair
        state_dict["bag_max"][pair]["base_in_quote"] = base_priced_in_quote * max_base_qty_for_pair
        state_dict["bag_max"][pair]["base_in_usd"] = total_usd_for_pair
        state_dict["bag_max"][pair]["quote"] = max_quote_qty_for_pair
        state_dict["bag_max"][pair]["quote_in_usd"] = total_usd_for_pair

        # ### ACTUAL BAG update
        #
        base_qty_in_quote = qty_base * base_priced_in_quote
        # TODO: (BELOW) should be `base_priced_in_usd` but cant do till have TUSD price correct
        base_qty_in_usd = qty_base * base_priced_in_quote
        quote_qty = max_quote_qty_for_pair - base_qty_in_quote
        qty_quote_in_usd = quote_qty * quote_priced_in_usd

        state_dict["bag_actual"][pair]["base"] = qty_base
        state_dict["bag_actual"][pair]["base_in_quote"] = base_qty_in_quote
        state_dict["bag_actual"][pair]["base_in_usd"] = base_qty_in_usd
        state_dict["bag_actual"][pair]["quote"] = quote_qty
        state_dict["bag_actual"][pair]["quote_in_usd"] = qty_quote_in_usd

        inventory_method = params["port"]["inventory_method"]

        if inventory_method == "LS_replication":
            if "LS" not in state_dict:
                print(f"resetting long short portfolio managment \n" * 10)
                state_dict["LS"] = {}

            if pair not in state_dict["LS"]:
                state_dict["LS"][pair] = {}

                # initial values, these never change during operation of this portfolio
                initial_TUSD = 50
                initial_BTC = (
                    max_base_qty_for_pair - initial_TUSD / base_priced_in_quote
                )  # should be `base_priced_in_usd` but cant do till have TUSD price correct
                initial_BTC_in_TUSD = (
                    initial_BTC * base_priced_in_quote
                )  # should be `base_priced_in_usd` but cant do till have TUSD price correct

                state_dict["LS"][pair]["initial_quote"] = initial_BTC
                state_dict["LS"][pair]["initial_base"] = initial_TUSD
                state_dict["LS"][pair]["BTC_before_trade"] = initial_BTC
                state_dict["LS"][pair]["BTC_before_trade_prior_iter"] = initial_BTC  # not used first iter
                state_dict["LS"][pair]["BTC_in_TUSD_before_trade"] = initial_BTC_in_TUSD
                state_dict["LS"][pair]["TUSD_before_trade"] = initial_TUSD
                state_dict["LS"][pair]["TUSD_before_trade_prior_iter"] = initial_TUSD  # not used first iter

            # not the first run for the pair
            else:
                state_dict["LS"][pair]["BTC_before_trade"] = (
                    state_dict["LS"][pair]["initial_quote"] + state_dict["LS"][pair]["mocked_port_BTC_target_current"]
                )  # reset, so value from prior iter
                state_dict["LS"][pair]["BTC_in_TUSD_before_trade"] = (
                    base_priced_in_quote * state_dict["LS"][pair]["BTC_before_trade"]
                )
                state_dict["LS"][pair]["TUSD_before_trade"] = state_dict["LS"][pair][
                    "TUSD_before_trade_prior_iter"
                ] + base_priced_in_quote * (
                    state_dict["LS"][pair]["BTC_before_trade_prior_iter"] - state_dict["LS"][pair]["BTC_before_trade"]
                )

            state_dict["LS"][pair]["replication_port_val_before_trade"] = (
                state_dict["LS"][pair]["BTC_in_TUSD_before_trade"] + state_dict["LS"][pair]["TUSD_before_trade"]
            )
            # TODO: (BELOW) should be `base_priced_in_usd` but cant do till have TUSD price correct
            state_dict["LS"][pair]["mocked_port_value_before_trade"] = (
                state_dict["LS"][pair]["replication_port_val_before_trade"]
                - base_priced_in_quote * state_dict["LS"][pair]["initial_quote"]
            )

            # `mocked_port_BTC_target_current`
            if state_dict["desired_position"][pair] == "short":
                # TODO: (BELOW) should be `base_priced_in_usd` but cant do till have TUSD price correct
                mocked_port_BTC_target_current = -state_dict["LS"][pair]["mocked_port_value_before_trade"] / base_priced_in_quote
            elif state_dict["desired_position"][pair] == "long":
                # TODO: (BELOW) should be `base_priced_in_usd` but cant do till have TUSD price correct
                mocked_port_BTC_target_current = state_dict["LS"][pair]["mocked_port_value_before_trade"] / base_priced_in_quote
            elif state_dict["desired_position"][pair] == "neutral":
                mocked_port_BTC_target_current = 0

            state_dict["LS"][pair]["mocked_port_BTC_target_current"] = mocked_port_BTC_target_current

            state_dict["bag_desired"][pair]["base"] = mocked_port_BTC_target_current + state_dict["LS"][pair]["initial_quote"]
            state_dict["bag_desired"][pair]["base_in_quote"] = base_priced_in_quote * state_dict["bag_desired"][pair]["base"]
            state_dict["bag_desired"][pair]["base_in_usd"] = base_priced_in_usd * state_dict["bag_desired"][pair]["base"]

            state_dict["bag_desired"][pair]["quote"] = (
                state_dict["LS"][pair]["TUSD_before_trade"]
                + (state_dict["LS"][pair]["BTC_before_trade"] - state_dict["bag_desired"][pair]["base"]) / base_priced_in_usd
            )
            state_dict["bag_desired"][pair]["quote_in_usd"] = state_dict["bag_desired"][pair]["quote"]

            if state_dict["desired_position"][pair] in ["short", "long"]:
                state_dict["LS"][pair]["mocked_port_TUSD_target_current"] = 0
                base_qty = state_dict["LS"][pair]["mocked_port_BTC_target_current"]
                quote_qty = state_dict["LS"][pair]["mocked_port_TUSD_target_current"]
            # TODO: ^^^^ consider multiple pairs sharing the same quote (will make multiple position rows in the df
            elif state_dict["desired_position"][pair] == "neutral":
                state_dict["LS"][pair]["mocked_port_TUSD_target_current"] = state_dict["LS"][pair][
                    "mocked_port_value_before_trade"
                ]
                base_qty = 0
                quote_qty = state_dict["LS"][pair]["mocked_port_TUSD_target_current"]
            else:
                print(f"state_dict['desired_position'][pair] = {state_dict['desired_position'][pair]}!!")
                raise ValueError

            # TODO: MULTIASSET_TRADING higher priority item here.. needed for multi asset trading but not  before
            pair_position = {
                "base": {
                    "size": base_qty,
                    "price": base_priced_in_quote,  # todo... should be done in USD but dont have yet
                    "symbol": "BTC",
                },  # TODO parameterize
                "quote": {
                    "size": quote_qty,
                    "price": quote_priced_in_usd,
                    "symbol": "TUSD",
                },  # TODO parameterize
            }

            ts = convert_date_format(time.time(), "pandas")
            positions_list = []

            for side in ["base", "quote"]:
                position = deepcopy(params["port"]["positions_table_info"])
                position.update(
                    {
                        "strategy": "peak_bottom____long_short",
                        "timestamp": ts,
                        "leg_group_id": int(ts.timestamp() * 1000),
                        "instrument": pair_position[side]["symbol"],
                        "size": pair_position[side]["size"],
                        "mid_price": pair_position[side]["price"],
                        "currency_price": 1,
                        "currency_name": "USD",
                    }
                )
                positions_list.append(position)

            # insert positions df into bob's table
            positions_df = pd.DataFrame(positions_list)
            ch_client.execute(
                "INSERT INTO algos_db.Positions VALUES ",
                positions_df.reset_index().to_dict("records"),
                types_check=True,
            )

            state_dict["positions_df____long_short"] = positions_df

            # write the current position to the prior one
            # reset prior iter values for next time.
            state_dict["LS"][pair]["BTC_before_trade_prior_iter"] = state_dict["LS"][pair]["BTC_before_trade"]
            state_dict["LS"][pair]["TUSD_before_trade_prior_iter"] = state_dict["LS"][pair]["TUSD_before_trade"]

        elif inventory_method == "stochastic_with_signal":
            # ### DESIRED BAG update
            #
            desired_position = state_dict["desired_position"][pair]
            if desired_position in {"long"}:  # 'buy', 'buy_again'  TODO: priority leveled ordering
                base_mult = 1
            elif desired_position in {"neutral"}:
                base_mult = 0.5
            elif desired_position in {"short"}:  # 'sell', 'sell_again', TODO: priority leveled ordering
                base_mult = 0
            quote_mult = 1 - base_mult

            state_dict["bag_desired"][pair]["base"] = state_dict["bag_max"][pair]["base"] * base_mult
            state_dict["bag_desired"][pair]["base_in_quote"] = state_dict["bag_max"][pair]["base_in_quote"] * base_mult
            state_dict["bag_desired"][pair]["base_in_usd"] = state_dict["bag_max"][pair]["base_in_usd"] * base_mult
            state_dict["bag_desired"][pair]["quote"] = state_dict["bag_max"][pair]["quote"] * quote_mult
            state_dict["bag_desired"][pair]["quote_in_usd"] = state_dict["bag_max"][pair]["quote_in_usd"] * quote_mult

        elif inventory_method == "stochastic_rebalance":
            state_dict["bag_desired"][pair]["base"] = state_dict["bag_max"][pair]["base"]
            state_dict["bag_desired"][pair]["base_in_quote"] = state_dict["bag_max"][pair]["base_in_quote"]
            state_dict["bag_desired"][pair]["base_in_usd"] = state_dict["bag_max"][pair]["base_in_usd"]
            state_dict["bag_desired"][pair]["quote"] = state_dict["bag_max"][pair]["quote"]
            state_dict["bag_desired"][pair]["quote_in_usd"] = state_dict["bag_max"][pair]["quote_in_usd"]


def update_account_balances(ccxt_client, state_dict):
    # update port holdings    ---- note: it gets all holdable assets on some exchanges....
    account_balances_t = (
        ccxt_client.fetch_balance()
    )  # ccxt returns dict of dicts:  'XRP': {'free': 0.0, 'used': 0.0, 'total': 0.0}
    del account_balances_t["info"]
    state_dict["account_balances"] = account_balances_t


def update_port_holdings_and_value(ccxt_client, ch_client, state_dict, trading_summaries, params):
    """updates things in `state_dict`
    differentiation between holdings and bags
       - holdings is EVERYTHING in the account
       - bags are things that are tradable according to pairs tracked
       - value is determined from bags, all holdings are not included in value nor touched by the bot by default
    """


    if trading_summaries[params["port"]["pairs_traded"][0]].shape[0] == 0:
        return

    # hard reset all these
    state_dict["port_value"] = 0
    state_dict["port_holdings_dict"] = {}  # {'free':free, 'locked':locked, 'total':total} NEEDS RESET EACH ITER
    state_dict["last_prices_by_symbol_in_usd"] = {}  # eventually will want a more advanced way of creating this
    state_dict["last_prices_by_pair_in_quote"] = {}  # eventually will want a more advanced way of creating this

    # get actual holdings on exchange
    update_account_balances(ccxt_client, state_dict)

    # loops over portfolio by ASSET ---- [BTC, ETH, TUSD]
    get_usd_value_of_port_holdings_and_positions(trading_summaries, ch_client, state_dict, params)

    # loops over portfolio by PAIR ---- [BTC-TUSD, ETH-TUSD, ETH-BTC]
    update_bag_dicts(state_dict, ch_client, params)


def update_desired_positions_dict(trading_summaries, signal_dfs_dict, state_dict, params):
    """adjusts state_dict['desired_position'] (dict): {'BTCUSDT':'long', 'LINKUSDT':neutral, 'XRPUSDT':'short'}"""

    if params["port"]["inventory_method"] == "stochastic_rebalance": 
        for pair in params["port"]["pairs_traded"]:
            state_dict["desired_position"][pair] = "long" 

    if params["port"]["inventory_method"] == "stochastic_with_signal": 
        print(f"""need to implement params["port"]["inventory_method"] == "stochastic_with_signal" """)
        raise NotImplemented

    if params["port"]["inventory_method"] == "LS_replication": 
        for pair in params["port"]["pairs_traded"]:
            triggered_actions = decide_live(
                state_dict=state_dict,
                signal=signal_dfs_dict[pair],
                prices=trading_summaries[pair]["vwap"],
                requests_dict=params["port"]["decision_params"],
                pair=pair,
                debug_triggers=False,
            )

            if len(triggered_actions) > 0:  # NOTE: only update desired position if an action is triggered
                action = triggered_actions[-1]
                position = "neutral" if action in ["exit_short", "exit_long"] else action
                state_dict["desired_position"][pair] = position  # [short, neutral, long]


def make_ccxt_order_info_dict(response):
    """takes a CCXT style placed OR fetch order response and makes it into an order info dict"""

    # things that gotta be done first
    order_info_dict = dict()

    order_info_dict["id"] = response["id"]
    order_info_dict["symbol"] = response["symbol"].replace("/", "-")  # fetch order may come with '/'...
    order_info_dict["clientOrderId"] = response["clientOrderId"]
    order_info_dict["timestamp"] = response["timestamp"]
    order_info_dict["price"] = response["price"]
    order_info_dict["amount"] = response["amount"]
    order_info_dict["filled"] = response["filled"]
    order_info_dict["cost"] = response["cost"]
    order_info_dict["side"] = response["side"]  # ###PAUL TODO: maybe need to switch this to [0, 1]?
    order_info_dict["status"] = response["status"]
    order_info_dict["type"] = response["type"]

    return order_info_dict


def make_order_observation_csv_line(order_info_dict):
    """returns a string to go in live order tracking file
    only to be used on a fetched order status using ccxt_client.fetch_order()

    keep as a string instead of looping over key in var because it allows for ctrl+shift+f'ing
    """

    try:
        remaining = order_info_dict["remaining"]
    except KeyError:
        remaining = 0

    new_live_order_line = (
        order_info_dict["id"]
        + ","
        + str(order_info_dict["symbol"])
        + ","
        + str(order_info_dict["side"])
        + ","
        + str(order_info_dict["price"])
        + ","
        + str(order_info_dict["amount"])
        + ","
        + str(order_info_dict["filled"])
        + ","
        + str(order_info_dict["cost"])
        + ","
        + str(remaining)
        + ","
        + str(order_info_dict["status"])
        + ","
        + str(order_info_dict["timestamp"])
        + ","
        + str(order_info_dict["type"])
        + str(order_info_dict["clientOrderId"])
        + ","
        + "\n"
    )

    return new_live_order_line


def process_placed_order(placed_order_res, state_dict, params):
    """makes live order observation from placed order response.. note there are subtle differences between
    a placed order response and a get_or der response which is an update on an already placed orders.py
    for more see the update from
    """

    # parse the placed order response
    order_info_dict = make_ccxt_order_info_dict(response=placed_order_res)
    order_id = placed_order_res["id"]
    symbol = placed_order_res["symbol"]

    # add the new order to the dictionary tracking open orders
    state_dict["order_open_dict"][(order_id, symbol)] = order_info_dict

    # ### write the order to the live files
    #
    open_order_fp = get_data_file_path(
        data_type="open_orders",
        pair="None",
        date="live",
        port=params["port"]["port_name"],
        exchange=params["port"]["exchange"],
        params=params,
    )

    new_live_order_line = make_order_observation_csv_line(order_info_dict)

    check_if_dir_exists_and_make(fp=open_order_fp)
    with open(open_order_fp, "a") as f:
        f.write(new_live_order_line)
    os.chmod(open_order_fp, 0o777)  # '0o777' needed for when running on systemd  # ###PAUL


def place_order(ccxt_client, B_or_S, pair, o_type, base_qty, price, state_dict, params):
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

    if pair not in params["port"]["pairs_traded"]:  # ###PAUL  not sure what I wanted to be doing here
        raise KeyError

    # ### verify constraints met for order... precision_amount and precision_price should be only ones affected
    #
    #
    info = params["pair_info_df"].loc[pair]

    # most important / relevant checks
    base_qty = round_by_step_or_decimal(quantity=base_qty, num_decimal=int(info["precision_amount"]), direction="down")
    price = round_by_step_or_decimal(quantity=price, step_size=info["precision_price"])

    # exchange rules
    if base_qty < info["limits_amount_min"] or base_qty > info["limits_amount_max"]:
        print("base_qty: " + str(base_qty) + 3 * ("\n LIMIT_HIT LIMIT_HIT LIMIT_HIT"))
        raise ValueError

    if price < info["limits_price_min"] or price > info["limits_price_max"]:
        print("price: " + str(price) + 3 * ("\n P_LIMIT_HIT P_LIMIT_HIT P_LIMIT_HIT"))
        raise ValueError

    # ###PAUL would like to get rid of the below and raise a ValueError also
    # notional requirements (makes sure that the order is large enough in terms of quote asset)
    if price * base_qty < info["limits_cost_min"]:
        print("    Price: " + str(price) + "\n")
        print("    base_qty: " + str(base_qty) + "\n")
        print("    info['limits_cost_min']: " + str(info["limits_cost_min"]) + "\n")

        return "order not placed MIN_NOTIONAL issue "

    # ### place order
    #
    #
    # string used to place order on pair on the exchange
    symbol = info["id"]  # formerly 'exchange_symbol'... now labled id because CCXT unified structure

    if o_type.lower() == "limit":
        print("placing order")
        print("Limit Order:  " + B_or_S + " " + str(base_qty) + " " + symbol + " for $" + str(price))

        order_res = ccxt_client.create_limit_order(symbol=symbol, side=B_or_S, amount=base_qty, price=price)

    else:
        print("Error: order type not supported")
        raise TypeError

    process_placed_order(order_res, state_dict, params)

    return order_res


def write_closed_order(pair, response, params):
    """writes order that has closed to a file of orders for that pair"""

    # response = ccxt_client.fetch_order(id=order_id, symbol=pair)
    order_info_dict = make_ccxt_order_info_dict(response)

    # TODO: ###PAUL_TODO: would be good to add USD_denomination to this info
    header = (
        "orderId,ticker,clientOrderId,placedTime,price,origQty,executedQty,cummulativeQuoteQty,side,status,ord_type,updateTime\n"
    )
    new_line = make_order_observation_csv_line(order_info_dict)

    daily_trade_fp = get_data_file_path(
        "closed_order", pair, date="live", port=params["port"]["port_name"], exchange=params["port"]["exchange"]
    )

    # check that the file exists for the correct time period
    file_existed = check_if_dir_exists_and_make(fp=daily_trade_fp)

    with open(daily_trade_fp, "a") as f:
        if file_existed == False:  # then new file, write header
            f.write(header)
        f.write(new_line)
    os.chmod(daily_trade_fp, 0o777)

    return None


def remove_order_from_open_tracking(tuple_key, response, state_dict, params):
    """serves 3 primary purposes:  1.) removes order from ./data/orders/open/open_orders.csv
    2.) writes the order to the pair's / day's closed order file
    3.) removes order from global tracking dictionary
    """

    order_id, universal_symbol = tuple_key

    # ### remove order from open order tracking file
    #
    open_order_fp = get_data_file_path(
        data_type="open_orders", pair=None, date="live", port=params["port"]["port_name"], exchange=params["port"]["exchange"]
    )

    try:
        with open(open_order_fp, "r") as f:
            lines = f.readlines()
    except:
        print(f" - in remove order exception ")
        import pdb

        pdb.set_trace()

    # rewrite file without the order_id in it
    with open(open_order_fp, "w") as f:
        for line in lines:
            if str(order_id) not in line[:15]:
                f.write(line)

    # ### write to closed order files
    write_closed_order(universal_symbol, response, params=params)

    # ### remove order from dictionary... must do last, info here used to write to closed order file
    #
    del state_dict["order_open_dict"][(order_id, universal_symbol)]

    return None


def close_order(ccxt_client, order_id, pair, state_dict, params):
    exchange_symbol = convert_symbol(pair, in_exchange="universal", out_exchange=params["port"]["exchange"])

    tuple_key = (order_id, pair)

    # cancel the order
    try:  # ###PAUL would like to handle closed orders with out a try except if possible. test out what the response is
        order_res = ccxt_client.cancel_order(id=order_id, symbol=exchange_symbol)
        remove_order_from_open_tracking(tuple_key, order_res, state_dict, params=params)

        print("closed order: ")
        print(order_res)

    except Exception as e:  # for now if this errors then check_for_closed_orders should handle it
        print("order cancel attempted, it seems order was filled: ")
        print("    symbol: " + exchange_symbol + "  orderId: " + str(order_id) + "/n /n /n")
        print(e)
        print("/n /n /n ")

    return None


def close_orders_for_assets_in_port_if_not_tracked(ccxt_client, state_dict, params):
    """checks orders on the ccxt_clients exchange and if any orders are open for pairs containing assets controlled
    by this bot this function will close the orders if they are not already tracked by the state dictionary
    """

    # can only get all open orders by setting this to False, otherwise fetch open will error
    ccxt_client.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
    all_opens = ccxt_client.fetch_open_orders()

    for open_order in all_opens:
        pair = open_order["symbol"].replace("/", "-")
        base_asset, quote_asset = pair.split("-")
        # delete this order unless we are already tracking it
        if base_asset in params["port"]["assets_in_port"] or quote_asset in params["port"]["assets_in_port"]:
            order_key = (open_order["id"], f"{base_asset}-{quote_asset}")
            if order_key in state_dict["order_open_dict"]:
                continue  # the order is already tracked, keep it and let down stream logic handle it
            else:
                print(
                    f"closing order on bot start for "
                    f"             close_order(ccxt_client, order_id={open_order['id']}, pair={pair}, state_dict, params)"
                )
                close_order(ccxt_client, open_order["id"], pair, state_dict, params)

    ccxt_client.options["warnOnFetchOpenOrdersWithoutSymbol"] = True

    return None


def get_open_orders(pair, state_dict):
    """goes over all the open orders for the set of API keys and if the new order
    # TODO: maintain two versions of `state_dict['order_open_dict']`
        * `state_dict['orders_open_by_ticker']`
        * `state_Dict['orders_open_by_exchange']`
        * would essentially make this kindof function unnecessary (need to maintain both of them which is ez)
    # TODO: this wouldn't affect startup order logic of `live_framework.py`
    """

    open_keys = []

    # ###PAUL_refractor... this could (should?) be built more DRY
    #
    # for order in open_orders check...
    for key in state_dict["order_open_dict"].keys():
        order_id, order_pair = key

        # if there is an open order
        if pair == order_pair:
            print("already an order open for pair  --->  " + pair)
            open_keys.append(key)

    orders_open = [state_dict["order_open_dict"][key] for key in open_keys]

    return orders_open


def update_last_time_checked(trading_summaries, signal_dfs_dict, state_dict, params):
    """updates the 'last_time_checked' per pair... multi ticker supported TODO: but multi exchange"""

    for pair in params["port"]["pairs_traded"]:
        if signal_dfs_dict:  # if we are using a signal based strategy this will not be empty and do the following
            if trading_summaries[pair].shape[0] == 0 or signal_dfs_dict[pair].shape[0] == 0:
                continue  # because nothing now could have been seen, we are stick at the same time.
            trading_summary_time = trading_summaries[pair].index[-1]
            signal_time = signal_dfs_dict[pair].index[-1]
            state_dict["last_time_checked"][pair] = min(trading_summary_time, signal_time)

        else:  # we are just concerned with 
            state_dict["last_time_checked"][pair] = trading_summaries[pair].index[-1]

    return None


def figure_price_qty_for_order(pair, diff, position, state_dict, params):
    """DEPRICATED, REPLACED BY `handle_ordering_after_state_update()` REMOVE AFTER CONSIDERING IMPLICATIONS"""
    # info needed whether buying or selling
    last_price_t = state_dict["last_prices_by_pair_in_quote"][pair]
    mid_vwap = last_price_t
    mid_ewm = last_price_t

    # BUYING
    if diff >= params["port"]["diff_thresh"]:
        if params["port"]["exchange"] == "binanceus":
            current_dollar_holdings = state_dict["port_holdings_dict"]["USD"]["total"]
            # TODO: ###PAUL_TODO: MULTIASSET Trading
            # TODO: the problem with using total USD with multiple orders is that we could want to
        else:
            # ###PAUL_usd_denomination TODO: want to use the pair's quote asset... any consideration for USD? in here?
            current_dollar_holdings = state_dict["port_holdings_dict"]["TUSD"]["total"]

        buy_dollars = min(diff, current_dollar_holdings)

        if position in ["long", "neutral"]:  # buy
            B_or_S = "buy"
            price = min(mid_vwap, mid_ewm)  # want to buy for cheaper since not high priority
            qty = buy_dollars / price * 0.99
        else:
            print(f"diff indicates a buy but position given was: {position}")
            raise ValueError

    # SELLING
    if diff <= -params["port"]["diff_thresh"]:
        baseAsset = params["pair_info_df"].loc[pair]["base"]
        baseAsset_holdings = state_dict["port_holdings_dict"][baseAsset]["free"]

        sell_dollars = min(-diff, min(mid_vwap, mid_ewm) * baseAsset_holdings)

        if position in ["short", "neutral"]:  # sell
            B_or_S = "sell"
            price = max(mid_vwap, mid_ewm)  # max cause want the highest price on non-urgent sell
            qty = 0.9999 * (sell_dollars / price)
        else:
            print(f"diff indicates a sell but position given was: {position}")
            raise ValueError

    return price, qty, B_or_S


def check_for_orders_and_close_unrelated(ccxt_client, state_dict, params):
    """checks all orders open on exchange (for the account's ccxt_client) and closes any outside of pairs_traded

    NOTE: this isnt used yet, it is the old version of check_for_closed_orders, but fetch_markets has an api limit
    on binance so this will be added back in as mentioned
    # ###PAUL_todo get this into the rotation with a twisted reactor task (every 5 minutes...)
    def cant use now that sharing an account
    """

    # get open orders from exchange
    ccxt_client.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
    open_orders_res_list = ccxt_client.fetch_open_orders()
    ccxt_client.options["warnOnFetchOpenOrdersWithoutSymbol"] = True

    order_res = "needed now for remove order from tracking, handle when this function goes live "

    # put list of keys: tuples (order_id, universal_symbol) from exchange collected
    open_orders_on_exchange = []
    for res in open_orders_res_list:
        exchange_symbol = res["symbol"].replace("/", "-")
        universal_symbol = convert_symbol(exchange_symbol, in_exchange=params["port"]["exchange"], out_exchange="universal")

        order_id = res["id"]
        tup = (order_id, universal_symbol)

        open_orders_on_exchange.append(tup)

    # loop through the open_order_dict, remove entry if the order is not in the orders on the exchange
    keys_to_delete = []
    for key in state_dict["order_open_dict"]:
        if key not in open_orders_on_exchange:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        remove_order_from_open_tracking(key, order_res, state_dict, params=params)

    return None


def check_for_closed_orders(ccxt_client, state_dict, params):
    """checks if any of the open orders being tracked are now closed and removes them from tracking
    TODO: need to add order fills to tracking consider ./data/orders/filled/  (filled being a new dir)
    """

    # ###PAUL_dev notes
    #
    # ###
    # |    status    |  kucoin   |   binance(us)  |  ### ccxt converts varying format status to open or closed...
    # |     open     |  'open'   |   'open'       |  ### where as binance uses FILLED, PARTIALLY_FILLED, etc...
    # |    closed    | 'closed'  |   'closed'     |  ### kucoin uses isActive: [True, False]
    temp_open_order_dict = deepcopy(state_dict["order_open_dict"])

    for key, value in temp_open_order_dict.items():
        order_id, universal_symbol = key
        exchange_symbol = convert_symbol(universal_symbol, in_exchange="universal", out_exchange=params["port"]["exchange"])
        order_res = ccxt_client.fetch_order(id=order_id, symbol=exchange_symbol)

        if order_res["status"] == "closed":
            remove_order_from_open_tracking(key, order_res, state_dict, params=params)


def print_update_on_bot(state_dict, signal_dfs_dict, params):  # utility that only uses state dict so it goes here...
    # TODO: needs a decent amount of updating for multi asset

    print(
        f" - ALGOS - LIVE BOT - portfolio iter: {state_dict['iter_count']}"
        f" ---- port: ' {params['port']['port_name']} ---- exchange: {params['port']['exchange']}\n"
    )

    print(f"    - last_prices_by_pair_in_quote ---- {state_dict['last_prices_by_pair_in_quote']}")
    print(f"    - last_prices_by_symbol_in_usd ---- {state_dict['last_prices_by_symbol_in_usd']}\n")

    if params['port']['decision_params']:  # if the dict here isn't empty, print the following 
        print(
            f"    - decision params \n"
            f"        - long / short \n"
            f"            - threshold: {params['port']['decision_params']['threshold']}"
            f"  ----  pred_dist: {params['port']['decision_params']['pred_dist']} \n"
            f"            - price_dist: {params['port']['decision_params']['price_dist']}"
            f"  ----  stop_limit: {params['port']['decision_params']['stop_limit']} \n"
            f"        - exit long / short \n"
            f"            - threshold: {params['port']['decision_params']['to_neutral_threshold']}"
            f"  ----  pred_dist: {params['port']['decision_params']['to_neutral_pred_dist']} \n"
            f"            - price_dist: {params['port']['decision_params']['to_neutral_price_dist']}"
            f"  ----  pred_dist: {params['port']['decision_params']['to_neutral_stop_limit']}\n\n\n\n\n"
        )


    if signal_dfs_dict:  # if dictionary isn't empty print these out 
        try:
            signal_value = signal_dfs_dict["BTC-TUSD"].iloc[-1]["value"]
        except:
            signal_value = "signal empty this iteration"

        print(f"    - current signal value --> {signal_value}")
        print(
            f"    - bearish: \n"
            f"        - signal \n"
            f"            - lowest: {state_dict['bearish']['lowest_pred'][0]}\n"
            f"            - highest: {state_dict['bearish']['highest_pred'][0]}\n"
            f"        - price\n"
            f"            - lowest: {state_dict['bearish']['lowest_price']}\n"
            f"            - highest: {state_dict['bearish']['highest_price']}\n"
            f"        - activations\n"
            f"            - exit_long: -- pred_dist: {state_dict['bearish']['activations']['exit_long']['pred_dist']} -- "
            f"price_dist:  {state_dict['bearish']['activations']['exit_long']['price_dist']} -- "
            f"stop_limit:  {state_dict['bearish']['activations']['exit_long']['stop_limit']} -- "
            f"threshold:  {state_dict['bearish']['activations']['exit_long']['threshold']}\n"
            f"            - short:     -- pred_dist: {state_dict['bearish']['activations']['short']['pred_dist']} -- "
            f"price_dist:  {state_dict['bearish']['activations']['short']['price_dist']} -- "
            f"stop_limit:  {state_dict['bearish']['activations']['short']['stop_limit']} -- "
            f"threshold:  {state_dict['bearish']['activations']['short']['threshold']} \n"
            f"    - bullish: \n"
            f"        - signal\n"
            f"            - lowest: {state_dict['bullish']['lowest_pred'][0]}\n"
            f"            - highest: {state_dict['bullish']['highest_pred'][0]}\n"
            f"        - price\n"
            f"            - lowest: {state_dict['bullish']['lowest_price']}\n"
            f"            - highest: {state_dict['bullish']['highest_price']}\n"
            f"        - activations\n"
            f"            - exit_short: -- pred_dist: {state_dict['bullish']['activations']['exit_short']['pred_dist']} -- "
            f"price_dist:  {state_dict['bullish']['activations']['exit_short']['price_dist']} -- "
            f"stop_limit:  {state_dict['bullish']['activations']['exit_short']['stop_limit']} -- "
            f"threshold:  {state_dict['bullish']['activations']['exit_short']['threshold']}\n"
            f"            - long:       -- pred_dist: {state_dict['bullish']['activations']['long']['pred_dist']} -- "
            f"price_dist:  {state_dict['bullish']['activations']['long']['price_dist']} -- "
            f"stop_limit:  {state_dict['bullish']['activations']['long']['stop_limit']} -- "
            f"threshold:  {state_dict['bullish']['activations']['long']['threshold']} \n\n\n\n"
        )

    for bag_type in ["bag_max", "bag_actual", "bag_desired"]:
        print(f"    - {bag_type}")
        for key, value in state_dict[bag_type].items():
            print(f"        - {key}:  {value}")

    if params["port"]["inventory_method"] == "LS_replication":
        print(f"    - mock portfolio")
        print(
            f"        - BTC: {state_dict['LS']['BTC-TUSD']['mocked_port_BTC_target_current']} -- "
            f"TUSD: {state_dict['LS']['BTC-TUSD']['mocked_port_TUSD_target_current']} -- "
            f"total_value: {state_dict['LS']['BTC-TUSD']['mocked_port_value_before_trade']} \n\n\n"
        )

    print(f"\n")


def handle_ordering_after_state_update(ccxt_client, trading_summaries, state_dict, params):
    """for each pair, considers updated state of portfolio and signal, creats an order or  closes and opens new orders"""

    for pair in params["port"]["pairs_traded"]:
        base = params['pair_info_df'].loc[pair]['base']
        quote = params['pair_info_df'].loc[pair]['quote']
        
        actual_base_in_quote_value = state_dict["bag_actual"][pair]["base_in_usd"]
        desired_base_in_quote_value = state_dict["bag_desired"][pair]["base_in_usd"]
        diff = desired_base_in_quote_value - actual_base_in_quote_value

        if diff >= params["port"]["diff_thresh"]:
            B_or_S = "buy"
        elif diff <= -params["port"]["diff_thresh"]:
            B_or_S = "sell"
        else:  # WE HAVE -->  -params["port"]["diff_thresh"] < diff < params["port"]["diff_thresh"]
            continue  # to next interation of the loop because order quantity is too small 

        print("order_stage_1 ---- pair: " + str(pair))
        print("order_stage_1 ---- diff: " + str(diff))

        ###PAUL TODO: consider orderbook for prices, currently using most recent buy / sell vwap #
        #       TODO: that works fine for BTC but not well for less liquid tickers (especially with fees)
        open_orders = get_open_orders(pair=pair, state_dict=state_dict)

        # for this strategy we should only have one order open for a pair at a time for the full value of diff
        num_open = len(open_orders)
        if num_open == 0:
            order_price = trading_summaries[pair]["vwap"].iloc[-1]
        elif num_open == 1:
            # do the check if the new order is a higher priority
            order = open_orders[0]
            open_order_price = order["price"]
            if B_or_S == "buy":
                new_price = trading_summaries[pair]["buy_vwap"].iloc[-1]
                if new_price > open_order_price:
                    order_price = new_price
                else:
                    order_price = None
            elif B_or_S == "sell":
                new_price = trading_summaries[pair]["sell_vwap"].iloc[-1]
                if new_price < open_order_price:
                    order_price = new_price
                else:
                    order_price = None
            if order_price is not None:
                close_order(ccxt_client, order["id"], order["symbol"], state_dict, params)

        else:  # too many orders
            print(f"warning we more orders than we should \n    - num_open = {num_open}")
            for order in open_orders:
                close_order(ccxt_client, order["id"], order["symbol"], state_dict, params)
            order_price = trading_summaries[pair]["vwap"].iloc[-1]

        if order_price is not None:  # we are ordering
            qty = math.fabs(state_dict["bag_desired"][pair]["base"] - state_dict["bag_actual"][pair]["base"])

            # ### the is an interesting paradigm with `bag_actual` where the value is assigned to it based on the total port value 
            #     if one pair goes over this value, the actual quote will be negative. This should should remain, the behavior 
            #     is desirable, however the name of "actual" maybe misleading, and should be reconsidered. 
            if B_or_S == "buy":
                max_by_pair = state_dict["bag_actual"][pair]["quote"] / state_dict["last_prices_by_pair_in_quote"][pair]
                max_by_holdings = state_dict["port_holdings_dict"][quote]["free"] 
                max_orderable_qty = min(max_by_pair, max_by_holdings)
                
            if B_or_S == "sell":
                max_by_pair = state_dict["bag_actual"][pair]["base"]
                max_by_holdings = state_dict["port_holdings_dict"][base]["free"] 
                max_orderable_qty = min(max_by_pair, max_by_holdings)

            if max_orderable_qty * state_dict["last_prices_by_symbol_in_usd"][base] < 11: 
                continue   # if biggest order less than $11 don't order...  $10 is usually minimum order

            qty = min(qty, 0.999 * max_orderable_qty)
            print(f"order_stage_3 ---- price:  {order_price}")
            print(f"order_stage_3 ---- qty:    {qty}")
            print(f"order_stage_3 ---- total_order_value: ' + str(total_order_value)")
            print(
                f"order_stage_3 ---- PLACING LIMIT ORDER ---- {B_or_S}  -  {qty}  -  {pair}  ${order_price} "
                f"---- in port_name: {params['port']['port_name']}"
            )

            try:
                order_res = place_order(
                    ccxt_client=ccxt_client,
                    B_or_S=B_or_S,
                    pair=pair,
                    o_type="limit",
                    base_qty=qty,
                    price=order_price,
                    state_dict=state_dict,
                    params=params,
                )
                process_placed_order(order_res, state_dict, params=params)
            except InsufficientFunds:
                print(f"order_post_attempt ---- attempted to place order with insufficient funds")

            # we only update our holdings / bags dict once per round of orders, to avoid trying to order with the quote asset we don't
            # have, we will update the quote asset holdings after the order is placed, selling something will cause fewer problems
                # which for now I am willing to let the try except catch above. 
            if B_or_S == "buy": 
                state_dict["port_holdings_dict"][quote]["free"] -= qty

def print_signal_update(state_dict, params):
    print(
        f"for signal update iter #: {state_dict['num_total_signal_updates']} ---- and "
        f" for process id update iter #: \n"
        f"---- updates {params['signal']['signal_make_delay']} second after the start of every minute \n "
        f"---- num_rows_added_since_printout: {state_dict['num_rows_added_since_printout']} "
    )


def reassess_bags_and_orders(ccxt_client, ch_client, trading_summaries, signal_dfs_dict, state_dict, params):
    """ 
    """

    check_for_closed_orders(ccxt_client, state_dict, params=params)  # quick enough to do at the beginning too

    update_trading_summaries(trading_summaries, state_dict, params=params, ch_client=ch_client)
    
    if params["port"]["signal_name"] != None:  # ###PAUL TODO: consider cleaning up handling of signal_dfs_dict when not used
        update_signals(signal_dfs_dict, state_dict, params=params)
    
    update_desired_positions_dict(trading_summaries, signal_dfs_dict, state_dict, params)
    update_port_holdings_and_value(ccxt_client, ch_client, state_dict, trading_summaries, params)
    handle_ordering_after_state_update(ccxt_client, trading_summaries, state_dict, params)

    time.sleep(0.1)  # gives small time for highly likely orders to fill before checking
    check_for_closed_orders(ccxt_client, state_dict, params=params)

    # only update the portfolios most recent update time if this function runs to fruition
    update_last_time_checked(trading_summaries, signal_dfs_dict, state_dict, params=params)
    cache_state_dict(state_dict, params=params)

    if state_dict["iter_count"] % params["port"]["print_alert_n_iters"] == 0:
        print_update_on_bot(state_dict, signal_dfs_dict, params=params)
    state_dict["iter_count"] += 1

    return None


if __name__ == "__main__":
    print(params.keys())
