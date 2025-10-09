#!/usr/bin/env python3

"""
Generate figure visualizing the group clusters for alternative ROI selection
"""

import sys
import os
from matplotlib import pyplot as plt
from matplotlib import font_manager
from fmri_analysis import surface_plotting as sp
from matplotlib.gridspec import GridSpec


study_data_dir = sys.argv[1]


group_clusters_dir = os.path.join(study_data_dir, 'derivatives', 'group_clusters')
figure_dir = os.path.join(study_data_dir,'derivatives','figures')

os.makedirs(figure_dir, exist_ok=True)


# plot parameters and initalization
plt.style.use("stylesheet.mplstyle")

# set font
font_files = font_manager.findSystemFonts(
    fontpaths=[os.path.join(os.path.dirname(__file__), 'fonts')])
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)
if 'Helvetica' in [f.name for f in font_manager.fontManager.ttflist]:
    plt.rcParams['font.family'] = 'Helvetica'
plt.rcParams.update({'font.size': 7})


# load data
group_mean_smoothed_fstat = sp.load_surf_data(
     os.path.join(group_clusters_dir,'L.164k_fs_LR.group.mean.smoothed.func.gii'))
surf = sp.load_surface_gifti(
    os.path.join(study_data_dir, 'derivatives','ciftify','zz_templates',
                 'colin.cerebral.L.flat.164k_fs_LR.surf.gii'))
clusters = sp.load_surf_data(
    os.path.join(group_clusters_dir, 'L.164k_fs_LR.group.clusters.shape.gii'))
atlas_fname = os.path.join(study_data_dir, 'derivatives','resources', 'Q1-Q6_RelatedValidation210.L.CorticalAreas_dil_Final_Final_Areas_Group_Colors.164k_fs_LR.label.gii')

# generate 1 x 3 subplot figure
fig = plt.figure(figsize=(18/2.54,5.2/2.54))
gs = GridSpec(1, 3, figure=fig, left=0, right=1, top=1, bottom=0, 
              wspace=0.1)
axs = [fig.add_subplot(gs[0, i]) for i in range(3)]


# 1. plot group mean smoothed fstat
sp.plot_surf_data_left_hemi(group_mean_smoothed_fstat, surf, atlas_fname, 
                            vmin=1, vmax=2.5, ax=axs[0])
axs[0].set_title('Group F-stat BOLD')
fig.text(0, 0.95, 'A', size=10, weight='bold')

# add an arrow pointing to p9-46v
arrowprops = dict(facecolor='black', arrowstyle='-|>', lw=0.5)
axs[0].annotate('p9-46v', xy=(-65, 25), xytext=(-140, -45),
                arrowprops=arrowprops, fontsize=6, color='black',
                ha='center', va='center')


# 2. plot group clusters
sp.plot_surf_clusters_left_hemi(clusters, surf, atlas_fname, ax=axs[1],
                                label_dict = {6:'MD4',5:'MD3A',4:'MD3B',10:'MD2'},
                                label_fontsize=3)
axs[1].set_title('Group clusters')
fig.text(1/3, 0.95, 'B', size=10, weight='bold')

# 3. empty plot with only a title to insert MD map from Assem et al. 2020 later
axs[2].set_xlim(axs[0].get_xlim())  # Match dimensions to first surface plot
axs[2].set_ylim(axs[0].get_ylim())
axs[2].set_aspect('equal')
axs[2].axis('off')
axs[2].set_title('MD regions (Assem et al. 2020)')
fig.text(2/3, 0.95, 'C', size=10, weight='bold')


# don't generate svg because it would contain every single vertex as a separate shape and be huge
#fig.savefig(os.path.join(figure_dir,f'figure_group-clusters.svg'), dpi=300)
fig.savefig(os.path.join(figure_dir,f'figure_group-clusters.png'), dpi=600)
plt.close()

