#!/usr/bin/env python3
"""
Statistical analysis of the sampled data (13_gl_sample_data.py) for all analyses: period x condition
ANOVAs, layer x contrast ANOVAs and a bootstrap of the signed layer x contrast interaction effect sizes,
to be compared with Finn et al. 2019. The results are saved together with the analysis parameters.
"""

import sys
import os
import pickle
from joblib import Parallel, delayed
import utils

study_data_dir = sys.argv[1]

# trial-average time points averaged in each analysis period
periods = {"delay": [3, 4], "response": [5, 6]}
# contrast whose layer difference is tested in each period (Finn et al. 2019),
# and the signed layer x contrast effect sizes (np2) found by Finn et al. 2019
period_contrasts = {"delay": "alpha - rem", "response": "act - non-act"}
finn_np2 = {"delay": 0.869, "response": -0.685}

MAX_CPUS = utils.max_cpus()

analysis_dir = os.path.join(study_data_dir, 'derivatives', 'analysis')
os.makedirs(analysis_dir, exist_ok=True)

# load the sampled data
with open(os.path.join(study_data_dir, 'derivatives', 'sample_data', 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
data_all_areas = sampled_data['data_all_areas']
areas = sampled_data['areas']
data_depth_gap = sampled_data['data_depth_gap']
data_no_slab_boundary = sampled_data['data_no_slab_boundary']
data_manual_roi = sampled_data['data_manual_roi']
data_group_clusters = sampled_data['data_group_clusters']
clusters_idcs = sampled_data['cluster_idcs']
run_conditions = sampled_data['run_conditions']
condition_contrasts = sampled_data['condition_contrasts']

def analyze(data, seed_task):
    return utils.analyze_sampled_data(data, run_conditions, condition_contrasts, periods,
                                      period_contrasts, seed=utils.seed_for(seed_task))

# 1. main replication analysis, for all areas, VASO and BOLD
results_all_areas = dict()
for method in ['bold', 'vaso']:
    results_all_areas[method] = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
        delayed(analyze)(data, f"bootstrap:{method}:area:{int(area)}")
        for area, data in zip(areas, data_all_areas[method]))

# 2. 1/3 depth gap analysis
results_depth_gap = analyze(data_depth_gap, "bootstrap:vaso:depth_gap")

# 3. With exclusion of subjects 2,3,4,7
results_no_slab_boundary = analyze(data_no_slab_boundary, "bootstrap:vaso:no_slab_boundary")

# 4. group cluster based rois
results_group_clusters = Parallel(n_jobs=min(len(clusters_idcs), MAX_CPUS))(
    delayed(analyze)(data, f"bootstrap:vaso:cluster:{int(cluster_idx)}")
    for cluster_idx, data in zip(clusters_idcs, data_group_clusters))

# 5. manual roi
results_manual_roi = analyze(data_manual_roi, "bootstrap:vaso:manual_roi")

# save the results
with open(os.path.join(analysis_dir, f'results.pkl'), 'wb') as f:
    pickle.dump({
        'results_all_areas': results_all_areas,
        'results_depth_gap': results_depth_gap,
        'results_no_slab_boundary': results_no_slab_boundary,
        'results_group_clusters': results_group_clusters,
        'results_manual_roi': results_manual_roi,
        'periods': periods,
        'period_contrasts': period_contrasts,
        'finn_np2': finn_np2}, f)