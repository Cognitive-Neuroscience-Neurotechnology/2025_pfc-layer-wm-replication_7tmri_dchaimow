#!/bin/bash
set -euo pipefail
studyDataDir=$1
subject=$2

# acquisition timing from the BIDS sidecars: volume TR and delays of the nulled and not nulled readouts
bidsJsonBase=${studyDataDir}/${subject}/func/${subject}_task-alpharem_acq
TR=$(jq '.RepetitionTime' ${bidsJsonBase}-nulled_run-1_bold.json)
delay_nulled=$(jq '.DelayTime' ${bidsJsonBase}-nulled_run-1_bold.json)
delay_notnulled=$(jq '.DelayTime' ${bidsJsonBase}-notnulled_run-1_bold.json)

# shift of the not nulled relative to the nulled readout as fraction of the TR (for BOLD correction)
shiftFraction=$(bc -l <<< "(${delay_notnulled}-${delay_nulled})/${TR}")

curDir=$(pwd)

preprocessDir=${studyDataDir}/derivatives/preprocess/${subject}

mkdir -p ${preprocessDir}
cd ${preprocessDir}

i=0
> func_runs_basenames.txt
for task in alpharem gonogo
do
    for run in 1 2
    do
        i=$(( i+1 ))
        fBaseName=func${i}_${task}
        echo ${fBaseName} >> func_runs_basenames.txt
        for readout in nulled notnulled
        do
            # import files
            3dTcat -prefix ${fBaseName}_${readout}.nii \
                ${studyDataDir}/${subject}/func/${subject}_task-${task}_acq-${readout}_run-${run}_bold.nii                
            # replace the first two volumes (not yet in steady state) by copies of volumes 2 and 3,
            # keeping the length of the time series
            3dTcat -overwrite -prefix ${fBaseName}_${readout}.nii \
                ${fBaseName}_${readout}.nii'[2..3]' \
                ${fBaseName}_${readout}.nii'[2..$]'
        done
    done
done    

# store readout delays for trial averaging
echo ${delay_nulled} > vaso_readout_onsets.txt
echo ${delay_notnulled} >> vaso_readout_onsets.txt

# motioncorrect
motioncorrect.sh -vaso $(< func_runs_basenames.txt)

# average runs according to conditions
for readout in nulled notnulled
do
    avgruns.sh func_alpharem_${readout}.nii \
            func1_alpharem_${readout}_mc.nii \
            func2_alpharem_${readout}_mc.nii 
    avgruns.sh func_gonogo_${readout}.nii \
                func3_gonogo_${readout}_mc.nii \
                func4_gonogo_${readout}_mc.nii 
    # average all (only for t1 calculation)
    avgruns.sh func_all_${readout}.nii func?_*_${readout}_mc.nii
done

# calculate t1 weighted
calct1.sh func_all

# calculate tSNR on bold correction of individual runs
for fBaseName in $(< func_runs_basenames.txt)
do
    mv ${fBaseName}_notnulled_mc.nii ${fBaseName}_notnulled.nii
    mv ${fBaseName}_nulled_mc.nii ${fBaseName}_nulled.nii
    
    boldcorrect.sh ${fBaseName} ${shiftFraction}

    # calculate tSNR of vaso
    3dTstat -cvarinv -prefix ${fBaseName}_vaso_tsnr.nii ${fBaseName}_vaso.nii
done

# clean up/organize files
mkdir -p motioncorrection_pars

mv min_outlier.txt motioncorrection_pars/
mv all_outcount.1D motioncorrection_pars/
rm c?func_all_T1_denoised.nii
rm func_all_T1_denoised_seg8.mat
rm pyscript_newsegment.m

for readout in nulled notnulled
do
    rm func_all_${readout}.nii
    mv all_${readout}_outcount.1D motioncorrection_pars/
    for fBaseName in $(< func_runs_basenames.txt)
    do
        mv ${fBaseName}_${readout}_disp.png motioncorrection_pars/
        mv ${fBaseName}_${readout}_rot.png motioncorrection_pars/
        mv ${fBaseName}_${readout}_trans.png motioncorrection_pars/
        mv ${fBaseName}_${readout}_mc_maxdisp_delt motioncorrection_pars/
        mv ${fBaseName}_${readout}_mc_maxdisp motioncorrection_pars/
        mv ${fBaseName}_${readout}_mc_reordered.par motioncorrection_pars/${fBaseName}_${readout}_mc.par
        rm ${fBaseName}_${readout}_mc.par
        rm ${fBaseName}_${readout}.nii
        if [ "${readout}" == "notnulled" ]; then
            rm ${fBaseName}_notnulled_tshift.nii
            rm ${fBaseName}_vaso.nii
        fi
    done
done

cd ${curDir}
