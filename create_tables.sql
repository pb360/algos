-- WEIRD STUFF HAPPENING IN THE VS CODE CONSUL CONNECTION... ALL OF THIS SHIT WORKS WHEN I RUN IT IN THE CLICKHOUSE CONSOLE
-- IM NOT GOING TO FIGHT VS CODE RIGHT NOW SO THIS IS JUST A STAGING AREA 

-- -- -- -- -- -- DROP TABLES SO THEY CAN BE REMADE 
-- -- -- -- -- DROP TABLE algos_db.Trades;
-- -- -- -- -- DROP TABLE algos_db.TradingSideConversion;
-- -- -- -- -- DROP TABLE algos_db.TradingSummary;
-- -- -- -- -- DROP TABLE algos_db.AlgosSignalNames;
-- -- -- -- -- DROP TABLE algos_db.AlgosSignals;

CREATE DATABASE IF NOT EXISTS algos_db;

CREATE TABLE IF NOT EXISTS algos_db.TradingSideConversion
( 
    side_int UInt8,      --  1  or  0 
    side_str VARCHAR(4)  -- buy or sell 
)
ENGINE=MergeTree()
ORDER BY side_str;


CREATE TABLE IF NOT EXISTS algos_db.Trades
(
    timestamp DateTime64,
    exchange VARCHAR(12),
    symbol VARCHAR(12),
    id String, 
    price Float64,
    amount Float64,
    buyer_is_taker UInt8

)
ENGINE = MergeTree()
ORDER BY (timestamp, id);


CREATE TABLE IF NOT EXISTS algos_db.TradingSummary
(
    timestamp DateTime64,  -- summary metrics for the close of the minute
    exchange VARCHAR(),
    symbol VARCHAR(12),
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    total_base_vol Float64,
    buyer_is_maker int,
    buyer_is_taker int,
    buy_base_vol Float64,
    sell_base_vol Float64,
    buy_quote_vol Float64,
    sell_quote_vol Float64,
    total_quote_vol Float64,
    buy_vwap Float64,
    sell_vwap Float64,
    vwap Float64,
    time_created DateTime64 DEFAULT now()
)
ENGINE  = MergeTree()
ORDER BY timestamp;


CREATE TABLE IF NOT EXISTS algos_db.AlgosSignalNames
(
    signal_id Int32,
    signal_name  String  -- allow as String because so few 
) ENGINE = MergeTree()
ORDER BY signal_id;


CREATE TABLE IF NOT EXISTS algos_db.AlgosSignals
(
    timestamp DateTime64,
    signal_id Int32,
    value Float64
) ENGINE = MergeTree()
ORDER BY timestamp;


CREATE TABLE IF NOT EXISTS algos_db.Positions
(
    timestamp DateTime64,
    strategy String,
    algo String,
    sub_account String,
    leg_group_id Int64,
    instrument String,
    exchange String,
    size Float64,
    mid_price Float64,
    currency_price Float64,
    currency_name String,
    funding_pnl Float64,
    margin Float64,
    ignore UInt8,
    adjustment UInt8
) ENGINE = MergeTree
ORDER BY timestamp;


--------------------         POSITIONS TABLE    example entry from python dict        --------------------
--------------------
-- 'strategy': 'peak_bottom____spot',
-- 'timestamp': ts,
-- 'leg_group_id': int(ts.timestamp() * 1000),
-- 'instrument': symbol,
-- 'size': qty,
-- 'mid_price': last_price,  # ###PAUL_usd_denomination TODO: i think this is okay to go
-- 'currency_price': 1,
-- 'currency_name': 'USD'