#!/bin/bash
set -euo pipefail
studyDataDir=$1
subject=$2

export FSLOUTPUTTYPE=NIFTI


fs_dir=${studyDataDir}/derivatives/freesurfer/${subject}
preprocess_dir=${studyDataDir}/derivatives/preprocess/${subject}
register_dir=${studyDataDir}/derivatives/register/${subject}
roi_dir=${studyDataDir}/derivatives/roi/${subject}
trialavg_dir=${studyDataDir}/derivatives/trialavg/${subject}
export_dir=${studyDataDir}/derivatives/export_for_manual_roi/${subject}

main_area=$(jq '.main_area' ${roi_dir}/roi_params.json)  # main ROI target area (08_sl_generate_rois.py)


mkdir -p ${export_dir}
cd ${export_dir}

# fs T1w image
mri_convert ${fs_dir}/mri/T1.mgz $export_dir/${subject}_fs_T1w.nii

# automatic roi, ANTs transformed into fs T1w space
antsApplyTransforms -d 3 -i $roi_dir/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A${main_area}.nii \
    -r $export_dir/${subject}_fs_T1w.nii \
    -o $export_dir/${subject}_fs_T1_roi.nii \
    -t \[ $register_dir/fs_to_func_0GenericAffine.mat,1 \] \
    -t $register_dir/fs_to_func_1InverseWarp.nii.gz \
    -n NearestNeighbor
# fs in func
cp $register_dir/fs_t1_in-func.nii $export_dir/${subject}_fs_T1_in-func.nii
# vaso T1w image
cp $preprocess_dir/func_all_T1.nii $export_dir/${subject}_vaso_T1w.nii
# bold fstat map
cp $trialavg_dir/trialavg_bold_combined_fstat.nii $export_dir/${subject}_bold_fstat.nii
# automatic ROI
cp $roi_dir/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A${main_area}.nii $export_dir/${subject}_roi.nii
# create empty manual layer ROI (to be drawn and saved as derivatives/roi/<subject>/roi_layers_manual.nii,
# from where export_manual_layer_rois_to_bids.py exports it to derivatives/manual-layer-rois for 13)
fslmaths $export_dir/${subject}_vaso_T1w.nii -mul 0 $export_dir/${subject}_roi_layers_manual.nii