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
from matplotlib import font_manager
import matplotlib

from matplotlib.path import Path
from matplotlib.patches import PathPatch
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable

study_data_dir = sys.argv[1]

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


def single_tsnr_plot(subject, ax):
    """
    Generate a single tSNR plot for a given subject that shows
    the tSNR map aveaged pver all runs with a superimposed ROI outline
    The displayed slice is the one going through the center of the ROI 
    (or alternatively the slice with the largest ROI area)
    The function returns the average tSNR value within the ROI
    """
    roi_dir = os.path.join(study_data_dir, 'derivatives', 'roi',subject)
    preprocess_dir = os.path.join(study_data_dir, 'derivatives', 'preprocess', subject)

    # load the roi
    roi = nib.load(
        os.path.join(roi_dir, 'roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A100.nii')).get_fdata()
    
    # calculate the slice with the largest ROI area
    roi_area = np.sum(roi, axis=(0,1))
    max_slice_idx = np.argmax(roi_area)
    
    # calculate the center of mass of the ROI
    roi_center = ndimage.measurements.center_of_mass(roi)
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
    # draw the contours on the image
    ax.imshow(tSNR_slice.T, cmap='hot',vmin=0,vmax=30)
    ax.plot(contours[0][:,0,1],contours[0][:,0,0],color=color,lw=.5,alpha=alpha)
    ax.plot([contours[0][-1,0,1],contours[0][0,0,1]],
            [contours[0][-1,0,0],contours[0][0,0,0]],color=color,lw=0.5,alpha=alpha)
    ax.axis('off')
    # set origin to lower left corner
    ax.invert_yaxis()
    return tSNR_roi_avg



    # # initialize figure
    # # 16.6 cm in inches is 6.54 inches
    # fig = plt.figure(figsize=(18/2.54,16/2.54), dpi=300)
    
    
    
    
    
# test
# generate a lyout of 3x7 subplots with one wide subplot in the 4th row
fig = plt.figure(figsize=(10, 5), layout='constrained')
gs = GridSpec(3, 8, figure=fig, width_ratios=[1,1,1,1,1,1,1,1], left=0, right=1, top=1, bottom=0,
              wspace=0.02, hspace=0) 
snr_values = []
for idx, subject_idx in enumerate(range(1, 22)):
    subject = f'sub-{subject_idx:02d}'
    ax = fig.add_subplot(gs[idx//7, idx%7])
    snr_values.append(single_tsnr_plot(subject, ax))
    #snr_values.append(np.random.normal()*3+16)
    ax.set_title(f'Subject {subject_idx}')
# plot into 4th row
print(snr_values)
#ax = fig.add_subplot(gs[0:3,7])
ax = fig.add_axes([0.90, 0.2, 0.08, 0.6])

#violins = sns.violinplot(data=snr_values,orient='v',inner='point',
#               ax=ax, color='red')
violins = ax.violinplot(snr_values, showextrema=False, 
                        showmeans=False, showmedians=True, widths=0.5)
ax.scatter([1]*len(snr_values),snr_values, color='black', s=2)

ax.set_ylim(0,30)
ax.set_xlim(-0.5,1.5)
ax.set_xticks([])
#ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)
# remove box around the plot
#ax.spines['top'].set_visible(False)
#ax.spines['right'].set_visible(False)
#ax.spines['left'].set_visible(False)
#ax.spines['bottom'].set_visible(False)




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
cb = matplotlib.colorbar.ColorbarBase(cax, cmap=matplotlib.cm.get_cmap(cmap),
                                norm=norm,
                                orientation='vertical')
ax.set_ylabel('tSNR')
ax.set_yticks([])
#ax.set_ylabel('')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)

# print median of tSNR values
print(f'Median tSNR value: {np.median(snr_values)}')


fig.savefig(os.path.join(figure_dir,
                        f'figure_snr.svg'), dpi=300)
fig.savefig(os.path.join(figure_dir,
                        f'figure_snr.png'), dpi=300)
plt.close()

