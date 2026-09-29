#!/usr/bin/env python3
"""
Generate the figure for the main results (VASO and BOLD versions).
"""
import sys
import os

import pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.colors import ListedColormap
import seaborn as sns
from utils import create_shared_subplots
from utils import seed_for
from utils import setup_figure_style
from utils import save_figure

study_data_dir = sys.argv[1]

figure_dir = os.path.join(study_data_dir,'derivatives','figures')
analysis_dir = os.path.join(study_data_dir, 'derivatives', 'analysis')
sample_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')

os.makedirs(figure_dir, exist_ok=True)

# parameters:
layers = ["superficial", "deep"]
events = {"Stim": 0, "Cue": 4, "Probe": 14}
hrf_delay = 6

# plot parameters and initalization
setup_figure_style()

# set color palette
palette = {"alpha": "tab:blue",
           "rem": "tab:green",
           "act": "tab:red",
           "non-act": "tab:orange",
           "alpha - rem": "#A74F9C",
           "act - non-act": "#199396"}

# load data
with open(os.path.join(analysis_dir, 'results.pkl'), 'rb') as f:
    saved_results = pickle.load(f)    
results_all_areas = saved_results['results_all_areas']
results_depth_gap = saved_results['results_depth_gap']
results_no_slab_boundary = saved_results['results_no_slab_boundary']
results_manual_roi = saved_results['results_manual_roi']
results_group_clusters = saved_results['results_group_clusters']
delay_tps = saved_results['periods']['delay']
response_tps = saved_results['periods']['response']
finn_np2 = [saved_results['finn_np2'][period] for period in ['delay', 'response']]
period_contrasts = saved_results['period_contrasts']

# load the sampled data
with open(os.path.join(sample_dir, 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
data_all_areas = sampled_data['data_all_areas']
areas = sampled_data['areas']
data_depth_gap = sampled_data['data_depth_gap']
data_no_slab_boundary = sampled_data['data_no_slab_boundary']
data_manual_roi = sampled_data['data_manual_roi']
data_group_clusters = sampled_data['data_group_clusters']
cluster_idcs = sampled_data['cluster_idcs']
main_area = sampled_data['main_area']
TR = sampled_data['tr']
# plot conditions of each run type and the contrasts in separate columns
condition_pairs = list(sampled_data['run_conditions'].values()) + [list(sampled_data['condition_contrasts'])]

def generate_timecourse_panel(gs, data, method, plot_key):

    axs = create_shared_subplots(gs, row_range=[0,1], col_range=[0,1,2])
    
    for column, condition_pair in enumerate(condition_pairs):
        for row, layer in enumerate(layers):         
            ax = axs[row, column]
            
            # plot time course
            g = sns.lineplot(x="timepoint", y="signal", hue="condition",
                             errorbar=("ci", 95),
                             n_boot=1000,
                             seed=seed_for(f"{plot_key}:timecourse:{row}:{column}"),
                             hue_order=condition_pair, palette=palette, ax=ax,
                             legend="brief" if row == 0 else False,
                             data=data.query("condition in @condition_pair and layer == @layer"))

            # mark delay and response analysis time points
            for line in g.get_lines():
                xdata = np.asarray(line.get_xdata())
                ydata = np.asarray(line.get_ydata())
                color = line.get_color()
                if len(xdata) == 9:
                    ax.scatter(xdata[delay_tps],ydata[delay_tps],facecolors='white', edgecolors=color,s=12,zorder=100)
                    ax.scatter(xdata[response_tps],ydata[response_tps],color=color,s=12,zorder=100)
            
            # add background shading of delay and probe periods and horizontal zero line
            ax.axhline(0, linewidth=0.5, color="gray") 
            ax.axvspan(events["Cue"], events["Probe"] + hrf_delay, alpha=0.2, color="gray")
            ax.axvline(events["Probe"], color="gray", linewidth=0.5, zorder=0)

            # set axis limits and labels
            ax.set_xlim(np.min(data["timepoint"]), np.max(data["timepoint"]))
            ax.set_xlabel("Trial time [s]")
            if method == "bold":
                ax.set_ylabel("BOLD signal (% change)")
            elif method == "vaso":
                ax.set_ylabel("VASO signal (neg. % change)")

            if row == 0:
                # remove legend title (only relevant for top row)
                handles, labels = ax.get_legend_handles_labels()
                ax.legend(handles=handles[:], labels=labels[:])

                # add delay and response period annotations to top
                trans = ax.get_xaxis_transform()
                ax.annotate("Delay", xy=((events["Cue"] + events["Probe"]) / 2, 1.12),
                            xycoords=trans, ha="center", va="top")
                ax.plot([events["Cue"], events["Probe"] - 0.2], [1.05, 1.05], 
                        color="gray", transform=trans, clip_on=False)

                ax.annotate("Resp.", xy=((events["Probe"] + events["Probe"] + hrf_delay) / 2, 1.12),
                             xycoords=trans,  ha="center", va="top")                
                ax.plot([events["Probe"] + 0.2, events["Probe"] + hrf_delay], [1.05, 1.05],
                        color="gray", transform=trans, clip_on=False)            

            elif row == 1:
                # add event anotations to bottom
                trans = ax.get_xaxis_transform()
                for key, value in events.items():
                    ax.annotate(key, xy=(value, 0), xycoords=trans, ha="center",  va="bottom")
            
            if column == 0:
                # layer labels
                ax.annotate(layer, xy=(0, 0.5),
                            xytext=(-ax.yaxis.labelpad - 5, 0),
                            xycoords=ax.yaxis.label,
                            textcoords="offset points",
                            size="large", ha="right", va="center",rotation=90)

    axs[0,0].text(-0.35,1.1, 'A', transform=axs[0,0].transAxes,size=10, weight='bold')

def generate_period_contrasts_panel(gs, results, method, plot_key):

    axs = create_shared_subplots(gs, row_range=[3], col_range=[0,1])
    
    for column, period in enumerate(["delay", "response"]):
        data_contrast_plot = results['contrast_period_average_data'].loc[
            (results['contrast_period_average_data']['period'] == period)]
        ax = axs[0,column]
        with plt.rc_context({'lines.linewidth': 1}):
            g = sns.pointplot(x="layer", y="signal", hue="condition", marker='none',
                              errorbar=("ci", 95),
                              n_boot=1000,
                              seed=seed_for(f"{plot_key}:contrast:{period}"),
                              ax=ax, palette=palette, data=data_contrast_plot,
                              err_kws={'linewidth': 0.5}, capsize=0.1,
                              order=['superficial','deep'])
        # add markers, according to period
        for line in [g.get_lines()[idx] for idx in [0,3]]:       
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            color = line.get_color()
            if column == 0:
                ax.scatter(xdata,ydata,facecolors='white', edgecolors=color,s=12,zorder=100)
                ax.legend().remove()
            else:
                ax.scatter(xdata,ydata,color=color,s=12,zorder=100)

        # add annotations (legend, title, p-value)
        ax.legend(title=None, loc="upper right", frameon=False)
        ax.set_title(f"{period.capitalize()} period", fontsize=7)
        if results["anova2"][period]["p-unc"][2] < 0.001:
            ax.text(0.5,0.1,'***', transform=ax.transAxes, ha='center', fontsize=7)
        elif results["anova2"][period]["p-unc"][2] < 0.01:
            ax.text(0.5,0.1,'**', transform=ax.transAxes, ha='center', fontsize=7)
        elif results["anova2"][period]["p-unc"][2] < 0.05:
            ax.text(0.5,0.1,'*', transform=ax.transAxes, ha='center', fontsize=7)
        ax.axhline(0, linewidth=0.5, color="gray") 

        # set axis labels and ranges
        if method == "vaso":
            ax.axis([-0.5 , 1.5, -1, 1.5])
            ax.set_ylabel("VASO signal (neg. % change)")        
        else:
            ax.axis([-0.5 , 1.5, -1.5, 5])
            ax.set_ylabel("BOLD signal (% change)")
        ax.xaxis.label.set_visible(False)    

    axs[0,0].text(-0.35,1.1, 'B', transform=axs[0,0].transAxes,size=10, weight='bold')

def generate_bootstrap_panel(gs, results, method, plot_key):

    ax = gs.figure.add_subplot(gs[3, 2])

    previous_state = np.random.get_state()
    try:
        np.random.seed(seed_for(f"{plot_key}:jitter"))
        sns.stripplot(
            x="period",
            y="np2",
            ax=ax,
            data=results["np2_signed_combined_data"],
            orient="v",
            jitter=0.2,
            alpha=0.5,
            size=2,
            color="tab:blue",
            edgecolor="none",
        )
    finally:
        np.random.set_state(previous_state)

    # plot and compare effect sizes
    line_xlims = [[-0.2, 0.2], [0.8, 1.2]]
    for i in [0, 1]:
        if i == 1:
            l0 = ax.hlines(results['np2_signed_response_est'],
                           line_xlims[i][0] - 0.1, line_xlims[i][1] + 0.1)
        else:
            l0 = ax.hlines(results['np2_signed_delay_est'],
                           line_xlims[i][0] - 0.1, line_xlims[i][1] + 0.1)

        # compare to Finn et al. 2019 (if vaso)
        if method == "vaso":
            col = ax.collections[i]
            y = col.get_offsets()[:, 1]
            
            if finn_np2[i]>0:
                perc = np.percentile(y, [0, 95])
                perc95=perc[1]
                col.set_cmap(ListedColormap(["tab:blue", "gray"]))
            else:
                perc = np.percentile(-y, [0, 95])
                perc95=-perc[1]
                perc = -perc[-1::-1]
                col.set_cmap(ListedColormap(["gray", "tab:blue"]))
            col.set_array(np.digitize(y, perc))
            col.set_edgecolor("none")
            
            # plot Finn et al. 2019 effect
            l1 = ax.hlines(finn_np2[i], line_xlims[i][0] - 0.1, line_xlims[i][1] + 0.1,
                           colors="tab:red", linestyles="dashed")
            # plot our one-sided 95% bound in direction of Finn et al. 2019 effect
            l2 = ax.hlines(perc95, line_xlims[i][0] - 0.1, line_xlims[i][1] + 0.1, 
                           colors="tab:gray")

    if method == "vaso":
        ax.legend([l0, l2, l1],
                  ["Effect (this study)",
                   "95% bound",
                   "Finn et al. (2019)"],
                  loc="lower left")
    else:
        ax.legend([l0], ["Effect (this study)"], loc="lower left")


    ax.set_ylabel("deep>superficial     superficial>deep")
    ax.xaxis.label.set_visible(False)    
    ax.set_xticklabels([f"{period} period\n({period_contrasts[period]})"
                        for period in ["delay", "response"]])
    ax.set_yticks([-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1])
    ax.set_yticklabels(['1','','$η_p^2$','','0','','$η_p^2$','','1'])
    ax.text(-0.25,1.1, 'C', transform=ax.transAxes,size=10, weight='bold')
    ax.set_ylim(-1, 1)
    ax.set_xlim(-0.5, 1.5)

def generate_figure(results, data, variant, method):
    plot_key = f"figure19:{method}:{variant or 'main'}"
    data = data.copy()
    data["timepoint"] = data["timepoint"] * TR
   
    # initialize figure
    # 16.6 cm in inches is 6.54 inches
    fig = plt.figure(figsize=(18/2.54,16/2.54), dpi=300)
    gs = GridSpec(4, 3, figure=fig, 
                  height_ratios=[2,2,0.5,2], 
                  left=0, right=1, top=1, bottom=0,
                  wspace=0.02, hspace=0.02) 
    # generate panels 
    generate_timecourse_panel(gs, data, method, plot_key)
    generate_period_contrasts_panel(gs, results, method, plot_key)
    generate_bootstrap_panel(gs, results, method, plot_key)    

    # save figure
    if variant is None:
        variant = ''
    else:
        variant = f'_{variant}'
    save_figure(fig, figure_dir, f'figure_main-results{variant}')
    plt.close()

# main figure
generate_figure(results_all_areas['vaso'][np.where(areas == main_area)[0][0]], 
                data_all_areas['vaso'][np.where(areas == main_area)[0][0]], 
                variant=None, method='vaso')
# bold figure
generate_figure(results_all_areas['bold'][np.where(areas == main_area)[0][0]], 
                data_all_areas['bold'][np.where(areas == main_area)[0][0]], 
                variant='bold', method='bold')

# depth gap figure
generate_figure(results_depth_gap, data_depth_gap, variant='depth_gap', method='vaso')

# no slab boundary figure
generate_figure(results_no_slab_boundary, data_no_slab_boundary, variant='no_slab_boundary',
                 method='vaso')

# group clusters figure
for cluster_idx, results, data in zip(cluster_idcs, results_group_clusters, data_group_clusters):
    generate_figure(results, data,
                    variant=f'group_cluster_{cluster_idx}', method='vaso')

# manual roi figure
generate_figure(results_manual_roi, data_manual_roi, variant='manual_roi',
                 method='vaso')
