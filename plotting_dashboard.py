# ### local imports
import sys

sys.path.insert(0, '..')  # for local imports from the top directory

from algos.config import params
from algos.feature import get_multiasset_trading_summaries
from algos.plotting import plot_framework

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import pickle

data_dir = params['dirs']['data_dir']
signal_or_framework = 'signal'


# ### bringing in things we may need
#
#
if signal_or_framework == 'signal':
    # signal_dict_name = f"signal_dict____2023_08_01____mlp_rolling____v2"
    # signal_dict_name = f"signal_dict____2023_08_01____mlp_rolling____v4"
    signal_dict_name = f"signal_dict____2023_08_03___mlp_rolling____validate"
    signal_dict_fp = f"{data_dir}pickled_signal_dicts/{signal_dict_name}.pickle"

    # # ### OPENING
    # #
    with open(signal_dict_fp, 'rb') as f:
        signal_dict = pickle.load(f)   # <<<------- COPY PASTE DESIRED VARIABLE HERE


if signal_or_framework == 'framework':
    # ### `framework_results`
    #
    framework_results_name = f"framework_results____0_06_peaks____MSE_loss____on_preds__0_0075_ewm__4_day_rolling_norm____split_0_65__0_15____NO_shuffled_train"
    framework_results_fp = f"{data_dir}pickled_framework_results/{framework_results_name}.pickle"
    # ### OPENING
    #
    with open(framework_results_fp, 'rb') as f:
        framework_results = pickle.load(f)  # <<<------- COPY PASTE DESIRED VARIABLE HERE


# TODO:
# TODO: need to make a function that creates a framework_results dictionary live reading clickhouse... can be lightweight as long as it contains everything in plot request
# TODO: need to make a function that creates a framework_results dictionary live reading clickhouse... can be lightweight as long as it contains everything in plot request
# TODO: need to make a function that creates a framework_results dictionary live reading clickhouse... can be lightweight as long as it contains everything in plot request
# TODO:

plot_requests = {
    # 'start_date': (2023, 5, 1),
    #              'end_date': (2023, 7, 12),
                 'prices': True,
                 'transact_times': False,
                 'preds': False,
                 'smoothed_preds': False,
                 'signal': True,
                 'port_val_ts': False,
                 'y_train_rti': True,
                 'ideal_top_bottoms': False}

temp_vwap_get_configs = {'BTC-TUSD': { # 'desired_features_dict': desired_features_dict,
                                      'exchange': 'binance',
                                      'start_date': (2018, 1, 1),
                                      'end_date': (2023, 7, 18),
                                      'alternative_data_pair': 'BTC-USDT',
                                      'alternative_data_exchange': 'binance',
                                      'alternative_start_date': (2018, 1, 1),
                                      'alternative_end_date': (2023, 2, 15),
                                      }
                         }

vwap_dict = get_multiasset_trading_summaries(temp_vwap_get_configs, columns=['vwap'])

# ### SETTING UP THE DASH APP
#
#
app = dash.Dash(__name__)

# Define your layout
app.layout = html.Div([
    dcc.Graph(id='live-plot'),
    dcc.Interval(id='graph-update', interval=600_000, n_intervals=0)  # Update every 1 second
])


# Define callback to update graph
@app.callback(Output('live-plot', 'figure'),
              [Input('graph-update', 'n_intervals')])
def update_graph(n):
    if signal_or_framework == 'framework':
        fig = plot_framework(plot_requests=plot_requests,
                             prices=vwap_dict['BTC-TUSD']['vwap'],
                             framework_results=framework_results,
                             downsample_n=20_000,
                             ideal_bottoms=None,
                             ideal_tops=None, )
    if signal_or_framework == 'signal':
        fig = plot_framework(plot_requests=plot_requests,
                             prices=vwap_dict['BTC-TUSD']['vwap'],
                             signal_dict=signal_dict,
                             downsample_n=20_000,
                             ideal_bottoms=None,
                             ideal_tops=None, )

    # import
    # go.Figure(data=go.Scatter(x=[1, 2, 3], y=[1, 3, 2]))

    import pickle;
    with open('{data_dir}temp/plotly_graph.pickle', 'wb') as f:
        pickle.dump(fig, f)
        print(f"pickled it")
    return fig

if __name__ == '__main__':
    for port in range(8051, 8100):  # This will try ports from 8051 to 8099
        try:
            app.run_server(debug=False, host="0.0.0.0", port=port)
            break
        except OSError as e:
            if 'address already in use' in str(e):
                continue
            raise