#!/usr/bin/env python3

"""
Generate all result values to be used in the text.
"""
import sys
import os
import pickle
import numpy as np


study_data_dir = sys.argv[1]

result_dir = os.path.join(study_data_dir,'derivatives','results')
analysis_dir = os.path.join(study_data_dir, 'derivatives', 'analysis')
sample_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')

os.makedirs(result_dir, exist_ok=True)

run_conditions = {"alpharem": ["alpha", "rem"], "gonogo": ["act", "non-act"]}

# 0. Load results data
# load the sampled data
with open(os.path.join(sample_dir, 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
data_all_areas = sampled_data['data_all_areas']
areas = sampled_data['areas']
data_depth_gap = sampled_data['data_depth_gap']
data_no_slab_boundary = sampled_data['data_no_slab_boundary']
data_manual_roi = sampled_data['data_manual_roi']
data_group_clusters = sampled_data['data_group_clusters']
cluster_idcs = sampled_data['cluster_idcs']

# load results
with open(os.path.join(analysis_dir,f'results.pkl'), 'rb') as f:
    saved_results = pickle.load(f)    
results_all_areas = saved_results['results_all_areas']
results_depth_gap = saved_results['results_depth_gap']
results_no_slab_boundary = saved_results['results_no_slab_boundary']
results_manual_roi = saved_results['results_manual_roi']
results_group_clusters = saved_results['results_group_clusters']

results_main = {modality: results_all_areas[modality][np.where(areas == 100)[0][0]] 
                for modality in ["bold", "vaso"]}

# 1. main analysis
for modality in ["bold", "vaso"]:
    with open(os.path.join(result_dir, f"ANOVA_{modality}.txt"), "w+") as f:
        for run_type in run_conditions.keys():
            for layer in ["superficial", "deep"]:
                print(f"({' vs. '.join(run_conditions[run_type])}) x (delay vs. probe) -> {layer} layer {modality} signal", file=f)
                print(results_main[modality]['anova1'][run_type, layer].to_string(max_cols=None), file=f)
                print("\n", file=f)

        for period in ['delay','response']:
            print(
                f"(superficial vs. deep layer) x (alpha contrast vs. action contrast) -> {period} period condition difference in {modality}", 
            file=f)
            print(results_main[modality]['anova2'][period].to_string(max_cols=None), file=f)
            print("\n", file=f)

            # bootstrap 95% CI
            np2_values = results_main['vaso']['np2_signed_combined_data']['np2']
            period_mask = results_main['vaso']['np2_signed_combined_data']['period'] == period
            if period == 'delay': 
                # Finn et al. 2019 signed np2 was positive (superficial > deep) for delay period
                print(f"95% confidence bound towards postive effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_up = {np.percentile(np2_values[period_mask],95)}", file=f)
            elif period == 'response':
                # Finn et al. 2019 signed np2 was negative (deep > superficial) for response period
                print(f"95% confidence bound towards negative effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_down = {-np.percentile(-np2_values[period_mask], 95)}", file=f)
            print("\n", file=f)

# 2. depth gap analysis
modality = "vaso"
with open(os.path.join(result_dir, f"ANOVA_depth_gap_{modality}.txt"), "w+") as f:
        for run_type in run_conditions.keys():
            for layer in ["superficial", "deep"]:
                print(f"({' vs. '.join(run_conditions[run_type])}) x (delay vs. probe) -> {layer} layer {modality} signal", file=f)
                print(results_depth_gap['anova1'][run_type, layer].to_string(max_cols=None), file=f)
                print("\n", file=f)

        for period in ['delay','response']:
            print(
                f"(superficial vs. deep layer) x (alpha contrast vs. action contrast) -> {period} period condition difference in {modality}", 
            file=f)
            print(results_depth_gap['anova2'][period].to_string(max_cols=None), file=f)
            print("\n", file=f)

            # bootstrap 95% CI
            np2_values = results_depth_gap['np2_signed_combined_data']['np2']
            period_mask = results_depth_gap['np2_signed_combined_data']['period'] == period
            if period == 'delay': 
                # Finn et al. 2019 signed np2 was positive (superficial > deep) for delay period
                print(f"95% confidence bound towards postive effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_up = {np.percentile(np2_values[period_mask],95)}", file=f)
            elif period == 'response':
                # Finn et al. 2019 signed np2 was negative (deep > superficial) for response period
                print(f"95% confidence bound towards negative effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_down = {-np.percentile(-np2_values[period_mask], 95)}", file=f)
            print("\n", file=f)

# 3. control without subjects whose ROI is at the slab boundary
with open(
        os.path.join(result_dir, f"ANOVA_no_slab_boundary" + f"_{modality}.txt"), "w+") as f:
        for run_type in run_conditions.keys():
            for layer in ["superficial", "deep"]:
                print(f"({' vs. '.join(run_conditions[run_type])}) x (delay vs. probe) -> {layer} layer {modality} signal", file=f)
                print(results_no_slab_boundary['anova1'][run_type, layer].to_string(max_cols=None), file=f)
                print("\n", file=f)

        for period in ['delay','response']:
            print(
                f"(superficial vs. deep layer) x (alpha contrast vs. action contrast) -> {period} period condition difference in {modality}", 
            file=f)
            print(results_no_slab_boundary['anova2'][period].to_string(max_cols=None), file=f)
            print("\n", file=f)

            # bootstrap 95% CI
            np2_values = results_no_slab_boundary['np2_signed_combined_data']['np2']
            period_mask = results_no_slab_boundary['np2_signed_combined_data']['period'] == period
            if period == 'delay': 
                # Finn et al. 2019 signed np2 was positive (superficial > deep) for delay period
                print(f"95% confidence bound towards postive effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_up = {np.percentile(np2_values[period_mask],95)}", file=f)
            elif period == 'response':
                # Finn et al. 2019 signed np2 was negative (deep > superficial) for response period
                print(f"95% confidence bound towards negative effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_down = {-np.percentile(-np2_values[period_mask], 95)}", file=f)
            print("\n", file=f)

# 4. manual rois
with open(
        os.path.join(result_dir, f"ANOVA_manual_roi_{modality}.txt"), "w+") as f:
        for run_type in run_conditions.keys():
            for layer in ["superficial", "deep"]:
                print(f"({' vs. '.join(run_conditions[run_type])}) x (delay vs. probe) -> {layer} layer {modality} signal", file=f)
                print(results_manual_roi['anova1'][run_type, layer].to_string(max_cols=None), file=f)
                print("\n", file=f)

        for period in ['delay','response']:
            print(
                f"(superficial vs. deep layer) x (alpha contrast vs. action contrast) -> {period} period condition difference in {modality}", 
            file=f)
            print(results_manual_roi['anova2'][period].to_string(max_cols=None), file=f)
            print("\n", file=f)

            # bootstrap 95% CI
            np2_values = results_manual_roi['np2_signed_combined_data']['np2']
            period_mask = results_manual_roi['np2_signed_combined_data']['period'] == period
            if period == 'delay': 
                # Finn et al. 2019 signed np2 was positive (superficial > deep) for delay period
                print(f"95% confidence bound towards postive effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_up = {np.percentile(np2_values[period_mask],95)}", file=f)
            elif period == 'response':
                # Finn et al. 2019 signed np2 was negative (deep > superficial) for response period
                print(f"95% confidence bound towards negative effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_down = {-np.percentile(-np2_values[period_mask], 95)}", file=f)
            print("\n", file=f)