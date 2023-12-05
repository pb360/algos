create table if not exists algos_db.TradingSummary
(
    timestamp datetime,  -- summary metrics for the close of the minute
    symbol VARCHAR(32),
    exchange VARCHAR(32),
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    total_base_vol FLOAT,
    buyer_is_maker int,
    buyer_is_taker int,
    buy_base_vol FLOAT,
    sell_base_vol FLOAT,
    buy_quote_vol FLOAT,
    sell_quote_vol FLOAT,
    total_quote_vol FLOAT,
    buy_vwap FLOAT,
    sell_vwap FLOAT,
    vwap FLOAT
    time_created DateTime DEFAULT now()
    -- json JSON
)
ENGINE  = MergeTree()
ORDER BY timestamp;

CREATE TABLE IF NOT EXISTS algos_db.AlgosSignalNames
(
    signal_id Int32,
    signal_name String
) ENGINE = MergeTree()
ORDER BY signal_id;

CREATE TABLE IF NOT EXISTS algos_db.AlgosSignals
(
    timestamp DateTime,
    signal_id Int32,
    value Float64
) ENGINE = MergeTree()
ORDER BY timestamp;




