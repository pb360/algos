import sys

sys.path.insert(0, "../")
sys.path.insert(0, "../..")

import argparse
from algos.config import params
from algos.utils import (
    get_secret,
    init_ch_client,
    convert_date_format,
    check_if_dir_exists_and_make, 
    query_trading_summary,
    check_df_for_missing_data_and_no_activity, 
    make_day_of_trading_summary_push_to_db,
    make_trading_summary_from_trades_in_batches,  )
from ccxt import binanceus as binanceus_nonpro 
import concurrent.futures
import datetime
import os
import pandas as pd
import pickle
import requests
import traceback
import zipfile
from zipfile import BadZipFile


data_dir = params["dirs"]["data_dir"]

binanceus_nonpro = binanceus_nonpro({
    'apiKey': get_secret('BINANCE_DATA_1_PUBLIC'),
    'secret': get_secret('BINANCE_DATA_1_PRIVATE'),
})
markets = binanceus_nonpro.load_markets()


def generate_dates(start_date, end_date, date_out_type="string"):

    if type(start_date) != datetime.datetime: 
        start_date = convert_date_format(start_date, 'datetime')
    if type(end_date) != datetime.datetime: 
        end_date = convert_date_format(end_date, 'datetime')

    while start_date <= end_date:
        if date_out_type == "string":
            yield start_date.strftime("%Y-%m-%d")
        if date_out_type == "tuple":
            yield convert_date_format(start_date, "tuple_to_day")
        start_date += datetime.timedelta(days=1)


def download_file(url, filename):
    """simple utility to download a file"""
    response = requests.get(url, stream=True)
    with open(filename, "wb") as fd:
        for chunk in response.iter_content(chunk_size=1024):
            fd.write(chunk)


def get_download_url(exchange, exchange_pair, filename):

    if exchange == "binance":
        # to check when a ticker becomes available just check manually via 
       # https://data.binance.vision/?prefix=data/spot/daily/trades/BTCUSDT/
        url = f"https://data.binance.vision/data/spot/daily/trades/{exchange_pair}/{filename}"
    elif exchange == "binance_us":
        # check here for start date of pair:  https://www.binance.us/institutions/market-history
        url = f"https://data.binance.us/public_data/spot/daily/trades/{exchange_pair}/{filename}"
    elif exchange == 'kraken': 
        print(f"need to implement binance us ")
        raise ValueError
    else:
        raise ValueError

    return url 


def read_trades_from_exchange_specific_format_csv_convert_to_algos(exchange, csv_filepath, ccxt_pair): 
    if exchange == "binance":  # foreign doesn't include a header... 
        cols = ["id", "price", "amount", "dollar_amount", "timestamp", "isBuyerMaker", "depricated"]
        trades_df = pd.read_csv(csv_filepath , names=cols)
        
        trades_df['buyer_is_taker'] = trades_df['isBuyerMaker'].map({False: 1, True: 0})
        trades_df = trades_df.drop(columns=['isBuyerMaker', 'depricated', ])

    elif exchange == "binance_us":  # binance us does include the header 
        trades_df = pd.read_csv(csv_filepath)

        # cols = [id, price, qty, quote_qty, time, is_buyer_maker ] 
        trades_df['buyer_is_taker'] = trades_df['is_buyer_maker'].map({False: 1, True: 0})
        trades_df = trades_df.rename(columns={'time': 'timestamp', 'qty': 'amount'})
        trades_df = trades_df.drop(columns=['is_buyer_maker', 'quote_qty'])

    elif exchange == 'kraken': 
        print(f"need to implement binance us ")
        raise ValueError
    else:
        print(f"exchange not supported ")
        raise ValueError
    
    if trades_df.shape[0] < 1: 
        raise ValueError

    trades_df["timestamp"] = pd.to_datetime(trades_df["timestamp"] / 1000, unit="s")
    trades_df = trades_df.set_index("timestamp")
    trades_df["id"] = trades_df["id"].astype(str)
    trades_df["symbol"] = ccxt_pair
    trades_df["exchange"] = exchange

    trades_df.index = trades_df.index.to_pydatetime()
    trades_df.reset_index(level=0, inplace=True)
    trades_df.rename(columns={"index": "timestamp"}, inplace=True)

    return trades_df 


def insert_df_in_batches(client, df, table_name='algos_db.Trades', batch_size=25000):
    total_rows = len(df)

    for start in range(0, total_rows, batch_size):
        end = min(start + batch_size, total_rows)
        batch = df.iloc[start:end]
        client.execute(
            f"INSERT INTO {table_name} VALUES", 
            batch.to_dict("records")
        )
        # print(f"Inserted rows {start} to {end} out of {total_rows}")


def get_spot_trades_convert_to_algos_delete_temp_csv_n_zip(ccxt_pair, date_tuple, exchange):
    """what the name of the function says..."""

    print(f"{exchange} -- {ccxt_pair} -- {date_tuple} ---- starting download, convert, and write to db")
    exchange_pair = markets[ccxt_pair]['id']
    
    date_str = convert_date_format(date_tuple, "string")
    exchange_pair = exchange_pair.upper()
    file_prefix = f"{exchange_pair}"
    filename = f"{file_prefix}-trades-{date_str}.zip"
    zip_filename = f"{filename}"  # The name you want to save the file as
    csv_filename = filename.replace(".zip", ".csv")

    save_path = f"{data_dir}temp_trades_storage/trade_csvs/"
    check_if_dir_exists_and_make(dir=save_path)

    # Full paths for the zip and csv files
    zip_filepath = os.path.join(save_path, zip_filename)
    csv_filepath = os.path.join(save_path, csv_filename)


    url = get_download_url(exchange=exchange, exchange_pair=exchange_pair, filename=filename)

    # download and extract 
    download_file(url, zip_filepath)

    # try to open it, early data often has bad zips 
    try: 
        with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
            zip_ref.extractall(save_path)
    except BadZipFile: 
        print(f"BadZipFile on {date_tuple} \n"*5)
        os.remove(zip_filepath)
        return None 

    # maybe combine these two 
    trades_df = read_trades_from_exchange_specific_format_csv_convert_to_algos(exchange=exchange, 
                                                                               csv_filepath=csv_filepath, 
                                                                               ccxt_pair=ccxt_pair)
    
    delete_query = f"""ALTER TABLE algos_db.Trades 
    DELETE WHERE
        exchange = '{exchange}'
        AND symbol = '{ccxt_pair}'
        AND toStartOfDay(timestamp) = toDateTime('{date_str}')"""

    ch_client = init_ch_client()

    ch_client.execute(delete_query)

    insert_df_in_batches(client=ch_client, df=trades_df, table_name='algos_db.Trades', batch_size=25000)

    print(f"fully ran db delete / write {exchange} -- {ccxt_pair} -- {date_tuple}") 

    os.remove(zip_filepath)
    os.remove(csv_filepath)

    return trades_df


def check_to_increase_start_date(exchange, symbol, requested_start_date): 
    query = f"""
    SELECT MAX(timestamp) AS max_timestamp
    FROM algos_db.Trades
    WHERE exchange = '{exchange}'
    AND symbol = '{symbol}'
    """
    
    ch_client = init_ch_client()
    latest_data_date = ch_client.execute(query)[0][0]
    
    if type(requested_start_date) != datetime.datetime: 
        requested_start_date = convert_date_format(requested_start_date, 'datetime.datetime')
    
    start_date = latest_data_date if requested_start_date < latest_data_date else requested_start_date
    
    state_date = convert_date_format(start_date, 'tuple_to_day') 
    
    return start_date 


def download_binance_trades(exchange, ccxt_pair, start_date, end_date, output="quiet", pickle_failed_days=False):
    i = 0
    failed_dates = []

    # ###PAUL TODO: hook for getting lastest date of trading, redefine start_date IF IT IS LATER THAN GIVEN START DATE 
    # note that if its earlier than a given start deate then it is likely that 
    start_date = check_to_increase_start_date(exchange=exchange, symbol=ccxt_pair, requested_start_date=start_date)

    for date in generate_dates(start_date, end_date, date_out_type="tuple"):
        get_spot_trades_convert_to_algos_delete_temp_csv_n_zip(ccxt_pair=ccxt_pair, 
                                                               date_tuple=date,
                                                               exchange=exchange)
        i += 1

    if pickle_failed_days:
        fp = f"{data_dir}temp_trades_storage/trade_csvs/missing_days_for_{pair}.pickle"
        # SAVING
        pickle.dump(failed_dates, open(fp, "wb"))

    return failed_dates


def download_binance_trades_multithreaded(exchange, ccxt_pair, start_date, end_date, output="quiet", pickle_failed_days=False, n_workers=5):
    failed_dates = []

    def worker(date):
        try:
            get_spot_trades_convert_to_algos_delete_temp_csv_n_zip(ccxt_pair=ccxt_pair, 
                                                                   date_tuple=date,
                                                                   exchange=exchange)
            return None  # No error
        except Exception as e:
            print(e)
            traceback.print_exc()
            return date  # Return the date if there was an error

    dates = generate_dates(start_date, end_date, date_out_type="tuple")

    with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
        results = executor.map(worker, dates)

    for date, result in zip(dates, results):
        if result is not None:
            failed_dates.append(result)
            print(f"Failed for date: {date}")

    if pickle_failed_days and failed_dates:
        fp = f"{data_dir}temp_trades_storage/trade_csvs/missing_days_for_{ccxt_pair}.pickle"
        pickle.dump(failed_dates, open(fp, "wb"))

    return failed_dates


def download_wrapper(params):
    try:
        # Unpack the parameters and call the download function
        download_binance_trades(params['exchange'], params['ccxt_pair'], params['start_date'], params['end_date'])
    except Exception as e: 
        print(f"\n \n \n the error was \n \n \n {e}")
        traceback.print_exc()


# ### an aside function unused, don't want to delete 
def get_and_save_futures_klines_csvs(date_str, file_prefix="BTCUSDT-1h-"):
    """gets binance futures klines data from their own website by downloading zip files and extracting them
    LIKELY BEST TO DEPRICATE TO AN IMPROVED VERSION OF
    get_spot_trades_convert_to_algos_delete_temp_csv_n_zip
    """
    filename = f"{file_prefix}{date_str}.zip"

    url = f"https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/{filename}"
    zip_filename = "test.zip"  # The name you want to save the file as
    csv_filename = filename.replace(".zip", ".csv")

    save_path = f"{data_dir}temp_trades_storage/"  # Replace with your desired path
    extracted_kline_csv_path = save_path + "kline_csvs/"

    # Full paths for the zip and csv files
    zip_filepath = os.path.join(save_path, zip_filename)
    csv_filepath = os.path.join(extracted_kline_csv_path, csv_filename)

    check_if_dir_exists_and_make(dir=None, fp=None)

    # Download the file
    # print(f"Downloading {zip_filename} to {zip_filepath}...")
    download_file(url, zip_filepath)

    # Extract the zip file
    # print(f"Extracting {zip_filepath}...")
    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        zip_ref.extractall(extracted_kline_csv_path)


def edit_start_date_of_trades_to_download(trades_to_download):
    

    return None 


# ###PAUL TODO: add verification for unique trading IDs 
def check_db_trading_summary_for_duplicates_delete_for_exchange_and_symbol_if_any(exchange, symbol, ch_client): 
    trading_summary = query_trading_summary(exchange=exchange,
                                            symbol=symbol,
                                            start_date=None,
                                            end_date=None,
                                            columns='all',
                                            ch_client=ch_client)
    
    num_duplicates = trading_summary.index.duplicated().sum()
    
    if num_duplicates > 0: 
        query = f"""ALTER TABLE algos_db.TradingSummary
                    DELETE WHERE exchange = '{exchange}' AND symbol = '{symbol}'
                 """
        ch_client.execute(query) 

        return True

    else: 
        return False

        
def check_continuity_of_trades_convert_to_summary_rewrite_missing_data(exchange_symbol_tuple, ch_client=None):
    """utility function that  
    
    ONLY SUPPORTS BINANCE (as binance is the only one with historical data) 1
    """

    if ch_client is None: 
        ch_client = init_ch_client() 

    exchange, symbol = exchange_symbol_tuple
    
    
    deleted_trading_summary = check_db_trading_summary_for_duplicates_delete_for_exchange_and_symbol_if_any(exchange=exchange, 
                                                                                                            symbol=symbol, 
                                                                                                            ch_client=ch_client) 
    
    # get the minimum dates from trades ande trading_summary for the given exchange / symbol  
    min_trades_timestamp = ch_client.query_dataframe(f"""SELECT MIN(timestamp)
                                                          FROM algos_db.Trades
                                                          WHERE exchange = '{exchange}'
                                                          AND symbol = '{symbol}' 
                                                          """)
    min_trades_timestamp = min_trades_timestamp['min_timestamp_'][0] 
    trades_start_tuple_to_day = convert_date_format(min_trades_timestamp, 'tuple_to_day')
    
    epoch_time = datetime.datetime.fromtimestamp(0)
    
    if deleted_trading_summary == True:
        min_summary_timestamp = epoch_time
        same_day = False
    
    else:
        min_summary_timestamp = ch_client.query_dataframe(f"""SELECT MIN(timestamp)
                                                              FROM algos_db.TradingSummary
                                                              WHERE exchange = '{exchange}'
                                                              AND symbol = '{symbol}' 
                                                              """)

        min_summary_timestamp = min_summary_timestamp['min_timestamp_'][0] 
        
        same_day = (min_trades_timestamp.year == min_summary_timestamp.year) \
                    and (min_trades_timestamp.month == min_summary_timestamp.month) \
                    and (min_trades_timestamp.day == min_summary_timestamp.day)
        
            
    if deleted_trading_summary == True or epoch_time == min_summary_timestamp or same_day == False:
        # for flow of code, this gets trashed and requeried in the while loop 
        trading_summary = make_trading_summary_from_trades_in_batches(exchange=exchange,
                                                                        symbol=symbol, 
                                                                        start_date=trades_start_tuple_to_day,
                                                                        end_date=None,  # goes to the current day. 
                                                                        freq='D')
    


    last_run_missing = None
    list_of_dates = []   # set to empty list because if we get an empty list after running everything, then we are good to go, all data is clean 
    
    i=0
    while last_run_missing != list_of_dates: 
        i += 1
        print(i) 
        last_run_missing = list_of_dates 
        
        trading_summary = query_trading_summary(exchange=exchange,
                                                symbol=symbol,
                                                start_date=min_trades_timestamp,
                                                end_date=None,
                                                columns='all',
                                                ch_client=ch_client)
    
        print(f"STARTING continunity and conversion process  ----  {exchange}  --  {symbol} \n"*1)
        
        missing_and_no_activity_info = \
            check_df_for_missing_data_and_no_activity(df=trading_summary, freq='min', gap_len=60, col='total_base_vol')
        
        set_of_date_tuples = set() 
        
        for start, end in missing_and_no_activity_info['no_activity_info']['start_end_tuple_list_no_vol']:
            print(f"start: {start} ---- end: {end}")
            date_range = pd.date_range(start=start, end=end, freq='min')
            date_range = date_range.normalize().unique()  # rounds everything to day, take only unique values 
            for date in date_range:
                date = convert_date_format(date, 'tuple_to_day')
                set_of_date_tuples.add(date) 
        list_of_dates = sorted(list(set_of_date_tuples))
    
        for date in list_of_dates: 
            get_spot_trades_convert_to_algos_delete_temp_csv_n_zip(ccxt_pair=symbol, date_tuple=date, exchange=exchange)
            make_day_of_trading_summary_push_to_db(exchange, symbol, date, overwrite_mode='python_side', ch_client=ch_client)
            
    return None 


def query_trades_each_day_make_trading_summary_push_to_clickhouse(exchange,
                                                                  start_date,
                                                                  end_date,
                                                                  pairs_list,
                                                                  pair=None,
                                                                  backup_pair=None,
                                                                  ):
    """
    input:
    pairs_list [(pair, backup_pair), ...] ---- or use one pair and backup_pair
    """

    if type(start_date) != datetime.datetime:
        convert_date_format(start_date, 'datetime')
    if type(end_date) != datetime.datetime:
        convert_date_format(end_date, 'datetime')

    date_range_arr = pd.date_range(start=start_date, end=end_date, freq='D')

    missing_dates_filled = []
    failed_dates = []

    if pair != None:
        pairs_list = [(pair, backup_pair)]

    for pair, backup_pair in pairs_list:
        for i in range(date_range_arr.shape[0] - 1):
            iter_start_date = date_range_arr[i]
            iter_end_date = date_range_arr[i + 1]
            if i % 5 == 0:
                print(f"iter {i} ---- {pair} for ---- {iter_start_date} --> iter_end_date: {iter_end_date}")

            try:
                trades = get_trades_data(exchange=exchange,
                                         symbol=pair,
                                         start_date=iter_start_date,
                                         end_date=iter_end_date,
                                         source='EAORS')

                if type(trades) == int or trades.shape[0] < 100:
                    if trades == 0:
                        print(f"    - no trades for iter_start_date: {iter_start_date} --> iter_end_date: "
                              f"{iter_end_date}")

                    trades = get_trades_data(exchange=exchange,
                                             symbol=backup_pair,
                                             start_date=iter_start_date,
                                             end_date=iter_end_date,
                                             source='EAORS')

                    if type(trades) == int or trades.shape[0] < 100:
                        raise ValueError

                    missing_dates_filled.append((iter_start_date, iter_end_date))

                trading_summary = convert_trades_df_to_trading_summary(trades)
                trading_summary = fill_trading_summary_interpolating_missing_minutes(trading_summary)

                push_trading_summary_to_clickhouse(trading_summary, exchange, pair)

                if trading_summary.shape[0] < 1440:
                    import pdb
                    pdb.set_trace()

            except:
                print(f"    - failed on {iter_start_date} --> iter_end_date: {iter_end_date}")
                failed_dates.append((iter_start_date, iter_end_date))

    return failed_dates


# # ### START:  SINGLE TICKER DEPTH FIRST VERSION ---- really for BTC mainly as it has so much data 
    # # ##          SINGLE TICKER DEPTH FIRST VERSION 
    # # #           SINGLE TICKER DEPTH FIRST VERSION 
    parser = argparse.ArgumentParser(description='process input parameters')

    # Define arguments
    parser.add_argument('--exchange', type=str, required=True, help='Exchange name (e.g., binance, binance_us)')
    parser.add_argument('--ccxt_pair', type=str, required=True, help='Currency pair (e.g., BTCUSDT, BTCUSD)')
    parser.add_argument('--start_date', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), required=True, help='End date in YYYY-MM-DD format')

    # Parse arguments
    args = parser.parse_args()

    # Use arguments
    exchange = args.exchange
    ccxt_pair = args.ccxt_pair
    start_date = args.start_date
    end_date = args.end_date

    # download_binance_trades(
    download_binance_trades_multithreaded(
        exchange=exchange, 
        ccxt_pair=ccxt_pair,
        start_date=start_date,
        end_date=end_date,
        output="verbose",
        pickle_failed_days=True,
        n_workers=18,
    )

    # # #         SINGLE TICKER DEPTH FIRST VERSION 
    # # ##        SINGLE TICKER DEPTH FIRST VERSION 
    # # ### END:  SINGLE TICKER DEPTH FIRST VERSION 

    
    
    # ### START:  MULTI THREADED BREADTH FIRST (many tickers, one date ) 
    # ##
    # # 
    trades_to_download = [
                # {'exchange': 'binance', 'ccxt_pair': 'BTC/USDT',    'start_date': (2021, 8, 14),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ETH/USDT',    'start_date': (2019, 1, 27),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'LINK/USDT',   'start_date': (2019, 1, 16),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'KDA/USDT',    'start_date': (2022, 3, 11),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ROSE/USDT',   'start_date': (2020, 11, 19),  'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ICP/USDT',    'start_date': (2021, 6, 10),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'AVAX/USDT',   'start_date': (2021, 6, 10),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'SOL/USDT',    'start_date': (2020, 8, 11),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'BNB/USDT',    'start_date': (2017, 11, 6),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'BNB/USDT',    'start_date': (2019, 7, 5),    'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'GRT/USDT',    'start_date': (2020, 12, 17),  'end_date': (2023, 12, 18)},

                                        
                # https://data.binance.vision/?prefix=data/spot/daily/trades/BTCUSDT/
                # https://www.binance.us/institutions/market-history
                
                # {'exchange': 'binance_us', 'ccxt_pair': 'BTC/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   # USD PAIRS RUN TILL (2023, 7, 15) 
                # {'exchange': 'binance_us', 'ccxt_pair': 'ETH/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   # USD PAIRS RUN TILL (2023, 7, 15) 
                # {'exchange': 'binance_us', 'ccxt_pair': 'LINK/USD',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 15)}, 
                # {'exchange': 'binance_us', 'ccxt_pair': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ROSE/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ICP/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'AVAX/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'SOL/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'BNB/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'GRT/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},

                # {'exchange': 'binance_us', 'ccxt_pair': 'BTC/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ETH/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'LINK/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ROSE/USDT',   'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ICP/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'AVAX/USDT',   'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'SOL/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'BNB/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'GRT/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                ]

    # Use ThreadPoolExecutor to execute the function in multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:

        # Map the download_wrapper function to the list of dictionaries
        executor.map(download_wrapper, trades_to_download)
    # # 
    # ##
    # ### MULTI THREADED BREADTH FIRST (many tickers, one date ) 

    print('done')


def main():
    # # ### START:  SINGLE TICKER DEPTH FIRST VERSION ---- really for BTC mainly as it has so much data 
    # # ##          SINGLE TICKER DEPTH FIRST VERSION 
    # # #           SINGLE TICKER DEPTH FIRST VERSION 
    parser = argparse.ArgumentParser(description='process input parameters')

    # Define arguments
    parser.add_argument('--exchange', type=str, required=True, help='Exchange name (e.g., binance, binance_us)')
    parser.add_argument('--ccxt_pair', type=str, required=True, help='Currency pair (e.g., BTCUSDT, BTCUSD)')
    parser.add_argument('--start_date', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), required=True, help='End date in YYYY-MM-DD format')

    # Parse arguments
    args = parser.parse_args()

    # Use arguments
    exchange = args.exchange
    ccxt_pair = args.ccxt_pair
    start_date = args.start_date
    end_date = args.end_date

    # download_binance_trades(
    download_binance_trades_multithreaded(
        exchange=exchange, 
        ccxt_pair=ccxt_pair,
        start_date=start_date,
        end_date=end_date,
        output="verbose",
        pickle_failed_days=True,
        n_workers=18,
    )

    # # #         SINGLE TICKER DEPTH FIRST VERSION 
    # # ##        SINGLE TICKER DEPTH FIRST VERSION 
    # # ### END:  SINGLE TICKER DEPTH FIRST VERSION 

    
    
    # ### START:  MULTI THREADED BREADTH FIRST (many tickers, one date ) 
    # ##
    # # 
    trades_to_download = [
                # {'exchange': 'binance', 'ccxt_pair': 'BTC/USDT',    'start_date': (2021, 8, 14),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ETH/USDT',    'start_date': (2019, 1, 27),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'LINK/USDT',   'start_date': (2019, 1, 16),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'KDA/USDT',    'start_date': (2022, 3, 11),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ROSE/USDT',   'start_date': (2020, 11, 19),  'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'ICP/USDT',    'start_date': (2021, 6, 10),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'AVAX/USDT',   'start_date': (2021, 6, 10),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'SOL/USDT',    'start_date': (2020, 8, 11),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'BNB/USDT',    'start_date': (2017, 11, 6),   'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'BNB/USDT',    'start_date': (2019, 7, 5),    'end_date': (2023, 12, 18)},
                {'exchange': 'binance', 'ccxt_pair': 'GRT/USDT',    'start_date': (2020, 12, 17),  'end_date': (2023, 12, 18)},

                                        
                # https://data.binance.vision/?prefix=data/spot/daily/trades/BTCUSDT/
                # https://www.binance.us/institutions/market-history
                
                # {'exchange': 'binance_us', 'ccxt_pair': 'BTC/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   # USD PAIRS RUN TILL (2023, 7, 15) 
                # {'exchange': 'binance_us', 'ccxt_pair': 'ETH/USD',     'start_date': (2019, 9, 17), 'end_date': (2023, 7, 15)},   # USD PAIRS RUN TILL (2023, 7, 15) 
                # {'exchange': 'binance_us', 'ccxt_pair': 'LINK/USD',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 15)}, 
                # {'exchange': 'binance_us', 'ccxt_pair': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ROSE/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ICP/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'AVAX/USD',   'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'SOL/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'BNB/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'GRT/USD',    'start_date': (2019, 9, 17),  'end_date': (2023, 7, 15)},

                # {'exchange': 'binance_us', 'ccxt_pair': 'BTC/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ETH/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'LINK/USDT',    'start_date': (2019, 9, 17), 'end_date': (2023, 12, 15)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'KDA/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ROSE/USDT',   'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'ICP/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'AVAX/USDT',   'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'SOL/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'BNB/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                # {'exchange': 'binance_us', 'ccxt_pair': 'GRT/USDT',    'start_date': (2019, 9, 17),  'end_date': (2023, 12, 19)},
                ]

    # Use ThreadPoolExecutor to execute the function in multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:

        # Map the download_wrapper function to the list of dictionaries
        executor.map(download_wrapper, trades_to_download)
    # # 
    # ##
    # ### MULTI THREADED BREADTH FIRST (many tickers, one date ) 

    print('done')


if __name__ == "__main__":
    main()