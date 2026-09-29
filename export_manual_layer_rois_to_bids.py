#!/usr/bin/env python3
"""
Exports the manually drawn layer ROIs (derivatives/roi/sub-XX/roi_layers_manual.nii, drawn on the images
exported by 12_sl_export_for_manual_roi_drawing.sh) as the BIDS derivative dataset
derivatives/manual-layer-rois, which is used by 13_gl_sample_data.py and distributed with the data set.

The ROIs are stored as discrete segmentations (_dseg, values 1 = superficial, 2 = deep, see desc-dlPFClayers_dseg.tsv) in the
voxel space of the functional images of each subject (space-func), with the header of the first functional run.

usage: export_manual_layer_rois_to_bids.py <study_data_dir> [<output_dir>]
"""

import sys
import os
import glob
import json
import numpy as np
import nibabel as nib

study_data_dir = os.path.abspath(sys.argv[1])
out_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else \
    os.path.join(study_data_dir, 'derivatives', 'manual-layer-rois')

layer_labels = {1: 'superficial', 2: 'deep'}
guidelines = [
    "draw layers as a connected collection of voxels without holes",
    "position the superficial layer such that there is no partial voluming with the cerebrospinal fluid",
    "position the deeper layer such that there is no partial voluming with white matter",
    "erode the superficial and deeper layers until there is no residual overlap of superficial and deeper layers",
    "keep the thickness of the superficial and deeper layers similar along the cortical ribbon",
    "choose the thickness of the superficial and deeper layers such that they fill as much of the cortex as "
    "possible without violating the guidelines above"]
description = ("Manually drawn superficial and deep layer ROIs in left dlPFC, drawn on the VASO T1-weighted image "
               "(mean of all functional runs, computed by 03_sl_preprocess_vaso.sh of the analysis code) following "
               "the guidelines of Finn et al. (2019).")

subjects = sorted(os.path.basename(os.path.dirname(f)) for f in
                  glob.glob(os.path.join(study_data_dir, 'derivatives', 'roi', 'sub-*', 'roi_layers_manual.nii')))
if not subjects:
    raise FileNotFoundError('no manual layer ROIs found in derivatives/roi/sub-*/roi_layers_manual.nii')

os.makedirs(out_dir, exist_ok=True)
raw_link = os.path.relpath(study_data_dir, out_dir) + '/'

# dataset level files
with open(os.path.join(out_dir, 'dataset_description.json'), 'w') as f:
    json.dump({"Name": "Manual layer ROIs for the replication of Finn et al. (2019)",
               "BIDSVersion": "1.10.0",
               "DatasetType": "derivative",
               "GeneratedBy": [{"Name": "Manual drawing",
                                "Description": "Superficial and deep layer ROIs drawn by hand on the VASO "
                                               "T1-weighted image of each subject, following the guidelines of "
                                               "Finn et al. (2019), see README."}],
               "SourceDatasets": [{"URL": "bids:raw:"}],
               "DatasetLinks": {"raw": raw_link}}, f, indent=4)

with open(os.path.join(out_dir, 'desc-dlPFClayers_dseg.tsv'), 'w') as f:
    print('index\tname', file=f)
    for index, name in layer_labels.items():
        print(f'{index}\t{name}', file=f)

with open(os.path.join(out_dir, 'README'), 'w') as f:
    print("Manual layer ROIs for the replication of Finn et al. (2019)\n", file=f)
    print(description + "\n", file=f)
    print("Label values (see desc-dlPFClayers_dseg.tsv): " + ", ".join(f"{i} = {n}" for i, n in layer_labels.items()) + ".\n", file=f)
    print("The ROIs are in the voxel space of the functional images of each subject (space-func), "
          "see SpatialReference in the sidecar files.\n", file=f)
    print("Drawing guidelines (Finn et al., 2019):", file=f)
    for idx, guideline in enumerate(guidelines, 1):
        print(f"{idx}. {guideline};", file=f)

# subject level files
for subject in subjects:
    func_files = sorted(glob.glob(os.path.join(study_data_dir, subject, 'func', f'{subject}_task-*_bold.nii*')))
    reference = [f for f in func_files if '_task-alpharem_acq-nulled_run-1_bold' in f][0]
    ref_img = nib.load(reference)

    roi_img = nib.load(os.path.join(study_data_dir, 'derivatives', 'roi', subject, 'roi_layers_manual.nii'))
    roi = np.asarray(roi_img.dataobj)
    # check that the ROI is on the voxel grid of the functional images and only contains layer labels
    if roi.shape != ref_img.shape[:3] or not np.allclose(roi_img.affine, ref_img.affine, atol=1e-3):
        raise ValueError(f'manual layer ROI of {subject} is not on the voxel grid of {reference}')
    if not set(np.unique(roi)) <= {0} | set(layer_labels):
        raise ValueError(f'manual layer ROI of {subject} contains values other than 0 and {list(layer_labels)}')

    # save with the exact voxel to world transformation of the functional reference image
    out_img = nib.Nifti1Image(roi.astype(np.uint8), ref_img.affine)
    out_img.set_qform(ref_img.affine, code=int(ref_img.header['qform_code']))
    out_img.set_sform(ref_img.affine, code=int(ref_img.header['sform_code']))
    out_img.header.set_xyzt_units(*ref_img.header.get_xyzt_units())

    subject_dir = os.path.join(out_dir, subject, 'anat')
    os.makedirs(subject_dir, exist_ok=True)
    out_base = os.path.join(subject_dir, f'{subject}_space-func_desc-dlPFClayers_dseg')
    nib.save(out_img, out_base + '.nii.gz')
    with open(out_base + '.json', 'w') as f:
        json.dump({"Description": description,
                   "SpatialReference": 'bids:raw:' + os.path.relpath(reference, study_data_dir),
                   "Sources": ['bids:raw:' + os.path.relpath(fname, study_data_dir) for fname in func_files]},
                  f, indent=4)
    print(f'{subject}: {out_base}.nii.gz')
