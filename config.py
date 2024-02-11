import os
import platform
import sys
import time

# ### time zone change... this must happen first and utils must be imported first
os.environ["TZ"] = "UTC"
time.tzset()


from copy import deepcopy
import dotenv
import os


def get_secret(key):  # this is here and utils to avoid a circular import
    # import pdb
    # pdb.set_trace()
    if key not in os.environ:
        raise KeyError(f"Key {key} not found!")
    return os.environ[key]


dotenv.load_dotenv()
machine_name = get_secret("MACHINE_NAME")


# ### function definitions... must be here as config is imported into utils, not the other way around
#
# this is also featured in utils
def reverse_dict(d):
    """takes a dictionary and flips the keys and values"""
    new_dict = {}

    for key in d.keys():
        value = d[key]
        new_dict[value] = key

    return new_dict


# ### important constants
#
#
constants = {
    "os": str(platform.system()),
    "email_port": 1025,
}

# ###PAUL this can likely be phased out (unless proves useful for live implementation for SC work)
# this is used in get_data_fp()... not worth trying to get rid of it
algos_dir = ""

dirs = {  # ###PAUL TODO: once depriciated `dirs` are removed consider what can be moved to machine specific
    #         TODO: and if a root directory can be established and put there. for now dont make it DRY
    "data_dir": "/home/paul/src/algos/data/",
    "live_data_dir": "/home/paul/src/algos/data/live/",
    "ports_data_dir": "/home/paul/src/algos/data/live/ports/",
}

# ### universe ---- what is collected, tracked, and traded via each exchange
#
#

universe = {
    "trade_collection_historical": {
        # SOURCE: https://data.binance.vision/?prefix=data/spot/BTCUSDT
        "binance": [
            {"symbol": "BTC/USDT", "start_date": (2021, 8, 14), "end_date": None},
            {"symbol": "ETH/USDT", "start_date": (2019, 1, 27), "end_date": None},
            {"symbol": "LINK/USDT", "start_date": (2019, 1, 16), "end_date": None},
            {"symbol": "KDA/USDT", "start_date": (2022, 3, 11), "end_date": None},
            {"symbol": "ROSE/USDT", "start_date": (2020, 11, 19), "end_date": None},
            {"symbol": "ICP/USDT", "start_date": (2021, 6, 10), "end_date": None},
            {"symbol": "AVAX/USDT", "start_date": (2021, 6, 10), "end_date": None},
            {"symbol": "SOL/USDT", "start_date": (2020, 8, 11), "end_date": None},
            {"symbol": "BNB/USDT", "start_date": (2017, 11, 6), "end_date": None},
            {"symbol": "BNB/USDT", "start_date": (2019, 7, 5), "end_date": None},
            {"symbol": "GRT/USDT", "start_date": (2020, 12, 17), "end_date": None},
        ],
        # SOURCE: https://www.binance.us/institutions/market-history
        "binance_us": [
            {
                "symbol": "BTC/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },  #  on binance_us, "USD" pairs ended (2023, 7, 15)
            {
                "symbol": "ETH/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "LINK/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 12, 15),
            },
            {
                "symbol": "KDA/USDT",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "ROSE/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "ICP/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "AVAX/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "SOL/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "BNB/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {
                "symbol": "GRT/USD",
                "start_date": (2019, 9, 17),
                "end_date": (2023, 7, 15),
            },
            {"symbol": "BTC/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "ETH/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "LINK/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "KDA/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "ROSE/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "ICP/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "AVAX/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "SOL/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "BNB/USDT", "start_date": (2019, 9, 17), "end_date": None},
            {"symbol": "GRT/USDT", "start_date": (2019, 9, 17), "end_date": None},
        ],
    },
    "trade_collection_live": {
        "binance_us": [
            "BTC/USDT",
        ]
    },
    "orderbook_collection": {"binance_us": ["KDA-USDT"]},
}


# ### data format ---- for pretty much everything in the repo
#
#
data_format = dict()


# data format for
data_format_ccxt = {
    "websocket_trade_columns": {
        "e": "event_type",
        "E": "msg_time",
        "s": "ticker",
        "t": "trade_id",
        "p": "price",
        "q": "quantity",
        "b": "buy_order_id",
        "a": "sell_order_id",
        "T": "trade_time",
        "m": "buyer_is_maker",
        "M": "ignore",
    },
    "websocket_trade_example": {
        "e": "trade",  # message type
        "E": 1609300202081,  # message time
        "s": "BNBBTC",  # Symbol
        "t": 12345,  # Trade ID
        "p": "0.001",  # Price
        "q": "100",  # Quantity
        "b": 88,  # Buyer order ID
        "a": 50,  # Seller order ID
        "T": 123456785,  # Trade time
        "m": True,  # Is the buyer the market maker?
        "M": True,
        # Ignore...  some legacy thing on binance side
    },
    "book_response_structure": {"structure": "###PAUL do this later"},
    "book_response_example": {"structure": "###PAUL do this later"},
    "trade_col_name_list": [
        "msg_time",
        "ticker",
        "trade_id",
        "price",
        "quantity",
        "buy_order_id",
        "sell_order_id",
        "trade_time",
        "buyer_is_maker",
    ],
    "trade_name_and_type": {
        "msg_time": float,
        "ticker": str,
        "trade_id": int,
        "price": float,
        "quantity": float,
        "buy_order_id": int,
        "sell_order_id": int,
        "trade_time": float,
        "buyer_is_maker": bool,
    },
    "price_name_and_type": {
        "buyer_is_maker": int,
        "buyer_is_taker": int,
        "buy_vol": float,
        "sell_vol": float,
        "buy_base_asset": float,
        "sell_base_asset": float,
        "buy_vwap": float,
        "sell_vwap": float,
    },
    "order_col_name_list": [
        "orderId",
        "ticker",
        "clientOrderId",
        "placedTime",
        "price",
        "origQty",
        "executedQty",
        "cummulativeQuoteQty",
        "side",
        "status",
        "ord_type",
        "updateTime",
    ],
    "order_col_name_type": {
        "orderId": int,
        "ticker": str,
        "clientOrderId": str,
        "placedTime": int,
        "price": float,
        "origQty": float,
        "executedQty": float,
        "cummulativeQuoteQty": float,
        "side": str,
        "status": str,
        "ord_type": str,
        "updateTime": int,
    },
    "order_filters_col_name_list": [
        "universal_symbol",
        "id",
        "base",
        "precision_amount",
        "quote",
        "precision_price",
        "limits_price_min",
        "limits_price_max",
        "limits_amount_min",
        "limits_amount_max",
        "limits_cost_min",
    ],
    "order_filters_name_type": {
        "id": str,  # us  corresponding to symbols_tracked
        "base": str,  # 'BTC' in 'BTCUSDT'
        "precision_amount": float,  # num of decimals for base
        "quote": str,  # 'USD' in 'BTCUSD'
        "precision_price": float,  # num of decimals for quote
        "limits_price_min": float,  # min price for BASE in QUOTE
        "limits_price_max": float,  # max price for BASE asset in QUOTE
        "limits_amount_min": float,  # min order of BASE asset allowed
        "limits_amount_max": float,  # max order of BASE asset allowed
        "limits_cost_min": float,  # min order in terms of QUOTE asset
    },
}

data_format["ccxt"] = data_format_ccxt


desired_features_dict = {
    "buy_to_sell_count_ratio": {
        "interval_lens": [1, 3, 10, 28, 59, 119, 360],
        "function_name": "get_ratio_of_metrics_rolling_sums",
        # note, if the argument is str it is written "'string'"
        "kwargs": {
            "df": "trading_summary",
            "metric_1": "'buyer_is_maker'",
            "metric_2": "'buyer_is_taker'",
        },
    },
    "buy_to_sell_vol_ratio": {
        "interval_lens": [
            1,
            3,
            10,
            28,
            59,
            119,
            360,
            1440,
        ],
        "function_name": "get_ratio_of_metrics_rolling_sums",
        "kwargs": {
            "df": "trading_summary",
            "metric_1": "'buy_base_vol'",
            "metric_2": "'sell_base_vol'",
        },
    },
    "momentum": {
        "interval_lens": [1, 3, 10, 28, 59, 119, 240, 1200, 4320, 14400],
        "function_name": "calculate_momentum",
        "kwargs": {
            "df": "trading_summary",
            "col": "'vwap'",
        },
    },
    "rsi": {
        "interval_lens": [10, 28, 59, 240, 1200, 4320, 14400, 56000],
        "function_name": "calc_rsi",
        "kwargs": {"series": "trading_summary['vwap']"},
    },
    # ###PAUL this is not what is wanted...
    # rolling variance is a good replacement for what this was trying to do
    # "roll_std_price": {'interval_lens': [15, 28, 59, 119, 240, 1200, 4320, 14400],
    #                    'function_name': 'calc_rolling_std',
    #                    'kwargs': {'series': "prices['vwap']"},
    # },
    "roll_std_vol": {
        "interval_lens": [15, 28, 59, 119, 240, 1200, 4320, 14400],
        "function_name": "calc_rolling_std",
        "kwargs": {"series": "prices['total_base_vol']"},
    },
    # ###PAUL TODO: ROLLING STD OF VOLATILITY
    #
    #
    # more complex metrics below this line
    # _=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_
    "macd": {
        "function_name": "calc_macd",
        "kwargs": {
            "series": "prices['vwap']",
        },
        "span_tuples": [(12, 26, 9), (4, 26, 9), (13, 26, 1), (12, 26, 3)],
        "multipliers": [1, 5, 15, 60, 150, 1600],
    },
    # EXAMPLE: keep this feature_name it is skipped by the code writer if left as is
    # _=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_
    "feature_name": {
        "interval_lens": [
            30,
            60,
            120,
        ],
        "function_name": "function_to_make_metric",
        "kwargs": {
            "col_name": "input_str",
            "metric_1": "input_str",
            "metric_2": "input_str",
        },
    },
}


if machine_name == "blackbox":
    active_services = {
        "trade_collect": {
            "exchanges": {
                "binance_us": [
                    "BTC/USDT",
                    "KDA/USDT",
                    "ETH/USDT",
                    "LINK/USDT",
                    "ROSE/USDT",
                    "ICP/USDT",
                    "AVAX/USDT",
                    "SOL/USDT",
                    "BNB/USDT",
                    "DOGE/USDT",
                    "GRT/USDT",
                ],
                "kraken": [
                    "BTC/USDT",
                    "ETH/USDT",
                    "LINK/USDT",
                    "AVAX/USDT",
                    "SOL/USDT",
                    "DOGE/USDT",
                    "BTC/USD",
                    "ETH/USD",
                    "LINK/USD",
                    "ICP/USD",
                    "AVAX/USD",
                    "SOL/USD",
                    "DOGE/USD",
                    "GRT/USD",
                ],
            },
            "trade_process_interval": "1min",  # starts the cycle of trades to db, summary, to decision every minute
            "trade_db_write_delay": 2,  # seconds after a UTC minute to write trades to DB
            "summary_process_delay": 10,  # number of seconds interval length to collect trades then push to table
        },
        "signals": {
            "prod_1____BTC_USDT_trades_only_data": {
                "signal_name": "prod_1____BTC_USDT_trades_only_data",
                "exchange": "binance",
                "pairs": ["BTC-TUSD"],
                # intended to replace symbol, as signals will have more than one pair soon
                "symbol": "BTC-USDT",  # TODO: depricate this for `pairs` shown above
                "mins_between_signal_updates": 2,
                "signal_make_delay": 10,  # seconds
                # TODO: the pipeline where this input, `desired_features_dict` writes code to `make_feature_set_printed_fn`
                "desired_features_dict": desired_features_dict,
            },
            "signal_dict____2023_08_23___mlp_rolling____to_2023_07_18": {
                "signal_name": "signal_dict____2023_08_23___mlp_rolling____to_2023_07_18",
                # 'exchange': 'binance',    # handled
                # 'pairs': ['BTC-TUSD'],
                # intended to replace symbol, as signals will have more than one pair soon
                "symbol": "BTC-USDT",  # TODO: depricate this for `pairs` shown above
                "mins_between_signal_updates": 2,
                "signal_make_delay": 30,  # seconds
                # TODO: the pipeline where this input, `desired_features_dict` writes code to `make_feature_set_printed_fn`
                "desired_features_dict": desired_features_dict,
                "feature_params": {
                    "eaors_trades": {  # 'data_source' : {source_specific_processing_information},
                        "BTC-USDT": {
                            "desired_features_dict": desired_features_dict,
                            "exchange": "binance",
                            "start_date": (2018, 1, 1),
                            "end_date": (2023, 7, 18),
                            "alternative_data_pair": None,
                        },
                        "BTC-TUSD": {
                            "desired_features_dict": desired_features_dict,
                            "exchange": "binance",
                            "start_date": (2018, 1, 1),
                            "end_date": (2023, 7, 18),
                            "alternative_data_pair": "BTC-USDT",
                            "alternative_data_exchange": "binance",
                            "alternative_start_date": (2018, 1, 1),
                            "alternative_end_date": (2023, 2, 15),
                        },
                        "ETH-USDT": {
                            "desired_features_dict": desired_features_dict,
                            "exchange": "binance",
                            "start_date": (2018, 1, 1),
                            "end_date": (2023, 7, 18),
                            "alternative_data_pair": None,
                        },
                        "ETH-TUSD": {
                            "desired_features_dict": desired_features_dict,
                            "exchange": "binance",
                            "start_date": (2018, 1, 1),
                            "end_date": (2023, 7, 18),
                            "alternative_data_pair": None,
                            "alternative_data_exchange": "binance",
                            "alternative_start_date": (2018, 1, 1),
                            "alternative_end_date": (2023, 2, 15),
                        },
                    },
                    # 'eaors_orderbook': {},
                    # 'l_map': {},
                    # 'sp500': {},
                    # 'commodities': {},
                    # 'forex': {'DXY': {'desired_features_dict': desired_features_dict},  # could be nearly identical to EAORS trade pipeline
                    "utc_time": True,
                    # ###PAUL TODO: consider refactoring preprocessing as its own key back in
                    # 'preprocessing': {
                    "preprocess_rolling_norm_n_obvs": 20 * 24 * 60,
                    # }
                },
            },
        },
        "ports": {
            "simple_stochastic_1": {
                "port_name": f"prod_1____BTC_USDT_trades_only_data",
                "signal_name": None,
                "exchange": "binance_us",
                "exchanges": None,  # for multi exchange portfolios, be sure to swap above to None (one must be)
                "pairs_traded": ["BTC-USDT"],
                "assets_in_port": {
                    "BTC",
                    "USDT",
                },  # ###PAUL TODO: generate this off pairs traded list?
                "mins_between_decision_check": 1,
                "check_signal_delay": 50,  # seconds
                "diff_thresh": 11,  # min volume in $ (should be liq...) for order to be placed
                "print_alert_n_iters": 1,
                "decision_delay": 35,
                "decision_params": {  # TODO: implement in `algos/data/live/ports/decision_params.json
                    "fee": 0.01,  # TODO: need to grab from port name
                    "max_workers": 70,
                    "cool_down": 15,
                    "threshold": -0.09999999999999998,
                    "pred_dist": 0.25,
                    "price_dist": 0.0185,
                    "stop_limit": 0.045,
                    "overrides": ["stop_limit"],
                    "any_two": [],
                    "to_neutral_threshold": 0.375,
                    "to_neutral_pred_dist": 0.14999999999999997,
                    "to_neutral_price_dist": 0.0022500000000000003,
                    "to_neutral_stop_limit": 0.0205,
                    "to_neutral_overrides": ["stop_limit"],
                    "to_neutral_any_two": [],
                },
                "positions_table_info": {  # all fields are shown below, commented out items figured RTI}
                    # 'timestamp': '',
                    # 'strategy': 'peak_bottom',
                    "algo": "prod_1____BTC_USDT_trades_only_data",
                    "sub_account": "maxs_binance",
                    # 'leg_group_id': '',  # leg_group_id = int(datetime.utcnow().timestamp() * 1000)
                    # 'instrument': '',
                    "exchange": "binance",
                    # 'size': '',
                    # 'mid_price': '',
                    # 'currency_price': '',
                    # 'currency_name': '',
                    "funding_pnl": 0,
                    "margin": 0,
                    "ignore": False,
                    # ###PAUL TODO: verify this is in table right (its lowercase false) for other peoples enteries
                    "adjustment": False,
                    # ###PAUL TODO: verify this is in table right (its lowercase false) for other peoples enteries
                },
            },
        },
    }

# ###TODO put trading summary and collection on whitebox, blackbox should only do pytorch work
if machine_name == "whitebox":
    active_services = {
        # 'ports': {'prod_1____BTC_USDT_trades_only_data':
        #               {'port_name': f"prod_1____BTC_USDT_trades_only_data",
        #                'signal_name': f"signal_dict____2023_08_23___mlp_rolling____to_2023_07_18",
        #                'exchange': 'binance',     # TODO: get rid of this infavor of multi exchange setup
        #                'exchanges': ['binance'],  # TODO: support this fully then get rid of the above
        #                'pairs_traded': ['BTC-TUSD'],
        #                'assets_in_port': {'BTC', 'TUSD'},  # ###PAUL TODO: generate this off pairs traded list?
        #                'mins_between_decision_check': 1,
        #                'check_signal_delay': 50,  # seconds
        #                'diff_thresh': 11,  # min volume in $ (should be liq...) for order to be placed
        #                'print_alert_n_iters': 1,
        #                'decision_delay': 35,
        #                'decision_params': {  # TODO: implement in `algos/data/live/ports/decision_params.json
        #                    'fee': 0.01,  # TODO: need to grab from port name
        #                    'max_workers': 70,
        #                    'cool_down': 15,
        #                    'threshold': -0.09999999999999998,
        #                    'pred_dist': 0.25,
        #                    'price_dist': 0.0185,
        #                    'stop_limit': 0.045,
        #                    'overrides': ['stop_limit'],
        #                    'any_two': [],
        #                    'to_neutral_threshold': 0.375,
        #                    'to_neutral_pred_dist': 0.14999999999999997,
        #                    'to_neutral_price_dist': 0.0022500000000000003,
        #                    'to_neutral_stop_limit': 0.0205,
        #                    'to_neutral_overrides': ['stop_limit'],
        #                    'to_neutral_any_two': []},
        #                'positions_table_info': {  # all fields are shown below, commented out items figured RTI
        #                    # 'timestamp': '',
        #                    # 'strategy': 'peak_bottom',
        #                    'algo': 'prod_1____BTC_USDT_trades_only_data',
        #                    'sub_account': 'maxs_binance',
        #                    # 'leg_group_id': '',  # leg_group_id = int(datetime.utcnow().timestamp() * 1000)
        #                    # 'instrument': '',
        #                    'exchange': 'binance',
        #                    # 'size': '',
        #                    # 'mid_price': '',
        #                    # 'currency_price': '',
        #                    # 'currency_name': '',
        #                    'funding_pnl': 0,
        #                    'margin': 0,
        #                    'ignore': False,
        #                    # ###PAUL TODO: verify this is in table right (its lowercase false) for other peoples enteries
        #                    'adjustment': False,
        #                    # ###PAUL TODO: verify this is in table right (its lowercase false) for other peoples enteries
        #                 },
        #                },
        #           },
    }


# ### initialize ---- parameters and create the dictionary
#
#
params = dict()

params["constants"] = constants
params["active_services"] = active_services
params["dirs"] = dirs
params["universe"] = universe
params["data_format"] = data_format
