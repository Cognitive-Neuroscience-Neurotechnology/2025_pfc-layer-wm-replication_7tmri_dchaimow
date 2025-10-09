#!/bin/bash
studyDataDir=$1
subject=$2

freesurfer_dir=${studyDataDir}/derivatives/freesurfer/${subject}
preprocess_dir=${studyDataDir}/derivatives/preprocess/${subject}
register_dir=${studyDataDir}/derivatives/register/${subject}
roi_dir=${studyDataDir}/derivatives/roi/${subject}
ref_anat_dir=${studyDataDir}/derivatives/ref-anat/${subject}

seg_reg_vis_dir=${studyDataDir}/derivatives/seg_reg_vis/${subject}
mkdir -p ${seg_reg_vis_dir}

export FSLOUTPUTTYPE=NIFTI

old_tmp_dir=${seg_reg_vis_dir}/tmp
rm -rf ${old_tmp_dir}
tmp_dir=$(mktemp -d)
mkdir -p ${tmp_dir}
cd ${tmp_dir}
# generate extended fs T1 in functional space
# cd ${studyDataDir}/derivatives/preprocess_vaso/${subject}
3dZeropad -z 50 -prefix func_all_T1_ext.nii ${preprocess_dir}/func_all_T1.nii

# # transform fs T1 to extended fs T1
# cd ${studyDataDir}/derivatives/ref_anat/${subject}
mri_convert ${freesurfer_dir}/mri/T1.mgz fs_T1.nii
antsApplyTransforms --interpolation 'BSpline[5]' \
    -d 3 \
    -i fs_T1.nii \
    -r func_all_T1_ext.nii \
    -t ${register_dir}/fs_to_func_1Warp.nii.gz \
    -t ${register_dir}/fs_to_func_0GenericAffine.mat \
    -o fs_T1_in-func-ext.nii

# generate a roi_layers.nii file by combining an roi mask with depth information
roi_file=${roi_dir}/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A100.nii
depth_file=${ref_anat_dir}/vdfs_depths_equivol.nii
# superficial layer = depth_file>0.5
fslmaths ${depth_file} -nan -thr 0.5 -bin superficial.nii -odt int
# deep layer = depth_file<0.5
fslmaths ${depth_file} -nan -thr 0 -uthr 0.5 -bin deep.nii -odt int
# combine layers with roi
fslmaths superficial.nii -mul 2 -add deep.nii -mul ${roi_file} roi_layers.nii -odt int


# calculate which coronal slice to use for visualization by reslicing and counting number of mask voxels in each slice
vx=$(find_max-roi_slice.sh roi_layers.nii x)
vy=$(find_max-roi_slice.sh roi_layers.nii y)
vz=$(find_max-roi_slice.sh roi_layers.nii z)

# translate voxel to world coordinates
read -r wx wy wz < <(voxel-to-world.py roi_layers.nii $vx $vy $vz)

world_loc=$(fslstats roi_layers.nii -c)

# print command line for fsleyes visualization
fsleyes render --scene ortho \
--worldLoc ${world_loc}  \
--displaySpace ${register_dir}/fs_t1_in-func.nii \
--xcentre  0.15225  0.01828 \
--ycentre  0.32576  0.02225 \
--zcentre  0.31041  0.16074 \
--xzoom 1537.3333331051592 \
--yzoom 1537.3333331051592 \
--zzoom 1537.3333331051592 \
--layout horizontal \
--hidex --hidez \
--hideCursor \
--bgColour 0.0 0.0 0.0 \
--fgColour 1.0 1.0 1.0 \
--cursorColour 0.0 1.0 0.0 \
--colourBarLocation top \
--colourBarLabelSide top-left \
--colourBarSize 100.0 \
--labelSize 24 \
--performance 3 \
--movieSync \
-of ${seg_reg_vis_dir}/seg-reg-vis_${subject}_opaque.png \
fs_T1_in-func-ext.nii \
--name "fs_T1_in-func-ext" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -23.236267231128675 199.8592941407981 \
--clippingRange -23.236267231128675 202.09024975451737 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
${register_dir}/fs_t1_in-func.nii \
--name "fs_t1_in-func" --disabled --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -16.926658826500674 185.89678397541172 \
--clippingRange -16.926658826500674 187.92501840343084 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
${preprocess_dir}/func_all_T1.nii \
--name "func_all_T1" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange 0.0 255.0 --clippingRange 0.0 257.55 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
roi_layers.nii \
--name "roi_layers" --overlayType volume \
--alpha 100 --brightness 37.5125 \
--contrast 74.97500000000001 --cmap brain_colours_diverging_bwr \
--negativeCmap greyscale --displayRange 0.999 2.0 \
--clippingRange 0.999 2.02 --gamma 0.0 --cmapResolution 256 \
--interpolation none --numSteps 60 --blendFactor 0.3 \
--smoothing 0 --resolution 70 --numInnerSteps 10 \
--clipMode intersection --volume 0 \
${register_dir}/L.pial.func.surf.gii \
--name "L.pial.func" --overlayType mesh \
--alpha 100.0 --brightness 50.0 --contrast 50.0 --lut random \
--cmap greyscale --negativeCmap greyscale --vertexDataIndex 0 --vertexSet \
${register_dir}/L.pial.func.surf.gii \
--colour 1.0 0.0 0.0 --outline --outlineWidth 0.1 --refImage \
fs_T1_in-func-ext.nii \
--coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01 \
--gamma 0.0 --cmapResolution 256 \
${register_dir}/L.white.func.surf.gii \
--name "L.white.func" --overlayType mesh --alpha 100.0 --brightness 50.0 --contrast 50.0 \
--lut random --cmap greyscale --negativeCmap greyscale --vertexDataIndex 0 --vertexSet \
${register_dir}/L.white.func.surf.gii --colour 0.0 0.0 1.0 \
--outline --outlineWidth 0.5619999997694977 \
--refImage fs_T1_in-func-ext.nii \
--coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01 \
--gamma 0.0 --cmapResolution 256


# print command line for fsleyes visualization
fsleyes render --scene ortho \
--worldLoc ${world_loc}  \
--displaySpace ${register_dir}/fs_t1_in-func.nii \
--xcentre  0.15225  0.01828 \
--ycentre  0.32576  0.02225 \
--zcentre  0.31041  0.16074 \
--xzoom 1537.3333331051592 \
--yzoom 1537.3333331051592 \
--zzoom 1537.3333331051592 \
--layout horizontal \
--hidex --hidez \
--hideCursor \
--bgColour 0.0 0.0 0.0 \
--fgColour 1.0 1.0 1.0 \
--cursorColour 0.0 1.0 0.0 \
--colourBarLocation top \
--colourBarLabelSide top-left \
--colourBarSize 100.0 \
--labelSize 24 \
--performance 3 \
--movieSync \
-of ${seg_reg_vis_dir}/seg-reg-vis_${subject}_noslab.png \
fs_T1_in-func-ext.nii \
--name "fs_T1_in-func-ext" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -23.236267231128675 199.8592941407981 \
--clippingRange -23.236267231128675 202.09024975451737 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
${register_dir}/fs_t1_in-func.nii \
--name "fs_t1_in-func" --disabled --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -16.926658826500674 185.89678397541172 \
--clippingRange -16.926658826500674 187.92501840343084 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
roi_layers.nii \
--name "roi_layers" --overlayType volume \
--alpha 39.333333340318255 --brightness 37.5125 \
--contrast 74.97500000000001 --cmap brain_colours_diverging_bwr \
--negativeCmap greyscale --displayRange 0.999 2.0 \
--clippingRange 0.999 2.02 --gamma 0.0 --cmapResolution 256 \
--interpolation none --numSteps 60 --blendFactor 0.3 \
--smoothing 0 --resolution 70 --numInnerSteps 10 \
--clipMode intersection --volume 0 \
${register_dir}/L.pial.func.surf.gii \
--name "L.pial.func" --overlayType mesh \
--alpha 100.0 --brightness 50.0 --contrast 50.0 --lut random \
--cmap greyscale --negativeCmap greyscale --vertexDataIndex 0 --vertexSet \
${register_dir}/L.pial.func.surf.gii \
--colour 1.0 0.0 0.0 --outline --outlineWidth 0.1 --refImage \
fs_T1_in-func-ext.nii \
--coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01 \
--gamma 0.0 --cmapResolution 256 \
${register_dir}/L.white.func.surf.gii \
--name "L.white.func" --overlayType mesh --alpha 100.0 --brightness 50.0 --contrast 50.0 \
--lut random --cmap greyscale --negativeCmap greyscale --vertexDataIndex 0 --vertexSet \
${register_dir}/L.white.func.surf.gii --colour 0.0 0.0 1.0 \
--outline --outlineWidth 0.5619999997694977 \
--refImage fs_T1_in-func-ext.nii \
--coordSpace affine --unlinkLowRanges --displayRange 0.0 1.0 --clippingRange 0.0 1.01 \
--gamma 0.0 --cmapResolution 256