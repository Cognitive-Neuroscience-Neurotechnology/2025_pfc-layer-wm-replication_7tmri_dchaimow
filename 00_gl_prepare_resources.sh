#!/bin/bash
studyDataDir=$1

# prepare HCP MMP1.0 atlas
ciftify_data_dir=$(conda run -n base python -c "import ciftify; print(ciftify.config.find_ciftify_global())")

# this appears to be the recommended MMP parcellation file, here taken from the local ciftify installation
# e.g. see here: https://groups.google.com/a/humanconnectome.org/g/hcp-users/c/oB-AOPqgJk0/m/WKbK4lwRAgAJ
# or here: https://groups.google.com/a/humanconnectome.org/g/hcp-users/c/7co1s05E_9Y/m/a-UUT2Q8AgAJ
# or here: https://www.mail-archive.com/freesurfer@nmr.mgh.harvard.edu/msg67045.html
# BALSA download link: https://balsa.wustl.edu/file/show/3VLx
parcellation_32k=${ciftify_data_dir}/HCP_S1200_GroupAvg_v1/Q1-Q6_RelatedValidation210.CorticalAreas_dil_Final_Final_Areas_Group_Colors.32k_fs_LR.dlabel.nii

resources_dir=${studyDataDir}/derivatives/resources
mkdir -p ${resources_dir}

tmp_dir=$(mktemp -d)
trap 'rm -rf ${tmp_dir}' EXIT
for hemisphere in LEFT RIGHT; do
    # get the first letter of the hemisphere
    hemi=${hemisphere:0:1}

    tmp_hemi_parcellation_32k=${tmp_dir}/Q1-Q6_RelatedValidation210.${hemi}.CorticalAreas_dil_Final_Final_Areas_Group_Colors.32k_fs_LR.label.gii
    hemi_parcellation_164k=${resources_dir}/Q1-Q6_RelatedValidation210.${hemi}.CorticalAreas_dil_Final_Final_Areas_Group_Colors.164k_fs_LR.label.gii
    sphere_32k=${ciftify_data_dir}/standard_mesh_atlases/${hemi}.sphere.32k_fs_LR.surf.gii
    sphere_164k=${ciftify_data_dir}/standard_mesh_atlases/fsaverage.${hemi}_LR.spherical_std.164k_fs_LR.surf.gii

    # extract single hemisphere parcellation
    wb_command -cifti-separate ${parcellation_32k} COLUMN -label CORTEX_${hemisphere} ${tmp_hemi_parcellation_32k}

    # resample to 164k
    wb_command -label-resample ${tmp_hemi_parcellation_32k} ${sphere_32k} ${sphere_164k} BARYCENTRIC ${hemi_parcellation_164k}
done

# prepare 0.5mm MNI template
export FSLOUTPUTTYPE=NIFTI_GZ
cp ${FSL_DIR}/data/standard/MNI152_T1_0.5mm.nii.gz ${resources_dir}/
cp ${FSL_DIR}/data/standard/MNI152_T1_1mm_brain_mask.nii.gz ${resources_dir}/

# create a 0.5mm brain mask
flirt -in ${resources_dir}/MNI152_T1_1mm_brain_mask.nii.gz \
      -ref ${resources_dir}/MNI152_T1_0.5mm.nii.gz \
      -out ${resources_dir}/MNI152_T1_0.5mm_brain_mask.nii.gz \
      -applyxfm \
      -interp nearestneighbour
rm ${resources_dir}/MNI152_T1_1mm_brain_mask.nii.gz

fslmaths ${resources_dir}/MNI152_T1_0.5mm.nii.gz -mas ${resources_dir}/MNI152_T1_0.5mm_brain_mask.nii.gz \
    ${resources_dir}/MNI152_T1_0.5mm_brain.nii.gz