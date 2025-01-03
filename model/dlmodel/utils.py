import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import argparse
import json
import subprocess
import os
import itertools
import random
from tabpfn import TabPFNClassifier
from tqdm import tqdm
from model.utils import (
    get_deep_args,show_results,tune_hyper_parameters,
    get_method,set_seeds
)
from model.lib.data import (
    get_dataset
)
import shutil

models = [
    'danets',
    'mlp',
    'node',
    'resnet',
    'switchtab',
    'tabcaps',
    'tabnet',
    'tangos'
]

indices_models = [
    'autoint',
    'dcn2',
    'ftt',
    'grownet',
    'saint',
    'snn',
    'tabtransformer'
]

tabr_ohe_models = [
    'tabr',
    'modernNCA'
]


def test_model(dataset, model, train_set, test_sets):
    metric1_by_model = []
    metric2_by_model = []

    if model =="TabPFN":
        file = "../configs/tabpfn.json"
        with open(file, 'r') as f:
            param_grid = json.load(f)
        model = TabPFNClassifier(device='gpu', N_ensemble_configurations=32)
        grid_search = GridSearchCV(estimator=model, param_grid=param_grid, cv=5)
        grid_search.fit(train_set.iloc[:, :-1], train_set.iloc[:, -1])
        best_params = grid_search.best_params_
        model = TabPFNClassifier(**best_params)
        model.fit(train_set.iloc[:, :-1], train_set.iloc[:, -1])
        for test_set in test_sets:
            X_test = test_set.iloc[:, :-1]
            y_test = test_set.iloc[:, -1]
            y_pred = downstream.predict(X_test)
            y_pred_proba = downstream.predict_proba(X_test)[:, 1]  # 获取正类概率
            accuracy = accuracy_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            metric1_by_model.append(accuracy)
            metric2_by_model.append(roc_auc)
        return metric1_by_model, metric2_by_model

    else:
        preprocessing(train_set, type="train")

        loss_list, results_list, time_list = [], [], []
        args, default_para, opt_space = get_deep_args()
        train_val_data, test_data, info = get_dataset(args.dataset, args.dataset_path)
        if args.tune:
            args = tune_hyper_parameters(args, opt_space, train_val_data, info)
        method = get_method(args.model_type)(args, info['task'] == 'regression')
        time_cost = method.fit(train_val_data, info)

        for test_set in test_sets:
            preprocessing(test_set, type="test")

            vl, vres, metric_name, predict_logits = method.predict(test_data, info, model_name=args.evaluate_option)
            loss_list.append(vl)
            results_list.append(vres)
            time_list.append(time_cost)
            metric1, metric2 = show_results(args, info, metric_name, loss_list, results_list, time_list)
            metric1_by_model.append(metric1)
            metric2_by_model.append(metric2)

    return metric1_by_model, metric2_by_model

def preprocessing(data, type):
    X, y = train_test_split(data, test_size=0.2, random_state=42)
    number = X.select_dtypes(exclude=['object'])
    category = X.select_dtypes(include=['object'])
    newfile = './dataset/' + dataset + '/'
    if type == "train":
        if number.shape[1] != 0:
            np.save(newfile + 'N_train.npy', number)
            np.save(newfile + 'N_val.npy', number)
        else:
            if os.path.exists(newfile + 'N_train.npy'):
                os.remove(newfile + 'N_train.npy')
            if os.path.exists(newfile + 'N_val.npy'):
                os.remove(newfile + 'N_val.npy')
        if category.shape[1] != 0:
            np.save(newfile + 'C_train.npy', category)
            np.save(newfile + 'C_val.npy', category)
        else:
            if os.path.exists(newfile + 'C_train.npy'):
                os.remove(newfile + 'C_train.npy')
            if os.path.exists(newfile + 'C_val.npy'):
                os.remove(newfile + 'C_val.npy')
        np.save(newfile + 'y_train.npy', y)
        np.save(newfile + 'y_val.npy', y)
    elif type == "test":
        if number.shape[1] != 0:
            np.save(newfile + 'N_test.npy', number)
        else:
            if os.path.exists(newfile + 'N_test.npy'):
                os.remove(newfile + 'N_test.npy')
        if category.shape[1] != 0:
            np.save(newfile + 'C_test.npy', category)
        else:
            if os.path.exists(newfile + 'C_test.npy'):
                os.remove(newfile + 'C_test.npy')
        np.save(newfile + 'y_test.npy', y)

    json_file = './dataset/' + dataset + '/info.json'
    with open(json_file, 'r') as file:
        info = json.load(file)
    info['n_num_features'] = number.shape[1]
    info['n_cat_features'] = category.shape[1]
    with open(json_file, 'w') as file:
        json.dump(info, file)
