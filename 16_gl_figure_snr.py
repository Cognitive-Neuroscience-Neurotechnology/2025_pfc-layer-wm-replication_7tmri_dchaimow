#!/usr/bin/env python3

"""
Generate figure showing SNR
"""

import sys
import os
import numpy as np
import nibabel as nib
from scipy import ndimage
import cv2
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib

from matplotlib.path import Path
from matplotlib.patches import PathPatch
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
import utils

study_data_dir = sys.argv[1]
subjects = utils.subjects()

# main ROI target area from 08_sl_generate_rois.py
main_area = utils.read_subject_params(study_data_dir, 'roi', 'roi_params.json', subjects)['main_area']

figure_dir = os.path.join(study_data_dir,'derivatives','figures')
result_dir = os.path.join(study_data_dir,'derivatives','results')

os.makedirs(figure_dir, exist_ok=True)
os.makedirs(result_dir, exist_ok=True)

# plot parameters and initalization
utils.setup_figure_style()


def single_tsnr_plot(subject, ax):
    """
    Generate a single tSNR plot for a given subject that shows
    the tSNR map averaged over all runs with a superimposed ROI outline
    The displayed slice is the one going through the center of the ROI 
    The function returns the average tSNR value within the ROI
    """
    roi_dir = os.path.join(study_data_dir, 'derivatives', 'roi',subject)
    preprocess_dir = os.path.join(study_data_dir, 'derivatives', 'preprocess', subject)

    # load the roi
    roi = nib.load(
        os.path.join(roi_dir, f'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A{main_area}.nii')).get_fdata()

    # calculate the center of mass of the ROI
    roi_center = ndimage.center_of_mass(roi)
    com_slice_idx = int(roi_center[2])  

    # load tSNR maps for all runs
    tSNRs = []
    for run_fname in ['func1_alpharem', 'func2_alpharem', 'func3_gonogo', 'func4_gonogo']:
        tSNRs.append(nib.load(
            os.path.join(preprocess_dir, f'{run_fname}_vaso_tsnr.nii')).get_fdata())
       
    tSNR_avg = np.mean(tSNRs, axis=0)
    # calculate the average tSNR value within the ROI
    roi_binary = (roi > 0).astype(np.uint8)
    tSNR_roi = tSNR_avg * roi_binary
    tSNR_roi_avg = np.nansum(tSNR_roi) / np.nansum(roi_binary)
    print(f'Average tSNR inside ROI in {subject}: {tSNR_roi_avg}')
    # plot the tSNR map
    roi_slice = roi_binary[:,:,com_slice_idx].copy()
    tSNR_slice = tSNR_avg[:,:,com_slice_idx].copy()
    upsample_factor = 10
    color = (0,0,1)
    alpha=1
    roi_slice_up = cv2.resize(roi_slice, (roi_slice.shape[1]*upsample_factor,
                              roi_slice.shape[0]*upsample_factor), 
                        interpolation=cv2.INTER_NEAREST)
    contours, _ = cv2.findContours(roi_slice_up, mode=cv2.RETR_EXTERNAL, 
                                                 method=cv2.CHAIN_APPROX_SIMPLE)
    # downsample contour coordinates
    contours = [((contour+0.5)/upsample_factor)-0.5 for contour in contours]
    # draw the (closed) contours of all ROI parts in the slice on the image
    ax.imshow(tSNR_slice.T, cmap='hot',vmin=0,vmax=30)
    for contour in contours:
        ax.plot(contour[:,0,1],contour[:,0,0],color=color,lw=.5,alpha=alpha)
        ax.plot([contour[-1,0,1],contour[0,0,1]],
                [contour[-1,0,0],contour[0,0,0]],color=color,lw=0.5,alpha=alpha)
    ax.axis('off')
    # set origin to lower left corner
    ax.invert_yaxis()
    return tSNR_roi_avg


# generate a layout of 3x7 subplots with the tSNR maps of all subjects
fig = plt.figure(figsize=(10, 5), layout='constrained')
gs = GridSpec(3, 8, figure=fig, width_ratios=[1,1,1,1,1,1,1,1], left=0, right=1, top=1, bottom=0,
              wspace=0.02, hspace=0) 
snr_values = []
for idx, subject in enumerate(subjects):
    ax = fig.add_subplot(gs[idx//7, idx%7])
    snr_values.append(single_tsnr_plot(subject, ax))
    ax.set_title(f'Subject {int(subject[4:])}')
print(snr_values)

# violin plot of the average tSNR values within the ROIs of all subjects, next to the maps
ax = fig.add_axes([0.90, 0.2, 0.08, 0.6])
violins = ax.violinplot(snr_values, showextrema=False, 
                        showmeans=False, showmedians=True, widths=0.5)
ax.scatter([1]*len(snr_values),snr_values, color='black', s=2)

ax.set_ylim(0,30)
ax.set_xlim(-0.5,1.5)
ax.set_xticks([])

ymin, ymax = ax.get_ylim()
xmin, xmax = ax.get_xlim()

# create a numpy image to use as a gradient
Nx,Ny=1,1000
imgArr = np.tile(np.linspace(0,1,Ny), (Nx,1)).T
cmap = 'hot'

for violin in violins['bodies']:
    violin.set_alpha(0)
    violin.set_edgecolor('black')
    path = Path(violin.get_paths()[0].vertices)
    patch = PathPatch(path, facecolor='none', edgecolor='none')
    ax.add_patch(patch)
    img = ax.imshow(imgArr, origin="lower", extent=[xmin,xmax,ymin,ymax], aspect="auto",
                    cmap=cmap,
                    clip_path=patch)

violins['cmedians'].set_color('gray')
   

# colorbar
ax_divider = make_axes_locatable(ax)
cax = ax_divider.append_axes("left", size="5%", pad="2%")
norm = matplotlib.colors.Normalize(vmin=ymin, vmax=ymax)
cb = matplotlib.colorbar.ColorbarBase(cax, cmap=matplotlib.colormaps[cmap],
                                norm=norm,
                                orientation='vertical')
ax.set_ylabel('tSNR')
ax.set_yticks([])
# remove box around the plot
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)

# print median of tSNR values
print(f'Median tSNR value: {np.median(snr_values)}')

# write tSNR values to the results
with open(os.path.join(result_dir, 'tSNR.txt'), 'w') as f:
    print(f'Average VASO tSNR inside the main ROI (A{main_area}), tSNR maps averaged over runs:', file=f)
    for subject, snr_value in zip(subjects, snr_values):
        print(f'{subject}: {snr_value}', file=f)
    print(f'Median tSNR value: {np.median(snr_values)}', file=f)


utils.save_figure(fig, figure_dir, 'figure_snr')
plt.close()

