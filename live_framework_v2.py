import os
import time

os.environ['TZ'] = 'UTC'
time.tzset()

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


# local imports
#
#
sys.path.insert(0, '..')
sys.path.insert(0, '../..')  # for hoth

from algos.bot_utils import (directory_check_for_portfolio_data,
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

from algos.config import params
from algos.decision import make_requests_dict
from algos.utils import get_secret


port_running = sys.argv[1]  # ###PAUL possibly causing errors in notebook import... uncomment later

# ### FILLING `params` ---- keep all operations on params together incase going to notebook is desired
#
#
# bring the portfolio's parameters "foward" for easier referencing ---- script only utilizes `params['port']`
params['port'] = deepcopy(params['active_services']['ports'][port_running])

ch_client = Client('10.0.1.86', port='9009')

#  TODO: dict of `ccxt_clients` for multi exchange stuff
if params['port']['exchange'] == 'binance':
    ccxt_client = ccxt.binance({'apiKey': get_secret("BINANCE_API_KEY_1"),
                                'secret': get_secret("BINANCE_SECRET_KEY_1")})
elif params['port']['exchange'] == 'kucoin':
    ccxt_client = ccxt.kucoin({'apiKey': get_secret("KUCOIN_API_KEY_1"),
                               'secret': get_secret("KUCOIN_SECRET_KEY_1"),
                               'password': get_secret("KUCOIN_PASSPHRASE_1"), })
else:
    print('exchange not supported')
    raise ValueError

params['port']['requests_dict'] = make_requests_dict(params['port']['decision_params'])
make_pair_info_df(ccxt_client=ccxt_client, state_dict=None, params=params)
get_set_of_assets_in_port(params)
get_primary_pricing_pair_per_asset(params)
directory_check_for_portfolio_data(params=params)

try:
    # DESIRED:   /opt/shared/crypto/algos/data/live/ports/prod_1____BTC_USDT_trades_only_data/state_dict.pickle'
    state_dict = load_cached_state_dict(params)
except FileNotFoundError:  # SHOULD ALWAYS BE THE FIRST TIME THE PORTFOLIO IS BEING RAN IN THIS CASE
    state_dict = {}
    state_dict['order_open_dict']  = {}
    state_dict['iter_count'] = 0  # should come from state dict in the case that the portfolio is restarting
    state_dict['desired_position'] = {}  # ticker: [short, neutral_
    initialize_bag_dicts(state_dict=state_dict, params=params)
    initialize_port_allocation_dict(state_dict=state_dict, params=params)
    initialize_positions_dict(state_dict=state_dict, params=params)
    initalize_last_time_checked(state_dict=state_dict, params=params)


close_orders_for_assets_in_port_if_not_tracked(ccxt_client, state_dict, params)

# ### live info used in decision algorithm
#
trading_summaries = dict()
signal_dfs_dict = dict()
print(f" - populated `trading_summaries`, `signal_dfs_dict`, `state_dict`, & `params` \n"
      f"     - ran one iteration of updates on them with no order placement")

# functionality to be wrapped for db updates / trading
now = pd.to_datetime(datetime.datetime.now())
next_time_to_check = (now.floor('min') + timedelta(seconds=params['port']['decision_delay'])).to_pydatetime()

num_updates = -1
while True:
    now = pd.to_datetime(datetime.datetime.now())
    if now > next_time_to_check:

        try:
            num_updates += 1

            print(f"\n\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
            print(f" - running iter {num_updates} of reassessing bags on this PID ")

            reassess_bags_and_orders(ccxt_client=ccxt_client,
                                     ch_client=ch_client,
                                     trading_summaries=trading_summaries,
                                     signal_dfs_dict=signal_dfs_dict,
                                     state_dict=state_dict,
                                     params=params)

            next_time_to_check = (now.floor('min')
                                  + timedelta(minutes=1)
                                  + timedelta(seconds=params['port']['decision_delay'])
                                  ).to_pydatetime()
        except SocketTimeoutError:
            print("Caught a ClickHouse socket timeout error. Skipping to next iteration.")
            continue  # This will skip the current iteration and move on to the next

        except ClickHouseError:
            print("Caught a general ClickHouse error. Skipping to next iteration.")
            continue  # This will skip the current iteration and move on to the next

        except Exception as e:
            print(f"Caught a non-ClickHouse error: \n\n {e}")
            raise RuntimeError

    time.sleep(1)
