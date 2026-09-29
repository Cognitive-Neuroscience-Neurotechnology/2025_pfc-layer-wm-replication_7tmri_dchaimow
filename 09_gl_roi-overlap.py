#!/usr/bin/env python3
"""
ROI overlap across subjects: transforms the ROIs of all subjects to the fs_LR surface and counts
at each vertex the number of subjects whose ROI covers it. The overlap maps are for inspection only
(they are not used by subsequent steps).
"""
import os
import sys
from fmri_analysis import layer_analysis as analysis
import numpy as np
from joblib import Parallel, delayed
import utils

study_data_dir = sys.argv[1]
subjects = utils.subjects()

MAX_CPUS = utils.max_cpus()

# ROIs generated in 08_sl_generate_rois.py
roi_params = utils.read_subject_params(study_data_dir, "roi", "roi_params.json", subjects)

ciftify_group_dir = os.path.join(study_data_dir, 'derivatives', 'ciftify')
register_group_dir = os.path.join(study_data_dir, 'derivatives', 'register')
roi_group_dir = os.path.join(study_data_dir, 'derivatives', 'roi')

roi_overlap_dir = os.path.join(study_data_dir, 'derivatives', 'roi_overlap')
os.makedirs(roi_overlap_dir, exist_ok=True)

def overlap_analysis(roi_surf_fname, overlap_out, subjects, hemi='L'):
    """ Counts at each fs_LR vertex the number of subjects whose ROI covers it. """
    roi_fs_LR_data = Parallel(n_jobs=min(len(subjects), MAX_CPUS))(
        delayed(analysis.transform_roi_native_surf_to_fs_LR)(
            os.path.join(roi_group_dir, subject, roi_surf_fname),
            os.path.join(ciftify_group_dir, subject),
            os.path.join(register_group_dir, subject, f"{hemi}.white.func.surf.gii"),
            os.path.join(register_group_dir, subject, f"{hemi}.pial.func.surf.gii"),
            hemi) for subject in subjects)
    n = np.sum(roi_fs_LR_data, axis=0)
    analysis.write_metric_gifti(overlap_out, n, hemi)

# 1. ROIs for the main analysis
for target_area in roi_params["target_areas"]:
    surf_roi_file = f"roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.shape.gii"
    overlap_out = os.path.join(roi_overlap_dir, f"roi-overlap_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.shape.gii")
    overlap_analysis(surf_roi_file, overlap_out, subjects)

# 2. group cluster ROIs
main_area = roi_params["main_area"]
for cluster_idx in roi_params["cluster_idcs"]:
    surf_roi_file = f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A{main_area}.shape.gii"
    overlap_out = os.path.join(roi_overlap_dir, f"roi-overlap_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A{main_area}.shape.gii")
    overlap_analysis(surf_roi_file, overlap_out, subjects)
