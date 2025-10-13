#!/usr/bin/env python3

"""
Generate the figure for the segmentation and registration results.
"""
import sys
import os

# 1st: generate images for each subject in fsleyes with ../process_seg-reg_vis_subject.sh
# for now assume it has been done and the images are in the right place

studyDataDir = sys.argv[1]
subjects = [f'sub-{i:02d}' for i in range(1, 22)]  # subjects are sub-01 to sub-21

figure_dir = f'{studyDataDir}/derivatives/figures/'
os.makedirs(figure_dir, exist_ok=True)

# 2nd: compose the figure
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# create a figure with one panel for each of the 21 subjects in a 3x7 grid
# define the figure, set size
fig, axs = plt.subplots(3, 7, figsize=(15, 7))

# load the images
for i, subject in enumerate(subjects):
    seg_reg_vis_dir = os.path.join(studyDataDir, 'derivatives', 'seg_reg_vis', subject)
    img = mpimg.imread(os.path.join(seg_reg_vis_dir,f'seg-reg-vis_{subject}_opaque.png'))
    axs[i//7, i%7].imshow(img)
    axs[i//7, i%7].axis('off')
    axs[i//7, i%7].set_title(f'Subject {i+1}')

plt.tight_layout()
plt.savefig(os.path.join(figure_dir,f'figure_seg-reg.png'),dpi=600)
plt.close()