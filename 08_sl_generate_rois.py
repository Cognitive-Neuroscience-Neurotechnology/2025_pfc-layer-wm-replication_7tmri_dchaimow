#!/usr/bin/env python3
import sys
import os
from tempfile import TemporaryDirectory

from fmri_analysis import layer_analysis as analysis
from fmri_analysis.generate_roi import find_roi
import numpy as np
from joblib import Parallel, delayed

""" Here we generate two types of ROIs:
1. ROIs for the main analysis, based on the group F-statistics and the Glasser atlas.
   We generate one ROI for each target area, from 20 to 400 in steps of 20.
2. ROIs that are based on the group analysis clusters, one ROI for each cluster.
"""

studyDataDir = sys.argv[1]
subject = sys.argv[2]

# set MAX_CPUS based on OMP_NUM_THREADS, set to 1 if not set
try:
    MAX_CPUS = int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    MAX_CPUS = 1

# set directories
register_dir = os.path.join(studyDataDir, "derivatives", "register", subject)
ref_anat_dir = os.path.join(studyDataDir, "derivatives", "ref-anat", subject)
trialavg_dir = os.path.join(studyDataDir, "derivatives", "trialavg", subject)
group_clusters_dir = os.path.join(studyDataDir, "derivatives", "group_clusters")
ciftify_dir = os.path.join(studyDataDir, "derivatives", "ciftify", subject)

roi_dir = os.path.join(studyDataDir, "derivatives", "roi", subject)
os.makedirs(roi_dir, exist_ok=True)

# we only consider the left hemisphere
hemi = "L"

# activation requirement from trial averaging F-statistics from both run types averaged
stat_file = os.path.join(trialavg_dir, "trialavg_bold_combined_fstat.nii")

# set surface files
white_surf = os.path.join(register_dir, f'{hemi}.white.func.surf.gii')
pial_surf = os.path.join(register_dir, f'{hemi}.pial.func.surf.gii')

# 1. ROIs for the main analysis
with TemporaryDirectory() as tmpdir:
    # atlas requirements: everything in dlPFC belonging to a single connected cluster overlapping p9-46v
    atlas_native_surf = os.path.join(ref_anat_dir, f"{subject}.glasser.{hemi}.native.label.gii")
    anat_region = os.path.join(tmpdir, "anat_region.shape.gii")
    anat_require_region = os.path.join(tmpdir, "anat_require_region.shape.gii")
    analysis.generate_atlas_region_hcp(atlas_native_surf,anat_region,(['L_p9-46v', 'L_46', 'L_8C', 'L_IFSp', 'L_IFSa']))
    analysis.generate_atlas_region_hcp(atlas_native_surf,anat_require_region,'L_p9-46v')

    target_areas = np.arange(20, 401, 20)  # from 20 to 400 in steps of 20

    # Parallelize ROI generation for different target areas
    def generate_roi_for_area(target_area):
        roi_file_name = f"roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.nii"
        surf_roi_file_name = f"roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{target_area}.shape.gii"
        # for area 100 we also save the smoothed stat and clusters for visualization
        if target_area == 100:
            surf_smoothed_stat_file_name = os.path.join(roi_dir, f"trialavg_bold_combined_fstat_smoothed.func.gii") 
            surf_clusters_file_name = os.path.join(roi_dir, f"clusters_trialavg_bold_combined_fstat_A{target_area}.shape.gii")
        else:
            surf_smoothed_stat_file_name = None
            surf_clusters_file_name = None

        find_roi(
            stat_file=stat_file,
            anat_region=anat_region,
            out_file=os.path.join(roi_dir, roi_file_name),
            target_type="area",
            target=target_area,
            white_surf=white_surf,
            pial_surf=pial_surf,
            hemi=hemi,
            anat_require_region=anat_require_region,
            cluster_roi=True,
            fwhm=3,
            cwd=tmpdir,
            keep_tmp=True,
            surf_roi_out=os.path.join(roi_dir,surf_roi_file_name),
            surf_smoothed_stat_out=surf_smoothed_stat_file_name,
            surf_clusters_out=surf_clusters_file_name)
        return roi_file_name
    Parallel(n_jobs=min(len(target_areas), MAX_CPUS))(delayed(generate_roi_for_area)(target_area) 
                                                        for target_area in target_areas)

# 2. ROIs based on group analysis clusters
with TemporaryDirectory() as tmpdir:
    # to use each cluster as a separate anatomical ROI constraint we first bring the group clusters into native subject space
    clusters_fs_LR = os.path.join(group_clusters_dir, "L.164k_fs_LR.group.clusters.shape.gii")
    clusters_native = os.path.join(tmpdir, f"{subject}.clusters.{hemi}.native.label.gii")
    analysis.fs_LR_labels_to_native_surf(clusters_fs_LR, ciftify_dir, pial_surf, white_surf, hemi, clusters_native)

    # get list of all integer non-zero cluster indeces in the cluster file
    #cluster_idcs = np.unique(nib.load(clusters_native).darrays[0].data)
    #cluster_idcs = cluster_idcs[cluster_idcs != 0]
    cluster_idcs = [4,5,6,9,10]  # manually set to these clusters that overlap dlPFC
    target_area = 100

    # Parallelize ROI generation for different clusters
    def generate_roi_for_cluster(cluster_idx):
        # define anat_region and anat_require_region
        anat_region = os.path.join(tmpdir, f"cluster_{cluster_idx}.shape.gii")
        analysis.generate_atlas_region_hcp(clusters_native, anat_region, cluster_idx)
        roi_file_name = f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A{target_area}.nii"
        surf_roi_file_name = f"roi_trialavg_bold_combined_fstat_group_cluster_{cluster_idx}_A{target_area}.shape.gii"
        find_roi(
            stat_file=stat_file,
            anat_region=anat_region,
            out_file=os.path.join(roi_dir, roi_file_name),
            target_type="area",
            target=target_area,
            white_surf=white_surf,
            pial_surf=pial_surf,
            hemi=hemi,
            anat_require_region=None,
            cluster_roi=True,
            fwhm=3,
            cwd=tmpdir,
            surf_roi_out=os.path.join(roi_dir,surf_roi_file_name))
        return roi_file_name
    Parallel(n_jobs=min(len(cluster_idcs), MAX_CPUS))(delayed(generate_roi_for_cluster)(cluster_idx) 
                                                      for cluster_idx in cluster_idcs)