import sys
sys.path.insert(0, '../')
sys.path.insert(0, '../..')

from algos.utils import convert_date_format

from clickhouse_driver import Client as CH_Client
import datetime
import os
import pandas as pd
import pickle
import requests
import zipfile


def download_file(url, filename):
    """simple utility to download a file"""
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as fd:
        for chunk in response.iter_content(chunk_size=1024):
            fd.write(chunk)


def get_and_save_futures_csvs(date_str, file_prefix='BTCUSDT-1h-'):
    """gets binance futures klines data from their own website by downloading zip files and extracting them
    LIKELY BEST TO DEPRICATE TO AN IMPROVED VERSION OF
    get_spot_trade_data_convert_to_eaors_format_delete_csv_and_zip_file
    """
    filename = f"{file_prefix}{date_str}.zip"

    url = f"https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/{filename}"
    zip_filename = "test.zip"  # The name you want to save the file as
    csv_filename = filename.replace(".zip", ".csv")

    save_path = "/opt/shared/crypto/algos/data/temp_trades_storage/"  # Replace with your desired path
    extracted_kline_csv_path = save_path + 'kline_csvs/'

    # Full paths for the zip and csv files
    zip_filepath = os.path.join(save_path, zip_filename)
    csv_filepath = os.path.join(extracted_kline_csv_path, csv_filename)

    # Download the file
    # print(f"Downloading {zip_filename} to {zip_filepath}...")
    download_file(url, zip_filepath)

    # Extract the zip file
    # print(f"Extracting {zip_filepath}...")
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(extracted_kline_csv_path)


def convert_binance_trades_to_eaors(trades_df, exchange, pair):

    trades_df = trades_df.drop(columns=['depricated', 'quote_amount'])
    trades_df['side'] = trades_df['side'].map(
        {False: True, True: False})  # invert, their side bool is buyer_is_maker, ours is seller_is_maker
    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'] / 1000, unit='s')
    trades_df = trades_df.set_index('timestamp')
    trades_df['id'] = trades_df['id'].astype(str)
    trades_df['symbol'] = pair
    trades_df['exchange'] = exchange

    trades_df.index = trades_df.index.to_pydatetime()
    trades_df.reset_index(level=0, inplace=True)
    trades_df.rename(columns={'index': 'timestamp'}, inplace=True)

    return trades_df


def get_spot_trade_data_convert_to_eaors_format_delete_csv_and_zip_file(pair, date_tuple, exchange='binance'):
    """ what the name of the function says... """

    date_str = convert_date_format(date_tuple, 'string')
    pair = pair.upper()
    file_prefix = f"{pair}"
    filename = f"{file_prefix}-trades-{date_str}.zip"

    url = f"https://data.binance.vision/data/spot/daily/trades/{pair}/{filename}"
    zip_filename = f"{filename}"  # The name you want to save the file as
    csv_filename = filename.replace(".zip", ".csv")

    save_path = "/opt/shared/crypto/algos/data/temp_trades_storage/trade_csvs/"

    # Full paths for the zip and csv files
    zip_filepath = os.path.join(save_path, zip_filename)
    csv_filepath = os.path.join(save_path, csv_filename)

    # Download the file
    # print(f"Downloading {zip_filename} to {zip_filepath}...")
    download_file(url, zip_filepath)

    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(save_path)

    cols = ['id', 'price', 'amount', 'quote_amount', 'timestamp', 'side', 'depricated']

    trades_df = pd.read_csv(csv_filepath, names=cols)
    if trades_df.shape[0] < 1:
        raise ValueError

    # TODO: better to use a map for this (find out about universal ticker map from EAORS, probably want to plug that in here
    if pair == "BTCTUSD":
        table_pair = "BTC-TUSD"  # solely used for adding a '-' to the pair
    elif pair == "BTCUSDT":
        table_pair = "BTC-USDT"  # solely used for adding a '-' to the pair
    elif pair == "ETHTUSD":
        table_pair = "ETH-TUSD"  # solely used for adding a '-' to the pair
    elif pair == "ETHUSDT":
        table_pair = "ETH-USDT"  # solely used for adding a '-' to the pair
    else:
        print(f"ticker not mapped!")


    trades_df = convert_binance_trades_to_eaors(trades_df, exchange, pair=table_pair)

    delete_query = f"""ALTER TABLE algos_db.Trades 
    DELETE WHERE
        exchange = '{exchange}'
        AND symbol = '{table_pair}'
        AND toStartOfDay(timestamp) = toDateTime('{date_str}')"""

    ch_client = CH_Client('10.0.1.86', port='9009')

    ch_client.execute(delete_query)
    ch_client.execute('INSERT INTO algos_db.Trades VALUES', trades_df.to_dict('records'))

    os.remove(zip_filepath)
    os.remove(csv_filepath)

    return trades_df


def generate_dates(start_date, end_date, date_out_type='string'):
    while start_date <= end_date:
        if date_out_type == 'string':
            yield start_date.strftime('%Y-%m-%d')
        if date_out_type == 'tuple':
            yield convert_date_format(start_date, 'tuple_to_day')
        start_date += datetime.timedelta(days=1)


def download_binance_trades(pair, start_date, end_date, output='quiet', pickle_failed_days=False):
    i = 0
    failed_dates = []
    for date in generate_dates(start_date, end_date, date_out_type='tuple'):
        if i%1 == 0:
            print(date)
        try:
            # get_and_save_futures_csvs(date=date, file_prefix='BTCUSDT-1h-')  # requires sting date
            get_spot_trade_data_convert_to_eaors_format_delete_csv_and_zip_file(pair=pair,
                                                                                date_tuple=date,
                                                                                exchange='binance')
        except:
            if output == 'verbose':
                print(f"failed on {date}")
                failed_dates.append(date)
        i += 1

    if pickle_failed_days:
        fp = f"/opt/shared/crypto/algos/data/temp_trades_storage/trade_csvs/missing_days_for_{pair}.pickle"
        # SAVING
        pickle.dump(failed_dates, open(fp, "wb"))

    return failed_dates

if __name__ == "__main__":
    # ### SAVING DATA
    #
    #
    pair = f"ETHUSDT"
    start_date = datetime.datetime(2023, 8, 7)
    end_date = datetime.datetime(2023, 8, 14)

    download_binance_trades(pair=pair,
                            start_date=start_date,
                            end_date=end_date,
                            output='verbose',
                            pickle_failed_days=True)