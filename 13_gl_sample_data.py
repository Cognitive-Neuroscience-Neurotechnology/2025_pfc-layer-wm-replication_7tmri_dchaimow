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

import numpy as np
import sys
from joblib import Parallel, delayed
import pickle
import sys
import os
import numpy as np
import utils 

study_data_dir = sys.argv[1]
subjects = [f'sub-{i:02d}' for i in range(1, 22)]  # subjects are sub-01 to sub-21

# set MAX_CPUS based on OMP_NUM_THREADS, set to 1 if not set
try:
    MAX_CPUS = int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    MAX_CPUS = 1

sample_data_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')
os.makedirs(sample_data_dir, exist_ok=True)

# 1. main replication analysis, for all areas, VASO and BOLD
areas = np.arange(20, 401, 20)  # from 20 to 400 in steps of 20
data_all_areas = dict()
for method in ['bold', 'vaso']:
    data_all_areas[method] = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
        delayed(utils.sample_data)(study_data_dir, subjects, method=method,
                                   roi_base_fname=f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{area}.nii')
        for area in areas)

# also quantify ROI volumes
volume_all_areas = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
    delayed(utils.estimate_roi_volume)(study_data_dir, subjects,
                                 roi_fname=f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{area}.nii')
    for area in areas)

# 2. 1/3 depth gap analysis
data_depth_gap = utils.sample_data(study_data_dir, subjects, depth_gap=1/3)

# 3. With exclusion of subjects 2,3,4,7
subjects_no_slab_boundary = [f'sub-{i:02d}' for i in range(1, 22) if i not in [2, 3, 4, 7]]
data_no_slab_boundary = utils.sample_data(study_data_dir, subjects_no_slab_boundary)

# 4. Group cluster based rois
# find all group clusters
cluster_idcs = [4,5,6,9,10]  # manually set to these clusters that overlap dlPFC
data_group_clusters = Parallel(n_jobs=min(len(cluster_idcs), MAX_CPUS))(
        delayed(utils.sample_data)(study_data_dir, subjects,
                                   roi_base_fname=f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A100.nii")
        for cluster_idx in cluster_idcs)

# 5. Manual rois
data_manual_roi = utils.sample_data(study_data_dir, subjects, 
                                     roi_base_fname='roi_layers_manual.nii',
                                     combined_layer_roi_file=True)

# Save the results
with open(os.path.join(sample_data_dir, 'sample_data.pkl'), 'wb') as f:
    pickle.dump({'data_all_areas': data_all_areas,
                 'volume_all_areas': volume_all_areas,
                 'areas': areas,
                 'data_depth_gap': data_depth_gap,
                 'data_no_slab_boundary': data_no_slab_boundary,
                 'data_group_clusters': data_group_clusters,
                 'cluster_idcs': cluster_idcs,
                 'data_manual_roi': data_manual_roi}, f)