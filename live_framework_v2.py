import sys
sys.path.insert(0, "..")

# standard imports
import ccxt
from clickhouse_driver import Client
from clickhouse_driver.errors import SocketTimeoutError
from clickhouse_driver.errors import Error as ClickHouseError  # base class used to catch all ClickHouse exceptions

from copy import deepcopy
import datetime
from datetime import timedelta
import pandas as pd
import sys
import time


# ### local imports
# ##
# #
from algos.config import params
from algos.decision import make_requests_dict
from algos.utils import init_ch_client, init_ccxt_client
from algos.bot_utils import (
    directory_check_for_portfolio_data,
    make_pair_info_df,
    initialize_bag_dicts,
    initialize_port_allocation_dict,
    initialize_positions_dict,
    initalize_last_time_checked,
    reassess_bags_and_orders,
    load_cached_state_dict,
    get_set_of_assets_in_port,
    get_primary_pricing_pair_per_asset,
    close_orders_for_assets_in_port_if_not_tracked,
)


def main():
    port_running = sys.argv[1]
    # bring the portfolio's parameters "foward" for easier referencing ---- script only utilizes `params['port']`
    params["port"] = deepcopy(params["active_services"]["ports"][port_running])
        
    if params["port"]["signal_name"] != None: 
        params["port"]["decision_params"] = make_requests_dict(params["port"]["decision_params"])

    ch_client = init_ch_client()
    ccxt_client = init_ccxt_client(exchange=params["port"]["exchange"],
                                   type="standard",
                                   api_key_names=params["port"]["api_key_names"])

    # setup for running portfolio by filling params and a directory check for portfolio tracking
    make_pair_info_df(ccxt_client=ccxt_client, state_dict=None, params=params)
    get_set_of_assets_in_port(params)
    get_primary_pricing_pair_per_asset(params)
    directory_check_for_portfolio_data(params=params)

    try:
        state_dict = load_cached_state_dict(params)
    except FileNotFoundError:
        # if first time running portfolio, it will initalize one. 
        state_dict = {}
        state_dict["order_open_dict"] = {}
        state_dict["iter_count"] = 0  # should come from state dict in the case that the portfolio is restarting
        state_dict["desired_position"] = {}  # ticker: [short, neutral_
        initialize_bag_dicts(state_dict=state_dict, params=params)
        initialize_port_allocation_dict(state_dict=state_dict, params=params)
        initialize_positions_dict(state_dict=state_dict, params=params)
        initalize_last_time_checked(state_dict=state_dict, params=params)

    close_orders_for_assets_in_port_if_not_tracked(ccxt_client, state_dict, params)

    # ### live info used in decision algorithm
    #
    trading_summaries = dict()
    signal_dfs_dict = dict()

    # functionality to be wrapped for db updates / trading
    now = pd.to_datetime(datetime.datetime.now())
    next_time_to_check = (now.floor("min") + timedelta(seconds=params["port"]["decision_delay"])).to_pydatetime()

    num_updates = -1
    while True:
        now = pd.to_datetime(datetime.datetime.now())
        if now > next_time_to_check:

            # try:
            num_updates += 1

            print(f"\n\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
            print(f" - running iter {num_updates} of reassessing bags on this PID ")

            reassess_bags_and_orders(
                ccxt_client=ccxt_client,
                ch_client=ch_client,
                trading_summaries=trading_summaries,
                signal_dfs_dict=signal_dfs_dict,
                state_dict=state_dict,
                params=params,
            )

            next_time_to_check = (
                now.floor("min") + timedelta(minutes=1) + timedelta(seconds=params["port"]["decision_delay"])
            ).to_pydatetime()
            # except SocketTimeoutError:
            #     print("Caught a ClickHouse socket timeout error. Skipping to next iteration.")
            #     continue  # This will skip the current iteration and move on to the next

            # except ClickHouseError:
            #     print("Caught a general ClickHouse error. Skipping to next iteration.")
            #     continue  # This will skip the current iteration and move on to the next

            # except Exception as e:
            #     print(f"Caught a non-ClickHouse error: \n\n {e}")
            #     raise RuntimeError

        time.sleep(1)


if __name__ == "__main__":
    main()
