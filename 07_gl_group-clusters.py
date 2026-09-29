#!/usr/bin/env python3
"""
Group analysis of the trial averaging F-statistics on the fs_LR surface (left hemisphere):
averaging across subjects, smoothing and clustering, and selection of the clusters overlapping dlPFC
(used as alternative ROI constraints).
"""
import os
import sys
from fmri_analysis import layer_analysis as analysis
from fmri_analysis.library.group_fslr_analysis import group_fslr_analysis
from fmri_analysis.library.cluster_surface import cluster_surface
import utils

study_data_dir = sys.argv[1]
subjects = utils.subjects()

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

# overview of all clusters with their indices, for selecting them by hand (below)
atlas = os.path.join(study_data_dir, 'derivatives', 'resources',
                     'Q1-Q6_RelatedValidation210.L.CorticalAreas_dil_Final_Final_Areas_Group_Colors.164k_fs_LR.label.gii')
utils.write_cluster_overview(clusters, surf, atlas,
                             os.path.join(group_clusters_dir, 'L.164k_fs_LR.group.clusters_overview'))

# 4. Select the clusters that resemble multiple demand parcels (Assem et al. 2020) and lie approximately in
# dlPFC, labeled with the corresponding parcels. They are selected by the Glasser areas they cover (chosen
# by hand from the cluster overview), as the cluster numbering changes with small changes of the data.
cluster_areas = {"MD4": ["a9-46v", "9-46d"],
                 "MD3A": ["46", "p9-46v"],
                 "MD3B": ["p9-46v", "8C", "IFSp"],
                 "MD2": ["55b", "6v", "6r", "PEF"]}
selected_clusters = utils.select_clusters_by_atlas(clusters, atlas, cluster_areas)
print("selected clusters:", selected_clusters)
utils.write_params(os.path.join(group_clusters_dir, "selected_clusters.json"),
                   {"cluster_idcs": list(selected_clusters), "cluster_labels": selected_clusters})