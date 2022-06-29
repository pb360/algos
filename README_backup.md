# algos readme

### this hard drive is meant to house trading algorithms and the data that they need to operate along with the data they produce during their operations



* drive layout - this drive should be placed at the root directory at <i> /mnt/algos/ </i>
  * <i> ./data/ </i>is the most important directory in the drive is specifically <i> /mnt/algos/data/* </i> which has a few main folders:
    * <i> live </i> -  data that is maintained in a live manner by some processes
      * i.e. <i> /mnt/algos/data/binance/trade/BTCUSDT </i> holds bitcoin trade data for binance which is recorded in real time
    * <i> ports </i> -  data created from various portfolios itself
      * i.e. <i> /mnt/algos/data/algo3/ </i> would be the directory that houses all orders placed/canceled and other data created by running the algo3 algorithm
      * NOTE: an algorithm can have more than one portfolio. For example, we could have <b> algo3 </b> have an equal portfolio and an sma portfolio. These would be found in
        * <i> algos/data/ports/algo3/orders/equal_weight </i>
        * <i> algos/data/ports/algo3/orders/sma_v1 </i>
  * <i> ./algo2 </i> - the directory for the algo2 algorithm
    * each new strategy will have its on folder at the top level of <i> /mnt/algos/ </i>... each strategy has
      * <i> ./<strategy_name>/data/ </i> where strategy specific data would go
        * The spirit of the data folder within each strategy's folder is data that is essential for that portfolio, or things that are private 
