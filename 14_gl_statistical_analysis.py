#!/usr/bin/env python3
"""
Run main analysis and save results for future visualization.

uses tenzero (trialavg5) data and 100 mm^2 target rois as main ROI size
(but analyses data for all ROI sizes)

includes:
- main replication analysis (100 mm^2 ROI)
- analysis of all ROI sizes (20, 40, ..., 400 mm^2)
- analysis of 100 mm^2 ROI with depth gap of 1/3
- analysis of 100 mm^2 ROI without slab boundary subjects

also runs analysis using a layer gap of 1/3, and without slab boundary subjects?
(100 mm^2 only)

args:
    - studyDataDir: path to the study data directory
""" 
import sys
from joblib import Parallel, delayed
import pickle
import sys
import os
import utils # TODO consider movin the functions here

study_data_dir = sys.argv[1]
subjects = [f'sub-{i:02d}' for i in range(1, 22)]  # subjects are sub-01 to sub-21

# set MAX_CPUS based on OMP_NUM_THREADS, set to 1 if not set
try:
    MAX_CPUS = int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    MAX_CPUS = 1

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

# 1. main replication analysis, for all areas, VASO and BOLD
results_all_areas = dict()
for method in ['bold', 'vaso']:
    results_all_areas[method] = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
        delayed(utils.analyze_sampled_data)(data) for data in data_all_areas[method])

# 2. 1/3 depth gap analysis
results_depth_gap = utils.analyze_sampled_data(data_depth_gap)

# 3. With exclusion of subjects 2,3,4,7
results_no_slab_boundary = utils.analyze_sampled_data(data_no_slab_boundary)

# 4. group cluster based rois
results_group_clusters = Parallel(n_jobs=min(len(clusters_idcs), MAX_CPUS))(
    delayed(utils.analyze_sampled_data)(data) for data in data_group_clusters)

# 5. manual roi
results_manual_roi = utils.analyze_sampled_data(data_manual_roi)

# save the results
with open(os.path.join(analysis_dir, f'results.pkl'), 'wb') as f:
    pickle.dump({
        'results_all_areas': results_all_areas,
        'results_depth_gap': results_depth_gap,
        'results_no_slab_boundary': results_no_slab_boundary,
        'results_group_clusters': results_group_clusters,
        'results_manual_roi': results_manual_roi}, f)