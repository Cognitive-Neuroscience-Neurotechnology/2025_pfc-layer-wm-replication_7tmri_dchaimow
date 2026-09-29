#!/bin/bash
# =============================================================================
# Configuration
# =============================================================================

# Study configuration
export STUDY_DATA_DIR="/ptmp/dchaimow/data/finn-et-al-2019_replication"
#export APPTAINER_IMAGE="/home/rglz/containers/gfae_20241105T141406Z_md5644663536cb3beb4d1647aaeee887320_git1f2ca16f8fbe6feedc606b0cfafd467b9b8a550c.sif"
export APPTAINER_IMAGE="/ptmp/dchaimow/containers/pfc-layer-wm-replication_container/pfc-layer-wm-replication_20260926T235011Z_md5a9f39131097e5f87a95fdf882425fe77.sif"
export CONDA_ENV="$STUDY_DATA_DIR/env"

# Paths (relative to script directory)
export LIBRARY_DIR="$(realpath "$(dirname "${BASH_SOURCE[0]}")/fmri_analysis/library")"
# Subject IDs (exported as space-separated string, used by run.sh and by utils.subjects())
export SUBJECTS_LIST="sub-01 sub-02 sub-03 sub-04 sub-05 sub-06 sub-07 sub-08 sub-09 sub-10 sub-11 sub-12 sub-13 sub-14 sub-15 sub-16 sub-17 sub-18 sub-19 sub-20 sub-21"

# Set run mode
# either: slurm, sequential or parallel (GNU parallel), will try to auto-detect if not set
export RUN_MODE=slurm

# Additional configuration options for apptainer or slurm (uncomment and modify as needed):
# export SLURM_OPTS="--cpus-per-task=4 --time=24:00:00"  # Example SLURM options
# export APPTAINER_EXTRA_ARGS="--nv"  # Set to "--nv" for GPU support, or "" for CPU-only
# export APPTAINER_BINDPATH="/ptmp:/ptmp,/scratch:/scratch"  # Add any additional bind paths here

# path for pipeline running and visualization tools
export PATH=$LIBRARY_DIR:$PATH

# to update the pipeline visualization pipeline.svg (shown in the README), run with all steps active:
# visualize_pipeline.sh pipeline.sh

# =============================================================================
# Specify Pipeline
# =============================================================================

# JOBNN=$(run.sh <script_to_run> <cpus_per_task> <max_time> [dependency_job_ids])
# - subject-level steps (_sl_) run as one job per subject, group-level steps (_gl_) as one job
# - to rerun part of the pipeline, comment out the steps that should not run;
#   dependencies on commented-out steps are dropped automatically
# - 00-02 (anatomical processing, ~15 h) are commented out, as they only need to run once
# - 01 uses the published brain masks (BIDS derivative dataset derivatives/brainmasks) by default (see README)
# - 13 needs the manually drawn layer ROIs (BIDS derivative dataset derivatives/manual-layer-rois),
#   drawn on the images exported by 12 (see README)
# - 22 only uses the raw BIDS behavioral data and has no dependencies
#JOB00=$(run.sh 00_gl_prepare_resources.sh 1 00:05:00)
#JOB01=$(run.sh 01_sl_mp2rage_recon-all.sh   8 12:00:00)
#JOB02=$(run.sh 02_sl_ciftify.sh 8 24:00:00 $JOB00:$JOB01)
JOB03=$(run.sh 03_sl_preprocess_vaso.sh 8 00:30:00)
JOB04=$(run.sh 04_sl_register.py 4 00:40:00 $JOB01:$JOB03)
JOB05=$(run.sh 05_sl_generate_ref-anat.py 8 01:00:00 $JOB00:$JOB01:$JOB02:$JOB04)
JOB06=$(run.sh 06_sl_trialavg.py 1 00:05:00 $JOB03)
JOB07=$(run.sh 07_gl_group-clusters.py 32 00:05:00 $JOB00:$JOB02:$JOB04:$JOB06)
JOB08=$(run.sh 08_sl_generate_rois.py 8 01:00:00 $JOB02:$JOB04:$JOB05:$JOB06:$JOB07)
JOB09=$(run.sh 09_gl_roi-overlap.py 32 00:10:00 $JOB02:$JOB04:$JOB08)
JOB10=$(run.sh 10_sl_roi-generation_visualization.sh 1 00:05:00 $JOB00:$JOB02:$JOB04:$JOB05:$JOB06:$JOB08)
JOB11=$(run.sh 11_sl_seg_reg_visualizations.sh 1 00:05:00 $JOB01:$JOB03:$JOB04:$JOB05:$JOB08)
JOB12=$(run.sh 12_sl_export_for_manual_roi_drawing.sh 1 00:05:00 $JOB01:$JOB03:$JOB04:$JOB06:$JOB08)
JOB13=$(run.sh 13_gl_sample_data.py 32 00:10:00 $JOB05:$JOB06:$JOB08)
JOB14=$(run.sh 14_gl_statistical_analysis.py 32 00:20:00 $JOB13)
JOB15=$(run.sh 15_gl_result_values.py 1 00:05:00 $JOB13:$JOB14)
JOB16=$(run.sh 16_gl_figure_snr.py 1 00:05:00 $JOB03:$JOB08)
JOB17=$(run.sh 17_gl_figure_roi-generation.py 1 00:05:00 $JOB10)
JOB18=$(run.sh 18_gl_figure_seg-reg.py 1 00:05:00 $JOB11)
JOB19=$(run.sh 19_gl_figure_main-results.py 1 00:05:00 $JOB13:$JOB14)
JOB20=$(run.sh 20_gl_figure_group-clusters.py 1 00:05:00 $JOB00:$JOB02:$JOB07)
JOB21=$(run.sh 21_gl_figure_roi-size-dependence.py 1 00:05:00 $JOB13:$JOB14)
JOB22=$(run.sh 22_gl_behavior_analysis.py 4 00:10:00)
JOB23=$(run.sh 23_gl_figure_roi-size-visualization.py 1 00:05:00 $JOB10)

# =============================================================================
# Notes
# =============================================================================

# approximate running times per job (fastest - slowest subject, subject numbers in parentheses);
# mp2rage_recon-all (with the published brain masks), ciftify and total from the run of 2026-09-28, the others
# from an earlier run

# mp2rage_recon-all     03:26:00 (18)   -   04:04:00 (15)
# ciftify               04:30:11 (21)   -   10:54:41 (1)
# preprocess_vaso       00:05:18 (18)   -   00:13:53 (6)
# register              00:01:43 (14)   -   00:03:03 (2, 12)
# generate_ref-anat     00:07:25 (20)   -   00:10:00 (8)
# trialavg              00:01:33 (6)    -   00:02:55 (7)
# group-clusters                            00:01:43
# generate_rois         00:13:58 (18)   -   00:19:38 (12)
# sample_data                               00:03:12
# statistical_analysis                      00:04:48
# total (critical path, preprocess_vaso and trialavg run concurrently with mp2rage_recon-all): 15:24:35
