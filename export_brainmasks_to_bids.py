#!/usr/bin/env python3
"""
Exports the brain masks of a run of 01_sl_mp2rage_recon-all.sh (<freesurfer_dir>/sub-XX/mri/brainmask_mask.mgz,
computed from the CAT12 segmentation) as the BIDS derivative dataset derivatives/brainmasks, which is used by
01_sl_mp2rage_recon-all.sh (brainmask_source=published) and distributed with the data set.

The CAT12 segmentation is not deterministic (its multithreaded denoising can change single voxels of the mask
between runs), so the published masks make the anatomical processing, and thereby the whole pipeline, reproducible.

The masks are stored in the voxel space of the UNIT1 image of each subject (the space in which they are computed);
the mapping from FreeSurfer's orig space is exact (both are 0.75 mm grids, orig is reoriented and padded).

usage: export_brainmasks_to_bids.py <study_data_dir> <freesurfer_dir> [<output_dir>]
"""

import sys
import os
import glob
import json
import numpy as np
import nibabel as nib

study_data_dir = os.path.abspath(sys.argv[1])
freesurfer_dir = os.path.abspath(sys.argv[2])
out_dir = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else \
    os.path.join(study_data_dir, 'derivatives', 'brainmasks')

description = ("Brain mask used for the FreeSurfer reconstruction (instead of FreeSurfer's skull stripping): all "
               "voxels with a non-zero grey or white matter probability in the CAT12 segmentation of the "
               "MPRAGE-ised UNIT1 image (UNIT1 multiplied with the normalised, SPM bias corrected INV2 image), "
               "computed by 01_sl_mp2rage_recon-all.sh of the analysis code.")

subjects = sorted(os.path.basename(os.path.dirname(os.path.dirname(f))) for f in
                  glob.glob(os.path.join(freesurfer_dir, 'sub-*', 'mri', 'brainmask_mask.mgz')))
if not subjects:
    raise FileNotFoundError(f'no brain masks found in {freesurfer_dir}/sub-*/mri/brainmask_mask.mgz')

os.makedirs(out_dir, exist_ok=True)
raw_link = os.path.relpath(study_data_dir, out_dir) + '/'

# dataset level files
with open(os.path.join(out_dir, 'dataset_description.json'), 'w') as f:
    json.dump({"Name": "Brain masks for the replication of Finn et al. (2019)",
               "BIDSVersion": "1.10.0",
               "DatasetType": "derivative",
               "GeneratedBy": [{"Name": "CAT12",
                                "Version": "12.8.2 (r2166)",
                                "Description": "Segmentation of the MPRAGE-ised UNIT1 image (standalone version "
                                               "with SPM12 and MATLAB Runtime R2017b), see README."}],
               "SourceDatasets": [{"URL": "bids:raw:"}],
               "DatasetLinks": {"raw": raw_link}}, f, indent=4)

with open(os.path.join(out_dir, 'README'), 'w') as f:
    print("Brain masks for the replication of Finn et al. (2019)\n", file=f)
    print(description + "\n", file=f)
    print("The CAT12 segmentation is not deterministic: its multithreaded denoising (SANLM) can change single "
          "voxels of the mask between runs, which changes the FreeSurfer surfaces of the subject. With these "
          "masks, the anatomical processing is reproducible.\n", file=f)
    print("The masks are in the voxel space of the UNIT1 image of each subject, see SpatialReference in the "
          "sidecar files.", file=f)

# subject level files
for subject in subjects:
    uni_file = os.path.join(study_data_dir, subject, 'anat', f'{subject}_UNIT1.nii')
    inv2_file = os.path.join(study_data_dir, subject, 'anat', f'{subject}_inv-2_MP2RAGE.nii')
    uni_img = nib.load(uni_file)
    mask_img = nib.load(os.path.join(freesurfer_dir, subject, 'mri', 'brainmask_mask.mgz'))
    mask = np.asarray(mask_img.dataobj)
    if not set(np.unique(mask)) <= {0, 1}:
        raise ValueError(f'brain mask of {subject} contains values other than 0 and 1')

    # map the UNIT1 voxels to orig voxels (exact: the grids have the same voxel size and are aligned)
    uni_to_orig = np.linalg.inv(mask_img.affine) @ uni_img.affine
    ijk = np.indices(uni_img.shape[:3]).reshape(3, -1)
    orig_ijk = uni_to_orig[:3, :3] @ ijk + uni_to_orig[:3, 3:]
    orig_idx = np.rint(orig_ijk).astype(int)
    if not np.allclose(orig_ijk, orig_idx, atol=1e-3):
        raise ValueError(f'voxel grids of the brain mask and {uni_file} are not aligned')
    inside = np.all((orig_idx >= 0) & (orig_idx < np.array(mask.shape)[:, None]), axis=0)
    native = np.zeros(ijk.shape[1], dtype=np.uint8)
    native[inside] = mask[tuple(orig_idx[:, inside])]
    native = native.reshape(uni_img.shape[:3])
    if native.sum() != mask.sum():
        raise ValueError(f'brain mask of {subject} extends beyond {uni_file}')

    # save with the exact voxel to world transformation of the UNIT1 image
    out_img = nib.Nifti1Image(native, uni_img.affine)
    out_img.set_qform(uni_img.affine, code=int(uni_img.header['qform_code']))
    out_img.set_sform(uni_img.affine, code=int(uni_img.header['sform_code']))
    out_img.header.set_xyzt_units(*uni_img.header.get_xyzt_units())

    subject_dir = os.path.join(out_dir, subject, 'anat')
    os.makedirs(subject_dir, exist_ok=True)
    out_base = os.path.join(subject_dir, f'{subject}_desc-brain_mask')
    nib.save(out_img, out_base + '.nii.gz')
    with open(out_base + '.json', 'w') as f:
        json.dump({"Description": description,
                   "Type": "Brain",
                   "SpatialReference": 'bids:raw:' + os.path.relpath(uni_file, study_data_dir),
                   "Sources": ['bids:raw:' + os.path.relpath(fname, study_data_dir)
                               for fname in [uni_file, inv2_file]]},
                  f, indent=4)
    print(f'{subject}: {out_base}.nii.gz')
