#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
from fmri_analysis import layer_analysis as analysis
import numpy as np
import glob
from joblib import Parallel, delayed
import nibabel as nib

study_data_dir = sys.argv[1]
subjects = [f'sub-{i:02d}' for i in range(1, 22)]  # subjects are sub-01 to sub-21

# set MAX_CPUS based on OMP_NUM_THREADS, set to 1 if not set
try:
    MAX_CPUS = int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    MAX_CPUS = 1

ciftify_group_dir = os.path.join(study_data_dir, 'derivatives', 'ciftify')
register_group_dir = os.path.join(study_data_dir, 'derivatives', 'register')
roi_group_dir = os.path.join(study_data_dir, 'derivatives', 'roi')

roi_overlap_dir = os.path.join(study_data_dir, 'derivatives', 'roi_overlap')
os.makedirs(roi_overlap_dir, exist_ok=True)

def transform_roi_to_fslr(roi_native_surf, ciftify_dir, surf_dir, 
                          hemi='L',roi_fslr_surf_out=None):
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        if roi_fslr_surf_out is None:
            roi_fslr_surf_out = os.path.join(tmpdirname, "roi_fslr_surf.shape.gii")
        
        # find names (subject) of native and fs_LR spheres
        native_sphere = glob.glob(
            os.path.join(ciftify_dir,"MNINonLinear","Native",
                f"*.{hemi}.sphere.MSMSulc.native.surf.gii"))[0]
        fs_LR_sphere = glob.glob(
            os.path.join(ciftify_dir, "MNINonLinear", 
                         f"*.{hemi}.sphere.164k_fs_LR.surf.gii"))[0]
        
        # find name of fs_LR midthickness for area correction
        fs_LR_mid_surf = glob.glob(
            os.path.join(ciftify_dir, "MNINonLinear", 
                         f"*.{hemi}.midthickness.164k_fs_LR.surf.gii"))[0]
        
        # create native mid surf for area correction
        white_surf = os.path.join(surf_dir,f"{hemi}.white.func.surf.gii")
        pial_surf = os.path.join(surf_dir,f"{hemi}.pial.func.surf.gii")
        native_mid_surf = os.path.join(tmpdirname, "mid.surf.gii")
        subprocess.run(["wb_command",
                        "-surface-average", native_mid_surf,
                        "-surf", pial_surf,
                        "-surf", white_surf])

        # resample roi to fs_LR space
        subprocess.run(["wb_command",
                        "-metric-resample", roi_native_surf,
                        native_sphere, fs_LR_sphere,
                        "ADAP_BARY_AREA",
                        roi_fslr_surf_out,
                        "-area-surfs", native_mid_surf, fs_LR_mid_surf])

        # threshold at 0.5 and binarize
        subprocess.run(["wb_command",
                        "-metric-math", f'roi_fslr_surf > 0.5',
                        roi_fslr_surf_out,
                        "-var", f'roi_fslr_surf', roi_fslr_surf_out])
        # load the resampled roi and return the data
        roi_fslr_surf_data = nib.load(roi_fslr_surf_out).darrays[0].data
    return roi_fslr_surf_data
        
def overlap_analysis(roi_surf_fname, overlap_out, subjects):
    results = Parallel(n_jobs=min(len(subjects), MAX_CPUS))(
        delayed(transform_roi_to_fslr)(
            os.path.join(roi_group_dir, subject, roi_surf_fname),
            os.path.join(ciftify_group_dir, subject),
            os.path.join(register_group_dir, subject),
            'L') for subject in subjects)

    # Assign results to group arrays
    n_subjects = len(subjects)
    group_roi_data = np.zeros((163842, n_subjects))

    for subject_index, roi_data in enumerate(results):
        group_roi_data[:, subject_index] = roi_data
    
    n = np.sum(group_roi_data > 0, axis=1)  # number of subjects with coverage at each vertex

    # write the results to metric file
    analysis.write_metric_gifti(overlap_out, n, 'L')
    
# 1. ROIs for the main analysis
target_areas = np.arange(20, 401, 20)  # from 20 to 400 in steps of 20
for target_area in target_areas:
    surf_roi_file = f"roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.shape.gii"
    overlap_out = os.path.join(roi_overlap_dir, f"roi-overlap_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.shape.gii")
    overlap_analysis(surf_roi_file, overlap_out, subjects)

# 2. group cluster ROIs
for cluster_idx in [4,5,6,9,10]:  # manually set to these clusters that overlap dlPFC
    surf_roi_file = f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A100.shape.gii"
    overlap_out = os.path.join(roi_overlap_dir, f"roi-overlap_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A100.shape.gii")
    overlap_analysis(surf_roi_file, overlap_out, subjects)