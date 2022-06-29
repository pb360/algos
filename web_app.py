#!/home/paul/miniconda3/envs/web_app/bin/python3 -u
# -*- coding: utf-8 -*-

""" used as a app file so it run anwhere inherently
runs on http://<server_host>:<port>/

"""
# ### utils first due to time zone issues... then other local packages
#
#
import math
from utils import *
import config

# ### pip imports
#
#
from collections import deque
import datetime
import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from plotly.subplots import make_subplots


# ### declarations
#
#
params = config.params

server_host = '24.0.143.55'
port_number = '8050'

timestep = 100  				# number of seconds to "walk" between sucessive plot iterations
plot_time_slice_size = 3600  	# total width in seconds of plot on tape
timestep_wait_time = 1000		# time between sucessive plot iteration updates

ticker = 'BTC-USDT'
start = datetime.date(2021, 1, 10)
end   = datetime.date(2021, 1, 17)

prices = get_data(data_type='price', pair=ticker, date='live', exchange='binance')
prices = prices.fillna(method='ffill')

exp1 = prices.ewm(span=12*60, adjust=False).mean()
exp2 = prices.ewm(span=26*60, adjust=False).mean()

macd = exp1 - exp2
macd_d5 = macd.subtract(macd.shift(5))
macd_d5 = macd_d5.fillna(method='bfill')

macd_d5_buy_vwap = macd_d5['buy_vwap']


# create app
app = dash.Dash(__name__)

app.layout = html.Div(
	[
		dcc.Graph(id = 'live-graph', animate = True),
		dcc.Interval(
			id = 'graph-update',
			interval = timestep_wait_time,
			n_intervals = 0
		),
	]
)


@app.callback(
	Output('live-graph', 'figure'),
	[ Input('graph-update', 'n_intervals') ]
)
def update_graph_scatter(i):
	print(i)
	x = prices.index[i*timestep: i*timestep + plot_time_slice_size]
	y_top = prices['buy_vwap'][i*timestep: i*timestep + plot_time_slice_size]
	y_bottom = macd['buy_vwap'][i*timestep: i*timestep + plot_time_slice_size]
	y_macd_d5 = macd_d5['buy_vwap'][i*timestep: i*timestep + plot_time_slice_size]

	fig = make_subplots(rows=3, cols=1)

	fig.add_trace(
		go.Scatter(x=x, y=y_top),
		row=1, col=1
	)

	fig.add_trace(
		go.Scatter(x=x, y=y_bottom),
		row=2, col=1
	)

	fig.add_trace(
		go.Scatter(x=x, y=y_macd_d5),
		row=3, col=1
	)

	fig.update_layout(height=800,
					  width=800,
					  title_text="Price and MACD",
					  xaxis=dict(range=[min(x),max(x)]),
					  xaxis2=dict(range=[min(x), max(x)]),
					  xaxis3=dict(range=[min(x), max(x)]),
					  yaxis=dict(range = [min(y_top),max(y_top)])
					 )

	return fig

server = app.server

if __name__ == '__main__':
	app.run_server(host=server_host, port=port_number, debug=True)
