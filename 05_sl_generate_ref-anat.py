#!/usr/bin/env python3
import os
import sys
from fmri_analysis import layer_analysis as analysis
import vdfs


studyDataDir = sys.argv[1]
subject = sys.argv[2]

try:
    MAX_CPUS = int(os.environ['OMP_NUM_THREADS'])
except KeyError:
    MAX_CPUS = 1

# set up directories
fs_dir = os.path.join(studyDataDir, "derivatives", "freesurfer", subject)
ciftify_dir = os.path.join(studyDataDir, "derivatives", "ciftify", subject)
register_dir = os.path.join(studyDataDir, "derivatives", "register", subject)

ref_anat_dir = os.path.join(studyDataDir, "derivatives", "ref-anat", subject)
os.makedirs(ref_anat_dir, exist_ok=True)

# 1. calculate vdfs depths
vdfs.process_voxeldepth_from_surfaces(
    os.path.join(register_dir, "lh.func.white"),
    os.path.join(fs_dir, "surf", "lh.area"),
    os.path.join(register_dir, "lh.func.pial"),
    os.path.join(fs_dir, "surf", "lh.area.pial"),
    os.path.join(register_dir, "rh.func.white"),
    os.path.join(fs_dir, "surf", "rh.area"),
    os.path.join(register_dir, "rh.func.pial"),
    os.path.join(fs_dir, "surf", "rh.area.pial"),
    os.path.join(register_dir, "fs_t1_in-func.nii"),
    os.path.join(ref_anat_dir, f"vdfs_depths_equivol.nii"),
    os.path.join(ref_anat_dir, f"vdfs_columns_equivol.nii"),
    method='equivol',
    upsample_factor=None,
    n_jobs=MAX_CPUS,
    force=True)

# 2. transform glasser atlas to native space
for hemi in ["L", "R"]:
    labels_fs_LR = os.path.join(studyDataDir, "derivatives", "resources", 
        f"Q1-Q6_RelatedValidation210.{hemi}.CorticalAreas_dil_Final_Final_Areas_Group_Colors.164k_fs_LR.label.gii")
    native_pial_surf = os.path.join(register_dir, f"{hemi}.pial.func.surf.gii")
    native_white_surf = os.path.join(register_dir, f"{hemi}.white.func.surf.gii")

    labels_native_volume_out = os.path.join(ref_anat_dir, f"glasser_{hemi}_in-func.nii")
    labels_native_surf_out = os.path.join(ref_anat_dir, f"{subject}.glasser.{hemi}.native.label.gii")
    volume_space_file = os.path.join(register_dir, "fs_t1_in-func.nii")
    
    analysis.fs_LR_labels_to_native_volume(labels_fs_LR, labels_native_volume_out,
                                           ciftify_dir, native_pial_surf, native_white_surf, 
                                           volume_space_file, hemi, labels_native_surf_out=labels_native_surf_out)