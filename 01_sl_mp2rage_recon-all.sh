#!/bin/bash
set -euo pipefail
studyDataDir=$1
subject=$2

# source of the brain mask for FreeSurfer:
# - published: the brain masks distributed with the data set (BIDS derivative dataset derivatives/brainmasks,
#   exported with export_brainmasks_to_bids.py), which makes this step reproducible
# - cat12: compute the brain mask from the CAT12 segmentation (not deterministic: its multithreaded denoising
#   can change single voxels of the mask between runs, see README)
brainmask_source=published

brainmask_args=()
if [ "$brainmask_source" = published ]; then
    brainmask=${studyDataDir}/derivatives/brainmasks/${subject}/anat/${subject}_desc-brain_mask.nii.gz
    if [ ! -f "$brainmask" ]; then
        echo "brain mask not found: $brainmask (set brainmask_source=cat12 to compute it)" >&2
        exit 1
    fi
    brainmask_args=(--brainmask "$brainmask")
fi

mp2rage_recon-all.py ${studyDataDir}/${subject}/anat/${subject}_inv-2_MP2RAGE.nii \
    ${studyDataDir}/${subject}/anat/${subject}_UNIT1.nii \
    --fs_dir ${studyDataDir}/derivatives/freesurfer/${subject} \
    --ncpu ${OMP_NUM_THREADS:-1} \
    "${brainmask_args[@]}"
