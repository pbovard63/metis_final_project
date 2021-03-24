'''
Functions on how to score the final models
'''
#Importing packages to be used in the functions:
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
import seaborn as sns
from sklearn.metrics import r2_score
import scipy.stats as st
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import OneHotEncoder
from sklearn import datasets
from sklearn.metrics import accuracy_score, precision_score, recall_score, precision_recall_curve,f1_score, fbeta_score
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from xgboost import XGBClassifier

#Importing some individual classification and regression functions:
from location_regression_functions import *
from pitch_cat_functions import *

def final_dataframe_setup_test(player_name, test_data, train_val_data):
    '''
    Arguments: takes in a player name and a dataframe of MLB league-wide pitch data.  The default split size for train/validation by at bat is 0.20.
    Returns: a dataframe of that pitchers pitches, split into training and validation sets for modeling.
    '''
    #Filtering the full dataset for the selected player, and removing null last pitches:
    player_df = test_data[(test_data.pitcher_full_name == player_name) & (test_data.last_pitch_px.notnull())]
    
    player_tv_data = train_val_data[(train_val_data.pitcher_full_name == player_name) & (train_val_data.last_pitch_px.notnull())]

    #One-hot-encoding the necessary columns.
    ohe_cols = ['stand', 'p_throws']
    ohe_df = column_ohe_maker(player_df, ohe_cols)

    #Numerically encoding the last pitch type and the current pitch type, using new functions since these must match the codings from the train/val set:
    type_list = player_tv_data['pitch_type'].value_counts().index
    type_dict = {}
    for i, pitch_type in enumerate(type_list):
        type_dict[pitch_type] = i
    print('Here is the coding for pitch type:')
    print(type_dict)
    #Last Pitch Type:
    last_type_list = player_tv_data['last_pitch_type'].value_counts().index
    last_type_dict = {}
    for i, pitch_type in enumerate(last_type_list):
        last_type_dict[pitch_type] = i
    print('Here is the coding for last pitch type:')
    print(last_type_dict)
    
    #Pitch_Type_Num
    ohe_df['Pitch_Type_Num'] = 0
    for i, pitch in enumerate(ohe_df['pitch_type']):
        if pitch in last_type_dict.keys():
            ohe_df.Pitch_Type_Num.iloc[i] = type_dict[pitch]
        else:
            ohe_df.Pitch_Type_Num.iloc[i] = 0 #If it's a new pitch, remove the row since there's no way to have trained on it.
           
        
    #Last Pitch Type Num:
    ohe_df['Last_Pitch_Type_Num'] = 0
    for i, pitch in enumerate(ohe_df['last_pitch_type']):
        if pitch in last_type_dict.keys():
            ohe_df.Last_Pitch_Type_Num.iloc[i] = last_type_dict[pitch]
        else:
            ohe_df.Last_Pitch_Type_Num.iloc[i] = 0 #If it's a new pitch, remove the row since there's no way to have trained on it.

    #Returning the output_df only, since splitting is not needed here:
    return ohe_df

def final_xgboost_pitch_classification_scorer(dataframe, model):
    '''
    Arguments: takes in a training and validation dataframe of a pitcher.
    Returns: an XGBoost classification model, with metrics on the validation set.
    '''
    #First, declaring the feature columns to use:
    xg_cols = ['Cluster','inning', 'top', 'on_1b', 'on_2b', 'on_3b', 'b_count', 's_count', 'outs', 'stand_R',
       'pitcher_run_diff','last_pitch_speed', 'last_pitch_px', 'last_pitch_pz','pitch_num','cumulative_pitches',
       'cumulative_ff_rate', 'cumulative_sl_rate', 'cumulative_ft_rate',
       'cumulative_ch_rate', 'cumulative_cu_rate', 'cumulative_si_rate',
       'cumulative_fc_rate', 'cumulative_kc_rate', 'cumulative_fs_rate',
       'cumulative_kn_rate', 'cumulative_ep_rate', 'cumulative_fo_rate',
       'cumulative_sc_rate', 'Last_Pitch_Type_Num', 'last_5_ff',
       'last_5_sl', 'last_5_ft', 'last_5_ch', 'last_5_cu', 'last_5_si',
       'last_5_fc', 'last_5_kc', 'last_5_fs', 'last_5_kn', 'last_5_ep',
       'last_5_fo', 'last_5_sc']
    
    #Setting up the X and y train/validation sets for random forest classification:
    X_xg_test = dataframe[xg_cols]
    y_xg_test = dataframe['Pitch_Type_Num']

    y_xg_test_pred = model.predict(X_xg_test)

    #Scoring:
    acc = accuracy_score(y_xg_test, y_xg_test_pred)
    prec = precision_score(y_xg_test, y_xg_test_pred, average='macro'), 
    recall = recall_score(y_xg_test, y_xg_test_pred, average='macro')
    print('Test Set Accuracy: {}'.format(acc))
    print('Test Set Precision: {}'.format(prec))
    print('Test Set Recall: {}'.format(recall))

    cm = confusion_matrix(y_xg_test, y_xg_test_pred)
    print('XGBoost Pitch Classification confusion matrix test set results:')
    print(cm)

    #Mapping the predictions onto the validation dataframe and outputting:
    dataframe['pitch_pred'] = y_xg_test_pred

    #returning the mapped frame:
    return dataframe

def final_px_linear_regression_scorer(dataframe, model):
    '''
    Arguments: takes in a training and validation dataframe.
    Returns: a linear regression model of the x location of the pitch (px), with the predicted values mapped onto the validation dataframe input.
    '''
    #Setting up the columns needed:
    px_cols = ['Cluster','inning', 'top', 'on_1b', 'on_2b', 'on_3b', 'b_count', 's_count', 'outs', 'stand_R',
       'pitcher_run_diff','last_pitch_speed', 'last_pitch_px', 'last_pitch_pz','pitch_num','cumulative_pitches',
       'Last_Pitch_Type_Num', 'pitch_pred']

    #Setting up the x and y inputs for linear regression:
    X_px_test = dataframe[px_cols]
    y_px_test = dataframe['px']
    
    #Fitting linear regression on the training data, then predicting and scoring on the validation set:
    y_px_pred_test = model.predict(X_px_test)
    px_mae = mae(y_px_test, y_px_pred_test)
    print('Val Px MAE: {} ft.'.format(px_mae))

    #Mapping the predicted px values onto the validation set:
    dataframe['px_pred'] = y_px_pred_test

    return dataframe


def final_pz_linear_regression_scorer(dataframe, model):
    '''
    Arguments: takes in a training and validation dataframe.
    Returns: a linear regression model of the x location of the pitch (px), with the predicted values mapped onto the validation dataframe input.
    '''
    #Setting up the columns needed:
    pz_cols = ['Cluster','inning', 'top', 'on_1b', 'on_2b', 'on_3b', 'b_count', 's_count', 'outs', 'stand_R',
       'pitcher_run_diff','last_pitch_speed', 'last_pitch_px', 'last_pitch_pz','pitch_num','cumulative_pitches',
       'Last_Pitch_Type_Num', 'Pitch_Type_Num', 'px_pred']

    #Setting up the x and y inputs for linear regression:
    X_pz_test = dataframe[pz_cols]
    y_pz_test = dataframe['pz']
    
    #Fitting linear regression on the training data, then predicting and scoring on the validation set:
    y_pz_pred_test = model.predict(X_pz_test)
    pz_mae = mae(y_pz_test, y_pz_pred_test)
    print('Val Pz MAE: {} ft.'.format(pz_mae))

    #Mapping the predicted px values onto the validation set:
    dataframe['pz_pred'] = y_pz_pred_test

    return dataframe

def pitch_prediction_test_score(player_name, data, model_list, train_val_data):
    '''
    Arguments: takes in a player name and a dataframe of MLB league-wide pitch data.  The default split size for train/validation by at bat is 0.20.
    Returns: Runs pitch classification modeling via Random Forest for pitch types, then pitch location prediction via linear regression.  
    Outputs a dataframe with the predicted values mapped onto the original validation dataframe.
    '''
    print('Pitch Modeling Test Set SCores for {}'.format(player_name)) #printing the pitcher name, so it's clear to the user

    #First, setting up the dataframe and splitting the data into train and validation sets:
    test_df = final_dataframe_setup_test(player_name, data, train_val_data)
    xg_model = model_list[0][0]
    px_model = model_list[0][1]
    pz_model = model_list[0][2]

    #Scoring and mapping out the models
    xg_df = final_xgboost_pitch_classification_scorer(test_df, xg_model)
    px_df = final_px_linear_regression_scorer(xg_df, px_model)
    pz_df = final_pz_linear_regression_scorer(px_df, pz_model)
        
    #returning the validation dataframe with the predictions mapped out:
    return pz_df

def multiple_pitcher_scores(player_name_list, data, model_dict, train_val_data):
    '''
    Arguments: takes in a list of player names and a dataframe of MLB league-wide pitch data.  The default split size for train/validation by at bat is 0.20.
    Returns: Runs pitch classification modeling via Random Forest for pitch types, then pitch location prediction via linear regression.  
    Outputs a dataframe with the predicted values mapped onto the original validation dataframe.
    '''
    counter = 0
    for player in player_name_list:
        model_list = model_dict[player]
        test_df = pitch_prediction_test_score(player, data, model_list, train_val_data)
        #Adding in a check to initiate the output dataframe for the first loop through:
        if counter == 0:
            output_df = pd.DataFrame(columns=test_df.columns)
        output_df = pd.concat([output_df, test_df])
        counter += 1
        print('\n')
        print('\n')
    return output_df
