#!/bin/bash
studyDataDir=$1
subject=$2

ciftifyDir=${studyDataDir}/derivatives/ciftify
freesurferDir=${studyDataDir}/derivatives/freesurfer
resourcesDir=${studyDataDir}/derivatives/resources


fmri-analysis/library/ciftify_recon_all_highres.sh ${ciftifyDir} ${freesurferDir} ${subject} \
    ${resourcesDir}/MNI152_T1_0.5mm