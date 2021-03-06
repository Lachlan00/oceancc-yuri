# Perform model
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from os import listdir
from os.path import isfile, join
from netCDF4 import Dataset
from progressbar import ProgressBar
import os

# user defined modules
from data_processes import *

###################################
# Build logistic regression model #
###################################
def current_model(trainData_dir, verbose=True):
    """
    Build current logistic regression classifier
    """
    if verbose:
        print('\nBuilding ocean current classification model.')
        print('loading dataset..')
    train_data = pd.read_csv(trainData_dir, parse_dates = ['datetime'],
                            infer_datetime_format = True)
    # add "day of year" (DoY) to dataset 
    train_data['DoY'] = [int(x.day) for x in train_data['datetime']]

    # standardise data and get fits to be used for later scaling
    if verbose:
        print('Standardising data..')
    scaler_temp = preprocessing.StandardScaler().fit(train_data[['temp']])
    scaler_salt = preprocessing.StandardScaler().fit(train_data[['salt']])
    # scale training dataset
    train_data['temp'] = scaler_temp.transform(train_data[['temp']])
    train_data['salt'] = scaler_salt.transform(train_data[['salt']])

    # fit logistic regression to the training data and cross validate
    if verbose:
        print('Cross validating logistic regression model..')
    lr_model = LogisticRegressionCV(cv=10)
    lr_model = lr_model.fit(train_data[['temp','salt','DoY']], np.ravel(train_data[['class']]))

    # report model feature importance
    if verbose:
        print('Model coeffecients')
        print(lr_model.coef_)
        print('Temp * SD')
        print(np.std(np.asarray(train_data['temp']), 0)*lr_model.coef_[0][0])
        print('Salt * SD')
        print(np.std(np.asarray(train_data['salt']), 0)*lr_model.coef_[0][1])

    # return model and standardisation data as dictionary
    return({"lr_model": lr_model, "scaler_temp": scaler_temp, "scaler_salt": scaler_salt})


######################################################################
# Obtain current classification probability counts from netCDF frame #
######################################################################
def current_probs(lr_model, fh, frame_time, frame_idx, eta_rho, xi_rho):
    # get temperature and salinity data in region of interest
    temp = fh.variables['temp'][frame_idx,29,:,:][eta_rho, xi_rho]
    salt = fh.variables['salt'][frame_idx,29,:,:][eta_rho, xi_rho]
    # place in data frame (ravel to 1d array)
    df = pd.DataFrame(data={'temp': temp.ravel(), 'salt': salt.ravel()})
        # scale data (using scaled data from built model)
    df['scaler_temp'] = lr_model['scaler_temp'].transform(df[['temp']])
    df['scaler_salt'] = lr_model['scaler_salt'].transform(df[['salt']])
    # add DoY
    df['DoY'] = int(frame_time.day)
    df['dt'] = frame_time
    df['eta'] = eta_rho
    df['xi'] = xi_rho
    # replace missing values
    #df = df.fillna(-9999)
    df = df.dropna()

    # get probabilities using model
    probs = lr_model['lr_model'].predict_proba(df[['scaler_temp','scaler_salt','DoY']])
    prob_A, prob_B = zip(*probs)
    df['CCprob'] = prob_A
    # # sub back in missing values (LINE NIT WORKING YET)
    # df[['temp','salt','DoY','CCprob']] = [x if x != 0.0 else np.nan for x in prob_EAC]
    
    # return row for data frame
    return df

###############################
# Compute current probability #
###############################
def CC_probs(ROMS_directory, lr_model, region, years=[2012, 2014], depthmax=1e10, 
    out_fn='./output/EACprob.csv'):
    """
    depthmax in meters (arbitarily large by default)
    """
    print('\nExtracting current classification probability data..')
    # get ROMS netCDF file list
    file_ls = [f for f in listdir(ROMS_directory) if isfile(join(ROMS_directory, f))]
    file_ls = list(filter(lambda x:'.nc' in x, file_ls))
    file_ls = sorted(file_ls)
    # strip all files strating with ._*
    file_ls = [f for f in file_ls if f[0:2] != '._']

    # __get lats and lons__
    nc_file = ROMS_directory + '/' + file_ls[0]
    fh = Dataset(nc_file, mode='r')
    lats = fh.variables['lat_rho'][:] 
    lons = fh.variables['lon_rho'][:]
    bath = fh.variables['h'][:]
    ocean_time = fh.variables['ocean_time'][:]
    array_dimensions = lons.shape

    # __keep only files with in year range__
    pbar = ProgressBar(max_value=len(file_ls))
    # extract count data from each netCDF file
    drop_idx = []
    print('Filtering nc files between '+str(years[0])+' and '+str(years[1]))
    pbar.update(0)
    for i in range(0, len(file_ls)):
        # import file
        nc_file = ROMS_directory + '/' + file_ls[i]
        fh = Dataset(nc_file, mode='r')
        # extract time
        ocean_time = fh.variables['ocean_time'][:]
        frame_time_start = oceantime_2_dt(ocean_time[0])
        frame_time_end = oceantime_2_dt(ocean_time[-1])
        
        # check if in range
        if not (((frame_time_start.year >= years[0]) & (frame_time_start.year <= years[1])) |
               ((frame_time_end.year >= years[0]) & (frame_time_end.year <= years[1]))):
            drop_idx = drop_idx + [i]
        
        pbar.update(i+1)
        # close file
        fh.close()

    # drop files not in list
    for i in sorted(drop_idx, reverse=True):
        del file_ls[i]

    # __combine lat and lon to list of tuples__
    point_tuple = zip(lats.ravel(), lons.ravel(), bath.ravel())
    # iterate over tuple points and keep every point that is in box
    point_list = []
    j = 0
    for i in point_tuple:
        if region[2] <= i[0] <= region[3] and region[0] <= i[1] <= region[1] and i[2] < depthmax:
            point_list.append(j)
        j = j + 1

    # make point list into tuple list of array coordinates
    eta_rho = []
    xi_rho = []
    for i in point_list:
        eta_rho.append(int(i/array_dimensions[1]))
        xi_rho.append(int(i%array_dimensions[1]))

    # set up progress bar
    pbar = ProgressBar(max_value=len(file_ls))
    
    # create data frame to hold count data
    store = [None]*10000000
    # extract count data from each netCDF file
    idx = 0
    print('Classifying ocean currents in '+str(len(file_ls))+' netCDF files..')
    pbar.update(0)
    for i in range(0, len(file_ls)):
        # import file
        nc_file = ROMS_directory + '/' + file_ls[i]
        fh = Dataset(nc_file, mode='r')
        # extract time
        ocean_time = fh.variables['ocean_time'][:]
        # get data
        for j in range(0, len(ocean_time)):
            # get dt from ocean_time
            frame_time = oceantime_2_dt(ocean_time[j])
            # get counts and sub into data frame
            df = current_probs(lr_model, fh, frame_time, j, eta_rho, xi_rho)
            # get lon and lat
            df['lon'] = lons[df.eta, df.xi]
            df['lat'] = lats[df.eta, df.xi]
            # arrange  data
            store[idx] = df[['lon', 'lat', 'eta', 'xi', 'dt', 'temp', 'scaler_temp', 'salt', 'scaler_salt','CCprob']]
            idx += 1
        
        # update progress
        pbar.update(i+1)
        # close file
        fh.close()

    # Fix up list of dataframes
    store = [x for x in store if x is not None]
    df = pd.concat(store).reset_index(drop=True)

    # save output
    df.to_csv(out_fn, index=False)
    print(out_fn)

