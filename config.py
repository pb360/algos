import platform
import sys

from machine_specfic.config_machine_specific import params_machine_specific
from local.config_local import params_local

# ### stuff from outside sources
#
#
device_info = {'device_name': params_machine_specific['device_name'],
               'os': str(platform.system()),
               }

keys = params_local['keys']

# ### important constants
#
#
ports = {'email_port': 1025}

# ###PAUL_migration ... this can stay however will need some updates
constants = {
    'secs_of_trades_to_keep_live': 60,  # number of minutes to keep trades in live file
    'live_trade_trim_interval': 30,  # how mnay seconds betweeen trimming live files
    'no_trade_message_timeout': 10,  # secs required for no msg until new scraping process starts
    'data_scrape_heartbeat': 8,  # check no_trade_message_timeout in heartbeat_check()
    'make_prices_from_trades_interval': 10,  # currently located in orders.py
    'update_signal_interval': 10,  # how many seconds between MACD signal update
    'order_sma_v1_interval': 15,  # order on signal interval   ###PAUL_migration should move to algos
    'secondary_order_interval': 2, # update market status and adjust orders ###PAUL_migration needs to mention binance
    'trade_watch_dog_interval': 20,
    # how long if no trade to restart trade collection w/ system-d ###PAUL_migration needs to mention binance
    'price_watch_dog_interval': 45,
    # how long if no price update to re-run orders.py w/ system-d ###PAUL_migration needs to mention binance
    'order_watch_dog_interval': 5 * 60,
    # how long if no orders to reset any given bot ###PAUL_migration needs to mention binance
    'os': str(platform.system()),
}
# ###PAUL_migration  ^^^^^^    this can stay however will need some updates   ^^^^^^


# ###PAUL_migration .... this should probably just go away, or be migrated to ./utils.py thats the only thing that'll
# ###PAUL_migration .... us it with get_data_fp()
dirs = {'repo_dir': '/mnt/algos/',
        'data_dir': '/mnt/algos/data/',
        'book_data_dir': '/mnt/algos/data/book/',
        'trade_data_dir': '/mnt/algos/data/trade/',
        'price_data_dir': '/mnt/algos/data/price/',
        'live_trade_data_dir': '/mnt/algos/data/live_trades/',
        'order_data_dir': '/mnt/algos/data/orders/',
        }
# ###PAUL_migration .... this should probably just go away, or be migrated to ./utils.py thats the only thing that'll
# ###PAUL_migration .... us it with get_data_fp()


# ### universe ---- what is collected, tracked, and traded via each exchange
#
#
universe = dict()

# ###PAUL just a copy paster from binance foreign, needs editing
universe_binance_foreign = {'coins_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp'],

                            'tick_collection_list': ['adausdt@trade', 'adabtc@trade', 'adausd@trade',
                                                     'bnbusdt@trade', 'bnbbtc@trade', 'bnbusd@trade',
                                                     'btcusdt@trade', 'btcbtc@trade', 'btcusd@trade',
                                                     'dogeusdt@trade', 'dogebtc@trade', 'dogeusd@trade',
                                                     'ethusdt@trade', 'ethbtc@trade', 'ethusd@trade',
                                                     'linkusdt@trade', 'linkbtc@trade', 'linkusd@trade',
                                                     'ltcusdt@trade', 'ltcbtc@trade', 'ltcusd@trade',
                                                     'xlmusdt@trade', 'xlmbtc@trade', 'xlmusd@trade',
                                                     'xrpusdt@trade', 'xrpbtc@trade', 'xrpusd@trade',
                                                     ],
                            # MUST BE ALL LOWER CASE.. not all exist but too busy to update now

                            'tickers_tracked': ['ADAUSDT', 'ADABTC',
                                                'BNBUSDT', 'BNBBTC',
                                                'BTCUSDT',  # this doesnt exist either 'BTCBTC',
                                                'DOGEUSDT',
                                                'ETHUSDT', 'ETHBTC',
                                                'LINKUSDT', 'LINKBTC',
                                                'LTCUSDT', 'LTCBTC',
                                                'XLMUSDT',
                                                'XRPUSDT', 'XRPBTC',
                                                ],

                            'tickers_traded': ['BTCUSDT'
                                               ],

                            'tickers_foreign_to_us_dict': {'ADAUSDT': 'ADAUSD', 'ADABTC': 'ADABTC',
                                                           'BNBUSDT': 'BNBUSD', 'BNBBTC': 'BNBBTC',
                                                           'BTCUSDT': 'BTCUSD',  # this doesnt exist either 'BTCBTC',
                                                           'DOGEUSDT': 'DOGEUSD',
                                                           'ETHUSDT': 'ETHUSD', 'ETHBTC': 'ETHBTC',
                                                           'LINKUSDT': 'LINKUSD', 'LINKBTC': 'LINKBTC',
                                                           'LTCUSDT': 'LTCUSD', 'LTCBTC': 'LTCBTC',
                                                           'XLMUSDT': 'XLMUSD',
                                                           'XRPUSDT': 'XRPUSD', 'XRPBTC': 'XRPBTC'
                                                           },

                            'tickers_us_to_foreign_dict': {'ADAUSD': 'ADAUSDT', 'ADABTC': 'ADABTC',
                                                           'BNBUSD': 'BNBUSDT', 'BNBBTC': 'BNBBTC',
                                                           'BTCUSD': 'BTCUSDT',  # this doesnt exist either 'BTCBTC',
                                                           'DOGEUSD': 'DOGEUSDT',
                                                           'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                           'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                           'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                           'XLMUSD': 'XLMUSDT',
                                                           'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                           }
                            }  # ###PAUL just a copy paster from binance foreign, needs editing
universe_kucoin = {'coins_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp'],

                   'tick_collection_list': ['adausdt@trade', 'adabtc@trade', 'adausd@trade',
                                            'bnbusdt@trade', 'bnbbtc@trade', 'bnbusd@trade',
                                            'btcusdt@trade', 'btcbtc@trade', 'btcusd@trade',
                                            'dogeusdt@trade', 'dogebtc@trade', 'dogeusd@trade',
                                            'ethusdt@trade', 'ethbtc@trade', 'ethusd@trade',
                                            'linkusdt@trade', 'linkbtc@trade', 'linkusd@trade',
                                            'ltcusdt@trade', 'ltcbtc@trade', 'ltcusd@trade',
                                            'xlmusdt@trade', 'xlmbtc@trade', 'xlmusd@trade',
                                            'xrpusdt@trade', 'xrpbtc@trade', 'xrpusd@trade',
                                            ],  # MUST BE ALL LOWER CASE.. not all exist but too busy to update now

                   'tickers_tracked': ['ADAUSDT', 'ADABTC',
                                       'BNBUSDT', 'BNBBTC',
                                       'BTCUSDT',  # this doesnt exist either 'BTCBTC',
                                       'DOGEUSDT',
                                       'ETHUSDT', 'ETHBTC',
                                       'LINKUSDT', 'LINKBTC',
                                       'LTCUSDT', 'LTCBTC',
                                       'XLMUSDT',
                                       'XRPUSDT', 'XRPBTC',
                                       ],

                   'tickers_traded': ['BTCUSDT'
                                      ],

                   'tickers_foreign_to_us_dict': {'ADAUSDT': 'ADAUSD', 'ADABTC': 'ADABTC',
                                                  'BNBUSDT': 'BNBUSD', 'BNBBTC': 'BNBBTC',
                                                  'BTCUSDT': 'BTCUSD',  # this doesnt exist either 'BTCBTC',
                                                  'DOGEUSDT': 'DOGEUSD',
                                                  'ETHUSDT': 'ETHUSD', 'ETHBTC': 'ETHBTC',
                                                  'LINKUSDT': 'LINKUSD', 'LINKBTC': 'LINKBTC',
                                                  'LTCUSDT': 'LTCUSD', 'LTCBTC': 'LTCBTC',
                                                  'XLMUSDT': 'XLMUSD',
                                                  'XRPUSDT': 'XRPUSD', 'XRPBTC': 'XRPBTC'
                                                  },

                   'tickers_us_to_foreign_dict': {'ADAUSD': 'ADAUSDT', 'ADABTC': 'ADABTC',
                                                  'BNBUSD': 'BNBUSDT', 'BNBBTC': 'BNBBTC',
                                                  'BTCUSD': 'BTCUSDT',  # this doesnt exist either 'BTCBTC',
                                                  'DOGEUSD': 'DOGEUSDT',
                                                  'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                  'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                  'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                  'XLMUSD': 'XLMUSDT',
                                                  'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                  }
                   }  # ###PAUL just a copy paster from binance foreign, needs editing
# ###PAUL just a copy paster from binance foreign, needs editing

universe['binance_foreign'] = universe_binance_foreign
universe['binance_us'] = universe_binance_us
universe['kucoin'] = universe_kucoin

# ###PAUL_migration ... should houses each set of websocket responses into its own exchange

# ### data format ---- for pretty much everything in the repo
#
#
data_format = dict()

# data format for
data_format_binance_foreign = {
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

    'order_filters_col_name_list': ['ticker', 'ticker_us', 'baseAsset', 'baseAssetPrecision', 'quoteAsset',
                                    'quoteAssetPrecision', 'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty',
                                    'stepSize', 'minNotional', 'marketMinQty', 'marketMaxQty', 'marketStepSize',
                                    ],

    'order_filters_name_type': {'ticker_us': str,  # us  corresponding to ticker_tracked
                                'baseAsset': str,  # 'BTC' in 'BTCUSDT'
                                'baseAssetPrecision': int,  # num of decimals for base
                                'quoteAsset': str,  # 'USD' in 'BTCUSD'
                                'quoteAssetPrecision': int,  # num of decimals for quote
                                'minPrice': float,  # min price for BASE in QUOTE
                                'maxPrice': float,  # max price for BASE asset in QUOTE
                                'tickSize': float,  # min price increment for QUOTE
                                'minQty': float,  # min order of BASE asset allowed
                                'maxQty': float,  # max order of BASE asset allowed
                                'stepSize': float,  # min increment of BASE asset allowed
                                'minNotional': float,  # min order in terms of QUOTE asset
                                'marketMinQty': float,  # min BASE asset for market order
                                'marketMaxQty': float,  # max BASE asset for market order
                                'marketStepSize': float  # min increment of BASE market order
                                },
}

# ###PAUL just a copy paster from binance foreign, needs editing
data_format_binance_us = {
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

    'order_filters_col_name_list': ['ticker', 'ticker_us', 'baseAsset', 'baseAssetPrecision', 'quoteAsset',
                                    'quoteAssetPrecision', 'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty',
                                    'stepSize', 'minNotional', 'marketMinQty', 'marketMaxQty', 'marketStepSize',
                                    ],

    'order_filters_name_type': {'ticker_us': str,  # us  corresponding to ticker_tracked
                                'baseAsset': str,  # 'BTC' in 'BTCUSDT'
                                'baseAssetPrecision': int,  # num of decimals for base
                                'quoteAsset': str,  # 'USD' in 'BTCUSD'
                                'quoteAssetPrecision': int,  # num of decimals for quote
                                'minPrice': float,  # min price for BASE in QUOTE
                                'maxPrice': float,  # max price for BASE asset in QUOTE
                                'tickSize': float,  # min price increment for QUOTE
                                'minQty': float,  # min order of BASE asset allowed
                                'maxQty': float,  # max order of BASE asset allowed
                                'stepSize': float,  # min increment of BASE asset allowed
                                'minNotional': float,  # min order in terms of QUOTE asset
                                'marketMinQty': float,  # min BASE asset for market order
                                'marketMaxQty': float,  # max BASE asset for market order
                                'marketStepSize': float  # min increment of BASE market order
                                },
}  ###PAUL just a copy paster from binance foreign, needs editing
data_format_kucoin = {
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

    'order_filters_col_name_list': ['ticker', 'ticker_us', 'baseAsset', 'baseAssetPrecision', 'quoteAsset',
                                    'quoteAssetPrecision', 'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty',
                                    'stepSize', 'minNotional', 'marketMinQty', 'marketMaxQty', 'marketStepSize',
                                    ],

    'order_filters_name_type': {'ticker_us': str,  # us  corresponding to ticker_tracked
                                'baseAsset': str,  # 'BTC' in 'BTCUSDT'
                                'baseAssetPrecision': int,  # num of decimals for base
                                'quoteAsset': str,  # 'USD' in 'BTCUSD'
                                'quoteAssetPrecision': int,  # num of decimals for quote
                                'minPrice': float,  # min price for BASE in QUOTE
                                'maxPrice': float,  # max price for BASE asset in QUOTE
                                'tickSize': float,  # min price increment for QUOTE
                                'minQty': float,  # min order of BASE asset allowed
                                'maxQty': float,  # max order of BASE asset allowed
                                'stepSize': float,  # min increment of BASE asset allowed
                                'minNotional': float,  # min order in terms of QUOTE asset
                                'marketMinQty': float,  # min BASE asset for market order
                                'marketMaxQty': float,  # max BASE asset for market order
                                'marketStepSize': float  # min increment of BASE market order
                                },
}  ###PAUL just a copy paster from binance foreign, needs editing
###PAUL just a copy paster from binance foreign, needs editing

data_format['binance_foreign'] = data_format_binance_foreign
data_format['binance_us'] = data_format_binance_us
data_format['kucoin'] = data_format_kucoin

# ### addresses
#
#
adresses = {'nano1_eth': '0x1f05cb5b0d8aab9299dBC6a0254432907B928843'}

# ### initialize ---- parameters and create the dictionary
#
#
params = dict()

params['constants'] = constants
params['universe'] = universe
params['keys'] = keys  ###PAUL consider not including in params
params['ports'] = ports
params['dirs'] = dirs
params['websocket_responses'] = websocket_responses
params['data_format'] = data_format
params['addresses'] = adresses
