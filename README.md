# Code for pfc layer working memory replication study 

## Organization

Filenames containing the code for all processing steps follow this convention:
`nn_(s|g)l_processing-step-description.(py|sh)`
where `nn` is the processing step, `sl` signifies a subject level process and `gl` a group level process.

The scripts are short, high-level descriptions of the analysis of this study. Each step defines the parameters it decides at its top and saves them together with its outputs (`*_params.json`, `selected_clusters.json` or the `.pkl` result files), from where subsequent steps read them. Study-specific helper functions are in `utils.py`, generic methods in the included submodules `fmri_analysis` and `vdfs`.

## Requirements

The scripts assume a software environment according to the apptainer recipe `container/pfc-layer-wm-replication.def` (see `container/README.md`) and a conda environment according to `environment.yml`, and the data set in BIDS format. The conda environment (exact linux-64 package builds) can be created with

```bash
conda env create -p <study_data_dir>/env -f environment.yml
```

which is where `pipeline.sh` expects it by default (`CONDA_ENV`).

## Running the pipeline

The entire analysis can be run efficiently, respecting dependencies between steps, by using the top-level script `pipeline.sh`, which uses pipeline running tools from `fmri_analysis`. To run `pipeline.sh`, clone the repository with its submodules (`git clone --recursive …`), then edit `pipeline.sh` (the values in it are the author's paths), setting:

* the location of the BIDS data set (`STUDY_DATA_DIR`), including the derivative datasets `derivatives/brainmasks` and `derivatives/manual-layer-rois` distributed with it
* the location of the apptainer container image (`APPTAINER_IMAGE`)
* the location of the conda environment (`CONDA_ENV`)
* optionally: parameters for running the pipeline on SLURM, GNU parallel or sequentially

The data set and the conda environment must be accessible inside the container: Apptainer mounts the home directory by default, other locations must be bound (e.g. `export APPTAINER_BINDPATH="/data:/data"` in `pipeline.sh`). FreeSurfer requires a license file (free, from the FreeSurfer website) at `~/license.txt`.

To rerun only part of the pipeline, comment out the steps that should not run in `pipeline.sh`.

### Brain masks

Step 01 reconstructs the cortical surfaces with FreeSurfer, using a brain mask from the CAT12 segmentation instead of FreeSurfer's skull stripping. The CAT12 segmentation is not deterministic: its multithreaded denoising (SANLM) sums contributions of its threads in a varying order, which can change single voxels of the mask between runs and thereby the surfaces of the subject and all subsequent results. To make the pipeline reproducible, the brain masks used for the results are distributed with the data set as the BIDS derivative dataset `derivatives/brainmasks`: one mask per subject, `sub-XX/anat/sub-XX_desc-brain_mask.nii.gz`, in the voxel space of the UNIT1 image of the subject.

Step 01 uses these masks by default (`brainmask_source=published` in `01_sl_mp2rage_recon-all.sh`); with `brainmask_source=cat12` it computes them with CAT12 instead. The masks of a run are exported with `export_brainmasks_to_bids.py <study_data_dir> <study_data_dir>/derivatives/freesurfer`. `compare_runs.py <derivatives_dir_a> <derivatives_dir_b>` quantifies the differences between two runs caused by differing brain masks (mask voxels, surface shifts, atlas labels and overlap of the main ROIs).

### Manual layer ROIs

Step 13 additionally analyses manually drawn layer ROIs. They are distributed with the data set as the BIDS derivative dataset `derivatives/manual-layer-rois`: one discrete segmentation per subject, `sub-XX/anat/sub-XX_space-func_desc-dlPFClayers_dseg.nii.gz`, in the voxel space of the functional images of the subject, with the label values (1 = superficial, 2 = deep) defined in `desc-dlPFClayers_dseg.tsv`.

To draw new layer ROIs, step 12 exports the images needed for drawing to `derivatives/export_for_manual_roi/sub-XX/`, including an empty `sub-XX_roi_layers_manual.nii`. Manually draw the superficial and deep layer ROIs (values 1 and 2, respectively) on the VASO T1w image, following the guidelines of Finn et al. (2019):

1. draw layers as a connected collection of voxels without holes;
2. position the superficial layer such that there is no partial voluming with the cerebrospinal fluid;
3. position the deeper layer such that there is no partial voluming with white matter;
4. erode the superficial and deeper layers until there is no residual overlap of superficial and deeper layers;
5. keep the thickness of the superficial and deeper layers similar along the cortical ribbon;
6. choose the thickness of the superficial and deeper layers such that they fill as much of the cortex as possible without violating the guidelines above.

Save the drawn layer ROIs as `derivatives/roi/sub-XX/roi_layers_manual.nii` and export them to `derivatives/manual-layer-rois` with `export_manual_layer_rois_to_bids.py <study_data_dir>` before running step 13.

## Outputs

Result values are written to text files in `derivatives/results/`, figures to `derivatives/figures/`.

![Processing pipeline](pipeline.svg "Visualization of the entire processing pipeline")
