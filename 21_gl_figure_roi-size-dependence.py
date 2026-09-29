#!/usr/bin/env python3

"""
Generate the figure for the roi size dependence results.
"""
import sys
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from matplotlib.gridspec import GridSpec
from utils import create_shared_subplots
from utils import seed_for
from utils import setup_figure_style
from utils import save_figure


study_data_dir = sys.argv[1]

figure_dir = os.path.join(study_data_dir,'derivatives','figures')
analysis_dir = os.path.join(study_data_dir, 'derivatives', 'analysis')
sample_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')


os.makedirs(figure_dir, exist_ok=True)


# plot parameters and initalization
setup_figure_style()


# load data
with open(os.path.join(analysis_dir, 'results.pkl'), 'rb') as f:
    saved_results = pickle.load(f)    
results_all_areas = saved_results['results_all_areas']
finn_np2 = saved_results['finn_np2']

with open(os.path.join(sample_dir, 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
data_all_areas = sampled_data['data_all_areas']
volume_all_areas = sampled_data['volume_all_areas']
areas = sampled_data['areas']


# 16.6 cm in inches is 6.54 inches
fig = plt.figure(figsize=(18/2.54,9/2.54), dpi=300)        

gs = GridSpec(2, 5, figure=fig, 
              width_ratios=[1,1,0.2,1,1], 
              left=0, right=1, top=1, bottom=0,
              wspace=0.02, hspace=0.02) 

# A Actual roi size as a function of target roi size
ax = fig.add_subplot(gs[0,0])

ax.boxplot(volume_all_areas,
           flierprops={'marker': 'x', 'markersize': 2 })

# boxplot positions are 1-based
ax.set_xticks([5,10,15,20], areas[np.array([4,9,14,19])])
ax.set_xlabel(r'target surface area [$mm^2$]')
ax.set_ylabel(r'actual ROI volume [$mm^3$]')

ax.text(-0.2,1.1, 'A', transform=ax.transAxes, 
        size=10, weight='bold')

# B VASO interaction effect with bootstrapped one-sided 95% bounds towards the Finn et al. 2019 effect
# (as in figure 19)
axs = create_shared_subplots(gs, row_range=[1], col_range=[0,1])
for period, finn_et_al_effect, ax in zip(['delay', 'response'], [finn_np2['delay'], finn_np2['response']], [axs[0,0], axs[0,1]]):
    bootstrap_results = [
        results_all_areas['vaso'][idx]['np2_signed_combined_data'][
            results_all_areas['vaso'][idx]['np2_signed_combined_data']['period']==period]['np2'] 
            for idx in range(len(areas))]

    # one-sided 95% bound in the direction of the Finn et al. 2019 effect
    if finn_et_al_effect > 0:
        np2_signed_bound = np.array([np.percentile(b, 95) for b in bootstrap_results])
    else:
        np2_signed_bound = np.array([-np.percentile(-b, 95) for b in bootstrap_results])
    np2_signed_values = np.array([results_all_areas['vaso'][idx][f'np2_signed_{period}_est']
                              for idx in range(len(areas))])
    p_values = np.array([results_all_areas['vaso'][idx]['anova2'][period]['p-unc'][2] 
                         for idx in range(len(areas))])

    # plot the point estimate and the one-sided 95% bound as lines
    l_effect, = ax.plot(areas, np2_signed_values, '-', color='tab:blue')
    l_bound, = ax.plot(areas, np2_signed_bound, '-', color='tab:gray')
    # shade the range from the bound away from the Finn et al. 2019 effect
    if finn_et_al_effect > 0:
        ax.fill_between(areas, -1, np2_signed_bound, color='tab:blue', alpha=0.12, lw=0, zorder=0)
    else:
        ax.fill_between(areas, np2_signed_bound, 1, color='tab:blue', alpha=0.12, lw=0, zorder=0)

    # plot asterisks where the p-value is below 0.05 using the same color as the line
    l_p, = ax.plot(areas[p_values<0.05], np2_signed_values[p_values<0.05], '*', color='tab:blue')

    # add horizontal line at finn_et_al_effect    
    l_finn = ax.axhline(finn_et_al_effect, color='tab:red', linestyle='--')
    # add horizontal at 0 (in background)
    ax.axhline(0, color='k',lw=0.1, zorder=0)
    
    ax.set_xlim(areas[0],areas[-1])
    ax.set_xlabel(r'target surface area [$mm^2$]')
    # y-axis as in figure 19: effect sizes of both directions of the layer difference
    ax.set_ylim(-1, 1)
    ax.set_yticks([-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1])
    ax.set_yticklabels(['1','','$η_p^2$','','0','','$η_p^2$','','1'])
    ax.set_ylabel("deep>sup.   sup.>deep", fontsize=6)
    ax.set_title(f"{period.capitalize()} period", fontsize=7)

axs[0][1].legend([l_effect, l_bound, l_finn, l_p],
                 ["Effect (this study)", "95% bound", "Finn et al. (2019)", "p<0.05"],
                 frameon=False, loc='upper left')
axs[0][0].text(-0.2,1.1, 'B', transform=axs[0][0].transAxes,
               size=10, weight='bold')
        

# C VASO and BOLD response amplitudes
axs = create_shared_subplots(gs, row_range=[0,1], col_range=[3,4])

for modality, finn_et_al_modality_levels, modality_axs in zip(
     ['bold', 'vaso'], [[[3.72,1.25],[2.75,0.9]],[[1.75,0],[-0.25,1.25]]],axs):
    data = pd.concat([results['period_average_data'].assign(area=area)
                      for results, area in zip(results_all_areas[modality], areas)], ignore_index=True)

    for period, condition, finn_et_al_levels, ax in zip(
        ['delay','response'],['alpha','act'],finn_et_al_modality_levels, modality_axs):

        sns.lineplot(x='area',y='signal',hue='layer',
                     errorbar=("ci", 95),
                     n_boot=1000,
                     seed=seed_for(f"figure21:{modality}:{period}:{condition}"),
                     data=data.query(f"period=='{period}' and condition=='{condition}'"), 
                     hue_order=['superficial','deep'], ax=ax)
        ax.axhline(finn_et_al_levels[0],linestyle='--')
        ax.axhline(finn_et_al_levels[1],linestyle='--',c='orange')
        ax.legend(frameon=False)
        ax.set_xlim(areas[0],areas[-1])
        ax.set_xlabel('target surface area [$mm^2$]')
        if modality == 'vaso':
            ax.set_ylim(-1,4)
        else:
            ax.set_ylim(-0,10)
        ax.set_ylabel('signal change [%]')

axs[0][1].legend(frameon=False, loc='upper right')
axs[0][0].text(-0.2,1.1, 'C', transform=axs[0][0].transAxes, 
               size=10, weight='bold')

fig.text(0.775,0.97,'BOLD')
fig.text(0.775,0.47,'VASO')

sns.despine()

save_figure(fig, figure_dir, 'figure_roi-size-dependence')
