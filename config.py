#!/home/paul/miniconda3/envs/binance/bin/python3
# -*- coding: utf-8 -*-

# ### imports
#
#
import platform
import sys
import os
import time

# ### time zone change... this must happen first and utils must be imported first
os.environ['TZ'] = 'UTC'
time.tzset()

# ###PAUL critical directory here... this must be correct for wherever the
# ###PAUL algos folder is on the  machine running it, then everything else will fall into line
algos_dir = '/mnt/'
sys.path.append(algos_dir)

from algos.machine_specfic.config_machine_specific import params_machine_specific
from algos.local.configs_local import params_local

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
constants = {
    'secs_of_trades_to_keep_live': 120,  # number of minutes to keep trades in live file
    'live_trade_trim_interval': 30,  # how mnay seconds betweeen trimming live files
    'no_trade_message_timeout': 30,  # secs required for no msg until new scraping process starts
    'data_scrape_heartbeat': 8,  # check no_trade_message_timeout in heartbeat_check()
    'make_prices_from_trades_interval': 10,  # currently located in orders.py
    'update_signal_interval': 10,  # how many seconds between MACD signal update
    'order_sma_v1_interval': 15,  # order on signal interval   ###PAUL_migration should move to algos
    'secondary_order_interval': 2,  # update market status and adjust orders ###PAUL_migration needs to mention binance
    'trade_watch_dog_interval': 30,
    # how long if no trade to restart trade collection w/ system-d ###PAUL_migration needs to mention binance
    'price_watch_dog_interval': 60,
    # how long if no price update to re-run orders.py w/ system-d ###PAUL_migration needs to mention binance
    'order_watch_dog_interval': 60,
    # how long if order check not updated to restart any live_bot
    'os': str(platform.system()),
    'signal_based_order_interval': 10,
    'email_port': 1025,
}
# ###PAUL_migration  ^^^^^^    this can stay however will need some updates   ^^^^^^


exchanges = ['binance_foreign', 'binance_us', ]

systemd_control = dict()

active_data_exchanges = ['binance_foreign', 'binance_us',
                         'kucoin',
                         ]  # where trades are able to be collected live
active_ports = params_machine_specific['active_ports']

# ###PAUL_todo
# ### this dictionary is not currently used. but this is the format i would like to move to
# ### maybe rename it the watchdog dictionary. also consider moving this to its own file or something which would
# ### be checked every so often to know whether to pull services or something.
#
#
# names of systemd services used to collect trades for each exchange
active_services_OLD_VERSION = {'trades': {'binance_foreign': 'algos_scrape_trades_binance_foreign',
                                          'binance_us': 'algos_scrape_trades_binance_us',
                                          'kucoin': 'algos_scrape_trades_kucoin',
                                          'silver': 'get to it',
                                          },
                               'prices': {'crypto': 'algos_pipe_trades_to_prices',
                                          },
                               'ports': {'sma_v1_equal_dist': {'service_name': 'algos_live_bot_sma_v1_equal_dist',
                                                               'exchange': 'binance_us',
                                                               },
                                         'markowitz_v1': {'service_name': 'algos_live_bot_markowitz_v1',
                                                          'exchange': 'binance_us',
                                                          },
                                         'ml_v1': {'service_name': 'algos_live_bot_ml_v1',
                                                   'exchange': 'binance_us',
                                                   },
                                         },
                               }

active_services = {'trades': {'binance_foreign': {'service': 'algos_scrape_trades_binance_foreign',
                                                  'script': '/mnt/algos/data_scrape_binance_foreign.py', },
                              'binance_us': {'service': 'algos_scrape_trades_binance_us',
                                             'script': '/mnt/algos/data_scrape_binance_us.py', },
                              'kucoin': {'service': 'algos_scrape_trades_kucoin',
                                         'script': '/mnt/algos/data_scrape_kucoin.py', },
                              'silver': {'service': 'algos_scrape_trades_silver_comex',
                                         'script': '/mnt/algos/data_scrape_silver_comex.py', },
                              },
                   'prices': {
                              'crypto': {'service': 'algos_pipe_trades_to_prices',
                                         'script': '/mnt/algos/data_pipe_prices_from_trades.py', },
                              },
                   'ports': {'sma_v1_equal_dist': {'service': 'algos_live_bot_sma_v1_equal_dist',
                                                   'script': '/mnt/algos/live_bot_sma_v1_equal_dist.py',
                                                   'exchange': 'binance_us',
                                                   },
                             'markowitz_v1': {'service': 'algos_live_bot_markowitz_v1',
                             'script': '/mnt/algos/live_bot_sma_v1_equal_dist get er done .py',
                                              'exchange': 'binance_us',
                                              },
                             'ml_v1': {'service': 'algos_live_bot_ml_v1',
                                       'exchange': 'binance_us',
                                       },
                             },
                   }

# used for watchdog... ticker of interest...
ticker_to_check_trades = {'binance_foreign': 'BTCUSDT',
                          'binance_us': 'BTCUSD',
                          'kucoin': 'BTC-USDT',
                          }

no_trade_time = {'binance_foreign': 60,
                 'binance_us': 90,  # binance_us kept restarting so give it a longer time...
                 'kucoin': 90,
                 }

systemd_control['active_data_exchanges'] = active_data_exchanges
systemd_control['active_ports'] = active_ports
systemd_control['active_services'] = active_services
systemd_control['ticker_to_check_trades'] = ticker_to_check_trades
systemd_control['ticker_to_check_trades'] = ticker_to_check_trades
systemd_control['no_trade_time'] = no_trade_time

exchanges_we_want_to_add_end_to_end_support_for = ['kucoin', ]

# ###PAUL_migration .... this should probably just go away, or be migrated to ./utils.py thats the only thing that'll
# ###PAUL_migration .... us it with get_data_fp()
dirs = {'algos_dir': algos_dir,  # this is where the the algos directory is located on the machine
        'repo_dir': algos_dir + 'algos/',
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
# ###PAUL_migration .... this should probably just go away, or be migrated to ./utils.py thats the only thing that'll
# ###PAUL_migration .... us it with get_data_fp()


# ### universe ---- what is collected, tracked, and traded via each exchange
#
#
universe = dict()
"""doc string for this dictionary because it is a bitch 
###PAUL_todo make a universial entry such that 
universe['universe']
is a reference to all or as many of the individual tickers for each exchange. this will make comparitive work easier 
can then make a 
for exchange in exchanges: 
    get_data(prices / trades, ticker, exchange) and do what you want to do (combine, compare...)  
"""

# ###PAUL_refractor for the live bot some temporary variables that will be in the universial dict will be below
# ###PAUL_refracto eventually these will need to move to params['universe']['universal']


universal = {}

universe_binance_foreign = {'coins_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp', 'xtz'],

                            'tick_collection_list': ['adausdt@trade', 'adabtc@trade',
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
                            # MUST BE ALL LOWER CASE.. not all exist but too busy to update now

                            'tickers_tracked': ['ADAUSDT', 'ADABTC',
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

                            'tickers_foreign_to_us_dict': {'ADAUSDT': 'ADAUSD', 'ADABTC': 'ADABTC',
                                                           'BNBUSDT': 'BNBUSD', 'BNBBTC': 'BNBBTC',
                                                           'BTCUSDT': 'BTCUSD',  # this doesnt exist either 'BTCBTC',
                                                           'DOGEUSDT': 'DOGEUSD',
                                                           'ETHUSDT': 'ETHUSD', 'ETHBTC': 'ETHBTC',
                                                           'LINKUSDT': 'LINKUSD', 'LINKBTC': 'LINKBTC',
                                                           'LTCUSDT': 'LTCUSD', 'LTCBTC': 'LTCBTC',
                                                           'XLMUSDT': 'XLMUSD',
                                                           'XRPUSDT': 'XRPUSD', 'XRPBTC': 'XRPBTC',
                                                           'XTZUSDT': 'XTZUSD', 'XTZBTC': 'XTZBTC',
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
                                                           'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                           },

                            # not correct, just place holder because it will be needed
                            'exchange_to_universial_tick_dict': {'ADAUSD': 'ADA-USDT', 'ADABTC': 'ADABTC',
                                                                 'BNBUSD': 'BNB-USDT', 'BNBBTC': 'BNBBTC',
                                                                 'BTCUSD': 'BTC-USDT',
                                                                 # this doesnt exist either 'BTCBTC',
                                                                 'DOGEUSD': 'DOGE-USDT',
                                                                 'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                                 'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                                 'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                                 'XLMUSD': 'XLMUSDT',
                                                                 'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                                 'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                                 },

                            # not correct, just place holder because it will be needed
                            'universial_to_exchange_tick_dict': {'ADAUSD': 'ADA-USDT', 'ADABTC': 'ADABTC',
                                                                 'BNBUSD': 'BNB-USDT', 'BNBBTC': 'BNBBTC',
                                                                 'BTCUSD': 'BTC-USDT',
                                                                 # this doesnt exist either 'BTCBTC',
                                                                 'DOGEUSD': 'DOGE-USDT',
                                                                 'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                                 'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                                 'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                                 'XLMUSD': 'XLMUSDT',
                                                                 'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                                 'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                                 },
                            }  # ###PAUL just a copy paster from binance foreign, needs editing

# ###PAUL just a copy paster from binance foreign, needs editing
universe_binance_us = {'coins_tracked': ['ada', 'bnb', 'btc', 'doge', 'eth', 'link', 'ltc', 'xlm', 'xrp', 'xtz'],

                       'tick_collection_list': ['adausdt@trade', 'adabtc@trade', 'adausd@trade',
                                                'bnbusdt@trade', 'bnbbtc@trade', 'bnbusd@trade',
                                                'btcusdt@trade', 'btcbtc@trade', 'btcusd@trade',
                                                'dogeusdt@trade', 'dogebtc@trade', 'dogeusd@trade',
                                                'ethusdt@trade', 'ethbtc@trade', 'ethusd@trade',
                                                'linkusdt@trade', 'linkbtc@trade', 'linkusd@trade',
                                                'ltcusdt@trade', 'ltcbtc@trade', 'ltcusd@trade',
                                                'xlmusdt@trade', 'xlmbtc@trade', 'xlmusd@trade',
                                                # 'xrpusdt@trade', 'xrpbtc@trade',
                                                # 'xrpusd@trade',  # trades still come?
                                                'xtzbtc@trade', 'xtzusd@trade',
                                                ],
                       # MUST BE ALL LOWER CASE.. not all exist but too busy to update now

                       'tickers_tracked': ['ADAUSDT', 'ADABTC', 'ADAUSD',
                                           'BNBUSDT', 'BNBBTC', 'BNBUSD',
                                           'BTCUSDT', 'BTCUSD',
                                           'DOGEUSDT', 'DOGEUSD',
                                           'ETHUSDT', 'ETHBTC', 'ETHUSD',
                                           'LINKUSDT', 'LINKBTC', 'LINKUSD',
                                           'LTCUSDT', 'LTCBTC', 'LTCUSD',
                                           'XLMUSDT', 'XLMUSD',
                                           # 'XRPUSDT', 'XRPBTC',  # 'XRPUSD', commented out from here because no USD
                                           'XTZBTC', 'XTZUSD',
                                           ],

                       # ###PAUL_refractor
                       # ###PAUL_refractor... temp hoder while. shouldn't be here
                       'tickers_traded': ['ADAUSDT', 'BNBUSDT', 'BTCUSDT', 'DOGEUSDT',
                                          'ETHUSDT', 'LINKUSDT', 'LTCUSDT', 'XLMUSDT', ],
                       # ###PAUL_refractor... temp hoder while. shouldn't be here
                       # ###PAUL_refractor

                       'tickers_foreign_to_us_dict': {'ADAUSDT': 'ADAUSD', 'ADABTC': 'ADABTC',
                                                      'BNBUSDT': 'BNBUSD', 'BNBBTC': 'BNBBTC',
                                                      'BTCUSDT': 'BTCUSD',  # this doesnt exist either 'BTCBTC',
                                                      'DOGEUSDT': 'DOGEUSD',
                                                      'ETHUSDT': 'ETHUSD', 'ETHBTC': 'ETHBTC',
                                                      'LINKUSDT': 'LINKUSD', 'LINKBTC': 'LINKBTC',
                                                      'LTCUSDT': 'LTCUSD', 'LTCBTC': 'LTCBTC',
                                                      'XLMUSDT': 'XLMUSD',
                                                      'XRPUSDT': 'XRPUSD', 'XRPBTC': 'XRPBTC',
                                                      'XTZUSDT': 'XTZUSD', 'XTZBTC': 'XTZBTC',
                                                      },  # ###PAUL this can be copied from binance_foreign

                       'tickers_us_to_foreign_dict': {'ADAUSD': 'ADAUSDT', 'ADABTC': 'ADABTC',
                                                      'BNBUSD': 'BNBUSDT', 'BNBBTC': 'BNBBTC',
                                                      'BTCUSD': 'BTCUSDT',  # this doesnt exist either 'BTCBTC',
                                                      'DOGEUSD': 'DOGEUSDT',
                                                      'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                      'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                      'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                      'XLMUSD': 'XLMUSDT',
                                                      'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                      'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                      },  # ###PAUL this can be copied from binance_foreign

                       # not correct, just place holder because it will be needed
                       'exchange_to_universial_tick_dict': {'ADAUSD': 'ADA-USDT', 'ADABTC': 'ADABTC',
                                                            'BNBUSD': 'BNB-USDT', 'BNBBTC': 'BNBBTC',
                                                            'BTCUSD': 'BTC-USDT',  # this doesnt exist either 'BTCBTC',
                                                            'DOGEUSD': 'DOGE-USDT',
                                                            'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                            'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                            'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                            'XLMUSD': 'XLMUSDT',
                                                            'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                            'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                            },

                       # not correct, just place holder because it will be needed
                       'universial_to_exchange_tick_dict': {'ADAUSD': 'ADA-USDT', 'ADABTC': 'ADABTC',
                                                            'BNBUSD': 'BNB-USDT', 'BNBBTC': 'BNBBTC',
                                                            'BTCUSD': 'BTC-USDT',  # this doesnt exist either 'BTCBTC',
                                                            'DOGEUSD': 'DOGE-USDT',
                                                            'ETHUSD': 'ETHUSDT', 'ETHBTC': 'ETHBTC',
                                                            'LINKUSD': 'LINKUSDT', 'LINKBTC': 'LINKBTC',
                                                            'LTCUSD': 'LTCUSDT', 'LTCBTC': 'LTCBTC',
                                                            'XLMUSD': 'XLMUSDT',
                                                            'XRPUSD': 'XRPUSDT', 'XRPBTC': 'XRPBTC',
                                                            'XTZUSD': 'XTZUSDT', 'XTZBTC': 'XTZBTC',
                                                            },
                       }  # ###PAUL just a copy paster from binance foreign, needs editing

universe_kucoin = {'coins_tracked': ['btc', 'dag', 'eth', 'fil', 'icp', 'kava', 'kda', 'link', 'ltc', 'noia', 'qrdo',
                                     'req', 'tel', 'vra', 'xlm', 'xmr', 'xpr', 'xrp', 'xtz'
                                     ],

                   # list which is looped over for in data scraper (sometimes funny format like '@trade' needed...)
                   'tick_collection_list': ['BTC-USDT', 'DAG-USDT', 'ETH-USDT', 'FIL-USDT', 'ICP-USDT', 'KAVA-USDT',
                                            'KDA-USDT', 'LINK-USDT', 'LTC-USDT', 'NOIA-USDT', 'QRDO-USDT', 'REQ-USDT',
                                            'TEL-USDT', 'VRA-USDT', 'XLM-USDT', 'XMR-USDT', 'XPR-USDT', 'XRP-USDT',
                                            'XTZ-USDT',
                                            ],

                   # identical list as  tick_collection_list above (for kucoin)
                   'tickers_tracked': ['BTC-USDT', 'DAG-USDT', 'ETH-USDT', 'FIL-USDT', 'ICP-USDT', 'KAVA-USDT',
                                       'KDA-USDT', 'LINK-USDT', 'LTC-USDT', 'NOIA-USDT', 'QRDO-USDT', 'REQ-USDT',
                                       'TEL-USDT', 'VRA-USDT', 'XLM-USDT', 'XMR-USDT', 'XPR-USDT', 'XRP-USDT',
                                       'XTZ-USDT',
                                       ],

                   # this variable should really be individually generated in each live_bot script.. ###PAUL maybe is?
                   'tickers_traded': ['KDA-USDT'
                                      # some day youll have more here........
                                      ],

                   # I like the <base>-<quote> structure in all caps... this will be the universial standard.. for when
                   # that actually needs to happen
                   'exchange_to_universial_tick_dict': {'BTC-USDT': 'BTC-USDT', 'DAG-USDT': 'DAG-USDT',
                                                        'ETH-USDT': 'ETH-USDT', 'FIL-USDT': 'FIL-USDT',
                                                        'ICP-USDT': 'ICP-USDT', 'KAVA-USDT': 'KAVA-USDT',
                                                        'KDA-USDT': 'KDA-USDT', 'LINK-USDT': 'LINK-USDT',
                                                        'LTC-USDT': 'LTC-USDT', 'NOIA-USDT': 'NOIA-USDT',
                                                        'QRDO-USDT': 'QRDO-USDT', 'REQ-USDT': 'REQ-USDT',
                                                        'TEL-USDT': 'TEL-USDT', 'VRA-USDT': 'VRA-USDT',
                                                        'XLM-USDT': 'XLM-USDT', 'XMR-USDT': 'XMR-USDT',
                                                        'XPR-USDT': 'XPR-USDT', 'XRP-USDT': 'XRP-USDT',
                                                        'XTZ-USDT': 'XTZ-USDT',
                                                        },

                   'universial_to_exchange_tick_dict': {'BTC-USDT': 'BTC-USDT', 'DAG-USDT': 'DAG-USDT',
                                                        'ETH-USDT': 'ETH-USDT', 'FIL-USDT': 'FIL-USDT',
                                                        'ICP-USDT': 'ICP-USDT', 'KAVA-USDT': 'KAVA-USDT',
                                                        'KDA-USDT': 'KDA-USDT', 'LINK-USDT': 'LINK-USDT',
                                                        'LTC-USDT': 'LTC-USDT', 'NOIA-USDT': 'NOIA-USDT',
                                                        'QRDO-USDT': 'QRDO-USDT', 'REQ-USDT': 'REQ-USDT',
                                                        'TEL-USDT': 'TEL-USDT', 'VRA-USDT': 'VRA-USDT',
                                                        'XLM-USDT': 'XLM-USDT', 'XMR-USDT': 'XMR-USDT',
                                                        'XPR-USDT': 'XPR-USDT', 'XRP-USDT': 'XRP-USDT',
                                                        'XTZ-USDT': 'XTZ-USDT',
                                                        },

                   }  # ###PAUL just a copy paster from binance foreign, needs editing
# ###PAUL just a copy paster from binance foreign, needs editing

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
    # ###PAUL issue here... see the websocket example... this will need processing each trade to format
    # ###PAUL into the binance format... i would as long as possible (which is forseeably forever) prefer to convert
    # ###PAUL all trade level data to this format. it works and all functionality is built off the assumption it is
    # ###PAUL like this
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
                                # 'M': 'ignore'
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

params['device_info'] = device_info
params['constants'] = constants
params['exchanges'] = exchanges
params['systemd_control'] = systemd_control
params['universe'] = universe
params['keys'] = keys  ###PAUL consider not including in params
params['dirs'] = dirs
params['data_format'] = data_format
params['addresses'] = adresses
