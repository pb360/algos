import sys
sys.path.insert(0, '..')  # for local imports from the top directory

from algos.config import params
from algos.gridsearch import make_list_of_combo_dicts, decision_multiprocess
from algos.utils import (query_trading_summary,
                         fill_trading_summary,)
from clickhouse_driver import Client
from copy import deepcopy
import numpy as np
# import pandas as pd
import os
import pickle
import random

data_dir = params['dirs']
#
ch_client = Client('10.0.1.86', port='9009')

n_gridsearch_options = 10_000  # ###PAUL TODO: get this into a gridsearch params

gs_file = f"grid_search____2023_09_06____on____signal_dict____2023_09_01___mlp_rolling_smaller_model____any_two_set"
gs_fp = f"{data_dir}gridsearches/{gs_file}.pickle"
if os.path.isfile(gs_fp):
    print(f"gs_df already exists at that filepath")
    raise FileExistsError

print(f"reading data")

# get trading summary and vwap

trading_summary = query_trading_summary(exchange='binance', symbol='BTC-TUSD', start_date=(2011, 1, 1), end_date=None, ch_client=ch_client)
trading_summary = fill_trading_summary(trading_summary)
vwap = deepcopy(trading_summary['vwap'])

# read signal
signal_dict_name = f"signal_dict____2023_09_01___mlp_rolling_smaller_model"
signal_dict_fp = f"{data_dir}pickled_signal_dicts/{signal_dict_name}.pickle"
with open(signal_dict_fp, 'rb') as f:
    signal_dict = pickle.load(f)  # <<<------- COPY PASTE DESIRED VARIABLE HERE

print(f"done reading data")

# ### GRIDSEARCH SETUP
#A
gs_n = 10

threshold = 0.5
pred_dist = 0.4
price_dist = 0.015
stop_limit = 0.025
# deltas
delta_threshold = 1.75
delta_pred_dist = 0.35
delta_price_dist = 0.0125
delta_stop_limit = 0.0125

exit_threshold = 0.25
exit_pred_dist = 0.4
exit_price_dist = 0.01
exit_stop_limit = 0.0125
# deltas
delta_exit_threshold = 1.75
delta_exit_pred_dist = 0.35
delta_exit_price_dist = 0.0085
delta_exit_stop_limit = 0.0085

threshold_min = threshold - delta_threshold  # max(0, threshold - delta_threshold)
pred_dist_min = max(0, pred_dist - delta_pred_dist)
price_dist_min = max(0, price_dist - delta_price_dist)
stop_limit_min = max(0, stop_limit - delta_stop_limit)
exit_threshold_min = exit_threshold - delta_exit_threshold  # max(0, exit_threshold - delta_exit_threshold)  # maybe should try letting this go negative
# exit_threshold_min = max(0, exit_threshold - delta_exit_threshold)  # maybe should try letting this go negative
exit_pred_dist_min = max(0, exit_pred_dist - delta_exit_pred_dist)
exit_price_dist_min = max(0, exit_price_dist - delta_exit_price_dist)
exit_stop_limit_min = max(0, exit_stop_limit - delta_exit_stop_limit)

threshold_max = threshold + delta_threshold
pred_dist_max = pred_dist + delta_pred_dist
price_dist_max = price_dist + delta_price_dist
stop_limit_max = stop_limit + delta_stop_limit
exit_threshold_max = exit_threshold + delta_exit_threshold
exit_pred_dist_max = exit_pred_dist + delta_exit_pred_dist
exit_price_dist_max = exit_price_dist + delta_exit_price_dist
exit_stop_limit_max = exit_stop_limit + delta_exit_stop_limit

decision_dict = \
    {
        'fee': [0.01],  # FEE IN PERCENT.
        # 'preds_out_ewm': [0.45, 0.575],  # ###PAUL this goes to model
        'max_workers': [70],
        'cool_down': [15],

        'threshold': list(np.linspace(start=threshold_min, stop=threshold_max, num=gs_n+1)),
        'pred_dist': list(np.linspace(start=pred_dist_min, stop=pred_dist_max, num=gs_n+1)),
        'price_dist': list(np.linspace(start=price_dist_min, stop=price_dist_max, num=gs_n-2)),
        # 'stop_limit': list(np.linspace(start=stop_limit_min, stop=stop_limit_max, num=gs_n - 1)),
        'stop_limit': list(np.linspace(start=stop_limit_min, stop=stop_limit_max, num=gs_n-2)),
        # 'stop_limit': [0.0088, 0.01, 0.015, ],
        'overrides': [['stop_limit'], ],
        # 'any_two': [[]],
        # 'any_two': [[], ['threshold', 'pred_dist', 'price_dist']],   # TODO: this should work and isn't...
        'any_two': [['threshold', 'pred_dist', 'price_dist']],

        'to_neutral_threshold': list(np.linspace(start=exit_threshold_min, stop=exit_threshold_max, num=gs_n+1)),
        'to_neutral_pred_dist': list(np.linspace(start=exit_pred_dist_min, stop=exit_pred_dist_max, num=gs_n+1)),
        'to_neutral_price_dist': list(np.linspace(start=exit_price_dist_min, stop=exit_price_dist_max, num=gs_n-2)),
        'to_neutral_stop_limit': list(np.linspace(start=exit_stop_limit_min, stop=exit_stop_limit_max, num=gs_n-3)),
        # 'to_neutral_stop_limit': [0.005, 0.009, 0.0125, ],
        'to_neutral_overrides': [['stop_limit'], ],
        # 'to_neutral_any_two': [[]],
        # 'to_neutral_any_two': [[], ['threshold', 'pred_dist', 'price_dist'], ],  # TODO: this should work and isn't...
        'to_neutral_any_two': [['threshold', 'pred_dist', 'price_dist'] ],
    }

target_params_nn_temp = {'skip': 'skip'}
model_params_nn_temp = {'skip': 'skip'}
decision_combos = make_list_of_combo_dicts(decision_dict)
print(f"initial length of decision_combos: {len(decision_combos)}")
decision_combos = random.choices(decision_combos, k=n_gridsearch_options)
print(f"after length of decision_combos: {len(decision_combos)}")

print(f"starting grid search")


gs_df = decision_multiprocess(decision_combos=decision_combos,
                              signal_dict=signal_dict,
                              prices=vwap,
                              target_params=target_params_nn_temp,
                              model_params=model_params_nn_temp,
                              max_workers=80,
                              debug=False)

gs_df['ranking_metric'] = gs_df['sharpe'] * gs_df['pnl'] / gs_df['num_transacts']

gs_df.to_pickle(gs_fp)

print(f"\ndone \ngridsearching \n\n")
