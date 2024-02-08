# ### local imports
import sys
sys.path.insert(0, '..')  # for local imports from the top directory
from algos.config import params
from algos.utils import (update_trading_summary_table, init_ch_client)
import datetime

from datetime import timedelta
import pandas as pd
import time

ch_client = init_ch_client() 

def main(): 

    # ### function input / preset variables
    decision_delay = 15

    # functionality to be wrapped for db updates / trading
    now = pd.to_datetime(datetime.datetime.now())
    next_time_to_check = (now.floor('min') + timedelta(seconds=decision_delay)).to_pydatetime()
    trading_summaries_tracked = params['active_services']['trading_summaries']

    num_updates = -1
    while True:
        try:
            now = pd.to_datetime(datetime.datetime.now())

            if now > next_time_to_check:
                num_updates += 1
                if num_updates % 1 == 0:
                    print(f"update iter #: {num_updates} ---- updates {decision_delay} seconds after the start of every minute")
                for exchange in trading_summaries_tracked.keys():
                    if exchange == 'processing_interval': 
                        continue
                    for pair in trading_summaries_tracked[exchange]:
                        print(f"    - pair: {pair} ---- exchange: {exchange}")

                        update_trading_summary_table(exchange=exchange, symbol=pair, ch_client=ch_client)

                next_time_to_check = next_time_to_check + timedelta(minutes=1)
            
            time.sleep(1)
        
        except Exception as e:
            print(f"higheset level exception in `update_trading_summary`")
            print(f"{e}")


if __name__ == '__main__':
    main() 


print("in update_trading_summary.py somehow got to the end of the script")
