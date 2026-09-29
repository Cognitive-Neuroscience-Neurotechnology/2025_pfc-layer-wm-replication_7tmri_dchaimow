#!/bin/bash
set -euo pipefail
studyDataDir=$1
subject=$2

freesurfer_dir=${studyDataDir}/derivatives/freesurfer/${subject}
preprocess_dir=${studyDataDir}/derivatives/preprocess/${subject}
register_dir=${studyDataDir}/derivatives/register/${subject}
roi_dir=${studyDataDir}/derivatives/roi/${subject}
ref_anat_dir=${studyDataDir}/derivatives/ref-anat/${subject}

seg_reg_vis_dir=${studyDataDir}/derivatives/seg_reg_vis/${subject}
mkdir -p ${seg_reg_vis_dir}

main_area=$(jq '.main_area' ${roi_dir}/roi_params.json)  # main ROI target area (08_sl_generate_rois.py)

export FSLOUTPUTTYPE=NIFTI

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT
cd ${tmp_dir}

# generate extended fs T1 in functional space (to show the anatomy beyond the functional slab)
3dZeropad -z 50 -prefix func_all_T1_ext.nii ${preprocess_dir}/func_all_T1.nii
mri_convert ${freesurfer_dir}/mri/T1.mgz fs_T1.nii
antsApplyTransforms --interpolation 'BSpline[5]' \
    -d 3 \
    -i fs_T1.nii \
    -r func_all_T1_ext.nii \
    -t ${register_dir}/fs_to_func_1Warp.nii.gz \
    -t ${register_dir}/fs_to_func_0GenericAffine.mat \
    -o fs_T1_in-func-ext.nii

# generate a roi_layers.nii file by combining an roi mask with depth information
roi_file=${roi_dir}/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A${main_area}.nii
depth_file=${ref_anat_dir}/vdfs_depths_equivol.nii
# superficial layer = depth_file>0.5
fslmaths ${depth_file} -nan -thr 0.5 -bin superficial.nii -odt int
# deep layer = depth_file<0.5
fslmaths ${depth_file} -nan -thr 0 -uthr 0.5 -bin deep.nii -odt int
# combine layers with roi (superficial = 1, deep = 2)
fslmaths deep.nii -mul 2 -add superficial.nii -mul ${roi_file} roi_layers.nii -odt int

# center the views on the center of gravity of the (binary) ROI
world_loc=$(fslstats ${roi_file} -c)


# fsleyes options shared by both renderings:
# coronal view (without cursor), zoomed in on the ROI, in functional space
scene_opts=(--scene ortho
    --displaySpace "${register_dir}/fs_t1_in-func.nii"
    --xcentre 0.15225 0.01828 --ycentre 0.32576 0.02225 --zcentre 0.31041 0.16074
    --xzoom 1537.3333331051592 --yzoom 1537.3333331051592 --zzoom 1537.3333331051592
    --layout horizontal --hidex --hidez --hideCursor
    --bgColour 0.0 0.0 0.0 --fgColour 1.0 1.0 1.0 --cursorColour 0.0 1.0 0.0
    --colourBarLocation top --colourBarLabelSide top-left --colourBarSize 100.0
    --labelSize 24 --performance 3 --movieSync)
# display options shared by all volume overlays
volume_opts=(--gamma 0.0 --cmapResolution 256 --interpolation none
    --numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70
    --numInnerSteps 10 --clipMode intersection --volume 0)
# extended fs T1 as background, and the (disabled) fs T1 within the slab
t1_overlays=(fs_T1_in-func-ext.nii --name "fs_T1_in-func-ext" --overlayType volume
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --cmap greyscale --negativeCmap greyscale
    --displayRange -23.236267231128675 199.8592941407981
    --clippingRange -23.236267231128675 202.09024975451737
    "${volume_opts[@]}"
    "${register_dir}/fs_t1_in-func.nii" --name "fs_t1_in-func" --disabled --overlayType volume
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --cmap greyscale --negativeCmap greyscale
    --displayRange -16.926658826500674 185.89678397541172
    --clippingRange -16.926658826500674 187.92501840343084
    "${volume_opts[@]}")
# VASO T1 (the functional slab)
vaso_t1_overlay=("${preprocess_dir}/func_all_T1.nii" --name "func_all_T1" --overlayType volume
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --cmap greyscale --negativeCmap greyscale
    --displayRange 0.0 255.0 --clippingRange 0.0 257.55
    "${volume_opts[@]}")
# layer ROI (superficial = 1, deep = 2, as in the manual layer ROIs) overlay options, without alpha (the image is given before them)
roi_layers_opts=(--name "roi_layers" --overlayType volume
    --brightness 37.5125 --contrast 74.97500000000001
    --cmap brain_colours_diverging_bwr --invert --negativeCmap greyscale
    --displayRange 0.999 2.0 --clippingRange 0.999 2.02
    "${volume_opts[@]}")
# pial (red) and white matter (blue) surface outlines
surface_overlays=("${register_dir}/L.pial.func.surf.gii" --name "L.pial.func" --overlayType mesh
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --lut random
    --cmap greyscale --negativeCmap greyscale --vertexDataIndex 0
    --vertexSet "${register_dir}/L.pial.func.surf.gii"
    --colour 1.0 0.0 0.0 --outline --outlineWidth 0.1 --refImage fs_T1_in-func-ext.nii
    --coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01
    --gamma 0.0 --cmapResolution 256
    "${register_dir}/L.white.func.surf.gii" --name "L.white.func" --overlayType mesh
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --lut random
    --cmap greyscale --negativeCmap greyscale --vertexDataIndex 0
    --vertexSet "${register_dir}/L.white.func.surf.gii"
    --colour 0.0 0.0 1.0 --outline --outlineWidth 0.5619999997694977 --refImage fs_T1_in-func-ext.nii
    --coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01
    --gamma 0.0 --cmapResolution 256)

# VASO slab and opaque layer ROI on the extended fs T1, with surface outlines
fsleyes render "${scene_opts[@]}" --worldLoc ${world_loc} \
    -of ${seg_reg_vis_dir}/seg-reg-vis_${subject}_opaque.png \
    "${t1_overlays[@]}" \
    "${vaso_t1_overlay[@]}" \
    roi_layers.nii --alpha 100 "${roi_layers_opts[@]}" \
    "${surface_overlays[@]}"

# semi-transparent layer ROI on the extended fs T1 (without VASO slab), with surface outlines
fsleyes render "${scene_opts[@]}" --worldLoc ${world_loc} \
    -of ${seg_reg_vis_dir}/seg-reg-vis_${subject}_noslab.png \
    "${t1_overlays[@]}" \
    roi_layers.nii --alpha 39.333333340318255 "${roi_layers_opts[@]}" \
    "${surface_overlays[@]}"
