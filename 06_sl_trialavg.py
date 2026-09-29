#!/usr/bin/env python3
"""
Trial averaging of the preprocessed VASO data (03_sl_preprocess_vaso.sh): estimates the trial-averaged
responses of all conditions for BOLD and VASO (percent signal change), and the F-statistic of the
trial averaging averaged over both run types (used for ROI generation and the group clusters).
"""

import sys
import os
import json
from nilearn.image import math_img

from fmri_analysis import layer_analysis as analysis
import utils

studyDataDir = sys.argv[1]
subject = sys.argv[2]

# conditions of each run type, keyed by their stimulus codes in the trial order
run_conditions = {"alpharem": {3: "alpha", 2: "rem"},
                  "gonogo": {5: "act", 4: "non-act"}}
trial_order = {"alpharem": [2, 3, 3, 3, 2, 2, 3, 2, 3, 3, 2, 2, 2, 3, 2, 3, 3, 3, 2, 2],
               "gonogo":  [4, 5, 5, 5, 4, 4, 5, 4, 5, 5, 4, 4, 4, 5, 4, 5, 5, 5, 4, 4]}
trial_duration = 32
onset_delay = 8

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

for run_type in run_conditions:
    in_files_nulled = [os.path.join(preprocess_dir, f"func_{run_type}_nulled.nii")]
    in_files_notnulled = [os.path.join(preprocess_dir, f"func_{run_type}_notnulled.nii")]

    # name trials by condition, so that the trial averages are named by condition
    trial_conditions = [run_conditions[run_type][code] for code in trial_order[run_type]]
    stim_times_runs = [analysis.calc_stim_times(onset_delay=onset_delay, trial_duration=trial_duration,
                                            trial_order=trial_conditions)]
    
    analysis.average_trials_vaso_3ddeconvolve(in_files_nulled, in_files_notnulled, 
                                              stim_times_runs, trial_duration, trialavg_dir, desc=run_type,
                                              polort=5, vaso_readout_delay=vaso_readout_delay, tentzero=True)

# Average the two run types fstat files
fstat_alpharem = os.path.join(trialavg_dir, 'trialavg_bold_alpharem_fstat.nii')
fstat_gonogo = os.path.join(trialavg_dir, 'trialavg_bold_gonogo_fstat.nii')
fstat_average = os.path.join(trialavg_dir, "trialavg_bold_combined_fstat.nii")
math_img("(img1+img2)/2",img1=fstat_gonogo,img2=fstat_alpharem).to_filename(fstat_average)

# save conditions and the time resolution of the trial averages (the volume TR) for subsequent steps
with open(os.path.join(studyDataDir, subject, "func",
                       f"{subject}_task-alpharem_acq-nulled_run-1_bold.json"), "r") as f:
    tr = json.load(f)["RepetitionTime"]
utils.write_params(os.path.join(trialavg_dir, "trialavg_params.json"),
                   {"run_conditions": {run_type: list(conditions.values())
                                       for run_type, conditions in run_conditions.items()},
                    "tr": tr})