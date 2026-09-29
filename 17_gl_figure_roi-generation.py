#!/usr/bin/env python3

"""
Generate figure visualizing the ROI generation procedure
"""

import sys
import os
import numpy as np
import matplotlib
import matplotlib.cm as cm
import matplotlib.image as mpimg
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import ConnectionPatch
import utils


study_data_dir = sys.argv[1]

# set exemplary subject to use for visualization
subject = 'sub-01'

figure_dir = os.path.join(study_data_dir,'derivatives','figures')
roi_generation_vis_dir = os.path.join(study_data_dir,'derivatives','roi-generation_vis',subject)

os.makedirs(figure_dir, exist_ok=True)


# plot parameters and initalization
utils.setup_figure_style()


def remove_borders(img):
    """Remove black and white borders from RGBA image."""
    # Convert to RGB if RGBA (ignore alpha channel for border detection)
    rgb = img[:, :, :3] if img.shape[2] == 4 else img
    
    # Find non-black AND non-white pixels
    black_threshold = 0.05  # Anything below this is considered black
    white_threshold = 0.95  # Anything above this is considered white
    
    # Pixels that are neither black nor white (content pixels)
    not_black = np.any(rgb > black_threshold, axis=2)
    not_white = np.any(rgb < white_threshold, axis=2)
    content_pixels = not_black & not_white
    
    # Find the bounding box of content pixels
    rows = np.any(content_pixels, axis=1)
    cols = np.any(content_pixels, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return img  # Return original if no content found
    
    row_min, row_max = np.where(rows)[0][[0, -1]]
    col_min, col_max = np.where(cols)[0][[0, -1]]
    
    # Crop the image
    return img[row_min:row_max+1, col_min:col_max+1]


# create a figure with a 2 x 4 grid layout
fig = plt.figure(figsize=(18/2.54, 9/2.54))
gs = GridSpec(2, 4, figure=fig, 
              width_ratios=[0.7, 1, 1, 0.7],  # Columns 0 and 3 are 70% the width
              wspace=0.3)  # Small spacing between columns

# Create subplots using GridSpec
axs = np.empty((2, 4), dtype=object)
for i in range(2):
    for j in range(4):
        axs[i, j] = fig.add_subplot(gs[i, j])



# place all three volume images
img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'combined-fstat-vol-vis_{subject}.png'))
axs[0,0].imshow(img)
axs[0,0].axis('off')
axs[0,0].set_title('BOLD activation (F-stat)', fontsize=7)
axs[0,0].text(0.05, 0.95, 'R', transform=axs[0,0].transAxes, 
              fontsize=7, color='white', 
              ha='left', va='top')
axs[0,0].text(0.95, 0.95, 'L', transform=axs[0,0].transAxes, 
              fontsize=7, color='white', 
              ha='right', va='top')

# add colorbar to the same axes
# match the fsleyes 'red-yellow' colormap used to render the F-stat image
cmap = matplotlib.colors.LinearSegmentedColormap.from_list('red-yellow', ['red', 'yellow'])
norm = matplotlib.colors.Normalize(vmin=3, vmax=10)
sm = cm.ScalarMappable(norm=norm, cmap=cmap)
sm.set_array([])  # Empty array

# create colorbar axis manually below the image
pos = axs[0,0].get_position()
cax = fig.add_axes([pos.x0 - 0.11, pos.y0 - 0.02, pos.width, 0.02])

cb1 = fig.colorbar(sm, cax=cax, orientation='horizontal')
cb1.set_label('F-value', fontsize=7)
cb1.ax.tick_params(labelsize=7)
cb1.set_ticks([3, 10])

img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'cortical-depths-vis_{subject}.png'))
axs[0,3].imshow(img)
axs[0,3].axis('off')
axs[0,3].set_title('Cortical depths', fontsize=7)
axs[0,3].text(0.05, 0.95, 'R', transform=axs[0,3].transAxes,
              fontsize=7, color='white', 
              ha='left', va='top')
axs[0,3].text(0.95, 0.95, 'L', transform=axs[0,3].transAxes,
              fontsize=7, color='white',
              ha='right', va='top')


img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'layer-roi-vol-vis_{subject}.png'))
axs[1,3].imshow(img)
axs[1,3].axis('off')
# make title appear below the image
axs[1,3].text(0.5, -0.06, 'Final ROI', transform=axs[1,3].transAxes,
              ha='center', va='top', fontsize=7)
axs[1,3].text(0.05, 0.95, 'R', transform=axs[1,3].transAxes, 
              fontsize=7, color='white', 
              ha='left', va='top')
axs[1,3].text(0.95, 0.95, 'L', transform=axs[1,3].transAxes, 
              fontsize=7, color='white', 
              ha='right', va='top')



img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'fstat_on_surf_{subject}.png'))
img_cropped = remove_borders(img)
axs[0,1].imshow(img_cropped)
axs[0,1].axis('off')

img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'clusters_on_surf_{subject}.png'))
img_cropped = remove_borders(img)
axs[0,2].imshow(img_cropped)
axs[0,2].axis('off')

img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'glasser_annotated_on_fsLR_surf_{subject}.png'))
img_cropped = remove_borders(img)
axs[1,1].imshow(img_cropped)
axs[1,1].axis('off')
pos = axs[1,1].get_position()
# place text underneath the image
fig.text(pos.x0 - 0.03, pos.y0 - 0.1, 'HCP MMP 1.0 Atlas\nGlasser et al. (2016)', ha='left', va='top', fontsize=7)


img = mpimg.imread(os.path.join(roi_generation_vis_dir,f'roi_on_surf_{subject}.png'))
img_cropped = remove_borders(img)
axs[1,2].imshow(img_cropped)
axs[1,2].axis('off')
pos = axs[1,2].get_position()
# place text underneath the image
fig.text(pos.x0 , pos.y0 - 0.1, 'require: cluster in p9-46v\n(allow to extend into surround)', ha='left', va='top', fontsize=7)



axs[1,0].axis('off')



# Add arrows showing the workflow
arrows = [
    # Top row: BOLD → F-stat surface → Clusters
    (axs[0,0], axs[0,1], (1, 0.5), (0, 0.5)),
    (axs[0,1], axs[0,2], (1, 0.5), (0, 0.5)),
    
    # Down to bottom row: Clusters → Final ROI
    (axs[0,2], axs[1,2], (0.5, 0), (0.5, 1)),
    (axs[0,3], axs[1,3], (0.5, 0), (0.5, 1)),
    
    
    # Bottom row: Atlas → ROI → Final volume
    (axs[1,1], axs[1,2], (1, 0.5), (0, 0.5)),
    (axs[1,2], axs[1,3], (1, 0.5), (0, 0.5)),
]

for ax1, ax2, start_pos, end_pos in arrows:
    arrow = ConnectionPatch(
        xyA=start_pos, coordsA='axes fraction', axesA=ax1,
        xyB=end_pos, coordsB='axes fraction', axesB=ax2,
        arrowstyle='-|>', shrinkA=5, shrinkB=5,
        mutation_scale=15, fc="black", linewidth=0.5
    )
    fig.add_artist(arrow)

# Add text on top of the arrow from axs[0,1] to axs[0,2]
pos1 = axs[0,1].get_position()
pos2 = axs[0,2].get_position()
# Calculate midpoint between the two subplots
mid_x = (pos1.x0 + pos1.width + pos2.x0) / 2
mid_y = pos1.y0 + pos1.height / 2

fig.text(mid_x - 0.015, mid_y + 0.1, 'cluster', ha='center', va='bottom',
         fontsize=7)



# save the figure
utils.save_figure(fig, figure_dir, 'figure_roi-generation')
plt.close()






