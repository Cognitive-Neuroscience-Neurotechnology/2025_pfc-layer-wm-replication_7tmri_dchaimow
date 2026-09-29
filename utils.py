#!/usr/bin/env python3
"""
Study specific analysis module for Finn et al. 2019 replication study.
"""

import os
import json
import random
import hashlib

import numpy as np
import pandas as pd
import nibabel as nib
import pingouin as pg

from fmri_analysis import layer_analysis as analysis

# TODO
# [ ] see if we can separate the response analysis
# [ ] consider adding roi volume analysis to roi generation?


# 0. pipeline helpers
def subjects():
    """ Subjects to process, as exported by pipeline.sh in SUBJECTS_LIST. """
    try:
        return os.environ["SUBJECTS_LIST"].split()
    except KeyError:
        raise RuntimeError("SUBJECTS_LIST is not set (it is exported by pipeline.sh)") from None

def max_cpus():
    """ Number of CPUs available to a processing step (OMP_NUM_THREADS is set by run.sh). """
    return int(os.environ.get("OMP_NUM_THREADS", 1))

def write_params(fname, params):
    """ Saves the parameters of a processing step next to its outputs, for use by subsequent steps. """
    with open(fname, "w") as f:
        json.dump(params, f, indent=4)

def read_params(fname):
    """ Reads parameters saved by a processing step with write_params. """
    with open(fname, "r") as f:
        return json.load(f)

def read_subject_params(study_data_dir, step_dir, fname, subjects):
    """ Reads the parameters saved by a subject-level step (in derivatives/<step_dir>/<subject>/<fname>)
    and checks that they are the same for all subjects. """
    params = [read_params(os.path.join(study_data_dir, "derivatives", step_dir, subject, fname))
              for subject in subjects]
    for subject, subject_params in zip(subjects, params):
        if subject_params != params[0]:
            raise ValueError(f"{fname} of {subject} differs from that of {subjects[0]}")
    return params[0]


# 1. sampling data
def sample_data(study_data_dir, subjects, roi_base_fname, run_conditions, condition_contrasts,
                method='vaso', depth_gap=0, roi_dir=os.path.join("derivatives", "roi", "{subject}"),
                layer_labels=None):
    """ Samples trial averaged data of all conditions (run_conditions: {run_type: [conditions]})
    from an ROI according to cortical layer, combines the data from all subjects into a single
    dataframe and adds the condition contrasts ({contrast: [condition1, condition2]}).
    The ROI of each subject is <study_data_dir>/<roi_dir>/<roi_base_fname>, where both may contain {subject}.
    Layers are defined by cortical depth, or, if layer_labels ({layer: label value}) is given, by the
    label values of the ROI file (layer ROI).
    The sampling is done using layer_analysis.sample_temporal_layer_data_to_df.
    """
    if layer_labels is None:
        layers_dict = {"superficial": [0.5 + depth_gap/2, 1], "deep": [0, 0.5 - depth_gap/2]}
    else:
        layers_dict = {layer: [value - 0.5, value + 0.5] for layer, value in layer_labels.items()}

    data_base_fnames = {condition: f"trialavg_{method}_{run_type}_response_condition_{condition}_prcchg.nii"
                        for run_type in run_conditions.keys()
                        for condition in run_conditions[run_type]}

    df = pd.DataFrame()
    for subject in subjects:
        trialavg_dir = os.path.join(study_data_dir, "derivatives", "trialavg", subject)
        refanat_dir = os.path.join(study_data_dir, "derivatives", "ref-anat", subject)

        roi_fname = os.path.join(study_data_dir, roi_dir.format(subject=subject),
                                 roi_base_fname.format(subject=subject))
        if layer_labels is not None:
            depths_fname = roi_fname
        else:
            depths_fname = os.path.join(refanat_dir, 'vdfs_depths_equivol.nii')

        data_fnames = {condition: os.path.join(trialavg_dir, data_base_fnames[condition])
                       for condition in data_base_fnames.keys()}

        df_subject = analysis.sample_temporal_layer_data_to_df(data_fnames, roi_fname, depths_fname,
                                                               layers_dict, tentzero=True)
        df_subject['subject'] = subject
        df = pd.concat([df, df_subject], ignore_index=True)

    # also calculate condition contrasts and add them to the data frame
    df_contrasts = analysis.calculate_df_condition_contrasts(df, condition_contrasts)
    df = pd.concat([df, df_contrasts], ignore_index=True)
    return df

def estimate_roi_volume(study_data_dir, subjects, roi_fname):
    """ Estimates the ROI volumes for all subjects in mm^3 """
    roi_volume = np.zeros(len(subjects))
    for idx, subject in enumerate(subjects):
        fname = os.path.join(study_data_dir, 'derivatives', 'roi', subject, roi_fname)
        roi = nib.load(fname)
        roi_bin = roi.get_fdata()>0
        roi_volume[idx] = roi_bin.sum() * np.prod(roi.header.get_zooms())
    return roi_volume


# 2. statistical analysis
MASTER_SEED = 1234

def seed_for(task):
    """Stable 32-bit seed derived from a descriptive task name."""
    key = f"{MASTER_SEED}:{task}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big")

def calculate_layerdiff_sign(data, condition):
    m = data.groupby(['condition','layer'])['signal'].mean()
    d = m[condition]['superficial'] - m[condition]['deep']
    return np.sign(d)

def bootstrap_sample_data(N, data_delay, data_response, rng):
    """ Draws N subjects with replacement and returns their delay and response period data,
    with the subjects renamed by their draw index (so that repeatedly drawn subjects count separately). """
    subjects = data_delay["subject"].unique()
    drawn_subjects = [rng.choice(subjects) for _ in range(N)]

    def resample(data):
        data_by_subject = {subject: data[data["subject"] == subject] for subject in subjects}
        return pd.concat([data_by_subject[subject].assign(subject=bootstrap_idx)
                          for bootstrap_idx, subject in enumerate(drawn_subjects)], ignore_index=True)

    return resample(data_delay), resample(data_response)


def bootstrap_analysis(anova_delay_data, anova_response_data, period_contrasts, seed):
    rng = random.Random(seed)
    n_trials = 1000
    N = anova_delay_data["subject"].nunique()  # resample as many subjects as in the data
    np2_delay = np.zeros(n_trials)
    np2_response = np.zeros(n_trials)

    for i_trial in range(n_trials):
        data_delay_bootstrap, data_response_bootstrap = bootstrap_sample_data(
            N, anova_delay_data, anova_response_data, rng=rng,
        )
        anova_delay_result = pg.rm_anova(
            data=data_delay_bootstrap,
            dv="signal",
            subject="subject",
            within=["layer", "condition"],
            effsize="np2")

        np2_delay[i_trial] = anova_delay_result['np2'][2] * calculate_layerdiff_sign(data_delay_bootstrap, period_contrasts['delay'])

        anova_response_result = pg.rm_anova(
            data=data_response_bootstrap,
            dv="signal",
            subject="subject",
            within=["layer", "condition"],
            effsize="np2")
        np2_response[i_trial] = anova_response_result['np2'][2] * calculate_layerdiff_sign(data_response_bootstrap, period_contrasts['response'])

    np2_combined_data = pd.concat(
        [
            pd.DataFrame({"np2": np2_delay, "period": "delay"}),
            pd.DataFrame({"np2": np2_response, "period": "response"}),
        ]
    )
    return np2_combined_data

def analyze_sampled_data(data, run_conditions, condition_contrasts, periods, period_contrasts, seed):
    """ Runs the statistical analysis of sampled data: period x condition ANOVAs (per run type and layer),
    layer x contrast ANOVAs (per period, with periods: {period: [time points]}) and a bootstrap
    of the layer x contrast interaction effect size, signed by the layer difference of the contrast
    tested in each period (period_contrasts: {period: contrast}).
    """
    results_anova1 = dict() # period x condition ANOVA (for each layer and run type)
    results_anova2 = dict() # contrast ANOVA (for each period)
    anova2_data = dict() # contrast ANOVA data (for the bootstrap analysis)
    period_average_data = analysis.calculate_df_period_averages(data, periods)
    for run_type in run_conditions.keys():
        conditions = run_conditions[run_type]
        for layer in ['superficial', 'deep']:
            anova_data = period_average_data.loc[
                (period_average_data["layer"] == layer) &
                (period_average_data["condition"].isin(conditions))]
            results_anova1[run_type, layer] = pg.rm_anova(
                            data=anova_data,
                            dv="signal",
                            subject="subject",
                            within=["period", "condition"],
                            effsize="np2")
    ### contrast anova
    contrast_period_average_data = analysis.calculate_df_condition_contrasts(period_average_data,
                                                                             condition_contrasts)
    for period in ['delay','response']:
        anova_data = contrast_period_average_data.loc[
                    (contrast_period_average_data["period"].isin([period]))]
        anova2_data[period] = anova_data
        results_anova2[period] = pg.rm_anova(
                    data=anova_data,
                    dv="signal",
                    subject="subject",
                    within=["layer", "condition"],
                    effsize="np2")

    ## bootstrap analysis
    np2_signed_combined_data = \
        bootstrap_analysis(anova2_data['delay'],
                            anova2_data['response'], period_contrasts, seed=seed)
    np2_signed_delay_est = results_anova2['delay']["np2"][2] * \
        calculate_layerdiff_sign(anova2_data['delay'], period_contrasts['delay'])
    np2_signed_response_est = results_anova2['response']["np2"][2] * \
        calculate_layerdiff_sign(anova2_data['response'], period_contrasts['response'])

    results = {'anova1': results_anova1, 'anova2': results_anova2,
                'np2_signed_combined_data': np2_signed_combined_data,
                'np2_signed_delay_est': np2_signed_delay_est,
                'np2_signed_response_est': np2_signed_response_est,
                'contrast_period_average_data': contrast_period_average_data,
                'period_average_data': period_average_data}
    return results


# 3. figures
def setup_figure_style():
    """ Sets the figure style of the study (stylesheet.mplstyle) and uses Helvetica if it is available.
    Helvetica font files can be provided in a fonts/ directory next to the pipeline scripts. """
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    code_dir = os.path.dirname(os.path.abspath(__file__))
    plt.style.use(os.path.join(code_dir, "stylesheet.mplstyle"))
    for font_file in font_manager.findSystemFonts(fontpaths=[os.path.join(code_dir, "fonts")]):
        font_manager.fontManager.addfont(font_file)
    if "Helvetica" in [f.name for f in font_manager.fontManager.ttflist]:
        plt.rcParams["font.family"] = "Helvetica"


def save_figure(fig, figure_dir, name, dpi=600, svg=True):
    """ Saves a figure as png and (optionally) svg with the settings of the study.
    Clip path ids in the svg file are renumbered in order of appearance, as matplotlib derives them
    from positions whose last digits can vary between runs, to keep the svg files reproducible. """
    import re
    save_kwargs = dict(dpi=dpi, bbox_inches='tight', pad_inches=0.05)
    if svg:
        svg_fname = os.path.join(figure_dir, f'{name}.svg')
        fig.savefig(svg_fname, metadata={"Date": None}, **save_kwargs)
        with open(svg_fname, 'r') as f:
            content = f.read()
        clip_ids = {}
        content = re.sub(r'(?<=clipPath id=")p[0-9a-f]{10}(?=")|(?<=url\(#)p[0-9a-f]{10}(?=\))',
                         lambda m: clip_ids.setdefault(m.group(0), f'clip{len(clip_ids)}'), content)
        with open(svg_fname, 'w') as f:
            f.write(content)
    fig.savefig(os.path.join(figure_dir, f'{name}.png'), **save_kwargs)


def write_cluster_overview(clusters_fname, flat_surf_fname, atlas_fname, out_basename):
    """ Writes an overview of surface clusters (left hemisphere, fs_LR) for selecting clusters by hand:
    a flat map of all clusters labeled with their indices (<out_basename>.png) and a table of the size
    of each cluster and the atlas areas it overlaps most (<out_basename>.txt). """
    import matplotlib.pyplot as plt
    from fmri_analysis import surface_plotting as sp
    clusters = np.asarray(sp.load_surf_data(clusters_fname)).astype(int)
    cluster_idcs = [int(idx) for idx in np.unique(clusters) if idx != 0]

    fig, ax = plt.subplots(figsize=(12, 8))
    sp.plot_surf_clusters_left_hemi(clusters, sp.load_surface_gifti(flat_surf_fname), atlas_fname, ax=ax,
                                    label_dict={idx: str(idx) for idx in cluster_idcs}, label_fontsize=8)
    ax.set_title("Clusters with their indices")
    fig.savefig(f"{out_basename}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    atlas = nib.load(atlas_fname)
    atlas_labels = atlas.darrays[0].data
    area_names = atlas.labeltable.get_labels_as_dict()
    with open(f"{out_basename}.txt", "w") as f:
        print("cluster  vertices  atlas areas overlapped most (fraction of the cluster)", file=f)
        for idx in cluster_idcs:
            in_cluster = clusters == idx
            areas, counts = np.unique(atlas_labels[in_cluster], return_counts=True)
            top_areas = sorted(zip(counts, areas), reverse=True)[:4]
            print(f"{idx:7d}  {in_cluster.sum():8d}  " +
                  ", ".join(f"{area_names.get(int(area), '?')} {count/in_cluster.sum():.0%}"
                            for count, area in top_areas), file=f)


def select_clusters_by_atlas(clusters_fname, atlas_fname, cluster_areas, min_fraction=0.5, min_ratio=1.5):
    """ Selects surface clusters (left hemisphere, fs_LR) by the atlas areas they cover, independent of the
    cluster numbering: for each label in cluster_areas ({label: [area names without 'L_' and '_ROI']}), the
    cluster with the most vertices within these areas, among the clusters with at least min_fraction of
    their vertices within them. Fails if no cluster qualifies, if the second best cluster has more than
    1/min_ratio of the overlap of the best, or if two labels select the same cluster.
    Returns {cluster index: label}. """
    from fmri_analysis import surface_plotting as sp
    clusters = np.asarray(sp.load_surf_data(clusters_fname)).astype(int)
    cluster_idcs = [int(idx) for idx in np.unique(clusters) if idx != 0]
    atlas = nib.load(atlas_fname)
    atlas_labels = atlas.darrays[0].data
    area_keys = {name: key for key, name in atlas.labeltable.get_labels_as_dict().items()}

    selected = {}
    for label, areas in cluster_areas.items():
        in_areas = np.isin(atlas_labels, [area_keys[f"L_{area}_ROI"] for area in areas])
        candidates = []  # (overlap, cluster index)
        for idx in cluster_idcs:
            in_cluster = clusters == idx
            overlap = int((in_cluster & in_areas).sum())
            if overlap >= min_fraction * in_cluster.sum():
                candidates.append((overlap, idx))
        candidates.sort(reverse=True)
        if not candidates:
            raise ValueError(f"no cluster within {areas} for {label}")
        if len(candidates) > 1 and candidates[0][0] < min_ratio * candidates[1][0]:
            raise ValueError(f"clusters {candidates[0][1]} and {candidates[1][1]} both match {label} ({areas}), "
                             "select by hand")
        idx = candidates[0][1]
        if idx in selected:
            raise ValueError(f"cluster {idx} matches both {selected[idx]} and {label}")
        selected[idx] = label
    return selected


def create_shared_subplots(gs,row_range=None,col_range=None):
    """Create subplots with automatic sharing and label hiding."""

    if row_range is None:
        row_range = range(gs.nrows)
    if col_range is None:
        col_range = range(gs.ncols)
    nrows, ncols = len(row_range), len(col_range)

    axs = np.empty((nrows, ncols), dtype=object)
    # create rows in reverse order so that the last row is created first,
    # i (the enumeration index) should also be reversed
    for i_reverse, row in enumerate(row_range[::-1]):
        for j, col in enumerate(col_range):
            i = nrows - 1 - i_reverse
            share_kwargs = {}
            if i_reverse > 0:
                share_kwargs['sharex'] =  axs[i + 1, j]
            if j > 0:
                share_kwargs['sharey'] = axs[i, 0]
            axs[i, j] = gs.figure.add_subplot(gs[row, col], **share_kwargs)
            axs[i, j].yaxis.label.set_visible(j == 0)
            axs[i, j].xaxis.label.set_visible((i == nrows - 1))
            axs[i, j].tick_params(labelbottom=(i == nrows - 1), labelleft=(j == 0))

    return axs
