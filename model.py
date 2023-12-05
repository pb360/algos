# ### local imports
import sys
sys.path.insert(0, '..')  # for local imports from the top directory
# ## local imports
#
from algos.targets import make_targets
from algos.feature import (adjust_start_dates_of_feature_params,
                           make_features, )

# ## standard stuff
#
from copy import deepcopy
from dateutil.relativedelta import relativedelta
import math
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader


def make_mlp_dataloader(x_in, batch_size, y_in=None, shuffle=False):
    """x is the feature set for a time period, y is a superset which is selected from using the indicies of X
    if promising this will need to be converted into an RTI rolling backtest version which wouldn't be too hard
    # ###PAUL TODO: naming, change args from `_in` to what they are from (series, df...)
    """

    x = torch.from_numpy(x_in.values).float()

    if y_in is not None:
        y = torch.from_numpy(y_in.loc[x_in.index].values).float()
        y = torch.reshape(y, (y.shape[0], 1))
        dataset = torch.utils.data.TensorDataset(x, y)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
    else:
        dataset = torch.utils.data.TensorDataset(x)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)

    return dataloader


# Define model
class NeuralNetwork(nn.Module):

    def __init__(self, feature_in_dim):
        super(NeuralNetwork, self).__init__()

        # def __init__(self):
        #     super(NeuralNetwork, self).__init__()
        self.flatten = nn.Flatten()

        self.linear_relu_stack = nn.Sequential(
            # layer 1
            nn.Dropout(0.5),
            nn.Linear(feature_in_dim, 200),
            nn.ReLU(),
            # layer 2
            nn.Dropout(0.5),
            nn.Linear(200, 100),
            nn.ReLU(),
            # layer 3
            nn.Dropout(0.5),
            nn.Linear(100, 50),
            nn.ReLU(),
            # layer 4
            nn.Dropout(0.5),
            nn.Linear(50, 10),
            nn.ReLU(),
            # output
            nn.Dropout(0.5),
            nn.Linear(10, 1),
        )

    def forward(self, x):
        x = self.flatten(x)
        y_pred = self.linear_relu_stack(x)
        return y_pred


def train(dataloader, model, loss_fn, optimizer, printout_level='Low'):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    size = len(dataloader.dataset)
    model.train()

    loss_values_list = []

    for batch, (X, y) in enumerate(dataloader):

        X, y = X.to(device), y.to(device)

        # Compute prediction error
        pred = model(X.float())
        loss = loss_fn(pred, y)
        loss_values_list.append(loss)

        # Backpropagation
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if  printout_level in ['High']:
            if batch % 100 == 0:
                loss, current_obvs_i = loss.item(), batch * len(X)
                print(f"batch #: {batch} --- loss = {loss:>7f}  [{current_obvs_i:>5d}/{size:>5d}]")

    if printout_level in ['Low', 'High']:
        mean_loss = sum(loss_values_list) / len(loss_values_list)
        print(f"-- train loss: {mean_loss} ")


def test(dataloader, model, loss_fn, verbose_output=False):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    size = len(dataloader.dataset)
    num_batches = len(dataloader)
    model.eval()
    test_loss = 0
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            pred = model(X)
            test_loss += loss_fn(pred, y).item()
    test_loss /= num_batches
    if verbose_output:
        print('test loss: ' + str(test_loss))
    return test_loss


def make_predictions_for_dataloader(dataloader, model):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    for i, (X, Y) in enumerate(dataloader):
        pred_t = model(X.to(device)).detach().cpu().numpy()

        if i == 0:
            preds = pred_t
        else:
            preds = np.concatenate((preds, pred_t))

    return preds


def make_predictions_for_dataloader_features_only(dataloader, model):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    for i, (X) in enumerate(dataloader):
        pred_t = model(X[0].to(device)).detach().cpu().numpy()

        if i == 0:
            preds = pred_t
        else:
            preds = np.concatenate((preds, pred_t))

    return preds


def reshape_preds(preds):
    # handling test preds for plotting if single digit prediction
    n = preds.shape[0]
    preds = np.reshape(preds, (n,))

    return preds


def process_preds_to_signal(preds, model_params, verbose_return=False):
    if 'preds_pd_ewm_alpha' in model_params:
        signal = preds.ewm(alpha=model_params['preds_pd_ewm_alpha']).mean()
        smoothed_preds = deepcopy(signal)  # deep copy because signal changes with post processing

    if model_params['rolling_normalize_preds']:
        assert ('signal_norm_window' in model_params)
        # normalizing the signal on rolling basis same as input, replace with preds as plot function idxs are still based off this
        signal_norm_window = model_params['signal_norm_window']
        signal = ((signal - signal.rolling(signal_norm_window).mean()).fillna(0) /
                  signal.rolling(signal_norm_window).std().fillna(method='ffill')).iloc[signal_norm_window - 1:]

    if verbose_return:
        return smoothed_preds, signal
    else:
        return signal


def make_signal_dict_from_preds(preds, y_train_rti, feature_params, target_params, model_params, model='not_supplied'):
    """
    model: leave not_supplied as default because cant pickle a decision tree so it won't always be given to this
    """

    smoothed_preds, signal = process_preds_to_signal(preds, model_params, verbose_return=True)

    signal_dict = {}
    signal_dict['y_train_rti'] = y_train_rti
    signal_dict['preds'] = preds.loc[signal.index]
    signal_dict['smoothed_preds'] = smoothed_preds.loc[signal.index]
    signal_dict['signal'] = signal
    signal_dict['feature_params'] = deepcopy(feature_params)
    signal_dict['target_params'] = deepcopy(target_params)
    signal_dict['model_params'] = deepcopy(model_params)
    signal_dict['model'] = deepcopy(model)

    return signal_dict


def rolling_train_and_backtest_mlp(x,
                                   prices,
                                   model,
                                   feature_params,  # ###PAUL TODO: bucket the params in one_run_params...
                                   target_params,
                                   model_params,
                                   printout_level,
                                   ):
    """ runs a rolling backtest for an MLP network...

    INPUTS:
        whole_x_df: a preprocessed dataframe with sparse cols pruned, rolling norm already preformed

    # ###PAUL TODO: there are a decent amount of things to get done in this
        # TODO: quickie... ensure normalized targets are clipped
        # TODO:     1.) the whole_x_df is fed in preprocessed (I dont think this is desirable
        # TODO:     2.) model be based off the shape of x so may need to do the rolling normalization ahead of time.. ^^

    """

    # ###PAUL TODO: consider relationship between target_params['interval_len_in_steps'] and model_params['batch_size']

    feature_names = x.columns  # this is needed to know what features the neural network is trained on
    # get first batch of indicies
    train_start_dti = x.index[0]
    train_end_dti = x.index[0] + relativedelta(days=model_params['train_days'])
    test_start_dti = train_end_dti + relativedelta(days=model_params['f_window'])
    test_end_dti = test_start_dti + relativedelta(days=model_params['step_size'])

    preds = pd.Series(index=x.index[test_start_dti <= x.index])
    y_train_no_vola_adjust = pd.Series(index=x.index)
    y_train_rti = pd.Series(index=x.index)  # note will need to drop NA on these at the end

    interval_len_in_steps = target_params['interval_len_in_steps']

    iter_count = 0
    while test_end_dti <= x.index[-1]:
        iter_count += 1

        train_dtis = x.index[np.logical_and((train_start_dti < x.index), (x.index <= train_end_dti))]
        test_dtis = x.index[np.logical_and((test_start_dti < x.index), (x.index <= test_end_dti))]

        # ###PAUL TODO: when adjusting this function for an LSTM should only need to change these, I think its best
        # TODO: to have both the train and test go back `lstm_len` observations (depends on what the dataloader making
        # TODO: requirements are
        x_train = x.loc[train_dtis]
        x_test = x.loc[test_dtis]

        try:
            # get target datetime indexs ---- THE BELOW INDEX WORK CONTAIN WAY MORE THAN NEEDED FOR DATETIMEINDEX WORK
            # KEEP ALL THIS COMPLICATION BECAUSE IT REPRESENTS A SMALL PORTION OF RUNTIME AND HELPS WITH DEBUGGING
            target_dtis = x.index[np.logical_and((train_start_dti < x.index), (x.index <= train_end_dti))]
            # number of intervals needed to make targets (really ensures enough observations for 1 full interval)
            num_target_making_intervals = math.ceil(target_dtis.shape[0] / interval_len_in_steps)

            # get start and end of interval needed for target making
            end_target_making_iloc = np.argmax(x.index == target_dtis[-1])
            start_target_making_iloc = end_target_making_iloc - (num_target_making_intervals * interval_len_in_steps)
            start_target_making_iloc = max(0, start_target_making_iloc)  # should only max out at the beginning
            start_target_making_dti = x.index[start_target_making_iloc]
            end_target_making_dti = x.index[end_target_making_iloc]

            target_making_mask = np.logical_and(start_target_making_dti < x.index, x.index <= end_target_making_dti)
            target_making_dtis = x.index[target_making_mask]

            prices_t = prices.loc[target_making_dtis]

            y_superset, _ = make_targets(series=prices_t, **target_params)
            y_train_no_vola_adjust[train_dtis] = y_superset.loc[train_dtis]

            if model_params['volatility_normalization_for_targets']:
                rolling_return_var = prices_t.pct_change(model_params['return_window_n']).fillna(method='ffill').fillna(
                    method='bfill').rolling(
                    model_params['variance_window_n']).var().fillna(method='ffill').fillna(method='bfill')
                max_return_var = max(rolling_return_var)
                scaling_factor = 2/3 + 1/3 * (rolling_return_var / max_return_var)
                y_superset = scaling_factor * y_superset

            if model_params['normalize_targets']:
                y_superset = (y_superset - y_superset.mean()) / y_superset.std()

        except:
            import pdb
            pdb.set_trace()

        y_train = y_superset.loc[train_dtis]

        y_train = np.clip(a=y_train, a_min=-6, a_max=6)  # don't want to go over 6 sigma...

        y_train_rti.loc[train_dtis] = y_train

        train_dataloader = make_mlp_dataloader(x_in=x_train,
                                               batch_size=model_params['batch_size'],
                                               y_in=y_train,
                                               shuffle=model_params['shuffle_train'])
        test_dataloader = make_mlp_dataloader(x_in=x_test,
                                              batch_size=model_params['batch_size'],
                                              y_in=None,
                                              shuffle=model_params['shuffle_test'])

        test_loss_list = []
        if iter_count > 1:
            num_epochs = model_params['num_epochs_when_rolling']
        elif iter_count == 1:
            num_epochs = model_params['num_epochs_for_train']
        for t in range(num_epochs):
            train(train_dataloader, model, model_params['loss_fn'], model_params['optimizer'], printout_level)
            iters_test_loss = test(train_dataloader, model, model_params['loss_fn'])
            test_loss_list.append(iters_test_loss)

        # ### printouts for iteration
        if printout_level in ['Low']:
            if iter_count % 25 == 0 or iter_count < 4:
                print(f"-- making preds for model -- running rolling train / test ---- iter: {iter_count}\n"
                      f"---- rolling step #: {iter_count} -- num_epochs: {num_epochs} "
                      f"-- avg_los: {float(sum(test_loss_list) / len(test_loss_list)):.5f}"
                      f"-- losses ---- {test_loss_list}",
                      flush=True)
        if printout_level in ['High']:
            print(f"---- rolling step #: {iter_count} -- num_epochs: {num_epochs} "
                  f"-- avg_los: {float(sum(test_loss_list)/len(test_loss_list)):.5f}"
                  f"-- loss"
                  f"es ---- {test_loss_list}")

        iter_preds = make_predictions_for_dataloader_features_only(test_dataloader, model)
        iter_preds = reshape_preds(iter_preds)

        preds.loc[test_dtis] = iter_preds

        # reset start and end indicies without
        train_start_dti = train_end_dti
        train_end_dti = train_end_dti + relativedelta(days=model_params['step_size'])
        test_start_dti = test_end_dti
        test_end_dti = test_end_dti + relativedelta(days=model_params['step_size'])

    # y_test will come out as a tensor, need to rebuild it as a pandas array with the indicies of x[train_days:]... i.e. just remove
    preds = preds.dropna()  # depending on stepsize some may be dropped
    y_train_rti = y_train_rti.dropna()

    signal_dict = make_signal_dict_from_preds(preds, y_train_rti, feature_params, target_params, model_params, model)
    signal_dict['y_train_no_vola_adjust'] = y_train_no_vola_adjust.fillna(0)
    signal_dict['feature_names'] = feature_names  # when running live need to know what was pruned for sparsness historically

    return signal_dict


def generate_signal(params, ch_client=None):
    """LIVE FUNCTION ---- used live, so it pulls what is needed from databases
    """

    # ###PAUL note on operation ---- timespan of data needed for output (first iteration vs rest of operation)
    #         - the first iteration should go well earlier than `total_cut` (calculated below)... the first iteration
    #           on a si
    #           gnal will fill the history for it (long term this is not a great idea because there is actually
    #           a look ahead.. on second thought, I think we can grab that from signal_dict.
    #           `signal_dict` should come in from the validation of a grid search and that can be used.
    #           making a signal from the model after it has rolled through all that data gives a significant look
    #           ahead ability and if anyone came to use signals generated for their own purposes it will make preformance
    #           look crazy good
    # ###PAUL TODO: ugly handling of `max_cut_time` but may end up deciding minor derivation of this is sufficient as optimized compute woudln't have one of these anymore
    x, max_cut_time = make_features(params=params, ch_client=ch_client)

    # run the first iteration on too much data with the same feature_params used for rolling train.
    # then after once we figure out what the needed cut is we can fix via this function to process minimum data
    # ###PAUL TODO: ugly handling of `max_cut_time` but may end up deciding minor derivation of this is sufficient as optimized compute woudln't have one of these anymore
    adjust_start_dates_of_feature_params(feature_params=params['signal_dict']['feature_params'],
                                         model_params=params['signal_dict']['model_params'],
                                         max_cut_time=max_cut_time,
                                         signal_id=params['signal_id'],
                                         ch_client=ch_client)


    try:
        feature_dataloader = make_mlp_dataloader(x, batch_size=24 * 60, y_in=None, shuffle=False)
        preds = make_predictions_for_dataloader_features_only(feature_dataloader, model=params['signal_dict']['model'])
        preds = reshape_preds(preds)
        preds = pd.Series(preds, index=x.index)
        signal = process_preds_to_signal(preds=preds, model_params=params['signal_dict']['model_params'])  # postprocessing

        return signal

    except UnboundLocalError:
        import pdb
        pdb.set_trace()
