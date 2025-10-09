#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../fmri-analysis/library"))
from fmri_analysis import layer_analysis as analysis
from fmri_analysis.group_fslr_analysis import group_fslr_analysis
from fmri_analysis.cluster_surface import cluster_surface

study_data_dir = sys.argv[1]
subjects = [f"sub-{i:02d}" for i in range(1, 22)] #TODO: should we have list of subjects as a parameter?

trialavg_dir = os.path.join(study_data_dir, 'derivatives', 'trialavg')
ciftify_dir = os.path.join(study_data_dir, 'derivatives', 'ciftify')
register_dir = os.path.join(study_data_dir, 'derivatives', 'register')

# 1. Group averaging in fslr space.
group_clusters_dir = os.path.join(study_data_dir, 'derivatives', 'group_clusters')
os.makedirs(group_clusters_dir, exist_ok=True)

group_fslr_analysis(firstlevel_analysis_dir=trialavg_dir,
                    ciftify_dir=ciftify_dir,
                    surf_dir=register_dir,
                    firstlevel_subpath='trialavg_bold_combined_fstat.nii',
                    subjects=subjects,
                    depth_ranges=None,
                    layer_contrasts=None,
                    group_contrasts='mean',
                    group_analysis_dir=group_clusters_dir,
                    smooth_sigma=None,
                    nan_as_zero=False)

# 2. Smooth the group F-statistics.
group_fstat_metric = os.path.join(group_clusters_dir,'L.164k_fs_LR.group.mean.func.gii')
smooth_fstat_metric = os.path.join(group_clusters_dir,'L.164k_fs_LR.group.mean.smoothed.func.gii')
surf = os.path.join(ciftify_dir,'zz_templates','colin.cerebral.L.flat.164k_fs_LR.surf.gii')
analysis.smooth_surfmetric_hcp(group_fstat_metric, smooth_fstat_metric, surf, sigma = 3)

# 3. Cluster the smoothed group F-statistics
clusters = os.path.join(group_clusters_dir,'L.164k_fs_LR.group.clusters.shape.gii')
cluster_surface(smooth_fstat_metric, surf, area=None, min_cluster_size=100, min_abs_value=1,negative=False,output=clusters)