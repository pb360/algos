# ### local imports
import sys
sys.path.insert(0, '..')  # for local imports from the top directory
from algos.utils import (convert_date_format,
                         query_trading_summary,
                         fill_trading_summary,
                         deduplicate_df_on_index_only, )

# ###PAUL TODO: this should be depricated by code which goes off last rolling value (significant engineering needed...)
# from algos import generate_code_for_feature_set  # TODO: this is
from algos.make_feature_set_printed_fn import make_feature_set_printed_fn  # imported below after making code
# TODO:
#  * need to add desired_features_dict to `signal_dict`... right now we are utilizing the same printed file and
#    never touching it. This is not a sustainable solution... while this piece (printing the code and importing it itself
#    does not need to be implemented currently.. passing the desired_features_dict should be handled properly though
#    the whole pipeline `params['signal']['desired_features_dict']
#
#  *  make_feature_set_printed_fn() write to file the import ... will need to run
# ... the above won't be a problem because there is a seprate desired features dict that will print code per ticker..
#     the purpose of this was to make smaller feature sets for the less significant pairs
from algos.make_feature_set_printed_fn import make_feature_set_printed_fn
# ###PAUL TODO: this should be depricated by code which goes off last rolling value (significant engineering needed...)

from clickhouse_driver import Client as CH_Client
from copy import deepcopy
import datetime
import numpy as np
import pandas as pd
import time


# def zscore(series, window):
#     """calculates the rolling z-score of a time series given a certain window
#     input:
#         x (pd.series)
#         window (int)
#     """
#
#     r = series.rolling(window=window)
#     m = r.mean().shift(5)
#     s = r.std(ddof=2).shift(5)
#     z = (series - m) / s
#     return z


# ### Example
# rolling_z = zscore(prices, 100)


def print_feature_making_code(desired_features_dict):
    """creates a function whose docstring should be something like:

    input:
        none
    output:
        var_name_list
        cut_time_list
        var_dict
        cut_dict
    """

    # should be the same for each interval, but for future workability each interval will store this info
    var_name_list = []
    cut_length_name_list = []

    # str for tab
    t = '    '

    # define the function

    print(f"import sys \n"
          f"sys.path.insert(0, '../') \n"
          f"from algos.feature_low_level import get_ratio_of_metrics_rolling_sums, calculate_momentum, "
          f"calc_rsi, calc_rolling_std, calc_macd")

    print('def make_feature_set_printed_fn(prices):')

    for feature in desired_features_dict.keys():
        """my version of decorator logic because I can't figure out the right way to do this
        """

        # skip dictionary's example entry
        if feature == 'feature_name':
            continue

        print(t + '# MAKE: ' + feature)
        # isolate parameters dictionary for the feature we are building right now
        feature_params_dict = desired_features_dict[feature]

        function_name = feature_params_dict['function_name']
        kwargs_dict = feature_params_dict['kwargs']

        # check if simple interval metric... all handled similarly
        if 'interval_lens' in feature_params_dict.keys():
            intervals = feature_params_dict['interval_lens']

            # this string has all the function inputs except for interval_len
            kwargs_str = ''
            for arg in kwargs_dict.keys():
                kwargs_str = kwargs_str + arg + '=' + kwargs_dict[arg] + ', '

            for interval in intervals:
                var_name = feature + '_' + str(interval)
                cut_var_name = feature + '_' + str(interval) + '_cut'

                var_name_list.append(var_name)
                cut_length_name_list.append(cut_var_name)

                print(t + var_name + ',   ' + cut_var_name + '  =  ' + function_name +
                      '(n=' + str(interval) + ', ' + kwargs_str + ')')

        # check if macd
        if feature == 'macd':
            kwargs_str = ''
            for arg in kwargs_dict.keys():
                kwargs_str = kwargs_str + arg + '=' + kwargs_dict[arg] + ', '

            for mult in feature_params_dict['multipliers']:
                for spans in feature_params_dict['span_tuples']:
                    s1 = spans[0]
                    s2 = spans[1]
                    d = spans[2]

                    var_name = feature + '_' + str(s1) + '_' + str(s2) + '_' + str(d) + '_x' + str(mult)
                    cut_var_name = var_name + '_cut'

                    var_name_list.append(var_name)
                    cut_length_name_list.append(cut_var_name)

                    # OUTPUT EXAMPLE: macd_1s1_2s1_1d_50mult, macd_1s1_2s1_1d_50mult_cut = calc_macd(series, span_1, span_2, span_d, mult=1)
                    print(t + var_name + ',   ' + cut_var_name + '  =  ' + function_name +
                          '(' + kwargs_str + 'spans=' + str(spans) + ', mult=' + str(mult) + ')')

        # END OF FOR LOOP FOR FEATURE IN FEATURE DICTS
        # put two lines between a batch of functions
        print('\n')

    print(t + '# MAKING list of variable names (keys of var_dict) ')

    print(t + 'var_name_list = [')
    l = len('var_name_list = [')
    for var in var_name_list:
        print(t + ' ' * l + "'" + var + "', ")
    print(t + ' ' * (l - 1) + ']')

    print(t + '\n')
    print(t + '# MAKING cut time list ')
    print(t + 'cut_time_list = [')

    l = len('cut_time_list = [')
    for var in cut_length_name_list:
        print(t + ' ' * l + var + ', ')
    print(t + ' ' * (l - 1) + ']')

    print(t + '\n')
    print(t + '# MAKING variable dictionary')

    # variable dictionary used to populate the data frame ---- print out
    print(t + 'var_dict = {')
    l = len('var_dict = {')
    for var in var_name_list:
        print(t + ' ' * (l) + "'" + var + "':" + var + ", ")
    print(t + ' ' * (l - 1) + '}')

    print(t + '\n')
    print(t + "# MAKING cut dictionary ---- {'var_name_key': correspoonding value is cut time int variable")
    print(t + "cut_dict = {")
    l = len('cut_dict = {')
    for var in var_name_list:
        print(t + ' ' * (l) + "'" + var + "': " + var + '_cut, ')
    print(t + ' ' * (l - 1) + "}")

    print(t + '\n')
    print(t + 'return var_name_list, cut_time_list, var_dict, cut_dict')


def make_feature_df_from_results_of_printed_code(trading_summary, cut_time_list, var_dict, freq='min'):  # ###PAUL name sucks
    """grabs all the features by name and appends them to a numpy array handling lengths as is needed

    input:
        var_names (list): of var names desired... can just feed in "var_name_list" made above or format:
                          ['macd_12_26_9_x60', 'macd_12_30_9_x60', ... ]
    """

    if freq in ['m', 'min', 'mins', 'minute', 'minutes', ]:

        feature_start_time = trading_summary.index[max(cut_time_list)]
        for key in var_dict.keys():
            var_dict[key] = var_dict[key][var_dict[key].index > feature_start_time]

        feature_df = pd.DataFrame(var_dict)

        feature_df.clip(lower=-10e12, upper=10e12, inplace=True)
        num_nans_pre_prune = feature_df.isna().sum().sum()

        feature_df.fillna(method='ffill', inplace=True)
        feature_df.fillna(method='bfill', inplace=True)
        feature_df.fillna(method='ffill', inplace=True)

        num_nans_post_prune = feature_df.isna().sum().sum()

        # print(f"-- post max_cut_len prune # NaNs --> {num_nans_pre_prune}  "
        #       f"-- processed array # NaNs:    -----> {num_nans_post_prune}",
        #       flush=True
        #       )

    return feature_df


def zip_hour_and_min_level_df(min_df, hour_df):
    _min_df = deepcopy(min_df)
    _hour_df = deepcopy(hour_df)

    min_idxs = _min_df.index
    hour_idxs = _hour_df.index

    minimum_idx = max(min(min_idxs), min(hour_idxs)).ceil('H')
    maximum_idx = min(max(min_idxs), max(hour_idxs)).floor('H')

    _min_df_mask = np.logical_and(minimum_idx <= min_idxs, min_idxs <= maximum_idx)
    _hour_df_mask = np.logical_and(minimum_idx <= hour_idxs, hour_idxs <= maximum_idx)

    _min_df = _min_df[_min_df_mask]
    _hour_df = _hour_df[_hour_df_mask]

    # resset these to the actual idxs
    min_idxs = _min_df.index
    hour_idxs = _hour_df.index

    hour_cols = _hour_df.columns
    num_hour_cols = len(hour_cols)

    # add hourly columns to the minute df, ensure no overlap # ###PAUL generalize this with a 'freq' argument
    for column in hour_cols:

        # if there is an overlap of column names rename minute (as hour will be put in using its names below)
        if column in _min_df.columns:
            _min_df[f"'minly_{column}"] = _min_df[column]
            del _min_df[column]

    prior_floor = None
    num_idxs = min_idxs.shape[0]
    hour_info_min_level_list = []
    num_cut_from_beginning = 0
    # populate each row of the minute level data with the corresponding hour
    for row_count, idx in enumerate(min_idxs):
        if row_count < 5 or row_count % 10000 == 0:
            print(f" - iter: {row_count} of {num_idxs}", flush=True)

        floored_idx = idx.floor('H') + datetime.timedelta(hours=-1)  # subtract hour because CQ dti is hour's open

        # if the floored index is new, then we need to to get the new hour's observation
        if floored_idx != prior_floor:
            matching_hour_mask = _hour_df.index == floored_idx
            hour_obvs = _hour_df[matching_hour_mask]
        if hour_obvs.shape[0] != 1:
            if row_count < 60:  # up to first hour may not have hourly data to match, ignore this
                num_cut_from_beginning += 1
                 # must pass, not continue, to ensure prior floor always updated
            else:
                print(f" --- this minute observation dose not have a corresponding hour, need to handle", flush=True)
                raise KeyError
        else:
            hour_info_min_level_list.append(list(hour_obvs.iloc[0].values))

        prior_floor = floored_idx

    hour_info_min_level_arr = np.array(hour_info_min_level_list)
    hour_info_min_level_df = pd.DataFrame(data=hour_info_min_level_arr,
                                          index=min_idxs[num_cut_from_beginning:],
                                          columns=hour_cols, )

    return hour_info_min_level_df


def rolling_normalize_feature_df(df, one_run_params=None, feature_params=None):
    if one_run_params is not None:
        feature_params = one_run_params['features']
    elif feature_params is None:
        print(f"must supply one of [one_run_params, feature_params]")
        raise ValueError

    # normalize the feature set in a rolling manner..
    preprocess_rolling_norm_n_obvs = feature_params['preprocess_rolling_norm_n_obvs']
    x_normed_rti = ((df - df.rolling(preprocess_rolling_norm_n_obvs).mean()).fillna(0) /
                    df.rolling(preprocess_rolling_norm_n_obvs).std().fillna(method='ffill')).iloc[
                   preprocess_rolling_norm_n_obvs - 1:]

    x_normed_rti = x_normed_rti.fillna(method='ffill').fillna(method='bfill').fillna(value=0)
    x_normed_rti = np.clip(a=x_normed_rti, a_min=-10, a_max=10)

    return x_normed_rti


def get_multiasset_trading_summaries(eaors_trade_request, columns='all', ch_client=None):
    """ feature_params['eaors_trades'] fed in, and outputs trading summaries (with historical imputation

    dev notes
        - in the live pipeline `update_trading_summary.py` would have produced all of this. So it would be accurate to just
          start at quering each ticker's trading summary.... WITH THAT BEING SAID, this function is more complex than the live one
          will need to be because it has to have backups for tickers and be able to concatenate this data.
        - the above complication is not too significant (and is a subcase of all tickers' `alternative_data_pair` being None.
          so this piece of functionality will be the same for historical and live purposes.
        - I think that all functions in make_features will have this trait
    """

    trading_summaries = {}
    trading_summary_pairs = list(eaors_trade_request.keys())

    for pair in trading_summary_pairs:

        pair_configs = eaors_trade_request[pair]
        trading_summary = query_trading_summary(exchange=pair_configs['exchange'],
                                                symbol=pair,
                                                start_date=pair_configs['start_date'],
                                                end_date=pair_configs['end_date'],
                                                columns=columns,
                                                ch_client=ch_client)

        if pair_configs['alternative_data_pair'] is not None:
            early_trading_summary = query_trading_summary(exchange=pair_configs['exchange'],
                                                          symbol=pair_configs['alternative_data_pair'],
                                                          start_date=pair_configs['alternative_start_date'],
                                                          end_date=pair_configs['alternative_end_date'],
                                                          columns=columns,
                                                          ch_client=ch_client)
            trading_summary_mask = trading_summary.index > early_trading_summary.index.max()
            trading_summary = trading_summary[trading_summary_mask]
            trading_summary = pd.concat([early_trading_summary, trading_summary])

        trading_summary = fill_trading_summary(trading_summary)
        trading_summary = deduplicate_df_on_index_only(trading_summary)

        trading_summaries[pair] = trading_summary

    return trading_summaries


def make_utc_time_based_column(pd_obj, freq, precast=True, verbose=False):
    """
    """

    if type(pd_obj) != pd.core.indexes.datetimes.DatetimeIndex:
        if verbose:
            print(f" - pd_obj is not a date time index... is {type(pd_obj)}")
        dti = pd_obj.index

    if precast:
        if freq.lower() in ['t', 'm', '1m', 'min', '1min', 'minute']:
            utc_col_df = pd.DataFrame(dti.minute, index=dti)
        if freq.lower() in ['h', '1h', 'hour', '1hour']:
            utc_col_df = pd.DataFrame(dti.hour, index=dti)
        if freq.lower() in ['d', '1d', 'day', '1day', 'day_of_month']:
            utc_col_df = pd.DataFrame(dti.day, index=dti)
        if freq.lower() in ['w', 'dow', 'weekday', 'day_of_week', ]:
            utc_col_df = pd.DataFrame(dti.dayofweek, index=dti)

    else:  # more for development, but produce index at granular level (1 per hour, day, etc...)
        if freq.lower() in ['t', 'm', '1m', 'min', '1min', 'minute']:
            mask = ~dti.floor('1Min').duplicated(keep='first')
            utc_col_df = pd.DataFrame(dti[mask].minute, index=dti[mask])
        if freq.lower() in ['h', '1h', 'hour', '1hour']:
            mask = ~dti.floor('1H').duplicated(keep='first')
            utc_col_df = pd.DataFrame(dti[mask].hour, index=dti[mask])
        if freq.lower() in ['d', '1d', 'day', '1day', 'day_of_month']:
            mask = ~dti.floor('1D').duplicated(keep='first')
            utc_col_df = pd.DataFrame(dti[mask].day, index=dti[mask])
        if freq.lower() in ['w', 'dow', 'weekday', 'day_of_week', ]:
            mask = ~dti.floor('1D').duplicated(keep='first')
            utc_col_df = pd.DataFrame(dti[mask].dayofweek, index=dti[mask])

        utc_col_df.columns = [f"utc_{freq}"]

    return utc_col_df


# ###PAUL TODO: this would be better off in utils.py
def merge_dfs_with_index_granularity_matching(features_to_merge, use_first_as_base_idx=True, freq='T'):
    """ merges list of pandas DFs/series together based on the index of the first item in the list
    """
    # frequency is set for now... planning on keeping freq at 1min with EAORS trades as base
    # its imaginable that in the future we would want to go to interval-less data (for order books or something weird)

    # get early / late dates
    early_dates = []
    late_dates = []
    for df in features_to_merge:
        early_dates.append(min(df.index))
        late_dates.append(max(df.index))

    # handle getting
    start_date = max(early_dates)
    if use_first_as_base_idx:
        base_df = features_to_merge[0]
        base_df = base_df.asfreq('T')
        end_date = max(base_df.index)
    else:
        end_date = min(late_dates)
        # ###PAUL TODO: I dont like how `freq` is handled
        base_df = pd.DataFrame(0, index=pd.date_range(start_date, end_date, freq=freq), columns=['Value'])

    time_clipped_and_resampled_dfs = []
    for df in features_to_merge:
        # TODO: more closely investigate the line below. Also if `use_first_as_base_idx` should check index?
        df = df.resample(base_df.index.freq).ffill()  # resample to match the index of the base_df
        mask = np.logical_and(start_date <= df.index, df.index <= end_date)  # isolate only to start and end time
        df = df[mask]  # isolate only to start and end time
        time_clipped_and_resampled_dfs.append(df)

    # Merge all resampled DataFrames
    result_df = pd.concat(time_clipped_and_resampled_dfs, axis=1)
    
    return result_df


def make_utc_time_df(base_df):
    UTC_min_col = make_utc_time_based_column(pd_obj=base_df, freq='T', precast=False, verbose=False)
    UTC_hour_col = make_utc_time_based_column(pd_obj=base_df, freq='h', precast=False, verbose=False)
    UTC_day_col = make_utc_time_based_column(pd_obj=base_df, freq='d', precast=False, verbose=False)
    UTC_dow_col = make_utc_time_based_column(pd_obj=base_df, freq='dow', precast=False, verbose=False)

    time_cols_for_df = [UTC_min_col, UTC_hour_col, UTC_day_col, UTC_dow_col]

    utc_df = merge_dfs_with_index_granularity_matching(time_cols_for_df, use_first_as_base_idx=True)

    return utc_df


def make_eaors_trades_features(eaors_trade_request, ch_client=None):
    """ does the feature handling

    # ###PAUL TODO: rebuild with `merge_dfs_with_index_granularity_matching` used... the pattern used here was taken
              TODO: and implemented there with some improvements
    """
    eaors_trade_features = []

    trading_summaries = get_multiasset_trading_summaries(eaors_trade_request, ch_client=ch_client)
    trading_summary_pairs = list(eaors_trade_request.keys())

    for pair in trading_summary_pairs:
        # ###PAUL TODO: this should be depricated by code which prints a python file that does the calculations
        var_name_list, cut_time_list, var_dict, cut_dict = make_feature_set_printed_fn(trading_summaries[pair])
        min_feature_df = make_feature_df_from_results_of_printed_code(trading_summary=trading_summaries[pair],
                                                                      cut_time_list=cut_time_list,
                                                                      var_dict=var_dict)
        # ###PAUL TODO: this should be depricated by code which prints a python file that does the calculations

        # ### add prefix to columns so when merged they have unique column names
        # ###PAUL TODO: next version of this function requests to come in the form
        #         TODO: eaors_trade_request['spot/futures'][exchange][pair]
        exchange = eaors_trade_request[pair]['exchange']
        prefix_str = f"{exchange}_{pair.replace('-', '_')}_"
        min_feature_df = min_feature_df.add_prefix(prefix_str)

        min_feature_df = min_feature_df.asfreq('T') # hard set frequency, depending on how its made, maybe not set.
        eaors_trade_features.append(min_feature_df)

    x_from_eaors_trades = merge_dfs_with_index_granularity_matching(eaors_trade_features,
                                                                    use_first_as_base_idx=False,  # only when we have all info
                                                                    # important to thinkabout the above in here...
                                                                    freq='T')
    x_from_eaors_trades = x_from_eaors_trades.asfreq('T')  # keep till above is confirmed to not need this line

    max_cut_time = max(cut_time_list)
    # ###PAUL TODO: ugly handling of `max_cut_time` but may end up deciding minor derivation of this is sufficient as optimized compute woudln't have one of these anymore
    # TODO: consider adding an entry to feature_params... I am not sure about how I feel about directly adding
    # TODO: and editing target, feature, model, and decision params in an automated way....
    # TODO: maybe a good convention to contain everything that can be adjusted by the framework into an ['auto'] top
    # TODO: level key...
    return x_from_eaors_trades, max_cut_time  # vwap dict for backtesting... may want to match to features. this is only a historical thing so maybe just worth


def make_features(params=None, feature_params=None, ch_client=None):
    """a pipeline function designed to process data from many sources into one dataframe

    input:
        params: used when running live in generate signal
        feature_params: used for data science work and generating a signal_dict

    * each if statement has handling for specific data sources
    * each item returned from an if statement is an individual dataframe
    * to force all index granularity from each of the sources to match we use merge_dfs_with_index_granularity_matching

    max_cut now ran via feature_params

    """
    if params is not None:
        feature_params = params['signal_dict']['feature_params']
    else:
        assert(feature_params is not None)

    features_to_merge \
        = []  # ist of DFs to merge with one another

    # assumes that eaors_trades_df is `base_df`
    if 'eaors_trades' in feature_params:
        eaors_trades_df, max_cut_time = make_eaors_trades_features(feature_params['eaors_trades'], ch_client=ch_client)
        # ###PAUL TODO: ugly handling of `max_cut_time` but may end up deciding minor derivation of this is sufficient as optimized compute woudln't have one of these anymore
        features_to_merge.append(eaors_trades_df)

    if 'eaormake_feature_set_printed_fns_orderbook' in feature_params:
        eaors_orderbook = make_eaors_orderbook_features(feature_params['eaors_orderbook'])
        features_to_merge.append(eaors_orderbook)

    if 'l_map' in feature_params:
        l_map = make_l_maps_features(feature_params['l_map'])
        features_to_merge.append(l_map)

    if 'utc_time' in feature_params:  # ###PAUL TODO: make this an hourly feature (eventually will depricate when have actually using another
        utc_df = make_utc_time_df(features_to_merge[0])  # first entry in `features_to_merge` acts as `base_df`
        features_to_merge.append(utc_df)

    x = merge_dfs_with_index_granularity_matching(features_to_merge, use_first_as_base_idx=True)
    if params is not None: # we are making it for a live run, need to see which columns are included
        x = x[params['signal_dict']['feature_names']]
    x = rolling_normalize_feature_df(df=x, feature_params=feature_params)  # preprocessing

    # ###PAUL TODO: ugly handling of `max_cut_time` but may end up deciding minor derivation of this is sufficient as optimized compute woudln't have one of these anymore
    return x, max_cut_time


def adjust_start_dates_of_feature_params(feature_params, model_params, max_cut_time, signal_id, ch_client=None):
    """ edits the start_dates of feature_params (in place) such that as little data as possible is queried

    the goal should be that there are as few edits needed as possible to various functions when adding new features
    the goal should be that there are as few edits needed as possible to various functions when adding new features
    there should be basically none required for adding support of new trading assets...
    with that being said this is one of the key ones... A TODO: list which should also be put in the algos ipynb
    - TODO: `feature_printed_code()`
    - TODO: this function
    - TODO: `make_features()`
    """

    if ch_client == None:
        print(f"warning -- clickhouse client set to none in `adjust_start_dates_of_feature_params()`")
        ch_client = CH_Client('10.0.1.86', port='9009')

    # try:   # ###PAUL_del_later
    max_signal_timestamp = ch_client.execute(f"""SELECT max(timestamp)
                                                FROM hoth.AlgosSignals
                                                WHERE signal_id == '{signal_id}';""")[0][0]

    # if there is not a signal the following query returns 1970-1-1 instead of no signal with this signal_id
    if max_signal_timestamp == convert_date_format((1970, 1, 1, 0, 0, 0), 'datetime'):
        print(f" WARNING: in time frame update with no entries for `signal_id` = {signal_id} \n"*5)

    else:
        if 'eaors_trades' in feature_params:
            pairs = feature_params['eaors_trades'].keys()

            cut_preprocessing = max(0, feature_params['preprocess_rolling_norm_n_obvs'])
            cut_postprocessing = max(0, model_params['signal_norm_window'])
            total_cut = max_cut_time + cut_preprocessing + cut_postprocessing

            # import pdb       # ###PAUL_del_later
            # pdb.set_trace()  # ###PAUL_del_later

            # total cut is # of minute observations in minutes
            st_in_epoch = max_signal_timestamp - datetime.timedelta(minutes=2*total_cut)
            # start_date = convert_date_format(st_in_epoch, 'pandas').round(freq='D')
            start_date = convert_date_format(st_in_epoch, 'tuple_to_day')
            end_date = convert_date_format(time.time()+2*24*60*60, 'tuple_to_day')  # add a day
            # TODO: on this look into whether params will handle `tuple_to_second` and change to this if it will
            # ###PAUL TODO: the above contains some quick and dirty fixes, fix that

            for pair in pairs:
                feature_params['eaors_trades'][pair]['start_date'] = start_date
                feature_params['eaors_trades'][pair]['end_date'] = end_date

        if 'lmaps' in feature_params:
            print(f"get look back needed to make liquidation map features (probably 30 - 90 days")

