def get_multiasset_trading_summaries(eaors_trade_request):
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
    vwap_dict = {}

    trading_summary_pairs = list(eaors_trade_request.keys())

    for pair in trading_summary_pairs:

        pair_configs = eaors_trade_request[pair]
        trading_summary = query_trading_summary(exchange=pair_configs['exchange'],
                                                symbol=pair,
                                                start_date=pair_configs['start_date'],
                                                end_date=pair_configs['end_date'])

        if pair_configs['alternative_data_pair'] is not None:
            early_trading_summary = query_trading_summary(exchange=pair_configs['exchange'],
                                                          symbol=pair_configs['alternative_data_pair'],
                                                          start_date=pair_configs['alternative_start_date'],
                                                          end_date=pair_configs['alternative_end_date'])
            early_trading_summary['symbol'] = pair  # override the pair for the alternative data pair
            trading_summary_mask = trading_summary.index > early_trading_summary.index.max()
            trading_summary = trading_summary[trading_summary_mask]
            trading_summary = pd.concat([early_trading_summary, trading_summary])

        trading_summary = fill_trading_summary(trading_summary)
        trading_summary = deduplicate_df_on_index_only(trading_summary)

        trading_summaries[pair] = trading_summary

        # get vwap after merging all the summaries since is just a trading_summary columns
        vwap = deepcopy(trading_summary[
                            'vwap'])  # ###PAUL TODO: when going through multi asset depricate vwap and just refer to the trading summary itself
        vwap_dict[pair] = vwap

    return trading_summaries, vwap_dict


def make_eaors_trades_features(eaors_trade_request):
    eaors_trade_features = []

    trading_summaries, vwap_dict = get_multiasset_trading_summaries(eaors_trade_request)

    trading_summary_pairs = list(feature_params['eaors_trades'].keys())

    # ###PAUL TODO: I like this method of merging to get a maxium data range of featureset. generalize this to all merges for this (shouldn't need live)
    early_dates = []
    late_dates = []
    # TODO: though dates will also vary so a better approach maybe to find  the earliest date available for each ticker after feature production.
    for pair in trading_summary_pairs:
        # ###PAUL TODO: this should be depricated by code which prints a python file that does the calculations
        var_name_list, cut_time_list, var_dict, cut_dict = make_feature_set_printed_fn(trading_summaries[pair])
        # ###PAUL TODO: this should be depricated by code which prints a python file that does the calculations
        min_feature_df = make_feature_df_from_results_of_printed_code(trading_summary=trading_summaries[pair],
                                                                      cut_time_list=cut_time_list,
                                                                      var_dict=var_dict)

        # ###PAUL TODO: next version of this function requests to come in the form  eaors_trade_request['spot/futures'][exchange][pair]
        exchange = eaors_trade_request[pair]['exchange']
        prefix_str = f"{exchange}_{pair.replace('-', '_')}_"
        min_feature_df = min_feature_df.add_prefix(prefix_str)
        min_feature_df = min_feature_df.asfreq('T')

        eaors_trade_features.append(min_feature_df)
        early_dates.append(min(min_feature_df.index))
        late_dates.append(max(min_feature_df.index))

    start_date = max(early_dates)
    end_date = min(late_dates)

    for i, pair in enumerate(trading_summary_pairs):  # dont really need to do using pair but so it goes for now.
        dti = eaors_trade_features[i].index
        mask = np.logical_and(start_date <= dti, dti <= end_date)
        eaors_trade_features[i] = eaors_trade_features[i][mask]

    x_from_eaors_trades = pd.concat(eaors_trade_features, axis=1)
    x_from_eaors_trades = x_from_eaors_trades.asfreq('T')

    return x_from_eaors_trades, vwap_dict  # vwap dict for backtesting... may want to match to features. this is only a historical thing so maybe just worth
    # keepping here because won't be this "dirty" for live purposes.
    # the alternative would be to just build a quick query when it comes backtest time (get vwap from algos_db.TradingSummary)


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


def match_index_granularity_and_merge_multi_source_features(features_to_merge):
    """ merges list of pandas DFs/series together based on the index of the first item in the list
    """

    base_df = features_to_merge[0]
    base_df = base_df.asfreq('T')
    # hard coding frequency for now... planning on keeping freq at 1min with EAORS trades as base
    # its imaginable that in the future we would want to go to interval-less data (for order books or something weird)

    # Process all DataFrames including the base DataFrame
    resampled_dfs = []
    for df in features_to_merge:
        df_resampled = df.resample(base_df.index.freq).ffill()  # Resample to match the index of the base_df
        resampled_dfs.append(df_resampled)  # Forward fill to impute missing values

    # Merge all resampled DataFrames
    result_df = pd.concat(resampled_dfs, axis=1)

    return result_df


def make_utc_time_df(base_df):
    UTC_min_col = make_utc_time_based_column(pd_obj=base_df, freq='T', precast=False, verbose=False)
    UTC_hour_col = make_utc_time_based_column(pd_obj=base_df, freq='h', precast=False, verbose=False)
    UTC_day_col = make_utc_time_based_column(pd_obj=base_df, freq='d', precast=False, verbose=False)
    UTC_dow_col = make_utc_time_based_column(pd_obj=base_df, freq='dow', precast=False, verbose=False)

    time_cols_for_df = [UTC_min_col, UTC_hour_col, UTC_day_col, UTC_dow_col]

    utc_df = match_index_granularity_and_merge_multi_source_features(time_cols_for_df)

    return utc_df
