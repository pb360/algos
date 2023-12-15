
# ### define things needed
symbol = 'BTC-USDT'
exchange = 'binance'

# Extract the zip file
print(f"Extracting {zip_filepath}...")
with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
    zip_ref.extractall(save_path)

# Load the data into a pandas DataFrame
print(f"Loading {csv_filepath} into a pandas DataFrame...")
df = pd.read_csv(csv_filepath)

# Now df is a pandas DataFrame with the data
print(df)

# ### run once
#
try:
    if read_and_process_binance_trades_once:
        pass
except NameError:
    read_and_process_binance_trades_once = True
    print(f"reading in downloaded trades")

    # ### read it in and make a copy
    #
    save_path = f"{data_dir}temp_trades_storage"  # Replace with your desired path
    zip_filename = "BTCUSDT-trades-2023-02.zip"  # The name you want to save the file as
    csv_filename = zip_filename.replace(".zip", ".csv")
    csv_filepath = os.path.join(save_path, csv_filename)
    df = pd.read_csv(csv_filepath)
    og_df = deepcopy(df)

# df = deepcopy(og_df)

# ### process trades data to match EAORS format
#
df.columns = ['timestamp', 'id', 'price', 'amount', 'side']
df['side'] = df['side'].map({False: 1, True: 0})  # invert, their side bool is buyer_is_maker, ours is seller_is_maker
df['timestamp'] = pd.to_datetime(df['timestamp'] / 1000, unit='s')
df = df.set_index('timestamp')
df['symbol'] = symbol
df['exchange'] = exchange
