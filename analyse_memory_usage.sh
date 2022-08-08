#!/bin/bash

# Look at memory usage for the listed jobs
# Note - might also need to look at 'State' if we're having job failures 
# Assuming that we're using topsStack with slurm arrays for each step, each step having a separate SLURM job id

# TODO - could add this to the python analyse timings script
# TODO - could read these directly from the job id log file
# TODO - we get an easier output format (showing usage and efficiency for memory and CPU) using 'seff <job_id>_<array_index>'

job_ids=(
18230498
18230499
18230500
18230501
18230502
18230503
18230504
18230505
18230506
18230507
18230508
18230509
18230510
18230511
18230512
18230513
18230514
18230515
18230516
18230517
18230518
18230519
18230520
18230521
)

mem_file='max_mem_usage.txt'
echo 'Maximum memory usage for each stage in the processing' > $mem_file
echo '' >> $mem_file
fmt='%-10s%-20s%-20s\n'
printf "$fmt" "Job num" "Job id" "MaxRSS" >> $mem_file

for ((i=0;i<${#job_ids[@]};i++)); do
    job_id="${job_ids[i]}"
    job_num=$(( $i + 1 ))
    outfile=${job_num}_${job_id}_sacct.txt
    sacct -j${job_id} --format=JobID%20,NodeList,MaxRSS,MaxVMSize,State%20 > $outfile 
    # Could also add 'ReqMem'
    # Just keep the lines with 'batch' - that's the relevant output for looking at memory
    # NOTE - this is the line we want when not using 'srun' within our sbatch scripts 
    # sed -i -n '/batch/p' $outfile 
    # If we're using 'srun' to call our ISCE commands, we want the lines ending in '.0'
    sed -i -n '/\.0/p' $outfile

    # find ./*_sacct_batch* -type f -exec sort -k3r -o {} {} \;
    # Sort based on MaxRSS 
    sort -k3r $outfile -o $outfile
    max_mem=$(awk 'FNR==1{print $3}' $outfile) 
    job_id=$(awk 'FNR==1{print $1}' $outfile) 

    # Write max memory to file for each stage
    printf "$fmt" "$job_num" "$job_id" "$max_mem" >> $mem_file

done

# Clean up log files
mkdir mem_usage
mv *_sacct.txt mem_usage
