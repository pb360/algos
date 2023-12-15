# ### local imports
import sys

sys.path.insert(0, '../')
from algos.bot_utils import (load_cached_state_dict,
                             cache_state_dict,
                             print_signal_update)
from algos.config import params
from algos.model import (generate_signal, )
from algos.utils import (get_signal_id,
                         add_signal_name_to_foreign_key_table,
                         update_signals_table, )

from clickhouse_driver import Client
import datetime
from datetime import timedelta
import pandas as pd
import pickle
import time


data_dir = params['dir']['data_dir']
ch_client = Client('10.0.1.86', port='9009')

# ### signals ---- get the signal and setup around it.
#
#           signal_id  |       signal_name
#          __________________________________________________________________________________________________
#               - 3.)  |  prod_1____BTC_USDT_trades_only_data
#               - 4.)  |  test signal made for pierre off of signal_dict____2023_08_03___mlp_rolling____validate
#               - 5.)  |  signal_dict____2023_08_03___mlp_rolling____validate
signal_name = sys.argv[1]
params['signal_name'] = signal_name
params['signal'] = params['active_services']['signals'][signal_name]
signal_dict_fp = f"{data_dir}pickled_signal_dicts/{signal_name}.pickle"
# # TODO:   vvvvvvvvvvvvvvvvvvvvv  add `signal_dict`s support to `get_data_file_path()`vvvvvvvvvvvvvvvvvvvvv
# signal_dict_fp = get_data_file_path(data_type='signal_dict',
#                                    date='',
#                                    # port=params['port']['port_name'],
#                                    signal=params['signal_name'],
#                                    # exchange=params['port']['exchange'],
#                                    params=params)
# # TODO:  ^^^^^^^^^^^^^^^^^^^^^^^   add `signal_dict`s support to `get_data_file_path()` ^^^^^^^^^^^^^^^^^^^^^^^

with open(signal_dict_fp, 'rb') as f:
    signal_dict = pickle.load(f)
    params['signal_dict'] = signal_dict

# get `signal_id` from database... if not there first time running and need to do some initialization
signal_id = get_signal_id(signal_name)
if signal_id is False:
    signal_id = add_signal_name_to_foreign_key_table(signal_name)
params['signal_id'] = signal_id

try:
    state_dict = load_cached_state_dict(params)
    try:
        params['signal_dict']['feature_params'] = state_dict['feature_params']
    except KeyError:  # ###PAUL TODOO: REMOVE THIS TRY EXCEPT LATER,, JUST MEANT FOR THE FIRST ITER OF CHANGING TIMING LOGIC `
        print(f"had to ")
        state_dict['feature_params'] = params['signal_dict']['feature_params']

except FileNotFoundError:
    # TODO: the start and end dates need to be contained in both the params (because they are initially hard coded
    # TODO: then convered into the state_dict... for now the way we are running it is fine. but eventually this
    # TODO: should move.. not I don't think speed up will be great at all. `params` are simply supposed to remain unchanged.
    state_dict = {}
    state_dict['iter_count'] = 0  # should come from state dict in the case that the portfolio is restarting
    state_dict['num_total_signal_updates'] = 0
    state_dict['last_time_checked'] = 0  # TODO: this could cause issues
    state_dict['now'] = pd.to_datetime(datetime.datetime.now())
    state_dict['num_rows_added_since_printout'] = 0
    state_dict['next_update_time'] = (state_dict['now'].floor('min') \
                                      + timedelta(seconds=params['signal']['signal_make_delay'])).to_pydatetime()

    state_dict['feature_params'] = params['signal_dict']['feature_params']  # ['eaors_trades'][pair]['start_date']

# always reset this number
state_dict['num_update_this_pid'] = 0

# ### LIVE LOOPING
#
while True:

    # only when we are updating a signal
    if state_dict['now'] > state_dict['next_update_time']:
        if state_dict['num_update_this_pid'] % 1 == 0 or state_dict['num_update_this_pid'] < 6:
            print_signal_update(state_dict, params)
            state_dict['num_rows_added_since_printout'] = 0

        # update the signal
        signal = generate_signal(params, ch_client=ch_client)
        num_rows_entered = update_signals_table(signal=signal, signal_id=params['signal_id'], ch_client=ch_client)

        state_dict['feature_params'] = params['signal_dict']['feature_params']
        cache_state_dict(state_dict, params)

        state_dict['num_update_this_pid'] += 1
        state_dict['num_total_signal_updates'] += 1
        state_dict['num_rows_added_since_printout'] += num_rows_entered
        state_dict['next_update_time'] = (state_dict['now'].floor('min')
                                          + timedelta(seconds=params['signal']['mins_between_signal_updates'])
                                          + timedelta(seconds=params['signal']['signal_make_delay'])
                                          ).to_pydatetime()
    time.sleep(1)
