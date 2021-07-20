from train import *
from classify import *
from data_processes import *
from data_visulisation import *

#################
# Configuration #
#################
# directories
ROMS_directory = '/Volumes/LP_MstrData/master-data/ocean/ROMS/Montague_subset'
# analysis zone box
analysisBox = [149, 151, -37.2, -35] # EAC Jet
# check study zone box position
check_boxROMS([analysisBox], ROMS_directory, 
            depthmax=4000, save=True, out_fn='./plots/ROMS_lowres.png', title='lowres',
            zoom2box=True)

# build EAC LR model
lr_model = current_model('./data/training_data.csv')

# get count data for regions
CC_probs(ROMS_directory, lr_model, analysisBox, years=[2012, 2014], out_fn='./output/EACprob.csv')
