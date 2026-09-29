#!/usr/bin/env python3
"""
Run analysis of behavior data.

We need to iterate over all subjects and runs and read in .tsv events files and .json event files.
The .json file contains the field StimulusPresentation['KeysRecorded'] which tells us
whether button presses were recorded for that subject. If not, we will note that in the results.

The .tsv files contain one line for every trial period of every trial.
We only need to obtain for every trial index (coded in column 'trial_idx') wheter the response
was correct (column 'correct') and what condition that trial belonged to (column 'condition').
Values may be 'n/a'. If a subject has only 'n/a' values it means that button press
recording did not work for that subject which we also want to note.
"""

import sys
import os
import csv
import json
import math
import io
from contextlib import redirect_stdout
import numpy as np
from scipy import stats
import utils



study_data_dir = sys.argv[1]

subjects = utils.subjects()

result_dir = os.path.join(study_data_dir, 'derivatives', 'results')
os.makedirs(result_dir, exist_ok=True)

# initialize results dict
run_type_conditions = {'alpharem': ['alpha', 'rem'],
                       'gonogo': ['go', 'nogo']}


def unique_trial_value(rows, field, trial_context, allow_na=True):
    """Return one consistent value for a field repeated across trial rows."""
    values = {row[field] for row in rows}
    if allow_na:
        values.discard('n/a')

    if len(values) > 1:
        raise ValueError(
            f'Conflicting {field} values for {trial_context}: {sorted(values)}')

    return next(iter(values), 'n/a')


def read_trials(events_file, expected_conditions):
    """Group an events TSV by trial_idx and validate repeated trial data."""
    with open(events_file, 'r', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))

    required_fields = {'trial_idx', 'condition', 'correct', 'response_time'}
    missing_fields = required_fields.difference(rows[0] if rows else {})
    if missing_fields:
        raise ValueError(
            f'Missing required columns in {events_file}: {sorted(missing_fields)}')

    rows_by_trial = {}
    for row in rows:
        trial_idx = row['trial_idx']
        if not trial_idx or trial_idx == 'n/a':
            raise ValueError(f'Missing trial_idx in {events_file}')
        rows_by_trial.setdefault(trial_idx, []).append(row)

    trials = []
    for trial_idx, trial_rows in rows_by_trial.items():
        context = f'{events_file}, trial {trial_idx}'
        condition = unique_trial_value(
            trial_rows, 'condition', context, allow_na=False)
        correct = unique_trial_value(trial_rows, 'correct', context)
        response_time = unique_trial_value(
            trial_rows, 'response_time', context)

        if condition not in expected_conditions:
            raise ValueError(
                f'Unexpected condition for {context}: {condition!r}; expected '
                f'one of {expected_conditions}')
        if correct not in {'True', 'False', 'n/a'}:
            raise ValueError(
                f'Unexpected correct value for {context}: {correct!r}')

        trials.append((condition, correct, response_time))

    return trials


results = dict()
for subject in subjects:
    results[subject] = dict()
    results[subject]['valid'] = True  # assume valid unless we find otherwise

    for run_type in run_type_conditions.keys():
        results[subject][run_type] = {'keys_recorded': {}}

        for condition in run_type_conditions[run_type]:
            results[subject][run_type][condition] = {
                'n_trials': 0,
                'n_correct': 0,
                'reaction_times': {1: [], 2: []},
            }

        # iterate over runs
        for run_idx in [1, 2]:
            events_stem = os.path.join(
                study_data_dir, subject, 'func',
                f'{subject}_task-{run_type}_run-{run_idx}_bold_events')

            # first check the json file to see if button presses were recorded for this subject
            # the criterion is that the field StimulusPresentation['KeysRecorded'] is True
            events_json_file = f'{events_stem}.json'

            with open(events_json_file, 'r') as f:
                events_metadata = json.load(f)
            keys_recorded = events_metadata['StimulusPresentation']['KeysRecorded']
            results[subject][run_type]['keys_recorded'][run_idx] = keys_recorded
            if not keys_recorded:
                print(f'No keypresses recorded for {subject}, {run_type}, run {run_idx}.')
                results[subject]['valid'] = False
                continue  # skip this run if no keypresses were recorded

            # Read and group the event-period rows into one record per trial.
            events_file = f'{events_stem}.tsv'
            trials = read_trials(events_file, run_type_conditions[run_type])

            for condition, correct, response_time in trials:

                # if condition is nogo, recompute the correct value to be 'True' if response_time is 'n/a' and 'False' otherwise
                if condition == 'nogo':
                    if response_time == 'n/a':
                        correct = 'True'
                    else:
                        correct = 'False'
                if condition == 'go':
                    if response_time == 'n/a':
                        correct = 'False'

                # count all trials:
                results[subject][run_type][condition]['n_trials'] += 1
                if correct == 'True':
                    results[subject][run_type][condition]['n_correct'] += 1
                    if response_time != 'n/a':
                        try:
                            reaction_time = float(response_time)
                        except ValueError as error:
                            raise ValueError(
                                f'Invalid response_time in {events_file}: '
                                f'{response_time!r}') from error
                        if not math.isfinite(reaction_time) or reaction_time < 0:
                            raise ValueError(
                                f'Invalid response_time in {events_file}: '
                                f'{response_time!r}')
                        results[subject][run_type][condition][
                            'reaction_times'][run_idx].append(reaction_time)

# calculate the average accuracy across subjects (in % with standard error)
# 1. for each condition of each run_type
# 2. for each run_type across all conditions
# 3. across all run_types and conditions
# two approaches:
# 1. only include subjects that have valid data for that run_type and condition
# 2. only include subjects that have valid data for all run_types and conditions
# print the results in a readable format and report on how many subjects and runs were included

def summarize_accuracy(subject_pool, conditions_by_run_type):
    """Return subject-level mean accuracy, SEM, and included sample sizes."""
    accuracies = []
    n_runs = 0

    for subject in subject_pool:
        n_trials = 0
        n_correct = 0
        for run_type, conditions in conditions_by_run_type.items():
            for condition in conditions:
                condition_results = results[subject][run_type][condition]
                n_trials += condition_results['n_trials']
                n_correct += condition_results['n_correct']

        if n_trials == 0:
            continue

        accuracies.append(n_correct / n_trials * 100)
        n_runs += sum(
            sum(results[subject][run_type]['keys_recorded'].values())
            for run_type in conditions_by_run_type
        )

    if not accuracies:
        return None

    sem = (np.std(accuracies, ddof=1) / np.sqrt(len(accuracies))
           if len(accuracies) > 1 else np.nan)
    return np.mean(accuracies), sem, len(accuracies), n_runs


def print_summary(label, summary):
    if summary is None:
        print(f'  {label}: no valid data')
        return

    mean_accuracy, sem_accuracy, n_subjects, n_runs = summary
    sem_text = f'{sem_accuracy:.2f}%' if not np.isnan(sem_accuracy) else 'n/a'
    print(f'  {label}: {mean_accuracy:.2f}% (SEM: {sem_text}; '
          f'{n_subjects} subjects, {n_runs} runs)')


def paired_alpharem_accuracy_test(subject_pool):
    """Paired t-test of subject-level alpha and rem accuracies."""
    alpha_accuracies = []
    rem_accuracies = []

    for subject in subject_pool:
        condition_accuracies = {}
        for condition in ['alpha', 'rem']:
            condition_results = results[subject]['alpharem'][condition]
            if condition_results['n_trials'] > 0:
                condition_accuracies[condition] = (
                    condition_results['n_correct'] /
                    condition_results['n_trials'] * 100)

        if len(condition_accuracies) == 2:
            alpha_accuracies.append(condition_accuracies['alpha'])
            rem_accuracies.append(condition_accuracies['rem'])

    if len(alpha_accuracies) < 2:
        return None

    test = stats.ttest_rel(alpha_accuracies, rem_accuracies)
    return (test.statistic, test.pvalue, len(alpha_accuracies),
            np.mean(alpha_accuracies), np.mean(rem_accuracies))


def print_alpharem_accuracy_test(subject_pool):
    test = paired_alpharem_accuracy_test(subject_pool)
    if test is None:
        print('  Alpha vs. rem: fewer than two subjects have both conditions')
        return

    statistic, pvalue, n_subjects, alpha_mean, rem_mean = test
    print(f'  Alpha vs. rem: paired t({n_subjects - 1}) = {statistic:.3f}, '
          f'p = {pvalue:.4g} (two-sided; {n_subjects} subjects; '
          f'alpha mean: {alpha_mean:.2f}%; rem mean: {rem_mean:.2f}%)')


def print_analysis(subject_pool):
    print('By condition:')
    for run_type, conditions in run_type_conditions.items():
        for condition in conditions:
            selection = {run_type: [condition]}
            print_summary(f'{run_type} / {condition}',
                          summarize_accuracy(subject_pool, selection))

    print('\nBy run type:')
    for run_type, conditions in run_type_conditions.items():
        selection = {run_type: conditions}
        print_summary(run_type, summarize_accuracy(subject_pool, selection))

    print('\nAcross all run types and conditions:')
    print_summary('overall', summarize_accuracy(subject_pool, run_type_conditions))

    print('\nPaired alpha-rem comparison:')
    print_alpharem_accuracy_test(subject_pool)


def summarize_reaction_time(subject_pool, conditions_by_run_type):
    """Return mean subject RT, SEM, and sample sizes for correct responses."""
    subject_means = []
    n_trials = 0

    for subject in subject_pool:
        reaction_times = []
        for run_type, conditions in conditions_by_run_type.items():
            for condition in conditions:
                reaction_times_by_run = results[subject][run_type][condition][
                    'reaction_times']
                reaction_times.extend(
                    reaction_time
                    for run_reaction_times in reaction_times_by_run.values()
                    for reaction_time in run_reaction_times
                )

        if reaction_times:
            subject_means.append(np.mean(reaction_times))
            n_trials += len(reaction_times)

    if not subject_means:
        return None

    sem = (np.std(subject_means, ddof=1) / np.sqrt(len(subject_means))
           if len(subject_means) > 1 else np.nan)
    return np.mean(subject_means), sem, len(subject_means), n_trials


def print_reaction_time_summary(label, summary):
    if summary is None:
        print(f'  {label}: no correct responses with a reaction time')
        return

    mean_rt, sem_rt, n_subjects, n_trials = summary
    sem_text = f'{sem_rt:.3f} s' if not np.isnan(sem_rt) else 'n/a'
    print(f'  {label}: {mean_rt:.3f} s (SEM: {sem_text}; '
          f'{n_subjects} subjects, {n_trials} trials)')


def paired_alpharem_reaction_time_test(subject_pool):
    """Paired t-test of subject-level alpha and rem mean reaction times."""
    alpha_means = []
    rem_means = []

    for subject in subject_pool:
        condition_means = {}
        for condition in ['alpha', 'rem']:
            reaction_times_by_run = results[subject]['alpharem'][condition][
                'reaction_times']
            reaction_times = [
                reaction_time
                for run_reaction_times in reaction_times_by_run.values()
                for reaction_time in run_reaction_times
            ]
            if reaction_times:
                condition_means[condition] = np.mean(reaction_times)

        if len(condition_means) == 2:
            alpha_means.append(condition_means['alpha'])
            rem_means.append(condition_means['rem'])

    if len(alpha_means) < 2:
        return None

    test = stats.ttest_rel(alpha_means, rem_means)
    return (test.statistic, test.pvalue, len(alpha_means),
            np.mean(alpha_means), np.mean(rem_means))


def print_alpharem_reaction_time_test(subject_pool):
    test = paired_alpharem_reaction_time_test(subject_pool)
    if test is None:
        print('  Alpha vs. rem: fewer than two subjects have RTs in both conditions')
        return

    statistic, pvalue, n_subjects, alpha_mean, rem_mean = test
    print(f'  Alpha vs. rem: paired t({n_subjects - 1}) = {statistic:.3f}, '
          f'p = {pvalue:.4g} (two-sided; {n_subjects} subjects; '
          f'alpha mean: {alpha_mean:.3f} s; rem mean: {rem_mean:.3f} s)')


def print_reaction_time_analysis(subject_pool):
    print('By condition:')
    for run_type, conditions in run_type_conditions.items():
        for condition in conditions:
            selection = {run_type: [condition]}
            print_reaction_time_summary(
                f'{run_type} / {condition}',
                summarize_reaction_time(subject_pool, selection))

    print('\nBy run type:')
    for run_type, conditions in run_type_conditions.items():
        selection = {run_type: conditions}
        print_reaction_time_summary(
            run_type, summarize_reaction_time(subject_pool, selection))

    print('\nAcross all run types and conditions:')
    print_reaction_time_summary(
        'overall', summarize_reaction_time(subject_pool, run_type_conditions))

    print('\nPaired alpha-rem comparison:')
    print_alpharem_reaction_time_test(subject_pool)


# print the analyses and also write them to the results
report = io.StringIO()
with redirect_stdout(report):
    print('Runs without recorded key presses:')
    for subject in subjects:
        runs = [(run_type, run_idx) for run_type in run_type_conditions
                for run_idx in results[subject][run_type]['keys_recorded']]
        missing = [(run_type, run_idx) for run_type, run_idx in runs
                   if not results[subject][run_type]['keys_recorded'][run_idx]]
        if len(missing) == len(runs):
            print(f'  {subject}: all runs')
        elif missing:
            print(f'  {subject}: ' + ', '.join(f'{run_type} run {run_idx}' for run_type, run_idx in missing))

    print('\nAvailable-case analysis')
    print('(subjects included wherever they have valid data)')
    print_analysis(subjects)
    print('\nReaction times for correct responses')
    print_reaction_time_analysis(subjects)

    complete_subjects = [subject for subject in subjects if results[subject]['valid']]
    print('\nComplete-case analysis')
    print('(only subjects with valid data for every run type and condition)')
    print_analysis(complete_subjects)
    print('\nReaction times for correct responses')
    print_reaction_time_analysis(complete_subjects)

print(report.getvalue(), end='')
with open(os.path.join(result_dir, 'behavior.txt'), 'w') as f:
    f.write(report.getvalue())
