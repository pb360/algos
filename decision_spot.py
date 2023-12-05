# ###PAUL this cell will not run propely... "_spot" is added to each function defined here to prevent naming issues but within the function the changes weren't made
#         could fix this, want to keep because its done differently
#         this was transported to this file, unlikely I will want to work with it again but its here if you do

def reset_state_dict_spot(whose_turn=None, who_just_went=None):
    both_none = whose_turn is None and who_just_went is None
    both_given = whose_turn is not None and who_just_went is not None
    if both_none or both_given:
        raise SyntaxError

    activations_dict = {'buy': {'threshold': {'state': False, 'cool_down': 0},
                                'pred_dist_from_min': {'state': False, 'cool_down': 0},
                                'price_dist_from_min': {'state': False, 'cool_down': 0},
                                },
                        'sell': {'threshold': {'state': False, 'cool_down': 0},
                                 'pred_dist_from_max': {'state': False, 'cool_down': 0},
                                 'price_dist_from_max': {'state': False, 'cool_down': 0},
                                 'trailing_stop_loss': {'state': False, 'cool_down': 0},
                                 },
                        }

    if who_just_went is not None:
        if who_just_went == 'buy':
            whose_turn = 'sell'
        else:
            whose_turn = 'buy'

    state_dict = {'whose_turn': whose_turn,
                  'lowest_pred': 100,
                  'highest_pred': -100,
                  'lowest_price': 7777777777.77,
                  'highest_price': -7777777777.77,
                  'activations': deepcopy(activations_dict),
                  }

    return state_dict


def get_state_spot(price, pred, B_or_S, switch_name, requests_dict, state_dict, ):
    """ gets the state of a switch (flipped True for on or False for off) given parameters

    Outputs:
        cond (bool): which is fed into the update_activation function
    """

    # state to be returned
    state = None

    if B_or_S == 'buy':
        if switch_name == 'threshold':
            value = requests_dict['buy']['threshold']['value']
            state = (value is None or pred < value)
        if switch_name == 'pred_dist_from_min':
            value = requests_dict['buy']['pred_dist_from_min']['value']
            state = (value is None or value < pred - state_dict['lowest_pred'])
        if switch_name == 'price_dist_from_min':
            value = requests_dict['buy']['price_dist_from_min']['value']
            threshold_price = (1 + value) * state_dict['lowest_price']
            state = (value is None or price > threshold_price)

    if B_or_S == 'sell':
        if switch_name == 'threshold':
            value = requests_dict['sell']['threshold']['value']
            state = (value is None or pred > value)
        if switch_name == 'pred_dist_from_max':
            value = requests_dict['sell']['pred_dist_from_max']['value']
            state = (value is None or value < state_dict['highest_pred'] - pred)
        if switch_name == 'price_dist_from_max':
            value = requests_dict['sell']['price_dist_from_max']['value']
            threshold_price = (1 - value) * state_dict['highest_price']
            state = (value is None or price < threshold_price)
        if switch_name == 'trailing_stop_loss':
            value = requests_dict['sell']['trailing_stop_loss']['value']
            threshold_price = (1 - value) * state_dict['highest_price']
            state = (value is None or price < threshold_price)

    if state == None:
        import pdb;
        pdb.set_trace()

    return state


def update_activation_v3_spot(state, B_or_S, switch_name, requests_dict, state_dict):
    """
    input:
        state (bool): describing whether the switch should be turned on or not
    """
    #     global state_dict

    cool_down_requested = requests_dict[B_or_S][switch_name]['cool_down']

    if state:
        state_dict['activations'][B_or_S][switch_name]['state'] = True
        if cool_down_requested is not None:
            state_dict['activations'][B_or_S][switch_name]['cool_down'] = 5 * 60 * 60
    else:
        if cool_down_requested is not None:
            _ = state_dict['activations'][B_or_S][switch_name]['cool_down'] - 1
            state_dict['activations'][B_or_S][switch_name]['cool_down'] = max(_, 0)

            if 0 >= state_dict['activations'][B_or_S][switch_name]['cool_down']:
                state_dict['activations'][B_or_S][switch_name]['state'] = False
                state_dict['activations'][B_or_S][switch_name]['cool_down'] = 0

    return state_dict


def get_buys_and_sells_v3_spot(preds, prices, requests_dict):
    """gets buys / sells for an interval

    inputs:
        preds (pd.Series): output of neural network, series NEEDS datetime index
        prices (pd.Series): series of prices
        requests_dict (dict): of structure above (ctrl+f...)
    output:
        transacts (dict): {'buy' {'idxs': [], 'datetimes': [], 'prices': []},
                          'sell': { " } }
    """

    # create a state_dict with a good initial state
    state_dict = reset_state_dict(whose_turn='buy')

    # get prices and a light quality check
    # prices = prices.loc[preds.index]['vwap']
    idxs = np.array(prices.index)
    prices = np.array(prices)
    assert (prices.shape[0] == preds.shape[0])

    # buy and sell times (in integer index form)
    transacts = {'buy': {'idxs': [],
                         'datetimes': [],
                         'prices': [],
                         },
                 'sell': {'idxs': [],
                          'datetimes': [],
                          'prices': [],
                          },
                 }

    # import pdb; pdb.set_trace()

    prices = np.append(prices, prices[-1])  ###PAUL_del_later
    # going through preds
    for i, pred in enumerate(preds):
        #         if i % 100000 == 0:
        #             print(i)
        # add pred / price to dataframe since last transaction
        price = prices[i]  ###PAUL_del_later
        index = idxs[i]

        # update low / high prediction since last transaction
        if pred < state_dict['lowest_pred']:
            state_dict['lowest_pred'] = pred
        if pred > state_dict['highest_pred']:
            state_dict['highest_pred'] = pred
        if price < state_dict['lowest_price']:
            state_dict['lowest_price'] = price
        if price > state_dict['highest_price']:
            state_dict['highest_price'] = price

        # get current state and then update the activation for each switch
        whose_turn = state_dict['whose_turn']

        # loop over all switches in the whose turn variable
        for switch in state_dict['activations'][whose_turn].keys():
            # ###PAUL_todo in the future instead of feeding price & pred in, maybe better to make
            # ###PAUL_todo this into a np.array of (n. p) and feed in a (1, p) array where
            # price and pred would be the first two... this allows expandable conditions to be met
            # such as limit orders... this would be updated above where index/price are declared
            cond = get_state(price, pred, whose_turn, switch, requests_dict, state_dict)
            state_dict = update_activation_v3(cond, whose_turn, switch, requests_dict, state_dict)

        # make list of all activations for whose turn it is
        activation_list = []
        activation_dict = {}
        for switch in state_dict['activations'][whose_turn].keys():
            state = state_dict['activations'][whose_turn][switch]['state']
            activation_list.append(state)
            activation_dict[switch] = state

        # if any activation on this list is true, whose_turn takes its turn
        single_override = False
        for switch in requests_dict['overrides'][whose_turn]:
            if activation_dict[switch]:
                single_override = True

        # if two or more of these switches are activated then send an order
        double_override = False
        num_true = 0
        for switch in requests_dict['any_two'][whose_turn]:
            if activation_dict[switch]:
                num_true += 1
        if num_true >= 2:
            double_override = True

            # if all switches are activated mark that time as a transaction
        if np.all(np.array(activation_list)) or single_override or double_override:
            transacts[whose_turn]['idxs'].append(i + 1)
            transacts[whose_turn]['datetimes'].append(preds.index[i])
            transacts[whose_turn]['prices'].append(price)
            state_dict = reset_state_dict(who_just_went=whose_turn)

    transacts['buy']['datetimes'] = pd.core.indexes.datetimes.DatetimeIndex(transacts['buy']['datetimes'])
    transacts['sell']['datetimes'] = pd.core.indexes.datetimes.DatetimeIndex(transacts['sell']['datetimes'])

    return transacts


def get_PnL_spot(transacts, fee=0.1, test_method=False):
    """gets PnL for transacts dict produced by get_buys_and_sells_v3(preds, prices, requests_dict)

    input:
        transats (dict): {'buy' {'idxs': [], 'datetimes': [], 'prices': []},
                          'sell': { " } }
        fee (float): in % by volume
    out:
        value: proportional change in value of the portfolio
    ###PAUL_TODO redo for shorting
    """

    value = 1
    test_value = 1
    last_sell = transacts['buy']['prices'][0]

    for buy, sell in zip(transacts['buy']['prices'], transacts['sell']['prices']):
        value = value * sell / buy * (1 - fee / 100) * (1 - fee / 100)
        inv_value = test_value * buy / last_sell * (
                    1 - fee / 100)  # the name value here is misleading, not value of portfolio
        last_buy = buy
        test_value = inv_value * sell / last_buy * (1 - fee / 100)
        last_sell = sell

    if test_method == True:
        value = test_value

    return value


def grid_search_parameters_spot(preds, prices, thresholds, pred_dists, price_dists, stop_limits):
    st = time.time()

    # lists for dataframe
    interval_list = []
    thresh_list = []
    pred_dist_list = []
    price_dist_list = []
    stop_limit_list = []
    pnl_list = []
    num_sells_list = []

    # inter counter
    i = -1

    ###PAUL this will be desirable later.. need to implement this function in current data form
    # preds = make_ewm_series_of_preds(interval, preds, ewm_c=0.0075)

    for thresh in thresholds:
        for pred_dist in pred_dists:
            for price_dist in price_dists:
                for stop_limit in stop_limits:

                    i += 1
                    if i % 10 == 0 or i < 5:
                        print(i)

                    requests_dict = {'buy': {'threshold': {'value': -thresh, 'cool_down': 30 * 60},
                                             'pred_dist_from_min': {'value': pred_dist, 'cool_down': 30 * 60},
                                             # value in real terms
                                             'price_dist_from_min': {'value': price_dist, 'cool_down': 30 * 60},
                                             # proportional to price
                                             },
                                     'sell': {'threshold': {'value': thresh, 'cool_down': 30 * 60},
                                              'pred_dist_from_max': {'value': pred_dist, 'cool_down': 30 * 60},
                                              # in real terms
                                              'price_dist_from_max': {'value': price_dist, 'cool_down': 30 * 60},
                                              # proportional to price
                                              'trailing_stop_loss': {'value': stop_limit, 'cool_down': 10}
                                              },
                                     'overrides': {'buy': [],
                                                   'sell': [
                                                       'trailing_stop_loss',
                                                   ],
                                                   },
                                     'any_two': {'buy': [],
                                                 # ['threshold', 'pred_dist_from_min', 'price_dist_from_min',],
                                                 'sell': [],
                                                 # ['threshold', 'pred_dist_from_min', 'price_dist_from_min',],
                                                 },
                                     }

                    transacts = get_buys_and_sells_v3(preds,
                                                      prices,
                                                      requests_dict,
                                                      )

                    pnl = get_PnL(transacts)

                    # interval_list.append(interval)  # not in interval system, may need one, keep as reminder
                    thresh_list.append(thresh)
                    pred_dist_list.append(pred_dist)
                    price_dist_list.append(price_dist)
                    stop_limit_list.append(stop_limit)
                    pnl_list.append(pnl)
                    num_sells_list.append(len(transacts['sell']['idxs']))

    df_dict = {
        # 'interval': interval_list,
        'thresh': thresh_list,
        'pred_dist': pred_dist_list,
        'price_dist': price_dist_list,
        'stop_limit': stop_limit_list,
        'pnl': pnl_list,
        'cycles': num_sells_list,
    }

    pnl_df = pd.DataFrame.from_dict(df_dict)

    et = time.time()
    tt = et - st
    print(f"total time: {tt}")

    return pnl_df
    return False


def make_requests_dict_spot(**decision_params):
    requests_dict = \
        {
            'buy': {
                'threshold': {'value': -decision_params['threshold'], 'cool_down': 30 * 60},
                'pred_dist_from_min': {'value': decision_params['pred_dist'], 'cool_down': 30 * 60},
                # value in real terms
                'price_dist_from_min': {'value': decision_params['price_dist'], 'cool_down': 30 * 60},
                # proportional to price
            },
            'sell': {
                'threshold': {'value': decision_params['threshold'], 'cool_down': 30 * 60},
                'pred_dist_from_max': {'value': decision_params['pred_dist'], 'cool_down': 30 * 60},
                # in real terms
                'price_dist_from_max': {'value': decision_params['price_dist'], 'cool_down': 30 * 60},
                # proportional to price
                'trailing_stop_loss': {'value': decision_params['stop_limit'], 'cool_down': 10}
            },

            'overrides': {
                'buy': [],
                'sell': [
                    'trailing_stop_loss',
                ],
            },

            'any_two': {
                'buy': [
                    # ['threshold', 'pred_dist_from_min', 'price_dist_from_min',],
                ],
                'sell': [
                    # ['threshold', 'pred_dist_from_min', 'price_dist_from_min',],
                ],
            },
        }
    return requests_dict


def get_port_value_and_return_series_spot_spot(prices, preds, model_results, fee=0.001):
    """gets the portfolio over time

    input:
        prices (pd.Series): prices during the backtest
        preds (pd.Series): y_hat
        transacts (dict): format in
    """

    num_buys = len(model_results['transacts']['buy']['idxs'])
    num_sells = len(model_results['transacts']['sell']['idxs'])

    if num_buys - num_sells == 0:
        pass
    elif num_buys - num_sells == 1:
        model_results['transacts']['buy']['idxs'] = model_results['transacts']['buy']['idxs'][:-1]
        model_results['transacts']['buy']['datetimes'] = model_results['transacts']['buy']['datetimes'][:-1]
        model_results['transacts']['buy']['prices'] = model_results['transacts']['buy']['prices'][:-1]
        num_buys = num_sells
    else:
        raise ValueError

    mask_prices_with_preds = np.logical_and(preds.index[0] <= prices.index, prices.index <= preds.index[-1])
    price_idxs_with_preds_index = prices[mask_prices_with_preds].index
    port_val = pd.Series(data=0, index=price_idxs_with_preds_index, dtype=float)
    port_val.sort_index(inplace=True)

    last_sell_dt = port_val.index[0]  # for start make last sell the beginning
    port_val[last_sell_dt] = 1 / (1 - fee)  # inflate starting value because first sell, isn't a real sell

    # ### an old method to to trash
    # set all values before the first buy as 1
    # port_val[port_val.index <= model_results['transacts']['buy']['datetimes'][0]] = 1

    # get portfolio value time series
    for i in range(num_buys):
        # print(f"i: {i}")

        try:  # ###PAUL_del_later if we get past this error
            buy_dt = model_results['transacts']['buy']['datetimes'][i]
        except IndexError:
            import pdb;
            pdb.set_trace()

            # carry the portfolio value over from last sell to the current buy
        last_port_value = port_val[last_sell_dt] * (1 - fee)
        at_last_sell_to_current_buy_mask = np.logical_and(last_sell_dt <= port_val.index, port_val.index <= buy_dt)
        port_val[at_last_sell_to_current_buy_mask] = last_port_value

        sell_dt = model_results['transacts']['sell']['datetimes'][i]
        # sell_price = model_results['transacts']['sell']['prices'][i]

        # get port value from buy to sell
        buy_price = prices[buy_dt]
        last_port_value = port_val[buy_dt]
        after_buy_at_sell_price_mask = np.logical_and(buy_dt < prices.index, prices.index <= sell_dt)
        prices_after_buy_to_sell = prices[after_buy_at_sell_price_mask]  # .sort_values(by='index')
        values_after_buy_to_sell = last_port_value * prices_after_buy_to_sell / buy_price * (1 - fee)
        # add values from buy to sel to the series
        port_val[values_after_buy_to_sell.index] = values_after_buy_to_sell

        last_sell_dt = sell_dt

    last_port_value = port_val[last_sell_dt] * (1 - fee)
    after_last_sell_mask = last_sell_dt < port_val.index
    port_val[after_last_sell_mask] = last_port_value

    # get series of portfolio returns from one period to the next
    port_returns = port_val.pct_change()
    port_returns = port_returns[1:]  # first value deleted because it is returns

    return port_val, port_returns


def get_sharpe_and_sortino_spot(r, freq="hour"):
    annualized_factor = np.sqrt(24 * 365) if freq == "hour" else np.sqrt(365)
    sharpe = r.mean() / r.std() * annualized_factor
    sortino = r.mean() / np.where(r >= 0, 0., r).std() * annualized_factor

    return sharpe, sortino


def backtest_decision_making_spot(all_prices, preds, **decision_params):
    """runs g(y_hat) = z given y_hat, price series, and decision making parametsr. it tells us what to do

    input:
        preds (pd.series): output of our model f(x) y_hat
    output:
        model_results (dict): with keys ['transacts' , 'pnl', 'sharpe', 'sortino', 'port_value_ts', 'num_transacts']
    """
    model_results = {}

    prices = all_prices[preds.index]

    requests_dict = make_requests_dict(**decision_params)
    # transacts dict
    transacts = get_buys_and_sells_v3(preds, prices, requests_dict, )
    model_results['transacts'] = transacts
    # num transacts
    num_transacts = len(transacts['sell']['idxs']) + len(transacts['buy']['idxs'])
    model_results['num_transacts'] = num_transacts
    model_results['num_buys'] = len(transacts['buy']['idxs'])
    model_results['num_sells'] = len(transacts['sell']['idxs'])
    # pnl
    pnl = get_PnL(transacts)
    model_results['pnl'] = pnl
    # portfolio value time series ###PAUL_todo
    # try:
    port_value_ts, port_return_ts = get_port_value_and_return_series(prices, preds, model_results, fee=0.001)
    # except IndexError:
    #     import pdb; pdb.set_trace() ###PAUL_PDB

    model_results['port_value_ts'] = port_value_ts
    model_results['port_return_ts'] = port_return_ts

    # calculate sharpe ratio and sortino ###PAUL_todo
    sharpe, sortino = get_sharpe_and_sortino(r=port_return_ts,
                                             freq="hour")  # get_sharpe_and_sortino(r, freq="hour")  # ###PAUL get this going
    model_results['sharpe'] = sharpe
    model_results['sortino'] = sortino
    model_results['preds'] = preds

    return model_results

