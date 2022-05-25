#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-

# ###PAUL TODO anywhere data is written with a column "ticker", but it is actually a pair, consider fixing this
# TODO         its alot of work but also would make things nice for me... probably something to ignore for now
# ### imports
#
#
from copy import deepcopy
import platform
import sys
import os
import time

# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

# add algos
algos_dir = '/mnt/'
sys.path.append(algos_dir)

from algos.machine_specfic.config_machine_specific import params_machine_specific
from algos.local.configs_local import params_local


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

# ### machine specific and local params
#
#
device_info = {'device_name': params_machine_specific['device_name'],
               'os': str(platform.system()),
               }
active_services = params_machine_specific['active_services']
addresses = params_local['addresses']
keys = params_local['keys']

# ### important constants ###PAUL_todo
#
#
constants = {'os': str(platform.system()),  # ###PAUL alot relies on this, this is kindof the thing that should be here
             'email_port': 1025,
             }

# this is used in get_data_fp()... not worth trying to get rid of it
dirs = {'algos_dir': algos_dir,  # this is where the the algos directory is located on the machine
        # 'repo_dir': algos_dir + 'algos/',
        'data_dir': algos_dir + 'algos/data/',
        'ext_pack_dir': algos_dir + 'algos/ext_packages',
        'book_data_dir': algos_dir + 'algos/data/book/',
        'trade_data_dir': algos_dir + 'algos/data/trade/',
        'price_data_dir': algos_dir + 'algos/data/price/',
        'live_trade_data_dir': algos_dir + 'algos/data/live_trades/',
        'order_data_dir': algos_dir + 'algos/data/orders/',
        'live_data_dir': algos_dir + 'algos/data/live/',
        'port_data_dir': algos_dir + 'algos/data/ports/',
        }

# ### universe ---- what is collected, tracked, and traded via each exchange
#
#
universe = dict()

universe_binance_foreign = {'exchange': 'binance_foreign',

                            # all tickers tracked as a base asset in at least one pair on this exchange
                            'tickers_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp', 'xtz'],

                            # websocket communication for exchange... this is how requests are sent
                            'pair_collection_list': ['adausdt@trade', 'adabtc@trade',
                                                     'bnbusdt@trade', 'bnbbtc@trade',
                                                     'btcusdt@trade',
                                                     'dogeusdt@trade', 'dogebtc@trade',
                                                     'ethusdt@trade', 'ethbtc@trade',
                                                     'linkusdt@trade', 'linkbtc@trade',
                                                     'ltcusdt@trade', 'ltcbtc@trade',
                                                     'xlmusdt@trade', 'xlmbtc@trade',
                                                     'xrpusdt@trade', 'xrpbtc@trade',
                                                     'xtzusdt@trade', 'xtzbtc@trade', 'xtzeth@trade',
                                                     ],

                            # trade communication for exchange... this string is what is sent for trade requests
                            'pairs_tracked': ['ADAUSDT', 'ADABTC',
                                                'BNBUSDT', 'BNBBTC',
                                                'BTCUSDT',
                                                'DOGEUSDT', 'DOGEBTC',
                                                'ETHUSDT', 'ETHBTC',
                                                'LINKUSDT', 'LINKBTC',
                                                'LTCUSDT', 'LTCBTC',
                                                'XLMUSDT', 'XLMBTC',
                                                'XRPUSDT', 'XRPBTC',
                                                'XTZUSDT', 'XTZBTC', 'XTZETH',
                                                ],


                            # how to convert the pair in exchange format to universal
                            'convert_dict': {'universal': {'ADAUSDT': 'ADA-USDT', 'ADABTC': 'ADA-BTC',
                                                           'BNBUSDT': 'BNB-USDT', 'BNBBTC': 'BNB-BTC',
                                                           'BTCUSDT': 'BTC-USDT',  # this doesnt exist either 'BTCBTC',
                                                           'DOGEUSDT': 'DOGE-USDT', 'DOGEBTC': 'DOGE-BTC',
                                                           'ETHUSDT': 'ETH-USDT', 'ETHBTC': 'ETH-BTC',
                                                           'ETHUSDT': 'ETH-USDT', 'ETHBTC': 'ETH-BTC',
                                                           'ETHUSDT': 'ETH-USDT', 'ETHBTC': 'ETH-BTC',
                                                           'ETHUSDT': 'ETH-USDT', 'ETHBTC': 'ETH-BTC',
                                                           'LINKUSDT': 'LINK-USDT', 'LINKBTC': 'LINK-BTC',
                                                           'LTCUSDT': 'LTC-USDT', 'LTCBTC': 'LTC-BTC',
                                                           'XLMUSDT': 'XLM-USDT', 'XLMBTC': 'XLM-BTC',
                                                           'XRPUSDT': 'XRP-USDT', 'XRPBTC': 'XRP-BTC',
                                                           'XTZUSDT': 'XTZ-USDT', 'XTZBTC': 'XTZ-BTC',
                                                           'XTZETH': 'XTZ-ETH',
                                                           },
                                             },
                            }

universe_binance_us = {'exchange': 'binance_us',

                       # all tickers tracked as a base asset in at least one pair on this exchange
                       'tickers_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp', 'xtz'],

                       # how they are fed into the websocket function (as is)
                       'pair_collection_list': ['adausdt@trade', 'adabtc@trade', 'adausd@trade',
                                                'bnbusdt@trade', 'bnbbtc@trade', 'bnbusd@trade',
                                                'btcusdt@trade', 'btcbtc@trade', 'btcusd@trade',
                                                'dogeusdt@trade', 'dogebtc@trade', 'dogeusd@trade',
                                                'ethusdt@trade', 'ethbtc@trade', 'ethusd@trade',
                                                'linkusdt@trade', 'linkbtc@trade', 'linkusd@trade',
                                                'ltcusdt@trade', 'ltcbtc@trade', 'ltcusd@trade',
                                                'xlmusdt@trade', 'xlmbtc@trade', 'xlmusd@trade',
                                                'xtzbtc@trade', 'xtzusd@trade',
                                                ],

                       # trade communication for exchange... this string is what is sent for trade requests
                       'pairs_tracked': ['ADAUSDT', 'ADABTC', 'ADAUSD',
                                           'BNBUSDT', 'BNBBTC', 'BNBUSD',
                                           'BTCUSDT', 'BTCUSD',
                                           'DOGEUSDT', 'DOGEUSD',
                                           'ETHUSDT', 'ETHBTC', 'ETHUSD',
                                           'LINKUSDT', 'LINKBTC', 'LINKUSD',
                                           'LTCUSDT', 'LTCBTC', 'LTCUSD',
                                           'XLMUSDT', 'XLMUSD',
                                           'XTZBTC', 'XTZUSD',
                                           ],


                       # how to convert the pair in exchange format to universal
                       'convert_dict': {'universal': {'ADAUSDT': 'ADA-USDTether', 'ADABTC': 'ADA-BTC',
                                                      'ADAUSD': 'ADA-USDT',
                                                      'BNBUSDT': 'BNB-USDTether', 'BNBBTC': 'BNB-BTC',
                                                      'BNBUSD': 'BNB-USDT',
                                                      'BTCUSDT': 'BTC-USDTether', 'BTCUSD': 'BTC-USDT',
                                                      'DOGEUSDT': 'DOGE-USDTether', 'DOGEUSD': 'DOGE-USDT',
                                                      'ETHUSDT': 'ETH-USDTether', 'ETHBTC': 'ETH-BTC',
                                                      'ETHUSD': 'ETH-USDT',
                                                      'LINKUSDT': 'LINK-USDTether', 'LINKBTC': 'LINK-BTC',
                                                      'LINKUSD': 'LINK-USDT',
                                                      'LTCUSDT': 'LTC-USDTether', 'LTCBTC': 'LTC-BTC',
                                                      'LTCUSD': 'LTC-USDT',
                                                      'XLMUSDT': 'XLM-USDTether', 'XLMUSD': 'XLM-USDT',
                                                      'XTZBTC': 'XTZ-BTC', 'XTZUSD': 'XTZ-USDT',
                                                      },
                                        },
                       }

universe_kucoin = {'exchange': 'kucoin',

                   # tickers tracked as a base asset in at least one pair on this exchange
                   'tickers_tracked': ['btc', 'dag', 'eth', 'fil', 'icp', 'kava', 'kda', 'link', 'ltc', 'noia', 'qrdo',
                                       'req', 'tel', 'vra', 'xlm', 'xmr', 'xpr', 'xrp', 'xtz'
                                       ],

                   # how they are fed into the websocket function (as is)
                   'pair_collection_list': ['BTC-USDT', 'DAG-USDT', 'ETH-USDT', 'FIL-USDT', 'ICP-USDT', 'KAVA-USDT',
                                            'KDA-USDT', 'LINK-USDT', 'LTC-USDT', 'NOIA-USDT', 'QRDO-USDT', 'REQ-USDT',
                                            'TEL-USDT', 'VRA-USDT', 'XLM-USDT', 'XMR-USDT', 'XPR-USDT', 'XRP-USDT',
                                            'XTZ-USDT',
                                            ],

                   # trade communication for exchange... this string is what is sent for trade requests
                   # identical list as  pair_collection_list  above (for kucoin unlike binance)
                   'pairs_tracked': ['BTC-USDT', 'DAG-USDT', 'ETH-USDT', 'FIL-USDT', 'ICP-USDT', 'KAVA-USDT',
                                       'KDA-USDT', 'LINK-USDT', 'LTC-USDT', 'NOIA-USDT', 'QRDO-USDT', 'REQ-USDT',
                                       'TEL-USDT', 'VRA-USDT', 'XLM-USDT', 'XMR-USDT', 'XPR-USDT', 'XRP-USDT',
                                       'XTZ-USDT',
                                       ],


                   # how to convert the pair in exchange format to universal
                   'convert_dict': {'universal': {'BTC-USDT': 'BTC-USDT', 'DAG-USDT': 'DAG-USDT',
                                                  'ETH-USDT': 'ETH-USDT', 'FIL-USDT': 'FIL-USDT',
                                                  'ICP-USDT': 'ICP-USDT', 'KAVA-USDT': 'KAVA-USDT',
                                                  'KDA-USDT': 'KDA-USDT', 'LINK-USDT': 'LINK-USDT',
                                                  'LTC-USDT': 'LTC-USDT', 'NOIA-USDT': 'NOIA-USDT',
                                                  'QRDO-USDT': 'QRDO-USDT', 'REQ-USDT': 'REQ-USDT',
                                                  'TEL-USDT': 'TEL-USDT', 'VRA-USDT': 'VRA-USDT',
                                                  'XLM-USDT': 'XLM-USDT', 'XMR-USDT': 'XMR-USDT',
                                                  'XPR-USDT': 'XPR-USDT', 'XRP-USDT': 'XRP-USDT',
                                                  'XTZ-USDT': 'XTZ-USDT',
                                                  }
                                    },

                   }

# ### make the universal universe dict entry
# ### the value of all these dictionaries set to deep copies for their relative exchanges... reverse_dict generates
# ### the reverse dictionary flipping keys and values... this minimizes errors as only 1 conversion dict per exchange
#
#
universal = {'from_universal': {'binance_foreign':  reverse_dict(universe_binance_foreign['convert_dict']['universal']),
                              'binance_us': reverse_dict(universe_binance_us['convert_dict']['universal']),
                              'kucoin': reverse_dict(universe_kucoin['convert_dict']['universal']),
                              },
             'to_universal': {'binance_foreign': deepcopy(universe_binance_foreign['convert_dict']['universal']),
                              'binance_us': deepcopy(universe_binance_us['convert_dict']['universal']),
                              'kucoin': deepcopy(universe_kucoin['convert_dict']['universal']),
                              },
             }

universe['universal'] = universal
universe['binance_foreign'] = universe_binance_foreign
universe['binance_us'] = universe_binance_us
universe['kucoin'] = universe_kucoin

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

    'order_filters_name_type': {'exchange_ticker': str,  # us  corresponding to pairs_tracked
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

    'order_filters_name_type': {'exchange_ticker': str,  # us  corresponding to ticker_tracked
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

    # ###PAUL_todo TODO order managment for kucoin
    'order_filters_col_name_list': ['ticker', 'ticker_us', 'baseAsset', 'baseAssetPrecision', 'quoteAsset',
                                    'quoteAssetPrecision', 'minPrice', 'maxPrice', 'tickSize', 'minQty', 'maxQty',
                                    'stepSize', 'minNotional', 'marketMinQty', 'marketMaxQty', 'marketStepSize',
                                    ],

    # ###PAUL_todo TODO order managment for kucoin
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

# ### initialize ---- parameters and create the dictionary
#
#
params = dict()

params['device_info'] = device_info
params['constants'] = constants
params['active_services'] = active_services
params['addresses'] = addresses
params['keys'] = keys
params['dirs'] = dirs
params['universe'] = universe
params['data_format'] = data_format
