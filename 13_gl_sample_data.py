#!/usr/bin/env python3
"""
Samples the trial-averaged data of all conditions from the layer ROIs of all subjects, for all analyses:
1. ROIs of all target areas (VASO and BOLD), and their volumes
2. main ROI with a depth gap of 1/3 between the layers
3. main ROI without the subjects whose ROI touches the slab boundary
4. group cluster ROIs
5. manually drawn layer ROIs (BIDS derivative dataset derivatives/manual-layer-rois)
The sampled data are saved together with the parameters needed by subsequent steps.
"""

import sys
import os
import csv
import pickle
import numpy as np
from joblib import Parallel, delayed
import utils

study_data_dir = sys.argv[1]
subjects = utils.subjects()

# condition contrasts, calculated in addition to the conditions
condition_contrasts = {"alpha - rem": ["alpha", "rem"],
                       "act - non-act": ["act", "non-act"]}
# subjects whose ROI touches the imaging slab boundary (excluded in a control analysis)
slab_boundary_subjects = ["sub-02", "sub-03", "sub-04", "sub-07"]

MAX_CPUS = utils.max_cpus()

# conditions and time resolution of the trial averages from 06_sl_trialavg.py
trialavg_params = utils.read_subject_params(study_data_dir, "trialavg", "trialavg_params.json", subjects)
run_conditions = trialavg_params["run_conditions"]
# ROIs generated in 08_sl_generate_rois.py
roi_params = utils.read_subject_params(study_data_dir, "roi", "roi_params.json", subjects)
areas = np.array(roi_params["target_areas"])
main_area = roi_params["main_area"]
cluster_idcs = roi_params["cluster_idcs"]
main_roi_fname = f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{main_area}.nii'

sample_data_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')
os.makedirs(sample_data_dir, exist_ok=True)

# 1. main replication analysis, for all areas, VASO and BOLD
data_all_areas = dict()
for method in ['bold', 'vaso']:
    data_all_areas[method] = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
        delayed(utils.sample_data)(study_data_dir, subjects,
                                   roi_base_fname=f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{area}.nii',
                                   run_conditions=run_conditions, condition_contrasts=condition_contrasts,
                                   method=method)
        for area in areas)
# also quantify ROI volumes
volume_all_areas = Parallel(n_jobs=min(len(areas), MAX_CPUS))(
    delayed(utils.estimate_roi_volume)(study_data_dir, subjects,
                                 roi_fname=f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{area}.nii')
    for area in areas)

# 2. 1/3 depth gap analysis
data_depth_gap = utils.sample_data(study_data_dir, subjects, main_roi_fname,
                                   run_conditions, condition_contrasts, depth_gap=1/3)

# 3. With exclusion of subjects whose ROI touches the slab boundary
subjects_no_slab_boundary = [subject for subject in subjects if subject not in slab_boundary_subjects]
data_no_slab_boundary = utils.sample_data(study_data_dir, subjects_no_slab_boundary, main_roi_fname,
                                          run_conditions, condition_contrasts)

# 4. Group cluster based rois
data_group_clusters = Parallel(n_jobs=min(len(cluster_idcs), MAX_CPUS))(
        delayed(utils.sample_data)(study_data_dir, subjects,
                                   roi_base_fname=f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A{main_area}.nii",
                                   run_conditions=run_conditions, condition_contrasts=condition_contrasts)
        for cluster_idx in cluster_idcs)

# 5. Manual rois (layer ROIs with the label values given in the lookup table of the dataset)
manual_roi_dir = os.path.join('derivatives', 'manual-layer-rois')
with open(os.path.join(study_data_dir, manual_roi_dir, 'desc-dlPFClayers_dseg.tsv'), 'r') as f:
    manual_layer_labels = {row['name']: int(row['index']) for row in csv.DictReader(f, delimiter='\t')}
data_manual_roi = utils.sample_data(study_data_dir, subjects, '{subject}_space-func_desc-dlPFClayers_dseg.nii.gz',
                                    run_conditions, condition_contrasts,
                                    roi_dir=os.path.join(manual_roi_dir, '{subject}', 'anat'),
                                    layer_labels=manual_layer_labels)

# Save the results (together with the parameters needed by subsequent steps)
with open(os.path.join(sample_data_dir, 'sample_data.pkl'), 'wb') as f:
    pickle.dump({'data_all_areas': data_all_areas,
                 'volume_all_areas': volume_all_areas,
                 'areas': areas,
                 'main_area': main_area,
                 'data_depth_gap': data_depth_gap,
                 'data_no_slab_boundary': data_no_slab_boundary,
                 'slab_boundary_subjects': slab_boundary_subjects,
                 'data_group_clusters': data_group_clusters,
                 'cluster_idcs': cluster_idcs,
                 'data_manual_roi': data_manual_roi,
                 'run_conditions': run_conditions,
                 'condition_contrasts': condition_contrasts,
                 'tr': trialavg_params['tr']}, f)
