#!/usr/bin/env python3
import subprocess
import os
import sys
from fmri_analysis import layer_analysis as analysis

studyDataDir = sys.argv[1]
subject = sys.argv[2]

# set up directories
fs_dir = os.path.join(studyDataDir, "derivatives", "freesurfer", subject)
preprocess_dir = os.path.join(studyDataDir, "derivatives", "preprocess", subject)

register_dir = os.path.join(studyDataDir, "derivatives", "register", subject)
os.makedirs(register_dir, exist_ok=True)

# 1. register freesurfer to epi
subprocess.run(["register_fs-to-vasoT1_no-manual.sh",
                os.path.join(preprocess_dir, "func_all_T1.nii"),
                fs_dir], cwd=register_dir, check=True)
# clean up
os.remove(os.path.join(register_dir, "fs_T1.nii"))
os.remove(os.path.join(register_dir, "fs_to_func_Warped.nii"))
os.remove(os.path.join(register_dir, "fs_to_func_InverseWarped.nii"))


# 2. transform freesurfer surface to epi_space
fs_to_func_reg = [os.path.join(register_dir, "fs_to_func_0GenericAffine.mat"),
                  os.path.join(register_dir, "fs_to_func_1InverseWarp.nii.gz")]
is_inverse_transform_flags = [False, True]
analysis.fs_surface_to_func(fs_to_func_reg, fs_dir, register_dir,
                            is_inverse_transform_flags,force=True)

# clean up
for hemi, hemi_hcp in zip(["lh", "rh"], ["L", "R"]):
    for surf in ["pial", "white"]:
        os.remove(os.path.join(register_dir, f"{hemi}.{surf}_converted.gii"))
        os.remove(os.path.join(register_dir, f"{hemi}.{surf}_convertedpoints.csv"))
        os.remove(os.path.join(register_dir, f"{hemi}.{surf}_convertedpoints_transformed.csv"))
        os.rename(os.path.join(register_dir, f"{hemi}.{surf}_converted.transformed.gii"),
                  os.path.join(register_dir, f"{hemi_hcp}.{surf}.func.surf.gii"))
        os.rename(os.path.join(register_dir, f"{hemi}.{surf}_func"),
                  os.path.join(register_dir, f"{hemi}.func.{surf}"))