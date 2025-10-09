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
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib import font_manager
from utils import create_shared_subplots


study_data_dir = sys.argv[1]

figure_dir = os.path.join(study_data_dir,'derivatives','figures')
analysis_dir = os.path.join(study_data_dir, 'derivatives', 'analysis')
sample_dir = os.path.join(study_data_dir, 'derivatives', 'sample_data')


os.makedirs(figure_dir, exist_ok=True)


# plot parameters and initalization
plt.style.use("stylesheet.mplstyle")

# set font
font_files = font_manager.findSystemFonts(
    fontpaths=[os.path.join(os.path.dirname(__file__), 'fonts')])
for font_file in font_files:
    font_manager.fontManager.addfont(font_file)
if 'Helvetica' in [f.name for f in font_manager.fontManager.ttflist]:
    plt.rcParams['font.family'] = 'Helvetica'
plt.rcParams.update({'font.size': 7})


# load data
with open(os.path.join(analysis_dir,f'results.pkl'), 'rb') as f:
    saved_results = pickle.load(f)    
results_all_areas = saved_results['results_all_areas']
areas = saved_results['areas']

with open(os.path.join(sample_dir, 'sample_data.pkl'), 'rb') as f:
    sampled_data = pickle.load(f)
data_all_areas = sampled_data['data_all_areas']
volume_all_areas = sampled_data['volume_all_areas']


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

ax.set_xticks([4,9,14,19], areas[np.array([4,9,14,19])])
ax.set_xlabel(r'target surface area [$mm^2$]')
ax.set_ylabel(r'actual ROI volume [$mm^3$]')

ax.text(-0.2,1.1, 'A', transform=ax.transAxes, 
        size=10, weight='bold')

# B VASO interaction effect with bootrsapped 95% confidence intervals
axs = create_shared_subplots(gs, row_range=[1], col_range=[0,1])
# After creating Panel B subplots
print("Panel B sharing check:")
print(f"axs[0,0] shares x with: {axs[0,0].get_shared_x_axes().get_siblings(axs[0,0])}")
print(f"axs[0,1] shares y with: {axs[0,1].get_shared_y_axes().get_siblings(axs[0,1])}")
for period, finn_et_al_effect, ax in zip(['delay', 'response'], [0.86, -0.68], [axs[0,0], axs[0,1]]):
    bootstrap_results = [
        results_all_areas['vaso'][idx]['np2_signed_combined_data'][
            results_all_areas['vaso'][idx]['np2_signed_combined_data']['period']==period]['np2'] 
            for idx in range(len(areas))]

    np2_signed_ci = np.array([b.quantile([0.025, 0.975]) for b in bootstrap_results])
    np2_signed_values = np.array([results_all_areas['vaso'][idx][f'np2_signed_{period}_est']
                              for idx in range(len(areas))])
    p_values = np.array([results_all_areas['vaso'][idx]['anova2'][period]['p-unc'][2] 
                         for idx in range(len(areas))])

    # plot the 95% confidence interval as a shaded area and the point estimate as a line
    ax.plot(areas, np2_signed_values, '-')
    ax.fill_between(areas, np2_signed_ci[:,0], np2_signed_ci[:,1], 
                    alpha=0.25, label='95% CI')

    # plot asterisks where the p-value is below 0.05 using the same color as the line
    ax.plot(areas[p_values<0.05], np2_signed_values[p_values<0.05], '*', 
            color='C0', label = 'p<0.05')

    # add horizontal line at finn_et_al_effect    
    ax.axhline(finn_et_al_effect, color='r', linestyle='--', 
               label='Finn et al. (2019) effect size')
    # add horizontal at 0 (in background)
    ax.axhline(0, color='k',lw=0.1, zorder=0)
    
    ax.set_xlim(areas[0],areas[-1])
    ax.set_xlabel(r'target surface area [$mm^2$]')
    ax.set_ylim(-0.9,1)
    ax.set_ylabel(r'signed $\eta_p^2$')
    

axs[0][1].legend(frameon=False, loc='upper left')
axs[0][0].text(-0.2,1.1, 'B', transform=axs[0][0].transAxes,
               size=10, weight='bold')
        

# C VASO and BOLD response amplitudes
axs = create_shared_subplots(gs, row_range=[0,1], col_range=[3,4])
print("Panel C sharing check:")
print(f"axs[0,0] shares x with: {axs[0,0].get_shared_x_axes().get_siblings(axs[0,0])}")
print(f"axs[0,1] shares y with: {axs[0,1].get_shared_y_axes().get_siblings(axs[0,1])}")
print(f"axs[1,0] shares x with: {axs[1,0].get_shared_x_axes().get_siblings(axs[1,0])}")
print(f"axs[1,1] shares y with: {axs[1,1].get_shared_y_axes().get_siblings(axs[1,1])}")

for modality, finn_et_al_modality_levels, modality_axs in zip(
     ['bold', 'vaso'], [[[3.72,1.25],[2.75,0.9]],[[1.75,0],[-0.25,1.25]]],axs):
    data = pd.concat([results['period_average_data'].assign(area=area)
                      for results, area in zip(results_all_areas[modality], areas)], ignore_index=True)

    for period, condition, finn_et_al_levels, ax in zip(
        ['delay','response'],['alpha','act'],finn_et_al_modality_levels, modality_axs):

        sns.lineplot(x='area',y='signal',hue='layer',
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

fig.savefig(os.path.join(figure_dir,
                         f'figure_roi-size-dependence.svg'), dpi=300)
fig.savefig(os.path.join(figure_dir,
                         f'figure_roi-size-dependence.png'), dpi=300)