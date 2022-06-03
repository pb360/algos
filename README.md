# algos
#### my next attempt at improving algorithmic trading methods


### this hard drive is meant to house trading algorithms and the data that they need to operate along with the data they produce during their operations

* <b> code that needs to be changed for each implementation </b> 
  * ./algos/config.py  - algos_dir must be defined
  

* drive layout - this drive should be placed at the root directory at <i> /mnt/algos/ </i>
  * <i> ./data/ </i>is the most important directory in the drive is specifically <i> /mnt/algos/data/* </i> which has a few main folders:
    * <i> live </i> -  data that is maintained in a live manner by some processes
      * i.e. <i> /mnt/algos/data/binance/trade/BTCUSDT </i> holds bitcoin trade data for binance which is recorded in real time
    * <i> ports </i> -  data created from various portfolios itself
      * i.e. <i> /mnt/algos/data/algo3/ </i> would be the directory that houses all orders placed/canceled and other data created by running the algo3 algorithm
      * NOTE: an algorithm can have more than one portfolio. For example, we could have <b> algo3 </b> have an equal portfolio and an sma portfolio. These would be found in
        * <i> algos/data/ports/algo3/orders/equal_weight </i>
        * <i> algos/data/ports/algo3/orders/sma_v1 </i>
  * <i> ./algo2 </i> - the directory for the algo2 algorithm development
    * each new strategy will have its on folder at the top level of <i> /mnt/algos/ </i>... each strategy has
      * <i> ./<strategy_name>/data/ </i> where strategy specific data would go
        * The spirit of the data folder within each strategy's folder is data that is essential for that portfolio, or things that are private
  * <i> ./machine_specific/ </i> - settings that are specific to each machine
    * EX: proton mail bridge password for sending emails (the bridge requires a different password on each device)
  * <i> ./local/ </i>
    * will house keys and private info which should not get out
  

## the largest revamp is the fact that <i> config.py </i> and <i> utils.py </i> need reworking
* I would really like to keep the utility and config file universial. 
  * This requires putting things like binance in many function inputs 
  * but this works better, that way the functionality is in there. 
  * Say I add kucoin, the framework then exists to implement logic in existing functionality while minimizing duplicate functionality 
  * Also it lets us import configs and utils as a broad file and use them... 
  * sounds like this is the best idea,, 
  * the approach will be copy the whole file over (we wont be pushing anything to git yet) 
    * then to remove and copy things to the new places they need to be 
    

## systemd services
* <b> located: </b>  <i> /usr/lib/systemd/system/  </i>

* general services 
    * <i> algos_binance_trades.service </i>  ---- gets the trades
* # all systemd services below still need re-working  
    * <i> algo2_binance_prices.service </i> creates price feed 
    * <i> algo2_watchdog.service </i>
        * makes sure we are running 
        * <b> need to add / remove bots that should be running on deployment / decomission </b> 
* bots 
    * <i> algo2_binance_bot_equal_split </i>
        * as the name says. splits investment in all tracked tickers equally, redistributes after $10 deviation 

* depricated services which need to be removed      
      * <i> algo2_binance_trades.service </i>
        * gets the trades
