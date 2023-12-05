"""CIRCULAR IMPORT AVOIDANCE
    - anything that ends up in the code generated code must be kept originally known as `make_feature_set_printed_fn`
      must go here.
    - `make_feature_set_printed_fn()` relies on things in this (and needs to import it
    - this is the cleanest way to avoid circular import issues.
    in this file.
 can't use the function `make_eaors_trades_features()`
anything that uses it must be put in feature_high_level.py due to it using `make_feature_set_printed_fn()`"""
# ### local imports
import sys
sys.path.insert(0, '..')  # for local imports from the top directory
from algos.utils import query_trading_summary, fill_trading_summary, deduplicate_df_on_index_only

import datetime
from copy import deepcopy
import numpy as np
import pandas as pd


def get_ratio_of_metrics_rolling_sums(df, n, metric_1, metric_2):
    """creates ratio of moving average sum of metric_1 and metric_2.
    for example if the following is called:
        get_ratio_of_metrics_rolling_sums(prices_df, n, 'buyer_is_maker', 'buyer_is_taker')
    a ratio of the number of buys vs the number of sells in the n minutes leading up to the time is calculated

    input:
        prices_df (pd.DataFrame): standard prices in 1 second intervals, made from trade streams
        n (int): number of second intervals to count
        metric_1 (str): metric for numerator of the ratio
        metric_2 (str): metric for the denominator of ratio

    output:
        ratio_df (pd.DataFrame): a DataFrame with time index "msg_time" and ratio of buys/sells
        obvs_cut_off (int): number of 1s obvservations needed cut off from the beginning of targets
    """

    numerator = df[metric_1].rolling(n).sum()
    denominator = df[metric_2].rolling(n).sum()

    ratio_series = numerator / denominator
    ratio_series[np.isnan(ratio_series)] = 0
    ratio_series = np.clip(ratio_series, a_min=0, a_max=5)

    obvs_cut_off = n - 1

    return ratio_series, obvs_cut_off


# ### EXAMPLES
# buy_to_sell_count_ratio_30,   buy_to_sell_count_ratio_30_cut   = get_ratio_of_metrics_rolling_sums(prices, 30,  'buyer_is_maker', 'buyer_is_taker')
# buy_to_sell_vol_ratio_30,   buy_to_sell_vol_ratio_30_cut   = get_ratio_of_metrics_rolling_sums(prices, 30,  'buy_vol', 'sell_vol')


def calculate_momentum(df, col, n):
    """calculates moving return (aka momentum) at n intervals for a given column of a df

    inputs:
        df (pd.DataFrame): the thing with the data
        col (str): name of column to do calculation on
        n (int): number of periods to do one calculation to the next)

    outputs:
        momentum_series
        obvs_cut_off
    """

    earlier_values = df[col].iloc[:-n]
    later_values = df[col].iloc[n:]
    earlier_values.index = later_values.index

    momentum_series = later_values / earlier_values

    obvs_cut_off = n

    return momentum_series, obvs_cut_off


# ### EXAMPLE
# momentum_30,    momentum_30_cut    = calculate_momentum(prices,    'buy_vwap',   30)


def calc_macd(series, spans, mult=1):
    """

    input:                         EXAMPLES
        series (pd.series) ---- prices['vwap']
        spans  (tuple)     ---- (12, 26, 9)
        mult   (int)       ---- 5000
    """

    span_1 = spans[0] * mult
    span_2 = spans[1] * mult
    span_d = spans[2] * mult

    exp1 = series.ewm(span=span_1, adjust=False).mean()
    exp2 = series.ewm(span=span_2, adjust=False).mean()

    macd = exp1 - exp2

    macd = macd.ewm(span=span_d, adjust=False).mean()

    obvs_cut = max(span_1, span_2) + span_d

    return macd, obvs_cut


# ### EXAMPLE
# series = prices['vwap']
# spans = (12, 26, 9)
# mult   = 5000

# macd, obvs_cut = calc_macd(series, spans, mult)


def calc_rsi(series, n=14):
    """
    Returns a pd.Series with the relative strength index.
    """

    series_delta = series.diff()

    # Make two series: one for lower closes and one for higher closes
    up = series_delta.clip(lower=0)
    down = -1 * series_delta.clip(upper=0)

    # Use exponential moving average
    ma_up = up.ewm(com=n - 1, adjust=True).mean()
    ma_down = down.ewm(com=n - 1, adjust=True).mean()

    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))

    obvs_cut = n

    return rsi, obvs_cut


def calc_rolling_std(series, n):
    rolling_std = series.rolling(n).std()
    obvs_cut = n - 1

    return rolling_std, obvs_cut
