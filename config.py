import os
import sys
import time
# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

# local imports
sys.path.insert(0, '..')  # for local imports from the top directory
from algos.machine_specific.config_machine_specific import params_machine_specific

from copy import deepcopy
import platform


# ### function definitions... must be here as config is imported into utils, not the other way around
#
# this is also featured in utils
def reverse_dict(d):
    """takes a dictionary and flips the keys and values
    """
    new_dict = {}

    for key in d.keys():
        value = d[key]
        new_dict[value] = key

    return new_dict


active_services = params_machine_specific['active_services']

# ### important constants ###PAUL_todo
#
#
constants = {'os': str(platform.system()),  # ###PAUL alot relies on this, this is kindof the thing that should be here
             'email_port': 1025,
             }

# ###PAUL this can likely be phased out (unless proves useful for live implementation for SC work)
# this is used in get_data_fp()... not worth trying to get rid of it
algos_dir = ''

dirs = {  # ###PAUL TODO: once depriciated `dirs` are removed consider what can be moved to machine specific
          #         TODO: and if a root directory can be established and put there. for now dont make it DRY
    'data_dir': '/home/paul/src/algos/data/',
    'live_data_dir': '/home/paul/src/algos/data/live/',
    'ports_data_dir': '/home/paul/src/algos/data/live/ports/',
}

# ### universe ---- what is collected, tracked, and traded via each exchange
#
#

universe = { 
    'trade_collection_historical': {
        # SOURCE: https://data.binance.vision/?prefix=data/spot/BTCUSDT
        'binance': [{'symbol': 'BTC/USDT',    'start_date': (2021, 8, 14), 'end_date': None},
                    {'symbol': 'ETH/USDT',    'start_date': (2019, 1, 27), 'end_date': None},
                    {'symbol': 'LINK/USDT',   'start_date': (2019, 1, 16), 'end_date': None},
                    {'symbol': 'KDA/USDT',    'start_date': (2022, 3, 11), 'end_date': None},
                    {'symbol': 'ROSE/USDT',   'start_date': (2020, 11, 19), 'end_date': None},
                    {'symbol': 'ICP/USDT',    'start_date': (2021, 6, 10), 'end_date': None},
                    {'symbol': 'AVAX/USDT',   'start_date': (2021, 6, 10), 'end_date': None},
                    {'symbol': 'SOL/USDT',    'start_date': (2020, 8, 11), 'end_date': None},
                    {'symbol': 'BNB/USDT',    'start_date': (2017, 11, 6), 'end_date': None},
                    {'symbol': 'BNB/USDT',    'start_date': (2019, 7, 5), 'end_date': None},
                    {'symbol': 'GRT/USDT',    'start_date': (2020, 12, 17), 'end_date': None},
                    ],

        # SOURCE: https://www.binance.us/institutions/market-history
        'binance_us':[
            {'symbol': 'BTC/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   #  on binance_us, "USD" pairs ended (2023, 7, 15) 
            {'symbol': 'ETH/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   
            {'symbol': 'LINK/USD',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 15)}, 
            {'symbol': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'ROSE/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'ICP/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'AVAX/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'SOL/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'BNB/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
            {'symbol': 'GRT/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},

            {'symbol': 'BTC/USDT',    'start_date': (2019, 9, 17), 'end_date': None},
            {'symbol': 'ETH/USDT',    'start_date': (2019, 9, 17), 'end_date': None},
            {'symbol': 'LINK/USDT',    'start_date': (2019, 9, 17), 'end_date': None},
            {'symbol': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'ROSE/USDT',   'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'ICP/USDT',    'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'AVAX/USDT',   'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'SOL/USDT',    'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'BNB/USDT',    'start_date': (2019, 9, 17),  'end_date': None},
            {'symbol': 'GRT/USDT',    'start_date': (2019, 9, 17),  'end_date': None},
            ]  
        },

    'trade_collection_live': {'binance_us': ['BTC/USDT', ] }, 

    'orderbook_collection': {'binance_us': ['KDA-USDT']}  
    }


# ### data format ---- for pretty much everything in the repo
#
#
data_format = dict()


# ### TODO: DEPRICATE DATA FORMAT.... delete all except CCXT cause it exists now 
# data format for
data_format_binance = {
    'websocket_trade_columns': {'e': 'event_type',
                                'E': 'msg_time',
                                's': 'ticker',
                                't': 'trade_id',
                                'p': 'price',
                                'q': 'quantity',
                                'b': 'buy_order_id',
                                'a': 'sell_order_id',
                                'T': 'trade_time',
                                'm': 'buyer_is_maker',
                                'M': 'ignore'
                                },

    'websocket_trade_example': {"e": "trade",  # message type
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

    'book_response_structure': {'structure': '###PAUL do this later'},

    'book_response_example': {'structure': '###PAUL do this later'},

    'trade_col_name_list': ['msg_time', 'ticker', 'trade_id', 'price', 'quantity',
                            'buy_order_id', 'sell_order_id', 'trade_time', 'buyer_is_maker'
                            ],

    'trade_name_and_type': {'msg_time': float,
                            'ticker': str,
                            'trade_id': int,
                            'price': float,
                            'quantity': float,
                            'buy_order_id': int,
                            'sell_order_id': int,
                            'trade_time': float,
                            'buyer_is_maker': bool,
                            },

    'price_name_and_type': {'buyer_is_maker': int,
                            'buyer_is_taker': int,
                            'buy_vol': float,
                            'sell_vol': float,
                            'buy_base_asset': float,
                            'sell_base_asset': float,
                            'buy_vwap': float,
                            'sell_vwap': float
                            },

    'order_col_name_list': ['orderId', 'ticker', 'clientOrderId', 'placedTime', 'price', 'origQty',
                            'executedQty', 'cummulativeQuoteQty', 'side', 'status', 'ord_type', 'updateTime',
                            ],

    'order_col_name_type': {'orderId': int,
                            'ticker': str,
                            'clientOrderId': str,
                            'placedTime': int,
                            'price': float,
                            'origQty': float,
                            'executedQty': float,
                            'cummulativeQuoteQty': float,
                            'side': str,
                            'status': str,
                            'ord_type': str,
                            'updateTime': int
                            },

    'order_filters_col_name_list': ['universal_symbol', 'id', 'base', 'precision_amount', 'quote',
                                    'precision_price', 'limits_price_min', 'limits_price_max',
                                    'limits_amount_min', 'limits_amount_max', 'limits_cost_min'],

    'order_filters_name_type': {'id': str,  # us  corresponding to symbols_tracked
                                'base': str,  # 'BTC' in 'BTCUSDT'
                                'precision_amount': float,  # num of decimals for base
                                'quote': str,  # 'USD' in 'BTCUSD'
                                'precision_price': float,  # num of decimals for quote
                                'limits_price_min': float,  # min price for BASE in QUOTE
                                'limits_price_max': float,  # max price for BASE asset in QUOTE
                                'limits_amount_min': float,  # min order of BASE asset allowed
                                'limits_amount_max': float,  # max order of BASE asset allowed
                                'limits_cost_min': float,  # min order in terms of QUOTE asset
                                },
}

# ###PAUL just a copy paster from binance foreign, needs editing
data_format_binanceus = {
    'websocket_trade_columns': {'e': 'event_type',
                                'E': 'msg_time',
                                's': 'ticker',
                                't': 'trade_id',
                                'p': 'price',
                                'q': 'quantity',
                                'b': 'buy_order_id',
                                'a': 'sell_order_id',
                                'T': 'trade_time',
                                'm': 'buyer_is_maker',
                                'M': 'ignore'
                                },

    'websocket_trade_example': {"e": "trade",  # message type
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

    'book_response_structure': {'structure': '###PAUL do this later'},

    'book_response_example': {'structure': '###PAUL do this later'},

    'trade_col_name_list': ['msg_time', 'ticker', 'trade_id', 'price', 'quantity',
                            'buy_order_id', 'sell_order_id', 'trade_time', 'buyer_is_maker'
                            ],

    'trade_name_and_type': {'msg_time': float,
                            'ticker': str,
                            'trade_id': int,
                            'price': float,
                            'quantity': float,
                            'buy_order_id': int,
                            'sell_order_id': int,
                            'trade_time': float,
                            'buyer_is_maker': bool,
                            },

    'price_name_and_type': {'buyer_is_maker': int,
                            'buyer_is_taker': int,
                            'buy_vol': float,
                            'sell_vol': float,
                            'buy_base_asset': float,
                            'sell_base_asset': float,
                            'buy_vwap': float,
                            'sell_vwap': float
                            },

    'order_col_name_list': ['orderId', 'ticker', 'clientOrderId', 'placedTime', 'price', 'origQty',
                            'executedQty', 'cummulativeQuoteQty', 'side', 'status', 'ord_type', 'updateTime',
                            ],

    'order_col_name_type': {'orderId': int,
                            'ticker': str,
                            'clientOrderId': str,
                            'placedTime': int,
                            'price': float,
                            'origQty': float,
                            'executedQty': float,
                            'cummulativeQuoteQty': float,
                            'side': str,
                            'status': str,
                            'ord_type': str,
                            'updateTime': int
                            },

    'order_filters_col_name_list': ['universal_symbol', 'id', 'base', 'precision_amount', 'quote',
                                    'precision_price', 'limits_price_min', 'limits_price_max',
                                    'limits_amount_min', 'limits_amount_max', 'limits_cost_min'],

    'order_filters_name_type': {'id': str,  # us  corresponding to symbols_tracked
                                'base': str,  # 'BTC' in 'BTCUSDT'
                                'precision_amount': float,  # num of decimals for base
                                'quote': str,  # 'USD' in 'BTCUSD'
                                'precision_price': float,  # num of decimals for quote
                                'limits_price_min': float,  # min price for BASE in QUOTE
                                'limits_price_max': float,  # max price for BASE asset in QUOTE
                                'limits_amount_min': float,  # min order of BASE asset allowed
                                'limits_amount_max': float,  # max order of BASE asset allowed
                                'limits_cost_min': float,  # min order in terms of QUOTE asset
                                },
}

data_format_kucoin = {
    'websocket_trade_columns': {'type': 'event_type',
                                'will do this manually via time.time()': 'msg_time',
                                'symbol': 'ticker',
                                'tradeId': 'trade_id',
                                'price': 'price',
                                'size': 'quantity',
                                'derived from maker / taker / side in real time': 'buy_order_id',
                                'derived from maker / taker / side in real time': 'sell_order_id',
                                'time': 'trade_time',
                                'derived from maker / taker / side in real time': 'buyer_is_maker',
                                },

    'websocket_trade_example': {'symbol': 'KDA-USDT',
                                'side': 'sell',
                                'type': 'match',
                                'makerOrderId': '624f101441645900017c716e',
                                'sequence': '1621541091162',
                                'size': '12.6875',
                                'price': '6.4292',
                                'takerOrderId': '624f101832db560001eb370e',
                                'time': '1649348632148020952',
                                'tradeId': '624f1018785778509c13a3d6'
                                },

    'book_response_structure': {'structure': '###PAUL do this later'},

    'book_response_example': {'structure': '###PAUL do this later'},

    'trade_col_name_list': ['msg_time', 'ticker', 'trade_id', 'price', 'quantity',
                            'buy_order_id', 'sell_order_id', 'trade_time', 'buyer_is_maker'
                            ],

    'trade_name_and_type': {'msg_time': float,
                            'ticker': str,
                            'trade_id': str,
                            'price': float,
                            'quantity': float,
                            'buy_order_id': str,
                            'sell_order_id': str,
                            'trade_time': float,
                            'buyer_is_maker': bool,
                            },

    'price_name_and_type': {'buyer_is_maker': int,
                            'buyer_is_taker': int,
                            'buy_vol': float,
                            'sell_vol': float,
                            'buy_base_asset': float,
                            'sell_base_asset': float,
                            'buy_vwap': float,
                            'sell_vwap': float
                            },

    # ###PAUL_todo TODO order managment for kucoin
    'order_col_name_list': ['orderId', 'ticker', 'clientOrderId', 'placedTime', 'price', 'origQty',
                            'executedQty', 'cummulativeQuoteQty', 'side', 'status', 'ord_type', 'updateTime',
                            ],

    # ###PAUL_todo TODO order managment for kucoin
    'order_col_name_type': {'orderId': int,
                            'ticker': str,
                            'clientOrderId': str,
                            'placedTime': int,
                            'price': float,
                            'origQty': float,
                            'executedQty': float,
                            'cummulativeQuoteQty': float,
                            'side': str,
                            'status': str,
                            'ord_type': str,
                            'updateTime': int
                            },

    'order_filters_col_name_list': ['universal_symbol', 'id', 'base', 'precision_amount', 'quote',
                                    'precision_price', 'limits_price_min', 'limits_price_max',
                                    'limits_amount_min', 'limits_amount_max', 'limits_cost_min'],

    'order_filters_name_type': {'id': str,  # us  corresponding to symbols_tracked
                                'base': str,  # 'BTC' in 'BTCUSDT'
                                'precision_amount': float,  # num of decimals for base
                                'quote': str,  # 'USD' in 'BTCUSD'
                                'precision_price': float,  # num of decimals for quote
                                'limits_price_min': float,  # min price for BASE in QUOTE
                                'limits_price_max': float,  # max price for BASE asset in QUOTE
                                'limits_amount_min': float,  # min order of BASE asset allowed
                                'limits_amount_max': float,  # max order of BASE asset allowed
                                'limits_cost_min': float,  # min order in terms of QUOTE asset
                                },
}  ###PAUL just a copy paster from binance foreign, needs editing
###PAUL just a copy paster from binance foreign, needs editing


# data format for
data_format_ccxt = {
    'websocket_trade_columns': {'e': 'event_type',
                                'E': 'msg_time',
                                's': 'ticker',
                                't': 'trade_id',
                                'p': 'price',
                                'q': 'quantity',
                                'b': 'buy_order_id',
                                'a': 'sell_order_id',
                                'T': 'trade_time',
                                'm': 'buyer_is_maker',
                                'M': 'ignore'
                                },

    'websocket_trade_example': {"e": "trade",  # message type
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

    'book_response_structure': {'structure': '###PAUL do this later'},

    'book_response_example': {'structure': '###PAUL do this later'},

    'trade_col_name_list': ['msg_time', 'ticker', 'trade_id', 'price', 'quantity',
                            'buy_order_id', 'sell_order_id', 'trade_time', 'buyer_is_maker'
                            ],

    'trade_name_and_type': {'msg_time': float,
                            'ticker': str,
                            'trade_id': int,
                            'price': float,
                            'quantity': float,
                            'buy_order_id': int,
                            'sell_order_id': int,
                            'trade_time': float,
                            'buyer_is_maker': bool,
                            },

    'price_name_and_type': {'buyer_is_maker': int,
                            'buyer_is_taker': int,
                            'buy_vol': float,
                            'sell_vol': float,
                            'buy_base_asset': float,
                            'sell_base_asset': float,
                            'buy_vwap': float,
                            'sell_vwap': float
                            },

    'order_col_name_list': ['orderId', 'ticker', 'clientOrderId', 'placedTime', 'price', 'origQty',
                            'executedQty', 'cummulativeQuoteQty', 'side', 'status', 'ord_type', 'updateTime',
                            ],

    'order_col_name_type': {'orderId': int,
                            'ticker': str,
                            'clientOrderId': str,
                            'placedTime': int,
                            'price': float,
                            'origQty': float,
                            'executedQty': float,
                            'cummulativeQuoteQty': float,
                            'side': str,
                            'status': str,
                            'ord_type': str,
                            'updateTime': int
                            },

    'order_filters_col_name_list': ['universal_symbol', 'id', 'base', 'precision_amount', 'quote',
                                    'precision_price', 'limits_price_min', 'limits_price_max',
                                    'limits_amount_min', 'limits_amount_max', 'limits_cost_min'],

    'order_filters_name_type': {'id': str,  # us  corresponding to symbols_tracked
                                'base': str,  # 'BTC' in 'BTCUSDT'
                                'precision_amount': float,  # num of decimals for base
                                'quote': str,  # 'USD' in 'BTCUSD'
                                'precision_price': float,  # num of decimals for quote
                                'limits_price_min': float,  # min price for BASE in QUOTE
                                'limits_price_max': float,  # max price for BASE asset in QUOTE
                                'limits_amount_min': float,  # min order of BASE asset allowed
                                'limits_amount_max': float,  # max order of BASE asset allowed
                                'limits_cost_min': float,  # min order in terms of QUOTE asset
                                },
}


data_format['binance'] = data_format_binance
data_format['binanceus'] = data_format_binanceus
data_format['kucoin'] = data_format_kucoin
data_format['ccxt'] = data_format_ccxt


# ### initialize ---- parameters and create the dictionary
#
#
params = dict()

params['constants'] = constants
params['active_services'] = active_services
params['dirs'] = dirs
params['universe'] = universe
params['data_format'] = data_format
