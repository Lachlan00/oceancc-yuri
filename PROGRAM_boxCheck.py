from train import *
from classify import *
from data_processes import *
from data_visulisation import *

#################
# Configuration #
#################
# directories
CARS_directory = '/Volumes/LP_MstrData/master-data/ocean/CARS/'
ROMS_directory = '/Volumes/LP_MstrData/master-data/ocean/ROMS/Montague_subset/'
# Training sources
sourcebox = [149, 151, -37.2, -35] # EAC Jet

# check study zone box positions
check_boxROMS([sourcebox], '/Volumes/LP_MstrData/master-data/ocean/ROMS/Montague_subset/', 
            depthmax=4000, save=True, out_fn='./plots/yuri_lowres.png', title='lowres',
            zoom2box=True)

check_boxROMS([sourcebox], '/Volumes/LP_MstrData/master-data/ocean/ROMS/highres/', 
            depthmax=4000, save=True, out_fn='./plots/yuri_highres.png', title='highres',
            zoom2box=True)

# # produce training data
# train_CARS(CARS_directory, './data/', sourceboxA, sourceboxB, plot_boxes=True)

# # build model
# lr_model = current_model('./data/training_data.csv')

# # get count data for regions
# count_Jarv = analyse_region_counts(ROMS_directory, lr_model, JervBox, depthmax=4000)
# count_Bate = analyse_region_counts(ROMS_directory, lr_model, BateBox, depthmax=4000)
# count_Howe = analyse_region_counts(ROMS_directory, lr_model, HoweBox, depthmax=4000)

# # save data
# count_Jarv.to_csv('./data/count_Jerv_jet.csv', index=False)
# count_Bate.to_csv('./data/count_Bate_jet.csv', index=False)
# count_Howe.to_csv('./data/count_Howe_jet.csv', index=False)