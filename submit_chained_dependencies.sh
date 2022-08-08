#!/bin/bash
set -e
# Submit a series of scripts to a SLURM job manager, each depending on the previous one finishing correctly 

# TODO - remove the debug queue from Sbatch option when running big jobs
echo 'Submitting topsStack jobs. Make sure that ISCE is loaded or these will fail'

# NOTE - if restarting mid way through the processing, need to deal with the timings file and remove finished steps from the list below

# List of scripts that we want to run
# First check that these exist 
topsstack_scripts=(
'run_01_unpack_topo_reference'
'run_02_unpack_secondary_slc'
'run_03_average_baseline'
'run_04_extract_burst_overlaps'
'run_05_overlap_geo2rdr'
'run_06_overlap_resample'
'run_07_pairs_misreg'
'run_08_timeseries_misreg'
'run_09_fullBurst_geo2rdr'
'run_10_fullBurst_resample'
'run_11_extract_stack_valid_region'
'run_12_merge_reference_secondary_slc'
'run_13_generate_burst_igram'
'run_14_merge_burst_igram'
'run_15_filter_coherence'
'run_16_unwrap'
'run_17_subband_and_resamp'
'run_18_generateIgram_ion'
'run_19_mergeBurstsIon'
'run_20_unwrap_ion'
'run_21_look_ion'
'run_22_computeIon'
'run_23_filtIon'
'run_24_invertIon'
)

# Check that we have all the run_* and .sbatch scripts in this directory before submitting
for ((i=0;i<${#topsstack_scripts[@]};i++)); do
    step=${topsstack_scripts[i]}
    if [ ! -f "${step}" ]; then
        echo "$step does not exist, exiting"
        exit
    fi
    if [ ! -f "${step}.sbatch" ]; then
        echo "${step}.sbatch does not exist, exiting"
        exit
    fi
done

echo 'File checks passed. Submitting jobs'

# echo 'Sourcing ISCE'
# $(makran_proj)


### Log files
start=`date +%s`
now=$(date '+(%Y-%m-%d) %T')
echo $now
printf -v date '%(%Y-%m-%d)T' -1 # Store this command in $date for file naming 
# Explanation of the printf command: https://stackoverflow.com/questions/30098992/what-does-printf-v-do 
# TODO not sure if writing every array element to this log is helpful, probably slows things down quite a lot - consider removing 
logfile="cmd_runall_${date}.log"

if [ -f "${logfile}" ] ; then
    rm -f "${logfile}"
fi

printf "####=========================================####\n" > ${logfile}
printf "####=========================================####\n" >> ${logfile}
printf "    Submitting all jobs at: `date` \n" >> ${logfile}
printf "####=========================================####\n" >> ${logfile}
printf "####=========================================####\n\n\n\n" >> ${logfile}

## Create files specifically for logging timings 
# One is in an easy format for quick inspection, the other in unix format for further processing
# TODO add date to timings file - need to pass the name to sbatch 
fmt="%-35s%-12s%-12s%-12s%-12s%-12s\n" # Need to modify this in write_sbatch_files.py as well
# printf -v date '%(%Y-%m-%d)T' -1 # Store this command in $date for file naming and start/ending times
printf "# Job submitted at: $now\n" >> timings.txt
printf "$fmt" "# Stage" "Job ID" "Array ID" "Start" "Finish" "Elapsed" >> timings.txt # Create a file to write all timings to, which is then written to by each stage
# Write a file with unix times for later processing 
now_unix=$(date "+%s")
printf "# Job submitted at: $now_unix\n" >> time_unix.txt
printf "$fmt" "# Stage" "Job ID" "Array ID" "Start (s)" "Finish (s)" "Elapsed (s)" >> time_unix.txt # Create a file to write all timings to, which is then written to by each stage

### SUBMIT JOBS 
# Submit the first job
# Pass the logfile as an argument 
# Need 'ALL' so we get other environment variables
# Add -q debug to use debug queue (will hit job threshold when using slurm arrays)
ID=$(sbatch --parsable --export=ALL,logfile=${logfile} "${topsstack_scripts[0]}.sbatch")
echo "Submitted $ID"
# Write a logfile with the ID of each stage
id_logfile="job_id_logfile_${date}.txt"
echo "IDs of Jobs submitted at: $now" >> $id_logfile
fmt_id="%-35s%-12s\\n"
printf "$fmt_id" "Stage" "Job ID" >> $id_logfile
printf "$fmt_id" "${topsstack_scripts[0]}" "$ID" >> $id_logfile
# echo $ID >> $id_logfile

# Loop over remaining scripts and submit them
for ((i=1;i<${#topsstack_scripts[@]};i++)); do
    sbatch_script="${topsstack_scripts[i]}.sbatch"
    ID=$(sbatch --parsable --dependency=afterok:${ID} --export=ALL,logfile=${logfile} $sbatch_script)
    printf "$fmt_id" "${topsstack_scripts[i]}" "$ID" >> $id_logfile
    echo "Submitted $ID"
done

# Note - if one job fails, all the rest will stay in the queue. Can kill all of your jobs by doing scancel -u <username>

echo 'All jobs submitted. Have a nice day.'
