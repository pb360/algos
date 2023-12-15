# ### local imports
import sys
import time

sys.path.insert(0, '..')  # for local imports from the top directory
from algos.config import params 
from algos.targets import split_train_test
from algos.decision import (backtest_decision_making, backtest_decision_making_multiprocess, )

import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import itertools
import numpy as np
import os
import pandas as pd
import pickle
from time import sleep

data_dir = params['dirs']['data_dir']

def make_list_of_combo_dicts(dict_of_gridsearch_lists):
    """
    input:
        dict_of_gridsearch_lists (dict): values to gridsearch over
                                         EX: {'param_1': [0.1, 0.01], 'p_2': [1, 10, 50]}
    output:
        list_of_combos: a list of all combos for a grid search. The above example would yield
                          EX: [{'param_1': 0.1, 'p_2': 1}, {'param_1': 0.1, 'p_2': 10}, ...]
    """
    combos = itertools.product(*dict_of_gridsearch_lists.values())
    list_of_combos = [dict(zip(dict_of_gridsearch_lists.keys(), cc)) for cc in combos]

    return list_of_combos


def add_prefix_to_dict_keys(prefix, d):
    d_out = {}  # need a new dict in order to not edit pass by reference dictionary

    for (k, v) in d.items():
        d_out[prefix + k] = v

    return d_out


def make_results_df(**gridsearch_params):
    """builds an empty results DF... gets name of each type parameter and appends the type of param as a prefix"""

    target_params_list = list(add_prefix_to_dict_keys(prefix='target_', d=gridsearch_params['targets']).keys())
    model_params_list = list(add_prefix_to_dict_keys(prefix='model_', d=gridsearch_params['model']).keys())
    decision_params_list = list(add_prefix_to_dict_keys(prefix='decision_', d=gridsearch_params['decision']).keys())

    col_name_list = target_params_list + model_params_list + decision_params_list

    col_name_list += ["sharpe", "sortino", 'pnl', 'num_transacts', ]
    results_df = pd.DataFrame(columns=col_name_list)

    return results_df


def make_current_iter_dict(target_params, model_params, decision_params):
    current_iter_params = {}

    # ###PAUL TODO: need to add features, better to do this after model is live
    #         TODO: that is a whole other dictionary to control which features are made
    current_iter_params.update(add_prefix_to_dict_keys(prefix='target_', d=target_params))
    current_iter_params.update(add_prefix_to_dict_keys(prefix='model_', d=model_params))
    current_iter_params.update(add_prefix_to_dict_keys(prefix='decision_', d=decision_params))

    return current_iter_params


def seperate_gridsearch_iter_dict_to_one_run_params(results_df_row):
    one_run_params = {'feature': {},
                      'targets': {},
                      'model': {},
                      'decision': {},
                      }

    for name, val in results_df_row.iteritems():

        if name.startswith("feature_"):
            name = name.replace("feature_", "")
            one_run_params['feature'][name] = val

        if name.startswith("target_"):
            name = name.replace("target_", "")
            one_run_params['targets'][name] = val

        if name.startswith("model_"):
            name = name.replace("model_", "")
            one_run_params['model'][name] = val

        if name.startswith("decision_"):
            name = name.replace("decision_", "")
            one_run_params['decision'][name] = val

    return one_run_params


def run_full_process(x, prices, run_on_validation_period=False, **one_run_params):
    """runs for loop over various parameters for making tarets, training models, and making decisions

    input:
        x (DataFrame): feature set for model to be trained with, DateTime indexed
        prices (pd.Series): prices for time period (prices may have more at start and end of x, DateTime indexed
        gridsearch_params (dict): a dictionary where the entery for each key represents parameters for that catgory
                                  EX: {'targets': {}, 'model': {}, 'decision': {}}

    output:
        results_df (DataFrame)
    """
    target_params = one_run_params['targets']

    dataset_dict = split_train_test(x, target_params['p_train'], target_params['p_test'], target_params['p_validate'])
    if run_on_validation_period == True:
        x_train = dataset_dict['x']['test']
        x_test = dataset_dict['x']['validation']
    elif run_on_validation_period == False:
        x_train = dataset_dict['x']['train']
        x_test = dataset_dict['x']['test']

    signal_dict = rolling_decision_tree_train(prices=prices,
                                              x_train=x_train,
                                              x_test=x_test,
                                              target_params=target_params,
                                              **one_run_params['model'])

    prices_for_preds = prices[signal_dict['preds'].index]
    decision_params = one_run_params['decision']

    # get preformance from this combo of params for target, model training, and the decision algorithm
    framework_results = backtest_decision_making(prices_for_preds, signal_dict, **decision_params)

    return framework_results


def get_downdraw_info(pv_ts_arr, freq='min'):
    """
    pv_ts_arr (np.arr): portfolio_timeseries_array formed from the pd_series in framework_results
    freq (str):
    """
    recoveries = []

    drawdowns = {'new_ath_idx': [],
                 'recovery_idx': [],
                 'drawdown_precent': [],
                 'drawdown_len_hours': [],
                 'drawdown_len_days': [],
                 }

    last_recovery_idx = 0

    while True:
        rest_of_pv_dist_from_ath = (
                pv_ts_arr[last_recovery_idx:] - np.maximum.accumulate(pv_ts_arr[last_recovery_idx:]))

        relative_first_obvs_below_new_ath_idx = np.argmax(rest_of_pv_dist_from_ath < 0)
        current_ath_idx = last_recovery_idx + relative_first_obvs_below_new_ath_idx - 1
        current_ath = pv_ts_arr[current_ath_idx]

        from_cur_ath_high_on_minus_ath = pv_ts_arr[current_ath_idx + 1:] - current_ath
        relative_recovery_idx = np.argmax(from_cur_ath_high_on_minus_ath > 0)

        if relative_recovery_idx == 0:
            drawdowns['new_ath_idx'] = np.array(drawdowns['new_ath_idx'])
            drawdowns['recovery_idx'] = np.array(drawdowns['recovery_idx'])
            drawdowns['drawdown_precent'] = np.array(drawdowns['drawdown_precent'])
            drawdowns['drawdown_len_hours'] = np.array(drawdowns['drawdown_len_hours'])
            drawdowns['drawdown_len_days'] = np.array(drawdowns['drawdown_len_days'])

            return recoveries, drawdowns
        else:
            recovery_idx = current_ath_idx + relative_recovery_idx

            bottom_of_drawdown = min(pv_ts_arr[current_ath_idx: recovery_idx])
            drawdown_precent = 100 * (1 - bottom_of_drawdown / current_ath)

            if freq in ['h', 'hr', 'hrs', 'hour', 'hours', ]:
                drawdown_len_hours = recovery_idx - current_ath_idx
            elif freq in ['m', 'min', 'mins', 'minute', 'minutes', ]:
                drawdown_len_hours = (recovery_idx - current_ath_idx) / 60

            drawdown_len_days = drawdown_len_hours / 24

            recoveries.append({'new_ath_idx': current_ath_idx,
                               'recovery_idx': recovery_idx,
                               'drawdown_precent': drawdown_precent,
                               'drawdown_len_hours': drawdown_len_hours,
                               'drawdown_len_days': drawdown_len_days,
                               })

            drawdowns['new_ath_idx'].append(current_ath_idx)
            drawdowns['recovery_idx'].append(recovery_idx)
            drawdowns['drawdown_precent'].append(drawdown_precent)
            drawdowns['drawdown_len_hours'].append(drawdown_len_hours)
            drawdowns['drawdown_len_days'].append(drawdown_len_days)

        last_recovery_idx = recovery_idx


def analyze_framework_run(framework_results, ts_freq='min'):
    port_val_ts = framework_results['port_value_ts']
    return_ts = framework_results['port_return_ts']

    # def print_out_port_preformance():
    num_longs = 0
    num_shorts = 0

    for d in framework_results['transacts_list']:
        if d['action'] == 'long':
            num_longs += 1
        if d['action'] == 'short':
            num_shorts += 1

    if ts_freq == "min":
        earlier = np.array(port_val_ts.iloc[:-24 * 60])
        later = np.array(port_val_ts.iloc[24 * 60:])
        annualized_factor = np.sqrt(24 * 365 * 60)
    elif ts_freq == "hour":
        earlier = np.array(port_val_ts.iloc[:-24])
        later = np.array(port_val_ts.iloc[24:])
        annualized_factor = np.sqrt(24 * 365)
    elif ts_freq == 'daily':
        earlier = np.array(port_val_ts.iloc[:-1])
        later = np.array(port_val_ts.iloc[1:])
        annualized_factor = np.sqrt(365)

    daily_returns = later / earlier - 1
    max_1_day_draw_down = min(daily_returns) - 1
    # histogram = px.histogram(daily_returns)

    daily_annualized_factor = np.sqrt(365)

    daily_sharpe = daily_returns.mean() / daily_returns.std() * daily_annualized_factor
    daily_sortino = daily_returns.mean() / np.where(daily_returns >= 0, 0.,
                                                    daily_returns).std() * daily_annualized_factor

    pv_ts_arr = np.array(port_val_ts)
    recoveries, drawdowns = get_downdraw_info(pv_ts_arr, freq=ts_freq)

    max_draw_down_idx = np.argmax(drawdowns['drawdown_precent'])
    max_drawdown_precent = drawdowns['drawdown_precent'][max_draw_down_idx]
    max_drawdown_len_days = drawdowns['drawdown_len_days'][max_draw_down_idx]
    mean_drawdown_precent = drawdowns['drawdown_precent'].mean()
    precent_drawdown_std = drawdowns['drawdown_precent'].std()
    mean_drawdown_len_days = drawdowns['drawdown_len_days'].mean()
    days_drawdown_std = drawdowns['drawdown_len_days'].std()
    days_drawdown_median = np.median(drawdowns['drawdown_len_days'])

    print(f"- portfolio info: \n"
          f"    - pnl      ----------------> {framework_results['pnl']} \n"
          f"    - num_longs:   ------------> {num_longs} \n"
          f"    - num_shorts:  ------------> {num_shorts} \n"
          f"    - max_1_day_draw_down: ----> {max_1_day_draw_down} \n"
          f"    - max_drawdown_precent: ---> {max_drawdown_precent} \n"  # cumulative 
          f"    - max_drawdown_len_days: --> {max_drawdown_len_days} \n"
          f"    - mean_drawdown_precent: --> {mean_drawdown_precent} \n"
          f"    - drawdown_%_std_dev: -----> {precent_drawdown_std} \n"
          f"    - mean_drawdown_len_days: -> {mean_drawdown_len_days} \n"
          f"    - days_drawdown_std: ------> {days_drawdown_std} \n"
          f"    - days_drawdown_median: ---> {days_drawdown_median} \n"
          f"\n"
          f"- hourly stats \n"
          f"    - avg return  -------------> {return_ts.mean()} \n"
          f"    - return std dev  ---------> {return_ts.std()} \n"
          f"    - sharpe     --------------> {framework_results['sharpe']} \n"
          f"    - sortino    --------------> {framework_results['sortino']} \n"
          f"\n"
          f"- daily stats: \n"
          f"    - avg return   ------------> {daily_returns.mean()} \n"
          f"    - return std dev  ---------> {daily_returns.std()} \n"
          f"    - sharpe   ----------------> {daily_sharpe} \n"
          f"    - sortino  ----------------> {daily_sortino} \n",
          flush=True
          )

    return drawdowns, recoveries


def delete_CURRENT_GRID_SEARCH_CSV_file():
    """before the decision multi process delete the file path"""

    fp = f"{data_dir}gridsearches/CURRENT_GRID_SEARCH.csv"

    try:
        os.remove(fp)
        print(f"SUCESSFULLY REMOVED: CURRENT_GRID_SEARCH.csv", flush=True)
    except:
        print(f"DID NOT REMOVE: CURRENT_GRID_SEARCH.csv ---- likely not there", flush=True)
        pass

    return None


def get_col_names_from_gridsearch_params(gridsearch_params):
    """builds an empty results DF... gets name of each type parameter and appends the type of param as a prefix"""

    target_params_list = list(add_prefix_to_dict_keys(prefix='target_', d=gridsearch_params['targets']).keys())
    model_params_list = list(add_prefix_to_dict_keys(prefix='model_', d=gridsearch_params['model']).keys())
    decision_params_list = list(add_prefix_to_dict_keys(prefix='decision_', d=gridsearch_params['decision']).keys())

    col_name_list = target_params_list + model_params_list + decision_params_list
    col_name_list += ["sharpe", "sortino", 'pnl', 'num_transacts', ]

    return col_name_list


def write_gridsearch_iter_results_and_file_first_iter(iter_results, gridsearch_params):
    """
    """

    # col_names = get_col_names_from_gridsearch_params(gridsearch_params)

    fp = f"{data_dir}gridsearches/CURRENT_GRID_SEARCH.csv"

    header = f""
    new_line = f""
    for col in col_names:
        header += f"{col}||"  # cant use , as separatior
        new_line += f"{iter_results[col]}||"
    header += f"\n"
    new_line += f"\n"

    if os.path.isfile(fp):
        with open(fp, "a") as f:
            f.write(new_line)

    # if fp not there, make it with first row being the key dicts or col names, if the file is there
    else:
        fp_dirname = os.path.dirname(fp)
        if os.path.isdir(fp_dirname) == False:
            os.makedirs(fp_dirname)

        # write the new line, and header if requested
        with open(fp, "a") as f:
            f.write(header)
            f.write(new_line)

    return None


def run_one_gridsearch_iter(preds, prices, target_params, model_params, decision_params):
    # try:

    # print(f" 1111.) INSIDE run_one_gridsearch_iter \n decision_params: \n \t {decision_params}", flush=True)
    # time.sleep(1)

    counter = decision_params[0]
    if counter % 50 == 0 or counter < 10:
        print(f" -- iter {counter} of gridsearch ", flush=True)
    decision_params = decision_params[1]

    # print(f" 2222.) BEFORE ITER_RESULTS \n decision_params: \n \t {decision_params}", flush=True)
    # time.sleep(1)

    iter_results = make_current_iter_dict(target_params, model_params, decision_params)

    # print(f" 3333.) BEFORE MODEL RESULTS  \n decision_params: \n \t {decision_params}", flush=True)
    # time.sleep(1)

    # get preformance from this combo of params for target, model training, and the decision algorithm
    framework_results = backtest_decision_making_multiprocess(prices, preds, **decision_params)

    # print(f" 4444.) AFTER MODEL RESULTS  \n decision_params: \n \t {decision_params}", flush=True)
    # time.sleep(1)

    # append the model's results to the dict for this iter
    iter_results['sharpe'] = framework_results['sharpe']
    iter_results['sortino'] = framework_results['sortino']
    iter_results['pnl'] = framework_results['pnl']
    iter_results['num_transacts'] = framework_results['num_transacts']

    # write_gridsearch_iter_results_and_file_first_iter(iter_results, gridsearch_params)
    # except IndexError:
    #     print(f"ALGOS/GRIDSEARCH.PY ---- on COUNTER: {counter} ---- IT APPEARS NO TRANSACTS \n", flush=True)
    #     time.sleep(0.2)
    #     pass

    return iter_results


def decision_multiprocess(decision_combos, signal_dict, prices, target_params, model_params, max_workers=40, debug=False):
    signal = deepcopy(signal_dict['signal'])
    results_dicts = []

    print(f"entering decision_multiprocess for {len(decision_combos)} iters", flush=True)

    final_results = []

    if debug == False:  # stanadard operation ---- us multithreading
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_one_gridsearch_iter,
                                signal,
                                prices,
                                target_params,
                                model_params,
                                decision_params,
                                ): decision_params for decision_params in enumerate(decision_combos)
            }

            for counter, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    results_dicts.append(future.result())
                    time.sleep(0.05)
                except IndexError:
                    pass
                    print(f"decision_multiprocess errored on iter: {counter}", flush=True)
                    sleep(0.15)
        for val in results_dicts:
            if val is not None:
                final_results.append(val)
    else:
        for decision_params in enumerate(decision_combos):
            iter_results = run_one_gridsearch_iter(signal, prices, target_params, model_params, decision_params)
            import pdb
            pdb.set_trace()
            final_results.append(iter_results)

    results_df = pd.DataFrame.from_records(final_results)
    results_df.reset_index(drop=True, inplace=True)

    return results_df


def grid_search_over_parameters(x, prices, gridsearch_params):
    """runs for loop over various parameters for making tarets, training models, and making decisions

    input:
        x (DataFrame): feature set for model to be trained with, DateTime indexed
        prices (pd.Series): prices for time period (prices may have more at start and end of x, DateTime indexed
        gridsearch_params (dict): a dictionary where the entery for each key represents parameters for that catgory
                                  EX: {'targets': {}, 'model': {}, 'decision': {}}

    output:
        results_df (DataFrame)
    """

    # delete_CURRENT_GRID_SEARCH_CSV_file()

    results_df = make_results_df(**gridsearch_params)

    # make list of all combos for each step ---- count combos for printouts
    target_combos = make_list_of_combo_dicts(gridsearch_params['targets'])
    model_combos = make_list_of_combo_dicts(gridsearch_params['model'])
    decision_combos = make_list_of_combo_dicts(gridsearch_params['decision'])
    num_target_combos = len(target_combos)
    num_model_combos = len(model_combos)
    num_decision_combos = len(decision_combos)
    num_total_combos = num_target_combos * num_model_combos * num_decision_combos

    iters_all_combo_dict = {}  # dictionary containing current iterations parameters, keys prefixed param type
    target_combo_iter = 0
    total_iter_count = 0
    for target_params in target_combos:
        target_combo_iter += 1
        print(f"-- target iter #: {target_combo_iter} of  {num_target_combos}", flush=True)

        dataset_dict = split_train_test(x, target_params['p_train'], target_params['p_test'],
                                        target_params['p_validate'])
        x_train = dataset_dict['x']['train']
        x_test = dataset_dict['x']['test']

        model_combo_iter = 0
        for model_params in model_combos:
            model_combo_iter += 1
            print(f"---- model iter #: {model_combo_iter} of  {num_model_combos} ", flush=True)

            signal_dict = rolling_decision_tree_train(prices=prices,
                                                      x_train=x_train,
                                                      x_test=x_test,
                                                      target_params=target_params,
                                                      model_params=model_params)

            max_workers_int = int(gridsearch_params['decision']['max_workers'][0])
            print(f"###PAUL _debug_del_later  ----  max_workers_int: {max_workers_int} ")
            import pdb; pdb.set_trace()

            results_df_for_iter = decision_multiprocess(decision_combos=decision_combos,
                                                        signal_dict=signal_dict,
                                                        prices=prices,
                                                        target_params=target_params,
                                                        model_params=model_params,
                                                        max_workers=max_workers_int)

            # try:
            # import pdb; pdb.set_trace()
            # if model_combo_iter == 1:
            #     results_df = results_df_for_iter
            #     results_df.reset_index(drop=True, inplace=True)
            # else:
            results_df = pd.concat((results_df, results_df_for_iter))
            results_df.reset_index(drop=True, inplace=True)
            # except:
            #     import pdb;
            #     pdb.set_trace()

    fp = '{data_dir}gridsearches/grid_search____most_recent.pickle'
    pickle.dump(results_df, open(fp, "wb"))

    return results_df
