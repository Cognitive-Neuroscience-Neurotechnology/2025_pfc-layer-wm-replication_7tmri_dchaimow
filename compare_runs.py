#!/usr/bin/env python3
"""
Compares the anatomical processing of two runs of the pipeline (two derivatives directories), to quantify the
effect of differences of the brain masks (the CAT12 segmentation is not deterministic, see README):

1. brain masks (FreeSurfer input, freesurfer/sub-XX/mri/brainmask_mask.mgz): differing voxels
2. FreeSurfer surfaces (white, pial) of the subjects whose surfaces differ: distance from each vertex to the
   other run's surface (exact point to triangle distance, in both directions), and where the larger (> 1 mm)
   shifts are: at the medial wall (no atlas label) or within the atlas region of the ROI definition
3. atlas labels (ref-anat/sub-XX/sub-XX.glasser.L.native.label.gii) within the atlas region of the ROI definition
   (08_sl_generate_rois.py): fraction of vertices whose label differs (nearest vertex of the other run)
4. main ROIs (roi/sub-XX/roi_..._dlPFC_require_p9-46v_A<main area>.nii, voxel space of the functional images):
   Dice coefficient

usage: compare_runs.py <derivatives_dir_a> <derivatives_dir_b>
"""

import sys
import os
import glob
import numpy as np
import nibabel as nib
from nibabel import freesurfer as fs
from scipy.spatial import cKDTree
import utils

run_a, run_b = (os.path.abspath(d) for d in sys.argv[1:3])

# atlas region of the ROI definition in 08_sl_generate_rois.py
roi_atlas_areas = ['p9-46v', '46', '8C', 'IFSp', 'IFSa']
roi_require_area = 'p9-46v'
large_shift = 1.0  # mm


def point_triangle_distances(p, a, b, c):
    """ Distances from points p to triangles (a, b, c) (all arrays n x 3), closest point after Ericson,
    Real-Time Collision Detection (2005). """
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - b
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - c
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    safe = lambda x: np.where(x == 0, 1e-30, x)
    denom = safe(va + vb + vc)
    q = a + ab * (vb / denom)[:, None] + ac * (vc / denom)[:, None]  # interior of the triangle
    edge_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    q[edge_ab] = (a + ab * (d1 / safe(d1 - d3))[:, None])[edge_ab]
    edge_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    q[edge_ac] = (a + ac * (d2 / safe(d2 - d6))[:, None])[edge_ac]
    edge_bc = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    q[edge_bc] = (b + (c - b) * ((d4 - d3) / safe((d4 - d3) + (d5 - d6)))[:, None])[edge_bc]
    for vertex_region, vertex in [((d1 <= 0) & (d2 <= 0), a), ((d3 >= 0) & (d4 <= d3), b),
                                  ((d6 >= 0) & (d5 <= d6), c)]:
        q[vertex_region] = vertex[vertex_region]
    return np.linalg.norm(p - q, axis=1)


def distances_to_surface(points, vertices, faces, k=10):
    """ Distances from points to a triangle mesh, using the triangles around the k nearest vertices. """
    vertex_faces = [[] for _ in range(len(vertices))]
    for face_idx, face in enumerate(faces):
        for v in face:
            vertex_faces[v].append(face_idx)
    table = np.full((len(vertices), max(map(len, vertex_faces))), -1)
    for v, face_list in enumerate(vertex_faces):
        table[v, :len(face_list)] = face_list
    _, nearest = cKDTree(vertices).query(points, k=k)
    dist = np.full(len(points), np.inf)
    for j in range(k):
        for column in range(table.shape[1]):
            face_idcs = table[nearest[:, j], column]
            valid = np.where(face_idcs >= 0)[0]
            tri = faces[face_idcs[valid]]
            d = point_triangle_distances(points[valid], vertices[tri[:, 0]], vertices[tri[:, 1]], vertices[tri[:, 2]])
            dist[valid] = np.minimum(dist[valid], d)
    return dist


def load_data(fname):
    return np.asarray(nib.load(fname).dataobj)


def atlas_areas(label_fname):
    """ Area name (without hemisphere prefix and _ROI) of each vertex of a native surface atlas label file. """
    img = nib.load(label_fname)
    names = img.labeltable.get_labels_as_dict()
    return np.array([names.get(int(key), '???').split('_', 1)[-1].removesuffix('_ROI')
                     for key in img.darrays[0].data])


subjects = sorted(os.path.basename(d) for d in glob.glob(os.path.join(run_a, 'freesurfer', 'sub-*')))
print(f'run a: {run_a}\nrun b: {run_b}\n')

# 1. brain masks
print('1. brain masks (FreeSurfer input)')
differing_subjects = []
for subject in subjects:
    mask_a = load_data(os.path.join(run_a, 'freesurfer', subject, 'mri', 'brainmask_mask.mgz')) > 0
    mask_b = load_data(os.path.join(run_b, 'freesurfer', subject, 'mri', 'brainmask_mask.mgz')) > 0
    n_diff = int((mask_a != mask_b).sum())
    print(f'   {subject}: {mask_a.sum():8d} mask voxels, {n_diff} differing')
    if n_diff:
        differing_subjects.append(subject)
print(f'   {len(differing_subjects)} of {len(subjects)} subjects differ\n')

# 2. surfaces
print(f'2. surfaces: distance to the other run\'s surface [mm] (subjects with differing surfaces); '
      f'shifts > {large_shift} mm: fraction at the medial wall, number in the ROI atlas region')
surface_subjects = []
for subject in subjects:
    for hemi, h in [('lh', 'L'), ('rh', 'R')]:
        areas = atlas_areas(os.path.join(run_a, 'ref-anat', subject, f'{subject}.glasser.{h}.native.label.gii'))
        for surf in ['white', 'pial']:
            va, fa = fs.read_geometry(os.path.join(run_a, 'freesurfer', subject, 'surf', f'{hemi}.{surf}'))
            vb, fb = fs.read_geometry(os.path.join(run_b, 'freesurfer', subject, 'surf', f'{hemi}.{surf}'))
            if va.shape == vb.shape and np.array_equal(va, vb) and np.array_equal(fa, fb):
                continue
            if subject not in surface_subjects:
                surface_subjects.append(subject)
            d_a = distances_to_surface(va, vb, fb)  # vertices of run a
            d = np.concatenate([d_a, distances_to_surface(vb, va, fa)])
            large = d_a > large_shift
            print(f'   {subject} {hemi}.{surf:5s}: median {np.median(d):.3f}, mean {d.mean():.3f}, '
                  f'99th percentile {np.percentile(d, 99):.3f}, > {large_shift} mm {100 * (d > large_shift).mean():.2f}% '
                  f'| at medial wall {100 * (areas[large] == "???").mean():.0f}%, '
                  f'in ROI atlas region {int(np.isin(areas[large], roi_atlas_areas).sum())}')
print(f'   {len(surface_subjects)} of {len(subjects)} subjects have differing surfaces\n')

# 3. atlas labels and 4. main ROIs
print('3. atlas labels in the ROI atlas region (left hemisphere) and 4. main ROIs')
for subject in subjects:
    va, _ = fs.read_geometry(os.path.join(run_a, 'freesurfer', subject, 'surf', 'lh.white'))
    vb, _ = fs.read_geometry(os.path.join(run_b, 'freesurfer', subject, 'surf', 'lh.white'))
    areas_a = atlas_areas(os.path.join(run_a, 'ref-anat', subject, f'{subject}.glasser.L.native.label.gii'))
    areas_b = atlas_areas(os.path.join(run_b, 'ref-anat', subject, f'{subject}.glasser.L.native.label.gii'))
    _, nearest = cKDTree(vb).query(va)
    changed = areas_a != areas_b[nearest]
    in_region = np.isin(areas_a, roi_atlas_areas)
    in_require = areas_a == roi_require_area

    main_area = utils.read_params(os.path.join(run_a, 'roi', subject, 'roi_params.json'))['main_area']
    roi_name = f'roi_trialavg_bold_combined_fstat_dlPFC_require_{roi_require_area}_A{main_area}.nii'
    roi_a = load_data(os.path.join(run_a, 'roi', subject, roi_name)) > 0
    roi_b = load_data(os.path.join(run_b, 'roi', subject, roi_name)) > 0
    dice = 2 * (roi_a & roi_b).sum() / (roi_a.sum() + roi_b.sum())
    print(f'   {subject}: label changed for {100 * changed[in_region].mean():4.1f}% of the ROI atlas region '
          f'({100 * changed[in_require].mean():4.1f}% of {roi_require_area}) | main ROI (A{main_area}): '
          f'{roi_a.sum()} vs {roi_b.sum()} voxels, Dice {dice:.2f}')
