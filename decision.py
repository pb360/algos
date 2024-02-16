import sys
sys.path.insert(0, "..")

from algos import params
from algos.utils import find_runs, convert_date_format

from copy import deepcopy
import numpy as np
import pandas as pd


actions_to_bull_or_bear_dict = {
    "exit_short": "bullish",
    "long": "bullish",
    "exit_long": "bearish",
    "short": "bearish",
}


def make_requests_dict(decision_params):
    """makes a request dict. cant edit params directly because also used for data science work"""
    if "cool_down" in decision_params:
        cool_down = decision_params["cool_down"]
    else:
        cool_down = 1

    if decision_params["threshold"] is not None:
        neg_threshold = -decision_params["threshold"]
    else:
        neg_threshold = decision_params["threshold"]

    if decision_params["to_neutral_threshold"] is not None:
        neg_to_neutral_threshold = -decision_params["to_neutral_threshold"]
    else:
        neg_to_neutral_threshold = decision_params["to_neutral_threshold"]

    # the bullish positions (i.e. "long" and "exit_short") have distances "from_min"s
    # while the bearish actions are distances measured "from_max" be it prediction or price....
    requests_dict = {
        "long": {
            "threshold": {"value": neg_threshold, "cool_down": cool_down},
            "pred_dist": {"value": decision_params["pred_dist"], "cool_down": cool_down},
            # value in real terms
            "price_dist": {"value": decision_params["price_dist"], "cool_down": cool_down},
            # proportional to price
            "stop_limit": {"value": decision_params["stop_limit"], "cool_down": None},
        },
        "short": {
            "threshold": {"value": decision_params["threshold"], "cool_down": cool_down},
            "pred_dist": {"value": decision_params["pred_dist"], "cool_down": cool_down},
            # in real terms
            "price_dist": {"value": decision_params["price_dist"], "cool_down": cool_down},
            # proportional to price
            "stop_limit": {"value": decision_params["stop_limit"], "cool_down": None},
            # ###PAUL should be a trailing stop down
        },
        "exit_short": {
            "threshold": {"value": neg_to_neutral_threshold, "cool_down": cool_down},
            "pred_dist": {"value": decision_params["to_neutral_pred_dist"], "cool_down": cool_down},
            "price_dist": {"value": decision_params["to_neutral_price_dist"], "cool_down": cool_down},
            "stop_limit": {"value": decision_params["to_neutral_stop_limit"], "cool_down": None},
        },
        "exit_long": {
            "threshold": {"value": decision_params["to_neutral_threshold"], "cool_down": cool_down},
            "pred_dist": {"value": decision_params["to_neutral_pred_dist"], "cool_down": cool_down},
            "price_dist": {"value": decision_params["to_neutral_price_dist"], "cool_down": cool_down},
            "stop_limit": {"value": decision_params["to_neutral_stop_limit"], "cool_down": None},
        },
        "overrides": {
            "long": decision_params["overrides"],
            "short": decision_params["overrides"],
            "exit_short": decision_params["to_neutral_overrides"],
            "exit_long": decision_params["to_neutral_overrides"],
        },
        "any_two": {
            "long": decision_params["any_two"],
            "short": decision_params["any_two"],
            "exit_short": decision_params["to_neutral_any_two"],
            "exit_long": decision_params["to_neutral_any_two"],
        },
    }

    return requests_dict


def update_state_dict(state_dict, action, mode="backtest"):
    """reset the state dictionary given the position that was just taken

    input:
        position (str): in ['short', 'neutral', 'long'] to represent what side of a trade we just went into

        IF WE GO LONG (OR SHORT) WE RESET EVERYTHING

    """

    # do these things every time
    if action in ["exit_long", "exit_short", "start"]:
        position = "neutral"
    else:
        position = action  # other options are just long / short

    state_dict["position"] = position

    if action in [
        "exit_long",
        "short",
        "start",
    ]:
        state_dict["bullish"] = {
            "lowest_pred": np.array([100]),
            "highest_pred": np.array([-100]),
            "lowest_price": 7777777777.77,
            "highest_price": -7777777777.77,
            "activations": {
                "exit_short": {
                    "threshold": {"state": False, "cool_down": 0},
                    "pred_dist": {"state": False, "cool_down": 0},
                    "price_dist": {"state": False, "cool_down": 0},
                    "stop_limit": {"state": False, "cool_down": None},
                },
                "long": {
                    "threshold": {"state": False, "cool_down": 0},
                    "pred_dist": {"state": False, "cool_down": 0},
                    "price_dist": {"state": False, "cool_down": 0},
                    "stop_limit": {"state": False, "cool_down": None},
                },
            },
        }

    if action in [
        "exit_short",
        "long",
        "start",
    ]:  # DO NOT CHANGE TO `elif` because neutral looks both ways
        state_dict["bearish"] = {
            "lowest_pred": np.array([100]),
            "highest_pred": np.array([-100]),
            "lowest_price": 7777777777.77,
            "highest_price": -7777777777.77,
            "activations": {
                "exit_long": {
                    "threshold": {"state": False, "cool_down": 0},
                    "pred_dist": {"state": False, "cool_down": 0},
                    "price_dist": {"state": False, "cool_down": 0},
                    "stop_limit": {"state": False, "cool_down": None},
                },
                "short": {
                    "threshold": {"state": False, "cool_down": 0},
                    "pred_dist": {"state": False, "cool_down": 0},
                    "price_dist": {"state": False, "cool_down": 0},
                    "stop_limit": {"state": False, "cool_down": None},
                },
            },
        }


def handle_triggered_transaction(
    state_dict, num_transacts, transacts_list, transacts, action, i, dti, price, triggers="debug_off"
):
    transacts_list.append({"action": action, "idx": i, "datetime": dti, "price": price, "triggers": triggers})
    num_transacts += 1
    transacts[action]["idxs"].append(i)
    transacts[action]["datetimes"].append(dti)
    transacts[action]["prices"].append(price)
    transacts[action]["triggers"].append(triggers)

    update_state_dict(state_dict=state_dict, action=action)
    position = state_dict["position"]

    return num_transacts, position


def get_state(
    price,
    pred,
    position,
    action,
    switch_name,
    requests_dict,
    state_dict,
):
    """gets the state of a switch (flipped True for on or False for off) given parameters

    Outputs:
        switch_state (bool): which is fed into the update_activation function
    """

    # state to be returned
    state = None

    if position == "short" or position == "neutral" and action == "long":
        if switch_name == "threshold":
            value = requests_dict[action]["threshold"]["value"]
            state = value is None or pred < value
        if switch_name == "pred_dist":
            value = requests_dict[action]["pred_dist"]["value"]
            state = value is None or value < pred - state_dict["bullish"]["lowest_pred"]
        if switch_name == "price_dist":
            value = requests_dict[action]["price_dist"]["value"]
            if value is not None:
                threshold_price = (1 + value) * state_dict["bullish"]["lowest_price"]
            state = value is None or price > threshold_price
        if switch_name == "stop_limit":
            value = requests_dict[action]["stop_limit"]["value"]
            if value is not None:
                threshold_price = (1 + value) * state_dict["bullish"]["lowest_price"]
            state = value is None or price > threshold_price

    elif position == "long" or position == "neutral" and action == "short":
        if switch_name == "threshold":
            value = requests_dict[action]["threshold"]["value"]
            state = value is None or pred > value
        if switch_name == "pred_dist":
            value = requests_dict[action]["pred_dist"]["value"]
            state = value is None or value < state_dict["bearish"]["highest_pred"] - pred
        if switch_name == "price_dist":
            value = requests_dict[action]["price_dist"]["value"]
            if value is not None:
                threshold_price = (1 - value) * state_dict["bearish"]["highest_price"]
            state = value is None or price < threshold_price
        if switch_name == "stop_limit":
            value = requests_dict[action]["stop_limit"]["value"]
            if value is not None:
                threshold_price = (1 - value) * state_dict["bearish"]["highest_price"]
            state = value is None or price < threshold_price

    return state


def update_activation_v3(state, action, switch_name, requests_dict, state_dict):
    """updates the ['state'] and ['cool_down'] values of state_dict[bull_or_bear]['activations'][action][switch_name]

    input:
        state (bool): the state to flip the switch to
        action (str): in ['short', 'exit_short', 'exit_long', 'long']
    """

    cool_down_requested = requests_dict[action][switch_name]["cool_down"]
    bull_or_bear = actions_to_bull_or_bear_dict[action]

    if state:
        state_dict[bull_or_bear]["activations"][action][switch_name]["state"] = True
        if cool_down_requested is not None:
            state_dict[bull_or_bear]["activations"][action][switch_name]["cool_down"] = cool_down_requested

    # if the switch isn't activated no need to adjust cool_down, this will save some time
    if state_dict[bull_or_bear]["activations"][action][switch_name]["state"]:
        if cool_down_requested is not None:
            new_cool_down_value = state_dict[bull_or_bear]["activations"][action][switch_name]["cool_down"] - 1
            state_dict[bull_or_bear]["activations"][action][switch_name]["cool_down"] = max(new_cool_down_value, 0)

            if new_cool_down_value <= 0:  # switch off
                state_dict[bull_or_bear]["activations"][action][switch_name]["state"] = False
                state_dict[bull_or_bear]["activations"][action][switch_name]["cool_down"] = 0


def run_decision_algo(preds, prices, requests_dict, debug_triggers=False, max_transacts=10_000):
    """gets buys / sells for an interval

    inputs:
        preds (pd.Series): output of neural network, series NEEDS datetime index
        prices (pd.Series): series of prices
        requests_dict (dict): of structure above (ctrl+f...)
    output:
        transacts (dict): {'long' {'idxs': [], 'datetimes': [], 'prices': []},
                          'short': { " } }
    """

    # create a state_dict with a good initial state
    state_dict = {}
    update_state_dict(state_dict=state_dict, action="start")

    # get prices and a light quality check
    # prices = prices.loc[preds.index]['vwap']
    idxs = np.array(prices.index)
    prices = np.array(prices)
    assert prices.shape[0] == preds.shape[0]

    # buy and sell times (in integer index form)
    num_transacts = 0
    transacts_list = []
    transacts_dict_of_lists = {
        "idxs": [],
        "datetimes": [],
        "prices": [],
        "triggers": [],
    }

    transacts = {
        "long": deepcopy(transacts_dict_of_lists),
        "short": deepcopy(transacts_dict_of_lists),
        "exit_short": deepcopy(transacts_dict_of_lists),
        "exit_long": deepcopy(transacts_dict_of_lists),
    }

    # going through preds
    for i, pred in enumerate(preds):

        if num_transacts > max_transacts:
            break

        # if i < 5 or i % 500 == 0:
        #     print(f"iter: {i} ---- pred: {pred} ---- position {state_dict['position']}", flush=True)
        # add pred / price to dataframe since last transaction
        price = prices[i]

        # get current state and then update the activation for each switch
        position = state_dict["position"]

        # print(f"standard break in `run_decision_algo()` ")  # ###PAUL_del_later
        # import pdb                                          # ###PAUL_del_later
        # pdb.set_trace()                                     # ###PAUL_del_later

        # get possible actions based on the position we are currenly in.
        if position == "short":  # then we can either...
            actions = ["exit_short", "long"]
        elif position == "long":
            actions = ["exit_long", "short"]
        elif position == "neutral":  # need to keep start for backtesting
            actions = ["long", "short"]

        # only update the bearish state dict if considering shorting, which includes exit_long by default
        if "short" in actions:
            if pred < state_dict["bearish"]["lowest_pred"]:
                state_dict["bearish"]["lowest_pred"] = pred
            if pred > state_dict["bearish"]["highest_pred"]:
                state_dict["bearish"]["highest_pred"] = pred
            if price < state_dict["bearish"]["lowest_price"]:
                state_dict["bearish"]["lowest_price"] = price
            if price > state_dict["bearish"]["highest_price"]:
                state_dict["bearish"]["highest_price"] = price
        if "long" in actions:  # same for long ---- note: DO NOT CHANGE TO `elif` as look both ways when neutral
            if pred < state_dict["bullish"]["lowest_pred"]:
                state_dict["bullish"]["lowest_pred"] = pred
            if pred > state_dict["bullish"]["highest_pred"]:
                state_dict["bullish"]["highest_pred"] = pred
            if price < state_dict["bullish"]["lowest_price"]:
                state_dict["bullish"]["lowest_price"] = price
            if price > state_dict["bullish"]["highest_price"]:
                state_dict["bullish"]["highest_price"] = price
        # except Exception as e:
        #     print(f"{e} \n \n \n in decision algo debug")
        #     import pdb
        #     pdb.set_trace()

        for action in actions:
            bull_or_bear = actions_to_bull_or_bear_dict[action]

            for switch in state_dict[bull_or_bear]["activations"][action].keys():
                switch_state = get_state(price, pred, position, action, switch, requests_dict, state_dict)
                update_activation_v3(switch_state, action, switch, requests_dict, state_dict)

            # make list of all activations for whose turn it is
            activation_list = []
            activation_dict = {}
            for switch in state_dict[bull_or_bear]["activations"][action].keys():
                state = state_dict[bull_or_bear]["activations"][action][switch]["state"]
                if switch not in requests_dict["overrides"][action]:
                    activation_list.append(state)
                activation_dict[switch] = state

            # if any activation on this list is true, whose_turn takes its turn
            single_override = False
            for switch in requests_dict["overrides"][action]:
                if activation_dict[switch]:
                    single_override = True

            # if two or more of these switches are activated then send an order
            double_override = False
            num_true = 0
            for switch in requests_dict["any_two"][action]:
                if activation_dict[switch]:
                    num_true += 1
            if num_true >= 2:
                double_override = True

            if np.all(np.array(activation_list)) or single_override or double_override:
                # print(f"an action was actually triggered in `run_decision_algo()`")  # ###PAUL_del_later
                # import pdb;                                                          # ###PAUL_del_later
                # pdb.set_trace()                                                      # ###PAUL_del_later
                if debug_triggers:
                    triggers = {
                        "activation_list": np.all(np.array(activation_list)),
                        "single_override": single_override,
                        "double_override": double_override,
                        "bull_or_bear": bull_or_bear,
                        "state_dict": state_dict[bull_or_bear],
                    }
                else:
                    triggers = "debug_triggers_off"
                # print(f"current position: {position}  --  action: {action}  --  switch: {switch} ON  ---- iter #: {i}",
                # flush=True)

                # ### not allowed to go directly from SHORT --> LONG   or   LONG --> SHORT
                if (position == "short" and action == "long") or (position == "long" and action == "short"):
                    if position == "short":
                        intermediate_action = "exit_short"
                    else:  # position == 'long'
                        intermediate_action = "exit_long"

                    num_transacts, position = handle_triggered_transaction(
                        state_dict=state_dict,
                        num_transacts=num_transacts,
                        transacts_list=transacts_list,
                        transacts=transacts,
                        action=intermediate_action,
                        i=i,
                        dti=preds.index[i],
                        price=price,
                        triggers=triggers,
                    )

                # ###PAUL TODO: reference position by the state dict only... then, no tracking through multiple scopes
                num_transacts, position = handle_triggered_transaction(
                    state_dict=state_dict,
                    num_transacts=num_transacts,
                    transacts_list=transacts_list,
                    transacts=transacts,
                    action=action,
                    i=i,
                    dti=preds.index[i],
                    price=price,
                    triggers=triggers,
                )

    transacts["long"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["long"]["datetimes"])
    transacts["short"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["short"]["datetimes"])
    transacts["exit_short"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["exit_short"]["datetimes"])
    transacts["exit_long"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["exit_long"]["datetimes"])

    return transacts_list, transacts  # ... old way of doing things. iterable list makes more sense for the variety of positions


def get_port_value_and_return_series(prices, preds, transacts_list=None, fee_in_percent=0.1):
    """gets the portfolio over time

    input:
        prices (pd.Series): prices during the backtest
        preds (pd.Series): y_hat
        transacts_list (dict): EXAMPLE:  [{'action': 'long', 'datetime':......   }, {}, ..., {} ]
    """

    transacts_list_dc = deepcopy(transacts_list)  # ran into issues with pass by reference (should be fine as list now)
    mask_prices_with_preds = np.logical_and(preds.index[0] <= prices.index, prices.index <= preds.index[-1])

    price_idxs_with_preds_index = prices[mask_prices_with_preds].index
    port_val = pd.Series(data=0, index=price_idxs_with_preds_index, dtype=float)
    port_val.sort_index(inplace=True)

    fee_multiplier = 1 - (fee_in_percent / 100)

    # try:
    transact = transacts_list_dc.pop(0)
    # except IndexError:
    #     print(f" ALGOS/DECISION.PY ---- NO TRANSACTS", flush=True)
    #     time.sleep(0.25)
    #     return 0, 0, 0  # handle getting zeros for  port_val, port_returns, pnl one level up

    action = transact["action"]
    when = transact["datetime"]
    price = transact["price"]

    qty_quote = start_value = 1
    last_transact_to_first_transact_mask = port_val.index <= when
    port_val[last_transact_to_first_transact_mask] = qty_quote

    transacts_list_dc.append({"action": "end", "datetime": port_val.index[-1], "price": prices[port_val.index[-1]]})

    # go through all the transactions
    for counter, transact in enumerate(transacts_list_dc):
        # print(f"transacts # - counter: {counter}", flush=True)
        last_action = action
        last_when = when
        last_price = price

        action = transact["action"]
        when = transact["datetime"]
        price = transact["price"]

        mask_at_last_transact_to_current = np.logical_and(last_when <= port_val.index, port_val.index <= when)
        prices_at_last_transact_to_current = prices[mask_at_last_transact_to_current]

        if last_action == "short":
            if action not in ["exit_short", "end"]:
                print(f"debug_1 for last_action = short  ----  current_action = {action}", flush=True)
                raise RuntimeError

            qty_base = (qty_quote / last_price) * fee_multiplier
            values = qty_quote + (last_price - prices_at_last_transact_to_current) * qty_base
            port_val[mask_at_last_transact_to_current] = values
            short_price = last_price
            # print(f"SHORTED      ----  qty_quote unchanged at >> {qty_quote}", flush=True)

        if last_action == "exit_short":
            if action not in ["long", "short", "end"]:
                print(f"debug_2 for last_action = exit_short  ----  current_action = {action}", flush=True)
                raise RuntimeError
            # print(f"EXITING SHORT: start - qty_quote = {qty_quote}", flush=True)
            short_pnl_in_quote = (short_price - last_price) * qty_base
            fee_in_quote_qty = qty_base * last_price * fee_in_percent / 100
            qty_quote = qty_quote + short_pnl_in_quote - fee_in_quote_qty
            port_val[mask_at_last_transact_to_current] = qty_quote
            # print(f"               end   - qty_quote = {qty_quote}", flush=True)
            # Delete to ensure actions are ordered correctly... should only be set directly before a short.
            del qty_base
            del short_price

            # print(f"EXITED SHORT ----  qty_quote now  -------->> {qty_quote}", flush=True)

        if last_action == "long":
            if action not in ["exit_long", "end"]:
                print(f"debug_3 for last_action = long  ----  current_action = {action}", flush=True)
                raise RuntimeError
            # print(f"LONGING        start - qty_quote = {qty_quote}", flush=True)

            qty_base = qty_quote / last_price * fee_multiplier
            values = prices_at_last_transact_to_current * qty_base
            port_val[mask_at_last_transact_to_current] = values
            short_price = last_price
            qty_quote = 0

        if last_action == "exit_long":
            if action not in ["long", "short", "end"]:
                print(f"debug_4 for last_action = exit_long  ----  current_action = {action}", flush=True)
                raise RuntimeError
            qty_quote = qty_base * last_price * fee_multiplier
            port_val[mask_at_last_transact_to_current] = qty_quote

            # print(f"               end   - qty_quote = {qty_quote}", flush=True)

            del qty_base

    # if we are in a short or a long at the end of the prediction period then close it out.
    if last_action == "short":
        short_pnl_in_quote = (short_price - price) * qty_base
        fee = qty_base * price * fee_multiplier
        qty_quote = qty_quote + short_pnl_in_quote - fee
    elif last_action == "long":
        qty_quote = qty_base * price * fee_multiplier

    # get series of portfolio returns from one period to the next
    port_returns = port_val.pct_change()
    port_returns = port_returns[1:]  # first value deleted because it is returns

    pnl = qty_quote / start_value

    return port_val, port_returns, pnl


def compute_pf_old(transacts_list):
    direction = pd.DataFrame(transacts_list)[["action", "datetime", "price"]].set_index("datetime")
    direction["action"] = direction["action"].map({"short": -1, "long": 1, "exit_short": 0, "exit_long": 0})
    direction["transactions_return"] = 1 + direction["action"].shift().fillna(0) * direction["price"].pct_change().fillna(0)
    direction = direction.merge(prices_t, left_index=True, right_index=True, how="outer")
    direction["transactions_return"] = direction["transactions_return"].fillna(1).cumprod()
    direction["action"] = direction["action"].fillna(method="ffill").fillna(0)
    direction["price"] = direction["price"].fillna(method="ffill")
    direction["current_return"] = 1 + direction["action"] * (direction["vwap"] / direction["price"] - 1)
    direction["pf_value"] = direction["transactions_return"] * direction["current_return"]
    return direction["pf_value"]


# def compute_pf(transacts_list, prices_t, bps=5):
#     fees = 1 - bps / 1e4
#     direction = pd.DataFrame(transacts_list)[["action", "datetime", "price"]].set_index("datetime")
#     direction["action"] = direction["action"].map({"short":-1, "long":1, "exit_short":0, "exit_long":0})
#     direction["transactions_return"] = 1 + fees * direction["action"].shift().fillna(0) * direction["price"].pct_change().fillna(0)
#     direction = direction.merge(prices_t, left_index=True, right_index=True, how="outer")
#     direction["transactions_return"] = direction["transactions_return"].fillna(1).cumprod()
#     direction["action"] = direction["action"].fillna(method="ffill").fillna(0)
#     direction["price"] = direction["price"].fillna(method="ffill")
#     direction["current_return"] = 1 + fees * direction["action"] * (direction["vwap"] / direction["price"] - 1)
#     direction["pf_value"] = direction["transactions_return"] * direction["current_return"]
#     pf_value = direction["pf_value"]
#     return pf_value


# ###PAUL TODO: PNL function from john... needs adjustment for fees then verification, other than that its good
def compute_pf(transacts_list, prices_t, bps=5):
    fees = 1 - bps / 1e4
    direction = pd.DataFrame(transacts_list)[["action", "datetime", "price"]].set_index("datetime")
    direction["action"] = direction["action"].map({"short": -1, "long": 1, "exit_short": 0, "exit_long": 0})
    direction["transactions_return"] = 1 + fees * direction["action"].shift().fillna(0) * direction["price"].pct_change().fillna(
        0
    )
    direction = direction.merge(prices_t, left_index=True, right_index=True, how="outer")
    direction["transactions_return"] = direction["transactions_return"].fillna(1).cumprod()
    direction["action"] = direction["action"].fillna(method="ffill").fillna(0)
    direction["price"] = direction["price"].fillna(method="ffill")
    direction["current_return"] = 1 + fees * direction["action"] * (direction["vwap"] / direction["price"] - 1)
    direction["pf_value"] = direction["transactions_return"] * direction["current_return"]
    pf_value = direction["pf_value"]
    return pf_value


def get_sharpe_and_sortino(r, freq="min"):
    if freq in ["m", "min", "mins", "minute", "minutes"]:
        annualized_factor = np.sqrt(24 * 365 * 60)
    elif freq == ["h", "hr", "hrs", "hour", "hours"]:
        annualized_factor = np.sqrt(24 * 365)
    elif freq == "day":
        np.sqrt(365)
    else:
        print(f" ---- something broke debug_spot 123456", flush=True)
        annualized_factor = np.sqrt(24 * 365 + 60)

    sharpe = r.mean() / r.std() * annualized_factor
    sortino = r.mean() / np.where(r >= 0, 0.0, r).std() * annualized_factor

    return sharpe, sortino


def backtest_decision_making(
    price_series,
    signal_dict,
    decision_params,
    decision_series_name="signal",
    freq="min",
):
    """runs g(y_hat) = z given y_hat, price series, and decision making parametsr. it tells us what to do

    input:
        preds (pd.series): output of our model f(x) y_hat
    output:
        signal_dict (dict): with keys ['transacts' , 'pnl', 'sharpe', 'sortino', 'port_value_ts', 'num_transacts']
    """

    preds = signal_dict[decision_series_name]

    # ###PAUL TODO: through preds (change the name to y_hat eventually...)
    # # TODO: controller for decision time series (max's request for going on targets unveild interesting behaviors)
    # preds = signal_dict['y_train_no_vola_adjust']
    prices = price_series.loc[preds.index]

    requests_dict = make_requests_dict(decision_params)
    transacts_list, transacts = run_decision_algo(
        preds=preds,
        prices=prices,
        requests_dict=requests_dict,
    )

    signal_dict["transacts"] = transacts
    signal_dict["transacts_list"] = transacts_list
    # num transacts
    num_transacts = len(transacts_list)
    signal_dict["num_transacts"] = num_transacts

    # if num_transacts != 0:

    fee = decision_params["fee"]
    port_value_ts, port_return_ts, pnl = get_port_value_and_return_series(
        prices=prices, preds=preds, transacts_list=transacts_list, fee_in_percent=fee
    )

    if pnl != 0:
        # temp pnl override  # ###PAUL TODO: URGENT investigate this behavior
        pnl = float(port_value_ts.iloc[-1])
        sharpe, sortino = get_sharpe_and_sortino(r=port_return_ts, freq=freq)
    else:
        sharpe = sortino = 0

    # else:
    #     raise NotImplementedError
    #     port_value_ts = port_return_ts = pnl = sharpe = sortino = 0

    framework_results = deepcopy(signal_dict)
    framework_results["port_value_ts"] = port_value_ts
    framework_results["port_return_ts"] = port_return_ts
    framework_results["pnl"] = pnl
    framework_results["sharpe"] = sharpe
    framework_results["sortino"] = sortino

    return framework_results


def backtest_decision_making_multiprocess(price_series, preds, freq="min", **decision_params):
    """the simplified version of backtest_decision making, multi processing is done at the model_param level

    input:
        preds (pd.series): output of our model f(x) y_hat
    output:
        framework_results (dict): with keys ['transacts' , 'pnl', 'sharpe', 'sortino', 'port_value_ts', 'num_transacts']
    """

    max_transacts = 10_000  # ###PAUL TODO: put this as an argument flowing nicely for rolling and batched

    prices = price_series[preds.index]

    requests_dict = make_requests_dict(decision_params)

    # transacts dict
    transacts_list, transacts = run_decision_algo(preds, prices, requests_dict, max_transacts=max_transacts)

    if len(transacts_list) >= max_transacts:
        port_value_ts = port_return_ts = pnl = 0
    else:
        # import pdb;      # ###PAUL_del_later
        # pdb.set_trace()  # ###PAUL_del_later
        port_value_ts, port_return_ts, pnl = get_port_value_and_return_series(
            prices=prices, preds=preds, transacts_list=transacts_list, fee_in_percent=decision_params["fee"]
        )

    if pnl != 0:
        sharpe, sortino = get_sharpe_and_sortino(r=port_return_ts, freq=freq)
    else:
        sharpe = sortino = 0

    # ### populate model results
    #
    framework_results = {}
    framework_results["num_transacts"] = len(transacts_list)
    framework_results["pnl"] = pnl
    framework_results["sharpe"] = sharpe
    framework_results["sortino"] = sortino

    return framework_results


def analyze_returns_at_start_and_end_of_threshold_break(signal, prices, thresh, minutes=None, hours=None, days=None):
    if type(prices) == pd.DataFrame:
        prices_matching_signal = prices["vwap"].loc[signal.index]
    elif type(prices) == pd.Series:
        prices_matching_signal = prices.loc[signal.index]

    minima_qualifiers = signal < -thresh
    maxima_qualifiers = signal > thresh

    min_values, min_starts, min_lens = find_runs(minima_qualifiers)
    max_values, max_starts, max_lens = find_runs(maxima_qualifiers)

    start_of_min_ilocs = min_starts[min_values == True]
    end_of_min_ilocs = start_of_min_ilocs + min_lens[min_values == True]
    start_of_max_ilocs = max_starts[max_values == True]
    end_of_max_ilocs = start_of_max_ilocs + max_lens[max_values == True]

    if minutes is not None:
        n_minutes = minutes
        n = minutes
        unit = f"min"
    elif hours is not None:
        n_minutes = int(hours * 60)
        n = hours
        unit = f"hr"
    elif days is not None:
        n_minutes = int(days * 24 * 60)
        n = days
        unit = f"day"

    # low threshold
    ilocs_t = start_of_min_ilocs
    ilocs_t = ilocs_t[ilocs_t < signal.shape[0] - n_minutes]
    r__from_start_of_low = prices_matching_signal.iloc[ilocs_t + n_minutes].values / prices_matching_signal.iloc[ilocs_t].values
    ilocs_t = end_of_min_ilocs
    ilocs_t = ilocs_t[ilocs_t < signal.shape[0] - n_minutes]
    r__from_end_of_low = prices_matching_signal.iloc[ilocs_t + n_minutes].values / prices_matching_signal.iloc[ilocs_t].values

    # high threshold
    ilocs_t = start_of_max_ilocs
    ilocs_t = ilocs_t[ilocs_t < signal.shape[0] - n_minutes]
    r__from_start_of_high = prices_matching_signal.iloc[ilocs_t + n_minutes].values / prices_matching_signal.iloc[ilocs_t].values
    ilocs_t = end_of_max_ilocs
    ilocs_t = ilocs_t[ilocs_t < signal.shape[0] - n_minutes]
    r__from_end_of_high = prices_matching_signal.iloc[ilocs_t + n_minutes].values / prices_matching_signal.iloc[ilocs_t].values

    print(
        f"threshold: {thresh} \n"
        f"- num low signal periods ---- {start_of_min_ilocs.shape[0]} \n"
        f"    - returns_{n}_{unit}____from_start_of_low    mean ---- {r__from_start_of_low.mean()} --- std_dev: {r__from_start_of_low.std()} \n"
        f"    - returns_{n}_{unit}____from_end_of_low      mean ---- {r__from_end_of_low.mean()} --- std_dev: {r__from_end_of_low.std()}  \n"
        f"- num high signal periods ---- {start_of_max_ilocs.shape[0]} \n"
        f"    - returns_{n}_{unit}____from_start_of_high   mean ---- {r__from_start_of_high.mean()} --- std_dev: {r__from_start_of_high.std()}  \n"
        f"    - returns_{n}_{unit}____from_end_of_high     mean ---- {r__from_end_of_high.mean()} --- std_dev: {r__from_end_of_high.std()}  \n"
    )

    transact_at_break_thresh_list = []
    for iloc in start_of_min_ilocs[start_of_min_ilocs < signal.shape[0] - n_minutes]:
        transact_at_break_thresh_list.append(
            {
                "action": "long",
                "idx": iloc,
                "datetime": prices_matching_signal.index[iloc],
                "price": prices_matching_signal.iloc[iloc],
                "triggers": "debug_triggers_off",
            }
        )
        transact_at_break_thresh_list.append(
            {
                "action": "exit_long",
                "idx": iloc + n_minutes,
                "datetime": prices_matching_signal.index[iloc + n_minutes],
                "price": prices_matching_signal.iloc[iloc + n_minutes],
                "triggers": "debug_triggers_off",
            }
        )

    for iloc in start_of_max_ilocs[start_of_max_ilocs < signal.shape[0] - n_minutes]:
        transact_at_break_thresh_list.append(
            {
                "action": "short",
                "idx": iloc,
                "datetime": prices_matching_signal.index[iloc],
                "price": prices_matching_signal.iloc[iloc],
                "triggers": "debug_triggers_off",
            }
        )
        transact_at_break_thresh_list.append(
            {
                "action": "exit_short",
                "idx": iloc + n_minutes,
                "datetime": prices_matching_signal.index[iloc + n_minutes],
                "price": prices_matching_signal.iloc[iloc + n_minutes],
                "triggers": "debug_triggers_off",
            }
        )

    transact_at_back_under_thresh_list = []
    for iloc in end_of_min_ilocs[end_of_min_ilocs < signal.shape[0] - n_minutes]:
        transact_at_back_under_thresh_list.append(
            {
                "action": "long",
                "idx": iloc,
                "datetime": prices_matching_signal.index[iloc],
                "price": prices_matching_signal.iloc[iloc],
                "triggers": "debug_triggers_off",
            }
        )
        transact_at_back_under_thresh_list.append(
            {
                "action": "exit_long",
                "idx": iloc + n_minutes,
                "datetime": prices_matching_signal.index[iloc + n_minutes],
                "price": prices_matching_signal.iloc[iloc + n_minutes],
                "triggers": "debug_triggers_off",
            }
        )

    for iloc in end_of_max_ilocs[end_of_max_ilocs < signal.shape[0] - n_minutes]:
        transact_at_back_under_thresh_list.append(
            {
                "action": "short",
                "idx": iloc,
                "datetime": prices_matching_signal.index[iloc],
                "price": prices_matching_signal.iloc[iloc],
                "triggers": "debug_triggers_off",
            }
        )
        transact_at_back_under_thresh_list.append(
            {
                "action": "exit_short",
                "idx": iloc + n_minutes,
                "datetime": prices_matching_signal.index[iloc + n_minutes],
                "price": prices_matching_signal.iloc[iloc + n_minutes],
                "triggers": "debug_triggers_off",
            }
        )

    return transact_at_break_thresh_list, transact_at_back_under_thresh_list


def get_feisable_transacts_list_from_time_strat(transacts_list):
    transacts_df = pd.DataFrame.from_records(transacts_list).sort_values(by="datetime")

    last_action = "start"
    last_action_map = {
        "start": ["long", "short"],
        "long": ["exit_long"],
        "exit_long": ["long", "short"],
        "short": ["exit_short"],
        "exit_short": ["long", "short"],
    }

    transacts_list = []
    for row in transacts_df.iterrows():
        action = row[1]["action"]

        if action not in last_action_map[last_action]:
            continue

        if action == last_action:
            print("error")
        last_action = action
        transacts_list.append(dict(row[1]))

    return transacts_list


def make_transacts_dict_from_list(transacts_list):
    transacts = {
        "long": {"idxs": [], "datetimes": [], "prices": [], "triggers": []},
        "exit_long": {"idxs": [], "datetimes": [], "prices": [], "triggers": []},
        "short": {"idxs": [], "datetimes": [], "prices": [], "triggers": []},
        "exit_short": {"idxs": [], "datetimes": [], "prices": [], "triggers": []},
    }

    for t in transacts_list:
        action = t["action"]
        transacts[action]["idxs"].append(t["idx"])
        transacts[action]["datetimes"].append(t["datetime"])
        transacts[action]["prices"].append(t["price"])
        transacts[action]["triggers"].append(t["triggers"])

    return transacts


def run_simple_signal_threshold_and_hold_time_based_framework(
    prices, signal_dict, thresh=2, days=None, hours=None, minutes=None, trigger_on="back_under", fee_in_percent=0
):
    """
    inputs:
        thresh (float): magnitude for signal to trigger long (low value) or a short (high value)
        days (int): how many days to hold after a trigger
        preds (pd.Series): only a pass through value for a
        signal (pd.Series): signal for the strategy
        trigger_on (str): when the signal triggers either the magnitude of the signal   "break_above"  or "back_under"
    """

    signal = signal_dict["signal"]

    # always last
    if type(prices) == pd.DataFrame:
        prices_matching_signal = prices["vwap"].loc[signal.index]
    elif type(prices) == pd.Series:
        prices_matching_signal = prices.loc[signal.index]

    transacts_list____on_break_above, transacts_list____on_back_under = analyze_returns_at_start_and_end_of_threshold_break(
        signal=signal,
        prices=prices_matching_signal,
        thresh=thresh,
        minutes=minutes,
        hours=hours,
        days=days,
    )

    # import ipdb
    # ipdb.set_trace()

    if trigger_on == "break_above":
        transacts_list = get_feisable_transacts_list_from_time_strat(transacts_list=transacts_list____on_break_above)
    if trigger_on == "back_under":
        transacts_list = get_feisable_transacts_list_from_time_strat(transacts_list=transacts_list____on_back_under)

    transacts_dict = make_transacts_dict_from_list(transacts_list)

    port_value_ts, port_return_ts, pnl = get_port_value_and_return_series(
        prices=prices_matching_signal, preds=signal, transacts_list=transacts_list, fee_in_percent=fee_in_percent
    )

    sharpe, sortino = get_sharpe_and_sortino(r=port_return_ts, freq="min")

    print(f"pnl     ---- {pnl} \n" f"sharpe  ---- {sharpe} \n" f"sortino ---- {sortino} \n")

    thresh_and_hold_time_based_framework_results = {}
    thresh_and_hold_time_based_framework_results["num_transacts"] = len(transacts_list)
    thresh_and_hold_time_based_framework_results["preds"] = signal_dict["preds"]
    thresh_and_hold_time_based_framework_results["smoothed_preds"] = signal_dict["smoothed_preds"]
    thresh_and_hold_time_based_framework_results["signal"] = signal_dict["signal"]
    thresh_and_hold_time_based_framework_results["y_train_rti"] = signal_dict["y_train_rti"]
    thresh_and_hold_time_based_framework_results["pnl"] = pnl
    thresh_and_hold_time_based_framework_results["sharpe"] = sharpe
    thresh_and_hold_time_based_framework_results["sortino"] = sortino
    thresh_and_hold_time_based_framework_results["port_value_ts"] = port_value_ts
    thresh_and_hold_time_based_framework_results["port_return_ts"] = port_return_ts
    thresh_and_hold_time_based_framework_results["transacts"] = transacts_dict
    thresh_and_hold_time_based_framework_results["transacts_list"] = transacts_list

    return thresh_and_hold_time_based_framework_results


def decide_live(state_dict, signal, prices, requests_dict, pair, debug_triggers=False):
    """gets buys / sells for an interval

    inputs:
        signal (pd.Series): output of neural network, series NEEDS datetime index
        prices (pd.Series): series of prices
        requests_dict (dict): of structure above (ctrl+f...)
    output:
        transacts (dict): {'long' {'idxs': [], 'datetimes': [], 'prices': []},
                          'short': { " } }
        ALSO UPDATES THE `state_dict`
    """

    triggered_actions = []  # for knowing if we need to change positions

    if signal.shape[0] == 0 or prices.shape[0] == 0:
        return triggered_actions  # triggered_transacts is empty if there is no signal or price for this iteration

    # get prices and a light quality check
    # prices = prices.loc[signal.index]['vwap']

    # if bullish / bearish not in state_dict need to initialize it for the decision algorithm
    if "bullish" not in state_dict.keys():
        update_state_dict(state_dict, action="start")

    # GET ALL DATES MATCHING
    start_date = max(min(signal.index), min(prices.index))
    end_date = min(max(signal.index), max(prices.index))
    prices = prices[np.logical_and(start_date <= prices.index, prices.index <= end_date)]
    signal = signal[np.logical_and(start_date <= signal.index, signal.index <= end_date)]

    if signal.shape[0] == 0 or prices.shape[0] == 0:
        return triggered_actions  # triggered_transacts is empty if there is no signal or price for this iteration

    assert prices.shape[0] == signal.shape[0]

    prices = np.array(prices)
    signal_np_arr = np.array(signal)

    # buy and sell times (in integer index form)
    num_transacts = 0
    transacts_list = []
    transacts_dict_of_lists = {
        "idxs": [],
        "datetimes": [],
        "prices": [],
        "triggers": [],
    }

    transacts = {
        "long": deepcopy(transacts_dict_of_lists),
        "short": deepcopy(transacts_dict_of_lists),
        "exit_short": deepcopy(transacts_dict_of_lists),
        "exit_long": deepcopy(transacts_dict_of_lists),
    }

    # going through signal
    for i, pred in enumerate(signal_np_arr):

        # if i < 5 or i % 500 == 0:
        #     print(f"iter: {i} ---- pred: {pred} ---- position {state_dict['position']}", flush=True)
        # add pred / price to dataframe since last transaction
        price = prices[i]

        # get current state and then update the activation for each switch
        position = state_dict["desired_position"][pair]

        # get possible actions based on the position we are currenly in.
        if position == "short":  # then we can either...
            actions = ["exit_short", "long"]
        elif position == "long":
            actions = ["exit_long", "short"]
        elif position == "neutral":
            actions = ["long", "short"]

        # only update the bearish state dict if considering shorting, which includes exit_long by default
        if "short" in actions:
            if pred < state_dict["bearish"]["lowest_pred"]:
                state_dict["bearish"]["lowest_pred"] = pred
            if pred > state_dict["bearish"]["highest_pred"]:
                state_dict["bearish"]["highest_pred"] = pred
            if price < state_dict["bearish"]["lowest_price"]:
                state_dict["bearish"]["lowest_price"] = price
            if price > state_dict["bearish"]["highest_price"]:
                state_dict["bearish"]["highest_price"] = price
        if "long" in actions:
            if pred < state_dict["bullish"]["lowest_pred"]:
                state_dict["bullish"]["lowest_pred"] = pred
            if pred > state_dict["bullish"]["highest_pred"]:
                state_dict["bullish"]["highest_pred"] = pred
            if price < state_dict["bullish"]["lowest_price"]:
                state_dict["bullish"]["lowest_price"] = price
            if price > state_dict["bullish"]["highest_price"]:
                state_dict["bullish"]["highest_price"] = price

        for action in actions:
            bull_or_bear = actions_to_bull_or_bear_dict[action]

            for switch in state_dict[bull_or_bear]["activations"][action].keys():
                switch_state = get_state(price, pred, position, action, switch, requests_dict, state_dict)
                update_activation_v3(switch_state, action, switch, requests_dict, state_dict)

            # make list of all activations for whose turn it is
            activation_list = []
            activation_dict = {}
            for switch in state_dict[bull_or_bear]["activations"][action].keys():
                state = state_dict[bull_or_bear]["activations"][action][switch]["state"]
                if switch not in requests_dict["overrides"][action]:
                    activation_list.append(state)
                activation_dict[switch] = state

            # if any activation on this list is true, whose_turn takes its turn
            single_override = False
            for switch in requests_dict["overrides"][action]:
                if activation_dict[switch]:
                    single_override = True

            # if two or more of these switches are activated then send an order
            double_override = False
            num_true = 0
            for switch in requests_dict["any_two"][action]:
                if activation_dict[switch]:
                    num_true += 1
            if num_true >= 2:
                double_override = True

            if np.all(np.array(activation_list)) or single_override or double_override:
                if debug_triggers:
                    triggers = {
                        "activation_list": np.all(np.array(activation_list)),
                        "single_override": single_override,
                        "double_override": double_override,
                        "bull_or_bear": bull_or_bear,
                        "state_dict": state_dict[bull_or_bear],
                    }
                else:
                    triggers = "debug_triggers_off"
                # print(f"current position: {position}  --  action: {action}  --  switch: {switch} ON  ---- iter #: {i}",
                # flush=True)

                # ### not allowed to go directly from SHORT --> LONG   or   LONG --> SHORT
                if (position == "short" and action == "long") or (position == "long" and action == "short"):
                    if position == "short":
                        intermediate_action = "exit_short"
                    else:  # position == 'long'
                        intermediate_action = "exit_long"

                    triggered_actions.append[intermediate_action]
                    num_transacts, position = handle_triggered_transaction(
                        state_dict=state_dict,
                        num_transacts=num_transacts,
                        transacts_list=transacts_list,
                        transacts=transacts,
                        action=intermediate_action,
                        i=i,
                        dti=signal.index[i],
                        price=price,
                        triggers=triggers,
                    )

                # ###PAUL TODO: reference position by the state dict only... then, no tracking through multiple scopes
                triggered_actions.append(action)
                num_transacts, position = handle_triggered_transaction(
                    state_dict=state_dict,
                    num_transacts=num_transacts,
                    transacts_list=transacts_list,
                    transacts=transacts,
                    action=action,
                    i=i,
                    dti=signal.index[i],
                    price=price,
                    triggers=triggers,
                )

    transacts["long"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["long"]["datetimes"])
    transacts["short"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["short"]["datetimes"])
    transacts["exit_short"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["exit_short"]["datetimes"])
    transacts["exit_long"]["datetimes"] = pd.core.indexes.datetimes.DatetimeIndex(transacts["exit_long"]["datetimes"])

    return triggered_actions  # ... old way of doing things. iterable list makes more sense for the variety of positions
