#!/bin/bash
studyDataDir=$1
subject=$2

fmri-analysis/library/mp2rage_recon-all.py ${studyDataDir}/${subject}/anat/${subject}_inv-2_MP2RAGE.nii \
                      ${studyDataDir}/${subject}/anat/${subject}_UNIT1.nii \
                      --fs_dir ${studyDataDir}/derivatives/freesurfer/${subject} \
                      --ncpu ${OMP_NUM_THREADS:-1} 