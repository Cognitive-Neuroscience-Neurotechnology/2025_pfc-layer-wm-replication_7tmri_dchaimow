#!/usr/bin/env python3
"""
Assume we have run ciftify and freesurfer and vaso processing and have registered fs T1 to vaso.
"""

import sys
import os
from nilearn.image import math_img

from fmri_analysis import layer_analysis as analysis

studyDataDir = sys.argv[1]
subject = sys.argv[2]
    
# set file paths
preprocess_dir = os.path.join(studyDataDir, "derivatives", "preprocess", subject)

trialavg_dir = os.path.join(studyDataDir, "derivatives", "trialavg", subject)
os.makedirs(trialavg_dir, exist_ok=True)

# read in vaso readout onsets from vaso_readout_onsets.txt
with open(os.path.join(preprocess_dir,"vaso_readout_onsets.txt"), 'r') as f:
    nulled_onset, notnulled_onset = [float(line.strip()) for line in f]
vaso_readout_delay = notnulled_onset - nulled_onset

# TODO: Now we are only shifting the times of the notnulled runs by the vaso readout delay,
# consider also shifting the nulled runs to account for the delay in the beginning, that would
# slightly shift the estimated time course.

trial_order = {"alpharem": [2, 3, 3, 3, 2, 2, 3, 2, 3, 3, 2, 2, 2, 3, 2, 3, 3, 3, 2, 2],
               "gonogo":  [4, 5, 5, 5, 4, 4, 5, 4, 5, 5, 4, 4, 4, 5, 4, 5, 5, 5, 4, 4]}
trial_duration = 32
onset_delay = 8

for run_type in ["alpharem", "gonogo"]:
    in_files_nulled = [os.path.join(preprocess_dir, f"func_{run_type}_nulled.nii")]
    in_files_notnulled = [os.path.join(preprocess_dir, f"func_{run_type}_notnulled.nii")]

    stim_times_runs = [analysis.calc_stim_times(onset_delay=onset_delay, trial_duration=trial_duration, 
                                            trial_order=trial_order[run_type])]
    
    analysis.average_trials_vaso_3ddeconvolve(in_files_nulled, in_files_notnulled, 
                                              stim_times_runs, trial_duration, trialavg_dir, desc=run_type,
                                              polort=5, vaso_readout_delay=vaso_readout_delay, tentzero=True)

# Average the two run types fstat files
fstat_alpharem = os.path.join(trialavg_dir, 'trialavg_bold_alpharem_fstat.nii')
fstat_gonogo = os.path.join(trialavg_dir, 'trialavg_bold_gonogo_fstat.nii')
fstat_average = os.path.join(trialavg_dir, "trialavg_bold_combined_fstat.nii")
math_img("(img1+img2)/2",img1=fstat_gonogo,img2=fstat_alpharem).to_filename(fstat_average)