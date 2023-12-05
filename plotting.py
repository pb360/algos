# ### local imports
from algos.utils import convert_date_format

import sys

sys.path.insert(0, '..')  # for local imports from the top directory

from algos.utils import downsample_pd_series, convert_date_format

from copy import deepcopy
import math
import numpy as np
import pandas as pd

from plotly.subplots import make_subplots
import plotly.graph_objects as go


# ###PAUL TODO: into plot_framework() and then delete the below, being kept for reference only
# ###PAUL TODO: move ideal bottom/peak time (note renameing from buy/sell) plotting functionality into plot framework
# plots price with points for buy or sell on the price timeseries
def plot_price_with_buy_sell_times_on_price(prices, buy_idxs, sell_idxs, p_start=0.0, p_finish=0.1):
    n = prices.shape[0]

    start_idx = math.floor(n * (p_start))
    end_idx = math.floor(n * (p_finish))

    # label what each of the timeseries are
    x_lab = 'time'
    y_top_lab = 'price'

    # isolating actual data that will be provided to plots
    x = prices.index[start_idx:end_idx]
    y_top = prices[start_idx:end_idx]

    # isolating proportion to plot buy and sell idxs
    #
    # early cut
    buy_idxs_t = buy_idxs[start_idx < buy_idxs]
    sell_idxs_t = sell_idxs[start_idx < sell_idxs]

    # late cut
    buy_idxs_t = buy_idxs_t[buy_idxs_t < end_idx]
    sell_idxs_t = sell_idxs_t[sell_idxs_t < end_idx]

    # comparing using indicies to index col labels
    buy_times = prices.index[buy_idxs_t.astype(int)]
    buy_prices = prices.iloc[buy_idxs_t.astype(int)]
    sell_times = prices.index[sell_idxs_t.astype(int)]
    sell_prices = prices.iloc[sell_idxs_t.astype(int)]

    fig = make_subplots(rows=1, cols=1)

    # top (price line)
    fig.add_trace(go.Scattergl(x=x, y=y_top, name=y_top_lab),
                  row=1,
                  col=1
                  )

    # buy points
    fig.add_trace(go.Scattergl(mode='markers',
                               marker=dict(color='chartreuse', size=13),
                               x=buy_times, y=buy_prices, name=y_top_lab),
                  row=1,
                  col=1
                  )

    # sell points
    fig.add_trace(go.Scattergl(mode='markers',
                               marker=dict(color='Red', size=13),
                               x=sell_times, y=sell_prices, name=y_top_lab),
                  row=1,
                  col=1
                  )

    fig.update_layout(height=800,
                      width=800,
                      xaxis=dict(range=[min(x), max(x)]),
                      xaxis2=dict(range=[min(x), max(x)]),
                      xaxis3=dict(range=[min(x), max(x)]),
                      yaxis=dict(range=[min(y_top), max(y_top)]),
                      title_text="Price and MACD",
                      )

    return fig


# ### PAUL TODO: differentiate between `signal_dict` and `framework_results` in the input.
# TODO: if signal_dict is given use current plotting functionality. If framework_results then color based on position...
def plot_framework(plot_requests,
                   prices,
                   signal_dict=None,
                   framework_results=None,
                   downsample_n=50_000,
                   ideal_bottoms=None,
                   ideal_tops=None, ):
    """ plots price with short/neutral/long points up top, on the bottom, the portfolio timeseries
    ###PAUL TODO: this should plot based off of a primary series, for now using preds will suffice
    """

    if framework_results is None:
        if signal_dict is None:
            print(f"must supply atleast one `signal_dict` or `framework_results`")
            raise ValueError
        framework_results = signal_dict
        plot_signal_or_framework = 'signal'
    else:
        if signal_dict is not None:
            print(f"can only supply one `signal_dict` or `framework_results` -- both were provided")
        plot_signal_or_framework = 'framework'

    # make figure
    fig = make_subplots(rows=2, cols=1, specs=[[{"secondary_y": True}],
                                               [{"secondary_y": False}]])

    # these will always be in framework_results (as they are created at the model iteration level)
    preds = framework_results['preds']
    prices = prices.loc[preds.index]

    # ### MAKE AND ASSERT ---- time series indicies are equal
    #
    # ###PAUL TODO: # prices should contain all ... bring prices down,
    # ###PAUL TODO: # assert (preds.index.equals(preds.index))

    og_pred_len = preds.shape[0]
    # ###PAUL TODO: clean up to allow start or end and just goo all the way to the corresponding side
    if 'start_date' in plot_requests and 'end_date' in plot_requests and \
            plot_requests['start_date'] is not None and plot_requests['end_date'] is not None:
        start_date = convert_date_format(plot_requests['start_date'], output_type='pandas')
        end_date = convert_date_format(plot_requests['end_date'], output_type='pandas')
        start_iloc = np.argmax(preds.index == start_date)
        end_iloc = np.argmax(preds.index == end_date)
    else:
        if 'p_start' in plot_requests and 'p_end' in plot_requests and \
                plot_requests['p_start'] is not None and plot_requests['p_end'] is not None:
            p_start = plot_requests['p_start']
            p_finish = plot_requests['p_end']
        else:
            p_start = 0
            p_finish = 1
        # get the iloc start and end of the subset
        start_iloc = math.floor(og_pred_len * p_start)
        end_iloc = math.floor(og_pred_len * p_finish)

    # subset preds and get prices to match the requested portion of the interval # ###PAUL TODO: replace with main focus series eventually
    plot_preds = preds.iloc[start_iloc: end_iloc]
    non_downsampled_subsetted_plot_dti = deepcopy(plot_preds.index)
    subset_pred_len = plot_preds.shape[0]
    if downsample_n > subset_pred_len:
        downsample_n = subset_pred_len

    # ### TOP ROW OF PLOT
    #
    #
    if plot_requests['prices']:  # TOP: (price line)
        plot_prices = prices[non_downsampled_subsetted_plot_dti]
        plot_prices, downsampled_price_ilocs = downsample_pd_series(series=plot_prices, downsample_n=downsample_n)

        if plot_signal_or_framework == 'framework':
            side_to_actions_dict = {'short': ['short', 'exit_short'],
                                    'long': ['long', 'exit_long'], }
            side_to_colors_dict = {'short': 'red',
                                   'long': 'green', }

            position_timespan_by_side_dict = {'short': [], 'long': []}
            position_price_series_by_side = {'short': [], 'long': []}

            for side in ['short', 'long']:
                print(f"SIDE: {side}")
                actions = side_to_actions_dict[side]

                num_starts = len(framework_results['transacts'][actions[0]]['datetimes'])
                num_stops = len(framework_results['transacts'][actions[1]]['datetimes'])
                num_trades = min(num_starts, num_stops)

                for i in range(num_trades):
                    # print(f" - i: {i}")
                    start_trade = framework_results['transacts'][actions[0]]['datetimes'][i]
                    end_trade = framework_results['transacts'][actions[1]]['datetimes'][i]
                    position_timespan_by_side_dict[side].append([start_trade, end_trade])

                    position_dti_mask = np.logical_and(start_trade <= plot_prices.index, plot_prices.index <= end_trade)
                    iters_positin_prices_series = plot_prices[position_dti_mask]
                    dtis = iters_positin_prices_series.index

                    if i == 0:
                        position_price_series_by_side[side] = iters_positin_prices_series
                    else:
                        position_price_series_by_side[side] = pd.concat([position_price_series_by_side[side],
                                                                         iters_positin_prices_series])

                    # plot_prices = plot_prices.drop(index=dtis)
                    plot_prices.loc[dtis] = np.NaN

                    fig.add_trace(go.Scattergl(x=iters_positin_prices_series.index,
                                               y=iters_positin_prices_series.values,
                                               marker=dict(color=side_to_colors_dict[side], size=2, opacity=1, ),
                                               showlegend=False,
                                               ),
                                  row=1, col=1,
                                  )

        fig.add_trace(go.Scattergl(x=plot_prices.index, y=plot_prices.values, name='price',
                                   marker=dict(color='black', size=2, opacity=1, ),
                                   connectgaps=False),
                      row=1, col=1, )

    if plot_requests['port_val_ts']:  # TOP - SECONDARY AXIS: port value
        try:
            plot_port_vals = framework_results['port_value_ts'][
                np.logical_and(non_downsampled_subsetted_plot_dti[0] <= framework_results['port_value_ts'].index,
                               framework_results['port_value_ts'].index <= non_downsampled_subsetted_plot_dti[-1])
            ]

            plot_port_vals, downsampled_port_val_ilocs = downsample_pd_series(series=plot_port_vals,
                                                                              downsample_n=downsample_n)
            fig.add_trace(go.Scattergl(x=plot_port_vals.index, y=plot_port_vals, name='port_val'),
                          row=1, col=1, secondary_y=True)
        except KeyError:
            print(f"NOT FOUND: framework_results['port_value_ts'] ---- likely passed 1st stage:  `signal_dict` ")

    if plot_requests['transact_times']:  # TOP - PRIMARY AXIS
        try:
            # ###PAUL TODO: verify ilocs of these transactions (should match up with smoothed preds and be correct)
            #         TODO: could do this with the transacts dict of one or two observations with dates, but manually
            # confirmed for now that this method is working correctly
            # ### transactions plot data:  [long, short, exit_long, exit_short]
            #
            long_idxs = np.array(deepcopy(framework_results['transacts']['long']['idxs']))
            short_idxs = np.array(deepcopy(framework_results['transacts']['short']['idxs']))
            exit_long_idxs = np.array(deepcopy(framework_results['transacts']['exit_long']['idxs']))
            exit_short_idxs = np.array(deepcopy(framework_results['transacts']['exit_short']['idxs']))

            # cut to match proportion requested
            long_idxs = long_idxs[np.logical_and(start_iloc < long_idxs, long_idxs < end_iloc)]
            short_idxs = short_idxs[np.logical_and(start_iloc < short_idxs, short_idxs < end_iloc)]
            exit_long_idxs = exit_long_idxs[np.logical_and(start_iloc < exit_long_idxs, exit_long_idxs < end_iloc)]
            exit_short_idxs = exit_short_idxs[np.logical_and(start_iloc < exit_short_idxs, exit_short_idxs < end_iloc)]

            # comparing using indicies to index col labels
            long_times = prices.index[long_idxs]
            long_prices = prices.iloc[long_idxs]
            short_times = prices.index[short_idxs]
            short_prices = prices.iloc[short_idxs]
            exit_long_times = prices.index[exit_long_idxs]
            exit_long_prices = prices.iloc[exit_long_idxs]
            exit_short_times = prices.index[exit_short_idxs]
            exit_short_prices = prices.iloc[exit_short_idxs]

            # TOP: long points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='forestgreen', size=14),
                                       x=long_times, y=long_prices, name='longs'),
                          row=1, col=1, secondary_y=False)

            # TOP: short points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='crimson', size=14),
                                       x=short_times, y=short_prices, name='shorts'),
                          row=1, col=1, secondary_y=False)

            # TOP: exit long points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='forestgreen', size=15, opacity=0.75, symbol='x'),
                                       x=exit_long_times, y=exit_long_prices, name='exit longs'),
                          row=1, col=1, secondary_y=False)

            # TOP: exit short points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='crimson', size=15, opacity=0.75, symbol='x'),
                                       x=exit_short_times, y=exit_short_prices, name='exit shorts'),
                          row=1, col=1)
        except KeyError:
            print(f"NOT FOUND: framework_results['transacts'] ---- likely passed 1st stage:  `signal_dict` ")


    # ###PAUL TODO: support plotting of ideal top / bottom's from target making
    #         TODO: not worth the effort for now... need to handle this in RTI rolling backtest
    if plot_requests['ideal_top_bottoms']:
        try:
            ideal_buy_sell_dict = framework_results['ideal_buy_sell_dict']
            start_date = non_downsampled_subsetted_plot_dti[0]
            end_date = non_downsampled_subsetted_plot_dti[-1]

            peaks_in_plot_time_mask = np.logical_and(start_date < ideal_buy_sell_dict['buy']['datetimes'],
                                                     ideal_buy_sell_dict['buy']['datetimes'] < end_date)

            buy_in_ilocs = ideal_buy_sell_dict['buy']['idxs'][peaks_in_plot_time_mask]
            buy_in_dates = ideal_buy_sell_dict['buy']['datetimes'][peaks_in_plot_time_mask]
            buy_in_prices = ideal_buy_sell_dict['buy']['prices'][peaks_in_plot_time_mask]
            sell_in_ilocs = ideal_buy_sell_dict['sell']['idxs'][peaks_in_plot_time_mask]
            sell_in_dates = ideal_buy_sell_dict['sell']['datetimes'][peaks_in_plot_time_mask]
            sell_in_prices = ideal_buy_sell_dict['sell']['prices'][peaks_in_plot_time_mask]

            # TOP: long points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='forestgreen', size=13),
                                       x=buy_in_dates, y=buy_in_prices, name='longs'),
                          row=1, col=1, secondary_y=False)

            # TOP: short points
            fig.add_trace(go.Scattergl(mode='markers',
                                       marker=dict(color='crimson', size=13),
                                       x=sell_in_dates, y=sell_in_prices, name='shorts'),
                          row=1, col=1, secondary_y=False)
        except KeyError:
            print(f"ideal tops and bottoms must be added to signal_dict / framework_results manually as of now")

    # ### BOTTOM ROW OF PLOT
    #
    #
    if plot_requests['preds']:  # BOTTOM: preds value ###PAUL plot smoothed vs not smoothed
        plot_preds, downsampled_pred_ilocs = downsample_pd_series(series=plot_preds, downsample_n=downsample_n)
        fig.add_trace(go.Scattergl(x=plot_preds.index, y=plot_preds, name='model_preds', opacity=0.5),
                      row=2, col=1)

    if plot_requests['smoothed_preds']:  # BOTTOM: preds value ###PAUL plot smoothed vs not smoothed
        smoothed_preds = framework_results['smoothed_preds']
        plot_smoothed_preds = smoothed_preds[non_downsampled_subsetted_plot_dti]
        plot_smoothed_preds, downsampled_smoothed_preds_ilocs = \
            downsample_pd_series(series=plot_smoothed_preds, downsample_n=downsample_n)
        fig.add_trace(go.Scattergl(x=plot_smoothed_preds.index, y=plot_smoothed_preds, name='smoothed_preds'),
                      row=2, col=1)

    if plot_requests['signal']:  # BOTTOM: preds value ###PAUL plot smoothed vs not smoothed
        print(f"PLOTTING THE SIGNAL")
        signal = framework_results['signal']
        plot_signal = signal[non_downsampled_subsetted_plot_dti]
        plot_signal, downsampled_signal_ilocs = downsample_pd_series(series=plot_signal, downsample_n=downsample_n)
        fig.add_trace(go.Scattergl(x=plot_signal.index, y=plot_signal, name='signal'),
                      row=2, col=1)

    if plot_requests['y_train_rti']:  # BOTTOM: port value  ###PAUL plot smoothed vs not smoothed
        y_train_rti = framework_results['y_train_rti']
        plot_y_train_rti = y_train_rti[np.logical_and(non_downsampled_subsetted_plot_dti[0] <= y_train_rti.index,
                                                      y_train_rti.index <= non_downsampled_subsetted_plot_dti[-1])]

        len_plot_y_train_rti = plot_y_train_rti.shape[0]
        downsample_n_temp = len_plot_y_train_rti if downsample_n > len_plot_y_train_rti else downsample_n
        plot_y_train_rti, downsampled_y_train_rti_ilocs = downsample_pd_series(series=plot_y_train_rti,
                                                                               downsample_n=downsample_n_temp)
        fig.add_trace(go.Scattergl(x=plot_y_train_rti.index, y=plot_y_train_rti, name='y_train_rti'),
                      row=2, col=1)

    # ### plot layout ###PAUL TODO: look into axis labels
    #
    #
    fig.update_layout(height=800,
                      width=800,
                      title_text="TOP: Price with Buys and Sells \n \n BOTTOM: Portfolio Value Over Time",
                      xaxis=dict(range=[min(plot_prices.index), max(plot_prices.index)]),
                      # xaxis2=dict(range=[min(plot_prices.index), max(plot_prices.index)]),
                      # xaxis3=dict(range=[min(plot_prices.index), max(plot_prices.index)]),
                      yaxis=dict(range=[min(plot_prices.values), max(plot_prices.values)]),
                      yaxis2=dict(),  # type='log') if plotting as a log is required
                      )
    
    print('figure created', flush=True)

    # set showlegend property by name of trace
    for trace in fig['data']:
        if (trace['name'] == 'no_legend'): trace['showlegend'] = False

    return fig
