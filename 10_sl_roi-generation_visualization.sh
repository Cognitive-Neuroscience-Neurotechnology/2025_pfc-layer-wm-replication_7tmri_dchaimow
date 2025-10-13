#!/bin/bash
studyDataDir=$1
subject=$2

register_dir=${studyDataDir}/derivatives/register/${subject}
roi_dir=${studyDataDir}/derivatives/roi/${subject}
ref_anat_dir=${studyDataDir}/derivatives/ref-anat/${subject}
trialavg_dir=${studyDataDir}/derivatives/trialavg/${subject}

roi_generation_vis_dir=${studyDataDir}/derivatives/roi-generation_vis/${subject}
mkdir -p ${roi_generation_vis_dir}

export FSLOUTPUTTYPE=NIFTI

tmp_dir=$(mktemp -d)
mkdir -p ${tmp_dir}

wb_command -scene-file-relocate surface_figures.scene  ${tmp_dir}/surface_figures.scene
cd ${tmp_dir}

# generate workbench surface plots
sed "s/sub-01/${subject}/g" surface_figures.scene > surface_figures_${subject}.scene
wb_command -scene-capture-image surface_figures_${subject}.scene "fstat_on_surf" ${roi_generation_vis_dir}/fstat_on_surf_${subject}.png \
    -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH   
wb_command -scene-capture-image surface_figures_${subject}.scene "clusters_on_surf" ${roi_generation_vis_dir}/clusters_on_surf_${subject}.png \
    -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH   
wb_command -scene-capture-image surface_figures_${subject}.scene "roi_on_surf" ${roi_generation_vis_dir}/roi_on_surf_${subject}.png \
    -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH   
wb_command -scene-capture-image surface_figures_${subject}.scene "glasser_annotated_on_surf" ${roi_generation_vis_dir}/glasser_annotated_on_surf_${subject}.png \
    -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH   
wb_command -scene-capture-image surface_figures_${subject}.scene "glasser_annotated_on_fsLR_surf" ${roi_generation_vis_dir}/glasser_annotated_on_fsLR_surf_${subject}.png \
    -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH   

# generate a roi_layers.nii file by combining an roi mask with depth information
roi_file=${roi_dir}/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A100.nii
depth_file=${ref_anat_dir}/vdfs_depths_equivol.nii

# superficial layer = depth_file>0.5
fslmaths ${depth_file} -nan -thr 0.5 -bin superficial.nii -odt int
# deep layer = depth_file<0.5
fslmaths ${depth_file} -nan -thr 0 -uthr 0.5 -bin deep.nii -odt int
# combine layers with roi
fslmaths superficial.nii -mul 2 -add deep.nii -mul ${roi_file} roi_layers.nii -odt int

# calculate which axial slice to use for visualization by reslicing and counting number of mask voxels in each slice
vx=$(find_max-roi_slice.sh roi_layers.nii x)
vy=$(find_max-roi_slice.sh roi_layers.nii y)
vz=$(find_max-roi_slice.sh roi_layers.nii z)

# translate voxel to world coordinates
read -r wx wy wz < <(voxel-to-world.py roi_layers.nii $vx $vy $vz)
world_loc=$(fslstats roi_layers.nii -c)

# combined fstat on fs_t1_in-func with colorbar
fsleyes render --scene ortho \
--worldLoc ${world_loc} \
--size 752 752 \
--displaySpace ${register_dir}/fs_t1_in-func.nii \
--xcentre  0.00000 -0.00000 \
--ycentre  0.00000 -0.00000 \
--zcentre  0.00000  0.00000 \
--xzoom 100 \
--yzoom 100 \
--zzoom 100 \
--layout horizontal \
--hidex --hidey \
--hideCursor \
--hideLabels \
--bgColour 0.0 0.0 0.0 \
--fgColour 1.0 1.0 1.0 \
--colourBarLocation bottom \
--colourBarLabelSide top-left \
--colourBarSize 100.0 \
--labelSize 24 \
--performance 3 \
-of ${roi_generation_vis_dir}/combined-fstat-vol-vis_${subject}.png \
${register_dir}/fs_t1_in-func.nii \
--name "fs_t1_in-func" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -16.303955291740294 183.34814845506676 \
--clippingRange -16.303955291740294 183.34814845506676 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
${trialavg_dir}/trialavg_bold_combined_fstat.nii \
--name "trial averaging F-stat" --overlayType volume \
--alpha 100.0 --brightness 63.85406876222495 --contrast 87.69790531437447 \
--cmap red-yellow --negativeCmap greyscale \
--displayRange 3.0 10.0 \
--clippingRange 3.0 28.892811279296875 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0

# cortical depth on fs_t1_in-func
fsleyes render --scene ortho \
--worldLoc ${world_loc} \
--size 752 752 \
--displaySpace ${register_dir}/fs_t1_in-func.nii \
--xcentre  0.00000 -0.00000 \
--ycentre  0.00000 -0.00000 \
--zcentre  0.00000  0.00000 \
--xzoom 100 \
--yzoom 100 \
--zzoom 100 \
--layout horizontal \
--hidex --hidey \
--hideCursor \
--hideLabels \
--bgColour 0.0 0.0 0.0 \
--fgColour 1.0 1.0 1.0 \
--colourBarLocation bottom \
--colourBarLabelSide top-left \
--colourBarSize 100.0 \
--labelSize 24 \
--performance 3 \
-of ${roi_generation_vis_dir}/cortical-depths-vis_${subject}.png \
${register_dir}/fs_t1_in-func.nii \
--name "fs_t1_in-func" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -16.303955291740294 183.34814845506676 \
--clippingRange -16.303955291740294 183.34814845506676 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 \
${ref_anat_dir}/vdfs_depths_equivol.nii \
--name "vdfs_depths_equivol" --overlayType volume \
--alpha 66 --brightness 50 --contrast 50 \
--cmap render3 --negativeCmap greyscale \
--displayRange 0.0 1.0 \
--clippingRange 0.0 1.0 \
--gamma 0.0 --cmapResolution 256 --interpolation none \
--numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70 \
--numInnerSteps 10 --clipMode intersection --volume 0 

# layer roi on fs_t1_in-func
fsleyes render --scene ortho \
--worldLoc ${world_loc} \
--size 752 752 \
--displaySpace ${register_dir}/fs_t1_in-func.nii \
--xcentre  0.00000 -0.00000 \
--ycentre  0.00000 -0.00000 \
--zcentre  0.00000  0.00000 \
--xzoom 100 \
--yzoom 100 \
--zzoom 100 \
--layout horizontal \
--hidex --hidey \
--hideCursor \
--hideLabels \
--bgColour 0.0 0.0 0.0 \
--fgColour 1.0 1.0 1.0 \
--colourBarLocation bottom \
--colourBarLabelSide top-left \
--colourBarSize 100.0 \
--labelSize 24 \
--performance 3 \
-of ${roi_generation_vis_dir}/layer-roi-vol-vis_${subject}.png \
${register_dir}/fs_t1_in-func.nii \
--name "fs_t1_in-func" --overlayType volume \
--alpha 100.0 --brightness 50.0 --contrast 50.0 \
--cmap greyscale --negativeCmap greyscale \
--displayRange -16.303955291740294 183.34814845506676 \
--clippingRange -16.303955291740294 183.34814845506676 \
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
--clipMode intersection --volume 0 



