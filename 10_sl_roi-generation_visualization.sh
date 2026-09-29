#!/bin/bash
set -euo pipefail
studyDataDir=$1
subject=$2

register_dir=${studyDataDir}/derivatives/register/${subject}
roi_dir=${studyDataDir}/derivatives/roi/${subject}
ref_anat_dir=${studyDataDir}/derivatives/ref-anat/${subject}
trialavg_dir=${studyDataDir}/derivatives/trialavg/${subject}

roi_generation_vis_dir=${studyDataDir}/derivatives/roi-generation_vis/${subject}
mkdir -p ${roi_generation_vis_dir}

main_area=$(jq '.main_area' ${roi_dir}/roi_params.json)  # main ROI target area (08_sl_generate_rois.py)
# ROI target areas for which layer ROIs are visualized (the extra area 50 is generated for this in 08)
vis_areas="50 ${main_area} 200"

export FSLOUTPUTTYPE=NIFTI

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

# Fill in the scene template before changing directory; data paths are absolute.
sed -e "s|studyDataDir|${studyDataDir}|g" \
    -e "s/sub-01/${subject}/g" \
    -e "s/_A100\./_A${main_area}./g" \
    surface_figures.scene > "${tmp_dir}/surface_figures_${subject}.scene"
cd "${tmp_dir}"


# generate workbench surface plots
for scene in fstat_on_surf clusters_on_surf roi_on_surf glasser_annotated_on_surf glasser_annotated_on_fsLR_surf; do
    wb_command -scene-capture-image surface_figures_${subject}.scene "${scene}" ${roi_generation_vis_dir}/${scene}_${subject}.png \
        -size-width-height 4 3 -units INCHES -resolution 600 PIXELS_PER_INCH
done


# fsleyes options shared by all volume renderings:
# orthogonal views (without cursor, labels and two of the three views) in functional space
scene_opts=(--scene ortho
    --displaySpace "${register_dir}/fs_t1_in-func.nii"
    --xcentre 0.00000 -0.00000 --ycentre 0.00000 -0.00000 --zcentre 0.00000 0.00000
    --xzoom 100 --yzoom 100 --zzoom 100
    --layout horizontal --hidex --hidey --hideCursor --hideLabels
    --bgColour 0.0 0.0 0.0 --fgColour 1.0 1.0 1.0
    --colourBarLocation bottom --colourBarLabelSide top-left --colourBarSize 100.0
    --labelSize 24 --performance 3)
# display options shared by all volume overlays
volume_opts=(--gamma 0.0 --cmapResolution 256 --interpolation none
    --numSteps 60 --blendFactor 0.3 --smoothing 0 --resolution 70
    --numInnerSteps 10 --clipMode intersection --volume 0)
# fs T1 in functional space as background
t1_overlay=("${register_dir}/fs_t1_in-func.nii" --name "fs_t1_in-func" --overlayType volume
    --alpha 100.0 --brightness 50.0 --contrast 50.0 --cmap greyscale --negativeCmap greyscale
    --displayRange -16.303955291740294 183.34814845506676
    --clippingRange -16.303955291740294 183.34814845506676
    "${volume_opts[@]}")
# layer ROI (superficial = 1, deep = 2, as in the manual layer ROIs) overlay options (the image is given before them)
roi_layers_opts=(--name "roi_layers" --overlayType volume
    --alpha 100 --brightness 37.5125 --contrast 74.97500000000001
    --cmap brain_colours_diverging_bwr --invert --negativeCmap greyscale
    --displayRange 0.999 2.0 --clippingRange 0.999 2.02
    "${volume_opts[@]}")


# generate roi_layers.nii files by combining an roi mask with depth information
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

# combined fstat on fs_t1_in-func with colorbar
fsleyes render "${scene_opts[@]}" --worldLoc ${world_loc} --size 752 752 \
    -of ${roi_generation_vis_dir}/combined-fstat-vol-vis_${subject}.png \
    "${t1_overlay[@]}" \
    ${trialavg_dir}/trialavg_bold_combined_fstat.nii \
    --name "trial averaging F-stat" --overlayType volume \
    --alpha 100.0 --brightness 63.85406876222495 --contrast 87.69790531437447 \
    --cmap red-yellow --negativeCmap greyscale \
    --displayRange 3.0 10.0 --clippingRange 3.0 28.892811279296875 \
    "${volume_opts[@]}"

# cortical depth on fs_t1_in-func
fsleyes render "${scene_opts[@]}" --worldLoc ${world_loc} --size 752 752 \
    -of ${roi_generation_vis_dir}/cortical-depths-vis_${subject}.png \
    "${t1_overlay[@]}" \
    ${depth_file} \
    --name "vdfs_depths_equivol" --overlayType volume \
    --alpha 66 --brightness 50 --contrast 50 \
    --cmap render3 --negativeCmap greyscale \
    --displayRange 0.0 1.0 --clippingRange 0.0 1.0 \
    "${volume_opts[@]}"


for area in ${vis_areas}; do
    roi_file=${roi_dir}/roi_trialavg_bold_combined_fstat_dlPFC_require_p9-46v_A${area}.nii

    # combine layers with roi
    fslmaths deep.nii -mul 2 -add superficial.nii -mul ${roi_file} roi_layers_A${area}.nii -odt int

    # center the views on the center of gravity of the (binary) ROI
    world_loc=$(fslstats ${roi_file} -c)

    # layer roi on fs_t1_in-func, full view and zoomed in on the ROI
    fsleyes render "${scene_opts[@]}" --worldLoc ${world_loc} --size 752 752 \
        -of ${roi_generation_vis_dir}/layer-roi-vol-vis_A${area}_${subject}.png \
        "${t1_overlay[@]}" \
        roi_layers_A${area}.nii "${roi_layers_opts[@]}"

    conda run -p $FSLDIR --no-capture-output fsleyes_render_zoom_roi.py \
        "${scene_opts[@]}" --worldLoc ${world_loc} --size 376 376 \
        -of ${roi_generation_vis_dir}/layer-roi-vol-vis_A${area}_zoom_${subject}.png \
        "${t1_overlay[@]}" \
        roi_layers_A${area}.nii "${roi_layers_opts[@]}"
done

# main ROI with the zoomed view as inset
cp ${roi_generation_vis_dir}/layer-roi-vol-vis_A${main_area}_${subject}.png \
   ${roi_generation_vis_dir}/layer-roi-vol-vis_${subject}.png

cp ${roi_generation_vis_dir}/layer-roi-vol-vis_A${main_area}_zoom_${subject}.png \
   ${roi_generation_vis_dir}/layer-roi-vol-vis_zoom_${subject}.png

composite-inset.py ${roi_generation_vis_dir}/layer-roi-vol-vis_${subject}.png \
    ${roi_generation_vis_dir}/layer-roi-vol-vis_zoom_${subject}.png \
    ${roi_generation_vis_dir}/layer-roi-vol-vis_${subject}.png \
    --corner lower-left --margin-px 10 --border-px 3
