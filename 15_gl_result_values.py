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


# 0. Load parameters and results
with open(os.path.join(sample_dir, 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
areas = sampled_data['areas']
main_area = sampled_data['main_area']
cluster_idcs = sampled_data['cluster_idcs']
run_conditions = sampled_data['run_conditions']

with open(os.path.join(analysis_dir, 'results.pkl'), 'rb') as f:
    saved_results = pickle.load(f)
results_all_areas = saved_results['results_all_areas']
finn_np2 = saved_results['finn_np2']

results_main = {modality: results_all_areas[modality][np.where(areas == main_area)[0][0]]
                for modality in ["bold", "vaso"]}


def write_anova_report(fname, results, modality):
    """ Writes the ANOVA results of one analysis and the bootstrap confidence bounds
    of the layer x contrast interaction effect sizes in the direction of Finn et al. 2019. """
    with open(fname, "w+") as f:
        for run_type in run_conditions.keys():
            for layer in ["superficial", "deep"]:
                print(f"({' vs. '.join(run_conditions[run_type])}) x (delay vs. response) -> {layer} layer {modality} signal", file=f)
                print(results['anova1'][run_type, layer].to_string(max_cols=None), file=f)
                print("\n", file=f)

        for period in ['delay','response']:
            print(
                f"(superficial vs. deep layer) x (alpha contrast vs. action contrast) -> {period} period condition difference in {modality}",
            file=f)
            print(results['anova2'][period].to_string(max_cols=None), file=f)
            print("\n", file=f)

            # one-sided 95% bootstrap bound
            np2_values = results['np2_signed_combined_data']['np2']
            period_mask = results['np2_signed_combined_data']['period'] == period
            if finn_np2[period] > 0:
                # Finn et al. 2019 signed np2 was positive (superficial > deep) for delay period
                print(f"95% confidence bound towards positive effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_up = {np.percentile(np2_values[period_mask],95)}", file=f)
            else:
                # Finn et al. 2019 signed np2 was negative (deep > superficial) for response period
                print(f"95% confidence bound towards negative effect of Finn et al. 2019 in {period} period:", file=f)
                print(f"np2_95perc_down = {-np.percentile(-np2_values[period_mask], 95)}", file=f)
            print("\n", file=f)


# reports: file name -> (results, modality)
reports = {
    # 1. main analysis
    "ANOVA_bold.txt": (results_main["bold"], "bold"),
    "ANOVA_vaso.txt": (results_main["vaso"], "vaso"),
    # 2. depth gap analysis
    "ANOVA_depth_gap_vaso.txt": (saved_results['results_depth_gap'], "vaso"),
    # 3. control without subjects whose ROI is at the slab boundary
    "ANOVA_no_slab_boundary_vaso.txt": (saved_results['results_no_slab_boundary'], "vaso"),
    # 4. manual rois
    "ANOVA_manual_roi_vaso.txt": (saved_results['results_manual_roi'], "vaso"),
}
# 5. group cluster rois
for cluster_idx, results in zip(cluster_idcs, saved_results['results_group_clusters']):
    reports[f"ANOVA_group_cluster_{cluster_idx}_vaso.txt"] = (results, "vaso")

for fname, (results, modality) in reports.items():
    write_anova_report(os.path.join(result_dir, fname), results, modality)
