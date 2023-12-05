# ### local imports
import sys

sys.path.insert(0, '..')  # for local imports from the top directory

from dateutil.relativedelta import relativedelta
import math
import numpy as np
import pandas as pd
from scipy import signal


def get_peak_and_valley_idxs_in_intervals(series,
                                          min_peak_dist=3,
                                          peak_prominence=0.015,
                                          interval_len_in_steps=400,
                                          ):
    """The goal of this function is to return numerical indexes of valleys and peaks in the series provided

    in order the functionality
    - 1.) breaks the series into intervals
    - 2.) takes average price of each interval, normalizes the interval WRT to that avg price
    --------> adds edges to each normalized interval. these edges are different for peak vs valley finding
    --------> verifies that we aren't identifying a peak on the way down, or valley on the way up at start of intervals
    - 3.) concatenates all the peak / valley idxs together

    outputs:
        valley_idxs (np.array): numerical indexes of valleys (relative to series)
        peak_idxs   (np.array): numerical indexes of peaks   (relative to series)
    """

    n_time_steps = series.shape[0]
    n_intervals = n_time_steps / interval_len_in_steps

    # make intervals to identify peaks and valleys in price normalized by the mean of the interval
    n_intervals_floor = math.floor(n_intervals)
    interval_idxs = []
    for i in range(n_intervals_floor):

        # if NOT last interval
        if i < n_intervals_floor - 1:

            if (i + 1) * interval_len_in_steps > n_time_steps:
                interval_idxs.append((i * interval_len_in_steps, n_time_steps))
                continue

            interval_idxs.append((i * interval_len_in_steps, (i + 1) * interval_len_in_steps))

        # last interval... just combine the last whole interval and whats left after
        else:
            # handles some seconds with no trades aka no price.... shouldn't be a problem after price getting update
            if i * interval_len_in_steps > n_time_steps:
                print('------ last interval made early ... indicates data issues ------', flush=True)
                continue  # if this condition is met then the last interval was handled in the last iteration

            interval_idxs.append((i * interval_len_in_steps, n_time_steps))

    # append these to each interval for peak / valley finding to let us find edge peaks / valleys
    peak_finding_edge_array = np.zeros(min_peak_dist)  # append cause scipy.find_peaks no do edge cases
    valley_finding_edge_array = np.ones(min_peak_dist) * 1000000  # append cause scipy.find_peaks no do edge cases

    peak_idxs = np.array([], dtype=int)
    valley_idxs = np.array([], dtype=int)

    last_peak_idx = -min_peak_dist - 1  # so we can find a peak / valley at the first point in the interval
    last_valley_idx = -min_peak_dist - 1  # so we can find a peak / valley at the first point in the interval

    # loop through each days prices, normalizing the using the mean for the interval
    for start_idx, end_idx in interval_idxs:
        sub_series = series.iloc[start_idx:end_idx]
        avg_price = sub_series.mean()  # NOTE AVERAGE PRICE TAKEN BEFORE APPENDING EDGE ARRAYS

        # append edge arrays for peak / valley finding
        peak_finding_series = np.concatenate((peak_finding_edge_array, sub_series, peak_finding_edge_array), 0)
        valley_finding_series = np.concatenate((valley_finding_edge_array, sub_series, valley_finding_edge_array), 0)

        # make prices relative to the mean
        peak_finding_series = peak_finding_series / avg_price
        valley_finding_series = -valley_finding_series / avg_price  # note the intentional sign flip for vallies

        interval_peak_idxs = signal.find_peaks(peak_finding_series,
                                               distance=min_peak_dist,
                                               prominence=peak_prominence)[0]

        interval_valley_idxs = signal.find_peaks(valley_finding_series,
                                                 distance=min_peak_dist,
                                                 prominence=peak_prominence)[0]

        ### offset for observations added for edge detection on peaks / valleys
        interval_peak_idxs = start_idx + interval_peak_idxs - min_peak_dist
        interval_valley_idxs = start_idx + interval_valley_idxs - min_peak_dist

        # price going down case... the prior interval vally leads into the first peak in our current interval
        if interval_peak_idxs.shape[0] != 0:  # if there is no peak then theres no problem
            # if too close then thats no good
            if (interval_peak_idxs[0] - last_valley_idx) < min_peak_dist / 3:
                # so we delete the valley from the last interval and the first peak from this interval
                np.delete(valley_idxs[-1])
                np.delete(interval_peak_idxs[0])

            # if there is a peak left in this interval concatenate it to the valid peak indexes
            if interval_peak_idxs.shape[0] != 0:
                peak_idxs = np.concatenate([peak_idxs, interval_peak_idxs])

        # price going up case... the prior interval peak leads into the valley of our current interval
        if interval_valley_idxs.shape[0] != 0:  # if there is no valley then theres no problem
            # if there is a peak and valley nearby this maybe okay.. check if they are too close
            if (interval_valley_idxs[0] - last_peak_idx) < min_peak_dist / 3:
                # so we delete the peak from the last interval and the first valley from this interval
                np.delete(peak_idxs[-1])
                np.delete(interval_valley_idxs[0])

            # if there is a valley left in this interval concatenate it to the valid valley indexes
            if interval_valley_idxs.shape[0] != 0:
                valley_idxs = np.concatenate([valley_idxs, interval_valley_idxs])

    if len(valley_idxs) == 0 or len(peak_idxs) == 0:
        print(f"interval missing a valley or peak -- algos.targets.py -- get_peak_and_valley_idxs_in_intervals \n" * 10,
              flush=True)
        print(f"put this here because I don't think this will happen but if it does built a price min/max output",
              flush=True)
    # TODO: ^^^^ the above, busy now but this is a ###PAUL_Cleanup must do

    return valley_idxs, peak_idxs


def make_peaks_vallies_to_alternating_buy_sell_idxs(series, buy_idxs, sell_idxs):
    """if signal may appear as buy, sell, sell, sell, buy   --transform-->   buy, sell, buy

    input:
        series    (pd.series and np.array??? maybe that later)
        buy_idxs  (np.array): example:  [0,  500]
        sell_idxs (np.array): example: [110, 300]

    output:
        buy_idxs  (np.array): example:  [0,  500]
        sell_idxs (np.array): example: [index which price is at a max between 110 and 300 as they are between
                                        the two buying indicies ]
    """

    # index for how far into the buy / sell array of idicies we are
    i_in_buys = 0
    i_in_sells = 0

    # set initial index of where we are in the buy / sell arrays
    buy_idx = buy_idxs[i_in_buys]
    sell_idx = sell_idxs[i_in_sells]

    # to find the proper min buy point and max sell point in a str
    # if there 3 valleys between 2 peaks (rare) we pick the minimum valley
    buys_under_consideration = []
    sells_under_consideration = []
    prices_for_buys = []
    prices_for_sells = []
    buy_price_to_idx_dict = {}
    sell_price_to_idx_dict = {}

    # final list to append the correct buy sell point in any consecutive runs
    alternating_buy_idxs = []
    alternating_sell_idxs = []

    # number of candidates... needed to end while loops
    n_buy_idxs = buy_idxs.shape[0]
    n_sell_idxs = sell_idxs.shape[0]

    whose_turn = 'buy' if buy_idx < sell_idx else 'sell'

    # then loop through all the idxs
    while i_in_buys < n_buy_idxs or i_in_sells < n_sell_idxs:
        if whose_turn == 'buy':
            whose_turn = 'sell'
            # start looking for buys... the current sell idx is higher than the buy
            while buy_idx < sell_idx:
                # get the buy idx
                buy_idx = int(buy_idx)
                buy_price = series[buy_idx]

                buys_under_consideration.append(buy_idx)
                prices_for_buys.append(buy_price)
                buy_price_to_idx_dict[buy_price] = buy_idx

                i_in_buys += 1

                try:
                    buy_idx = buy_idxs[i_in_buys]
                except IndexError:
                    if i_in_buys == n_buy_idxs:  # which will locate well past the end
                        buy_idx = max(sell_idxs) + 1_000_000_000_000
                        break

            if len(prices_for_buys) != 0:
                # compare consecutive valley / buys to see which is the lowest
                optimal_buy_price = min(prices_for_buys)
                optimal_buy_idx = buy_price_to_idx_dict[optimal_buy_price]
                alternating_buy_idxs.append(optimal_buy_idx)

                # clear out lists
                buys_under_consideration.clear()
                prices_for_buys.clear()
                buy_price_to_idx_dict = {}

        elif whose_turn == 'sell':
            whose_turn = 'buy'
            # now the next sell idx should be less than the buy_idx
            while sell_idx < buy_idx:
                sell_idx = int(sell_idx)
                sell_price = series[sell_idx]

                sells_under_consideration.append(sell_idx)
                prices_for_sells.append(sell_price)
                sell_price_to_idx_dict[sell_price] = sell_idx

                i_in_sells += 1

                try:
                    sell_idx = sell_idxs[i_in_sells]
                except IndexError:
                    if i_in_sells == n_sell_idxs:  # which will locate 1 past the end
                        sell_idx = max(buy_idxs) + 1_000_000_000
                        break

            if len(prices_for_sells) != 0:
                optimal_sell_price = max(prices_for_sells)
                optimal_sell_idx = sell_price_to_idx_dict[optimal_sell_price]
                alternating_sell_idxs.append(optimal_sell_idx)

                # clear out lists
                sells_under_consideration.clear()
                prices_for_sells.clear()
                sell_price_to_idx_dict = {}

    alternating_buy_idxs = np.array(alternating_buy_idxs)
    alternating_sell_idxs = np.array(alternating_sell_idxs)

    return alternating_buy_idxs, alternating_sell_idxs


def get_datetimes_for_buy_sell_idxs(series, buy_ilocs, sell_ilocs):
    """given numerical indicies for each series return the corresponding date time index
    """

    buy_idxs_datetime = series.index[buy_ilocs]
    sell_idxs_datetime = series.index[sell_ilocs]

    return buy_idxs_datetime, sell_idxs_datetime


def make_targets_from_buy_sell_idxs(series, buy_ilocs, sell_ilocs, **target_params):
    """makes a target series ranging from -1 to 1 based on the prices between a valley and peak

    input:
        - series (pd.series): of prices with a pd.datetime index
        - buy_ilocs (np.array): of a counting indicies for buys  [ 3, 10, 100]
        - buy_ilocs (np.array): of a counting indicies for buys  [ 5, 33, 169]

        - NOTES:
            - buy and sell idxs must alternate or things get whacky

    - Development Note for Later (perfection thing)
      - because of the dumb way you did this you have to throw out the last point if it is a sell.
        should have implemented a generator that yields the next buy/ then sell, slowly walking along from
        buy to sell to buy to sell. scaling one segment at a time.

    """
    # series must be continuous because we rely on that many times through the process

    targets = pd.Series(dtype=float)  # series to fill up with targets
    n_transacts = buy_ilocs.shape[0] + sell_ilocs.shape[0]

    buy_ilocs = list(buy_ilocs)
    sell_ilocs = list(sell_ilocs)

    buy_iloc = buy_ilocs[0]
    sell_iloc = sell_ilocs[0]

    whose_turn = 'buy' if buy_iloc < sell_iloc else 'sell'

    iter_count = 0
    while len(buy_ilocs) > 0 or len(sell_ilocs) > 0:
        iter_count += 1
        if whose_turn == 'buy':
            whose_turn = 'sell'
            buy_iloc = buy_ilocs.pop(0)
            if len(sell_ilocs) > 0:
                sell_iloc = sell_ilocs[0]
            elif len(sell_ilocs) == 0:
                pass  # keep the old value of sell_iloc (as that will still be the high of the upcoming interval)
            else:
                import pdb; pdb.set_trace; raise RuntimeError
            start_iloc = buy_iloc
            end_iloc = sell_iloc
        elif whose_turn == 'sell':
            whose_turn = 'buy'
            sell_iloc = sell_ilocs.pop(0)
            if len(buy_ilocs) > 0:
                buy_iloc = buy_ilocs[0]
            elif len(buy_ilocs) == 0:
                pass  # keep the old value of buy_iloc (as that will still be the low of the upcoming interval)
            else:
                import pdb; pdb.set_trace; raise RuntimeError
            start_iloc = sell_iloc
            end_iloc = buy_iloc

        # low = series[buy_iloc]   # ###PAUL investiage whether this is causing issues... seems like rarely the buy
        # iloc isn't the min and the sell iloc isn't the max. fixed by taking min and  max of series
        # high = series[sell_iloc]
        if iter_count == 1:  # we are at the beginning, append early prices
            series_to_normalize = series.iloc[: end_iloc]
        elif iter_count == n_transacts:  # we are on the last transaction include all to the end
            series_to_normalize = series.iloc[start_iloc:]
        else:
            series_to_normalize = series.iloc[start_iloc: end_iloc]

        low = min(series_to_normalize)
        high = max(series_to_normalize)

        mid_price = (low + high) / 2
        half_spread = (high - low) / 2
        normalized_sub_series = (series_to_normalize - mid_price) / half_spread

        # ###PAUL TODO: toggle normalization... all prices between each interval (probably no use in this tbh but can't hurt to run)
        # ###PAUL_toggle_normalize_signal ---- (un)comment the single line below
        # normalized_sub_series = (normalized_sub_series - normalized_sub_series.mean()) / normalized_sub_series.std()
        targets = pd.concat((targets, normalized_sub_series))

    if 'pd_ewm_alpha' in target_params and target_params['pd_ewm_alpha'] is not None:
        targets = targets.ewm(alpha=target_params['pd_ewm_alpha']).mean()
        targets.fillna(method='bfill', inplace=True)
        targets.fillna(method='ffill', inplace=True)
    if 'smoothing_window' in target_params and target_params['smoothing_window'] is not None:
        targets = targets.rolling(target_params['smoothing_window']).mean()
        targets.fillna(method='bfill', inplace=True)
        targets.fillna(method='ffill', inplace=True)

    return targets


def make_targets(series, **target_params):
    """wraps the target making process into one function and returns the output in a nice format"""

    valley_idxs, peak_idxs = \
        get_peak_and_valley_idxs_in_intervals(series=series,
                                              min_peak_dist=target_params['min_peak_dist'],
                                              peak_prominence=target_params['peak_prominence'],
                                              interval_len_in_steps=target_params['interval_len_in_steps'], )

    buy_idxs, sell_idxs = make_peaks_vallies_to_alternating_buy_sell_idxs(series=series,
                                                                          buy_idxs=valley_idxs,
                                                                          sell_idxs=peak_idxs, )

    buy_datetimes, sell_datetimes = get_datetimes_for_buy_sell_idxs(series=series,
                                                                    buy_ilocs=buy_idxs,
                                                                    sell_ilocs=sell_idxs, )

    targets = make_targets_from_buy_sell_idxs(series=series,
                                              buy_ilocs=buy_idxs,
                                              sell_ilocs=sell_idxs,
                                              **target_params,  # ##PAUUL TODO vector multiple params per entry
                                              )

    targets.index = pd.to_datetime(targets.index)

    buy_prices = series.loc[buy_datetimes]
    sell_prices = series.loc[sell_datetimes]

    ideal_buy_sell_dict = {'buy': {'idxs': buy_idxs, 'datetimes': buy_datetimes, 'prices': buy_prices, },
                           'sell': {'idxs': sell_idxs, 'datetimes': sell_datetimes, 'prices': sell_prices, },
                           }

    return targets, ideal_buy_sell_dict


def split_train_test(x, p_train, p_test, p_validate):
    """ starts from the beginning of the data set and grabs a proprion of the data set for each `p_*` input
    """

    # will allow less than 1, if we want to save data for later, later, later
    assert (1 >= p_train + p_test + p_validate)
    len_x = len(x)

    train_end_iloc = int((p_train) * len_x)
    test_end_iloc = int((p_train + p_test) * len_x)
    validate_end_iloc = int((p_train + p_test + p_validate) * len_x)

    x_train = x.iloc[:train_end_iloc]
    x_test = x.iloc[train_end_iloc:test_end_iloc]
    x_validate = x.iloc[test_end_iloc:validate_end_iloc]

    return {'x': {'train': x_train, 'test': x_test, 'validate': x_validate}}


# ###PAUL TODO: this file is in big need of an iloc vs dti clairity cleanup


def analyze_signal(prices, signal_dict, signal_series_name='signal', target_series_name='y_train_rti'):

    if type(prices) == pd.DataFrame:
        prices = prices['vwap']
    # elif type(prices) == pd.Series:

    signal_analysis = {}

    # ### y_to_y_hat_corr
    #
    start_dt = max(min(signal_dict[target_series_name].index), min(signal_dict[signal_series_name].index))
    end_dt = min(max(signal_dict[target_series_name].index), max(signal_dict[signal_series_name].index))

    target = signal_dict[target_series_name].loc[start_dt:end_dt]
    pred = signal_dict[signal_series_name].loc[start_dt:end_dt]
    vwap = prices.loc[start_dt: end_dt]

    assert(target.index.equals(pred.index))
    assert(target.index.equals(vwap.index))
    y_to_y_hat_corr = np.corrcoef(target, pred)
    signal_analysis['y_to_y_hat_corr'] = y_to_y_hat_corr

    # ### differences correlation
    #
    early_target = target.iloc[:-1]
    later_target = target.iloc[1:]
    early_target.index = later_target.index
    target_diff = later_target - early_target

    early_pred = pred.iloc[:-1]
    later_pred = pred.iloc[1:]
    early_pred.index = later_pred.index
    pred_diff = later_pred - early_pred

    y_to_y_hat_deltas_corr = np.corrcoef(target_diff, pred_diff)
    signal_analysis['y_to_y_hat_deltas_corr'] = y_to_y_hat_deltas_corr

    n = 60
    returns_1_hr = vwap.pct_change(n).fillna(0).shift(-n).fillna(0)
    y_to_1_hr_price_return_corr = np.corrcoef(target, returns_1_hr)
    signal_analysis['y_to_1_hr_price_return_corr'] = y_to_1_hr_price_return_corr

    y_hat_to_1_hr_price_return_corr = np.corrcoef(pred, returns_1_hr)
    signal_analysis['y_hat_to_1_hr_price_return_corr'] = y_hat_to_1_hr_price_return_corr

    n = 24 * 60
    returns_1_day = vwap.pct_change(n).fillna(0).shift(-n).fillna(0)
    y_to_1_day_price_return_corr = np.corrcoef(target, returns_1_day)
    signal_analysis['y_to_1_day_price_return_corr'] = y_to_1_day_price_return_corr

    y_hat_to_1_day_price_return_corr = np.corrcoef(pred, returns_1_day)
    signal_analysis['y_hat_to_1_day_price_return_corr'] = y_hat_to_1_day_price_return_corr

    n = 10 * 24 * 60
    returns_10_day = vwap.pct_change(n).fillna(0).shift(-n).fillna(0)

    y_hat_to_10_day_price_return_corr_str = np.corrcoef(pred, returns_10_day)
    signal_analysis['y_hat_to_10_day_price_return_corr_str'] = y_hat_to_10_day_price_return_corr_str

    # reset start and end for new increasingly sparse comparisons
    early_pred = pred[:-15]
    later_pred = pred.iloc[15:]
    early_pred.index = later_pred.index
    pred_diff = later_pred - early_pred
    start_dt = max(min(pred_diff.index), min(returns_1_hr.index))
    end_dt = min(max(pred_diff.index), max(returns_1_hr.index))

    y_hat_15m_diff____1_hr_return____corr = np.corrcoef(pred_diff.loc[start_dt: end_dt],
                                                       returns_1_hr.loc[start_dt: end_dt])
    signal_analysis['y_hat_15m_diff____1_hr_return____corr'] = y_hat_15m_diff____1_hr_return____corr

    # reset start and end for new increasingly sparse comparisons
    early_pred = pred[:-60]
    later_pred = pred.iloc[60:]
    early_pred.index = later_pred.index
    pred_diff = later_pred - early_pred
    start_dt = max(min(pred_diff.index), min(returns_1_hr.index))
    end_dt = min(max(pred_diff.index), max(returns_1_hr.index))

    y_hat_1h_diff____1_hr_return____corr = np.corrcoef(pred_diff.loc[start_dt: end_dt],
                                                       returns_1_hr.loc[start_dt: end_dt])
    signal_analysis['y_hat_1h_diff____1_hr_return____corr'] = y_hat_1h_diff____1_hr_return____corr

    # reset start and end for new increasingly sparse comparisons
    early_pred = pred[:-24 * 60]
    later_pred = pred.iloc[24 * 60:]
    early_pred.index = later_pred.index
    pred_diff = later_pred - early_pred
    start_dt = max(min(pred_diff.index), min(returns_1_day.index))
    end_dt = min(max(pred_diff.index), max(returns_1_day.index))

    y_hat_1d_diff____1d_return____corr = np.corrcoef(pred_diff.loc[start_dt: end_dt],
                                                     returns_1_day.loc[start_dt: end_dt])
    signal_analysis['y_hat_1d_diff____1d_return____corr'] = y_hat_1d_diff____1d_return____corr

    # import pdb;
    # pdb.set_trace()

    return signal_analysis


def print_signal_analysis(signal_analysis):
    print(f"signal analysis: ")
    y_to_y_hat_corr_str = str(signal_analysis['y_to_y_hat_corr']).replace('\n', '\n\t')
    print(f" - y_to_y_hat_corr:                    \n \t{y_to_y_hat_corr_str}")

    y_to_y_hat_deltas_corr_str = str(signal_analysis['y_to_y_hat_deltas_corr']).replace('\n', '\n\t')
    print(f" - y_to_y_hat_deltas_corr:             \n \t{y_to_y_hat_deltas_corr_str}")

    y_to_1_hr_price_return_corr_str = str(signal_analysis['y_to_1_hr_price_return_corr']).replace('\n', '\n\t')
    print(f" - y_to_1_hr_price_return_corr:        \n \t{y_to_1_hr_price_return_corr_str}")

    y_hat_to_1_hr_price_return_corr_str = str(signal_analysis['y_hat_to_1_hr_price_return_corr']).replace('\n', '\n\t')
    print(f" - y_hat_to_1_hr_price_return_corr:    \n \t{y_hat_to_1_hr_price_return_corr_str}")

    y_to_1_day_price_return_corr_str = str(signal_analysis['y_to_1_day_price_return_corr']).replace('\n', '\n\t')
    print(f" - y_to_1_day_price_return_corr :      \n \t{y_to_1_day_price_return_corr_str}")

    y_hat_to_1_day_price_return_corr_str = str(signal_analysis['y_hat_to_1_day_price_return_corr']).replace('\n',
                                                                                                            '\n\t')
    print(f" - y_hat_to_1_day_price_return_corr:   \n \t{y_hat_to_1_day_price_return_corr_str}")

    y_hat_15m_diff____1_hr_return____corr = str(signal_analysis['y_hat_15m_diff____1_hr_return____corr']).replace('\n',
                                                                                                                '\n\t')
    print(f" - y_hat_15m_diff____1_hr_return____corr:   \n \t{y_hat_15m_diff____1_hr_return____corr}")

    y_hat_1h_diff____1_hr_return____corr = str(signal_analysis['y_hat_1h_diff____1_hr_return____corr']).replace('\n',
                                                                                                                '\n\t')
    print(f" - y_hat_1h_diff____1_hr_return____corr:   \n \t{y_hat_1h_diff____1_hr_return____corr}")
    #
    # y_hat_1d_diff____1d_return____corr = str(signal_analysis['y_hat_1d_diff____1d_return____corr']).replace('\n',
    #                                                                                                         '\n\t')
    # print(f" - y_hat_1d_diff____1d_return____corr:   \n \t{y_hat_1d_diff____1d_return____corr}")
    #
    # y_hat_to_10_day_price_return_corr_str = str(signal_analysis['y_hat_to_10_day_price_return_corr_str']).replace('\n',
    #                                                                                                         '\n\t')
    # print(f" - y_hat_to_10_day_price_return_corr_str:   \n \t{y_hat_to_10_day_price_return_corr_str}")
