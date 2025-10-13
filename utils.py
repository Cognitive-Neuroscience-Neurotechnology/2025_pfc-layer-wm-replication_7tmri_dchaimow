#!/usr/bin/env python3
"""
Study specific analysis module for Finn et al. 2019 replication study.
"""

# 1. sampling data
# to sample data we currently run dr.prepare_single_subject_data
# let us write a similar function here
#  we need to check wheter it is/can be made general enough to be moved into fmri-analysis library

import pandas as pd
import os
import numpy as np
import nibabel as nib

from fmri_analysis import layer_analysis as analysis

# lets start by writing a function that samples data for a single subject
# we first define layers, optionally introducing a depth gap
# then we sample using anlysis.sample_temporal_layer_data for each condition and combine the resulting
# dataframes into a single dataframe

def sample_data(study_data_dir,subjects, method = 'vaso',
                roi_base_fname='roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A100.nii',
                depth_gap=0, combined_layer_roi_file=False):
    """ Sets up all study related parameters in order to sample trial averaged data under 
    multiple conditions from an ROI according to cortical layer and combines the data 
    from all subjects into a single dataframe. The sampling is done using 
    layer_analysis.sample_temporal_layer_data_to_df.
    """
    run_conditions = {"alpharem": ["alpha", "rem"], "gonogo": ["act", "non-act"]}
    condition_code = {"rem": 2, "alpha": 3, "non-act": 4, "act": 5}
    layers_dict = {"superficial": [0.5 + depth_gap/2, 1], "deep": [0, 0.5 - depth_gap/2]}
    condition_contrasts = {"alpha - rem": ["alpha", "rem"], 
                           "act - non-act": ["act", "non-act"]}

    data_base_fnames = {condition: f"trialavg_{method}_{run_type}_response_condition_{condition_code[condition]}_prcchg.nii"
                        for run_type in run_conditions.keys()
                        for condition in run_conditions[run_type]}
    
    df = pd.DataFrame()
    for subject in subjects:
        trialavg_dir = os.path.join(study_data_dir, "derivatives", "trialavg", subject)
        roi_dir = os.path.join(study_data_dir, "derivatives", "roi", subject)
        refanat_dir = os.path.join(study_data_dir, "derivatives", "ref-anat", subject)

        roi_fname = os.path.join(roi_dir, roi_base_fname)
        if combined_layer_roi_file:
            depths_fname = os.path.join(roi_dir, roi_base_fname)
            layers_dict = {"superficial": [0.5, 1.5], "deep": [1.5, 2.5]}
        else:
            depths_fname = os.path.join(refanat_dir, 'vdfs_depths_equivol.nii')

        data_fnames = {condition: os.path.join(trialavg_dir, data_base_fnames[condition])
                       for condition in data_base_fnames.keys()}



        df_subject = analysis.sample_temporal_layer_data_to_df(data_fnames, roi_fname, depths_fname, 
                                                               layers_dict, tentzero=True)
        df_subject['subject'] = subject
        df = pd.concat([df, df_subject], ignore_index=True)

    # also calculate condition contrasts and add them to the data frame
    df_contrasts = analysis.calculate_df_condition_contrasts(df, condition_contrasts)
    df = pd.concat([df, df_contrasts], ignore_index=True)
    return df

def estimate_roi_volume(study_data_dir, subjects, roi_fname):
    """ Estimates the ROI volumes for all subjects in mm^3 """
    roi_volume = np.zeros(len(subjects))
    for idx, subject in enumerate(subjects):
        fname = os.path.join(study_data_dir, 'derivatives', 'roi', subject, roi_fname)
        roi = nib.load(fname)
        roi_bin = roi.get_fdata()>0
        roi_volume[idx] = roi_bin.sum() * np.prod(roi.header.get_zooms())
    return roi_volume




# 2. run analysis
import pingouin as pg
import numpy as np
import random

# TODO
# [ ] move/adapt summarize_data_in_periods to layer_analysis
# [ ] see if we need non summarized contrast data
# [ ] calculate contrasts on the summarized data
# [ ] move bootstrap_analysis to layer_analysis or here
# [ ] see if we can separate the response analysis
# [ ] consider adding roi volume analysis to roi generation?
# [ ] what about ROI surface overlap?


run_conditions = {"alpharem": ["alpha", "rem"], "gonogo": ["act", "non-act"]}

def calculate_layerdiff_sign(data, condition):
    m = data.groupby(['condition','layer'])['signal'].mean()
    d = m[condition]['superficial'] - m[condition]['deep']
    return np.sign(d)

def bootstrap_sample_data(N, data_delay, data_response):
    subjects = data_delay["subject"].unique()
    bootstrap_data_delay = pd.DataFrame(columns=data_delay.columns)
    bootstrap_data_response = pd.DataFrame(columns=data_response.columns)
    for bootstrap_idx in range(N):
        subj_idx = random.choice(subjects)

        subject_data_delay = data_delay[data_delay["subject"] == subj_idx]
        subject_data_delay = subject_data_delay.assign(subject=bootstrap_idx)
        bootstrap_data_delay = pd.concat([
            bootstrap_data_delay,
            subject_data_delay
        ], ignore_index=True)

        subject_data_response = data_response[data_response["subject"] == subj_idx]
        subject_data_response = subject_data_response.assign(subject=bootstrap_idx)
        bootstrap_data_response = pd.concat([
            bootstrap_data_response,
            subject_data_response
        ], ignore_index=True)

    return bootstrap_data_delay, bootstrap_data_response


def bootstrap_analysis(anova_delay_data, anova_response_data):
    n_trials = 1000
    N = 21
    np2_delay = np.zeros(n_trials)
    np2_response = np.zeros(n_trials)

    for i_trial in range(n_trials):
        data_delay_bootstrap, data_response_bootstrap = bootstrap_sample_data(
            N, anova_delay_data, anova_response_data
        )
        anova_delay_result = pg.rm_anova(
            data=data_delay_bootstrap,
            dv="signal",
            subject="subject",
            within=["layer", "condition"],
            effsize="np2")
      
        np2_delay[i_trial] = anova_delay_result['np2'][2] * calculate_layerdiff_sign(data_delay_bootstrap, 'alpha - rem')

        anova_response_result = pg.rm_anova(
            data=data_response_bootstrap,
            dv="signal",
            subject="subject",
            within=["layer", "condition"],
            effsize="np2")
        np2_response[i_trial] = anova_response_result['np2'][2] * calculate_layerdiff_sign(data_response_bootstrap, 'act - non-act')

    np2_combined_data = pd.concat(
        [
            pd.DataFrame({"np2": np2_delay, "period": "delay"}),
            pd.DataFrame({"np2": np2_response, "period": "response"}),
        ]
    )
    return np2_combined_data

def analyze_sampled_data(data):
    results_anova1 = dict() # period x condition ANOVA (for each layer and run type) 
    results_anova2 = dict() # contrast ANOVA 
    anova2_vaso_data = dict() # contrast ANOVA data for VASO bootstrap analysis
    np2_signed_combined_data = dict() # np2_signed_combined_data
    np2_signed_response_est = dict() # np2_signed_response_est
    np2_signed_delay_est = dict() # np2_signed_delay_est
    period_average_data = analysis.calculate_df_period_averages(data, 
                            {'delay': [3, 4], 'response': [5, 6]})
    print("Period average data:")
    print(period_average_data.head())
    print(period_average_data.columns)
    for run_type in run_conditions.keys():
        conditions = run_conditions[run_type]
        for layer in ['superficial', 'deep']:
            anova_data = period_average_data.loc[
                (period_average_data["layer"] == layer) &
                (period_average_data["condition"].isin(conditions))]
            print(f"ANOVA data for {run_type} {layer} :")
            print(anova_data.head())
            print(anova_data.columns)
            results_anova1[run_type, layer] = pg.rm_anova(
                            data=anova_data,
                            dv="signal",
                            subject="subject",
                            within=["period", "condition"],
                            effsize="np2")
    ### contrast anova
    contrast_period_average_data = analysis.calculate_df_condition_contrasts(period_average_data,
                            {'alpha - rem': ('alpha', 'rem'), 'act - non-act': ('act', 'non-act')})
    for period in ['delay','response']:
        anova_data = contrast_period_average_data.loc[
                    (contrast_period_average_data["period"].isin([period]))]
        anova2_vaso_data[period] = anova_data
        print(f"ANOVA2 data for {period} period:")
        print(anova_data.head())
        print(anova_data.columns)
        results_anova2[period] = pg.rm_anova(
                    data=anova_data,
                    dv="signal",
                    subject="subject",
                    within=["layer", "condition"],
                    effsize="np2")

    ## bootstrap analysis
    np2_signed_combined_data = \
        bootstrap_analysis(anova2_vaso_data['delay'],
                            anova2_vaso_data['response'])
    np2_signed_delay_est = results_anova2['delay']["np2"][2] * \
        calculate_layerdiff_sign(anova2_vaso_data['delay'], 'alpha - rem')
    np2_signed_response_est = results_anova2['response']["np2"][2] * \
        calculate_layerdiff_sign(anova2_vaso_data['response'], 'act - non-act')
    
    results = {'anova1': results_anova1, 'anova2': results_anova2,
                'np2_signed_combined_data': np2_signed_combined_data,
                'np2_signed_delay_est': np2_signed_delay_est,
                'np2_signed_response_est': np2_signed_response_est,
                'contrast_period_average_data': contrast_period_average_data,
                'period_average_data': period_average_data}    
    return results


def create_shared_subplots(gs,row_range=None,col_range=None):
    """Create subplots with automatic sharing and label hiding."""
    
    if row_range is None:
        row_range = range(gs.nrows)
    if col_range is None:
        col_range = range(gs.ncols)
    nrows, ncols = len(row_range), len(col_range)

    axs = np.empty((nrows, ncols), dtype=object)
    # create rows in reverse order so that the last row is created first,
    # i (the enumeration index) should also be reversed
    for i_reverse, row in enumerate(row_range[::-1]):
        for j, col in enumerate(col_range):
            i = nrows - 1 - i_reverse
            share_kwargs = {}
            if i_reverse > 0:
                share_kwargs['sharex'] =  axs[i + 1, j]

                print(f"Creating subplot at ({row}, {col}) stored in axs[{i},{j}] with shared xaxis from axs[{nrows-1},{j}]")
            if j > 0:
                share_kwargs['sharey'] = axs[i, 0]
                print(f"Creating subplot at ({row}, {col}) stored in axs[{i},{j}] with shared yaxis from axs[{i},0]")
                
            if i_reverse==0 and j==0:
                print(f"Creating subplot at ({row}, {col}) stored in axs[{i},{j}]")
            axs[i, j] = gs.figure.add_subplot(gs[row, col], **share_kwargs)
            axs[i, j].yaxis.label.set_visible(j == 0)
            axs[i, j].xaxis.label.set_visible((i == nrows - 1))
            axs[i, j].tick_params(labelbottom=(i == nrows - 1), labelleft=(j == 0))
            
    return axs