# Python script to write sbatch files for tops stack on Caltech's HPC
# NOTE - modify email address in sbatch template before using
import pandas as pd
import sys
import argparse

parser = argparse.ArgumentParser(description='Create sbatch files for running tops stack')

# Required track argument
parser.add_argument('track', type=str, help='Track, for naming the job (e.g. "T115a")')
# parser.add_argument('--logfile','-l', type=str, help='Logfile for the entire run. Each step has its own log, and all output also goes to a central log')
args      = parser.parse_args()
track     = args.track
# logfile = args.logfile
infile    = 'resources_array.cfg'
cpus_per_node_lim = 56 # No more than this many CPUs per node
# Need to check the nodes your system has available and how many CPUs they have


df         = pd.read_table(infile,header=0,delim_whitespace=True)
df.columns = df.columns.str.replace('#', '') # Remove comment character from column names

# Iterate over the run files, write an sbatch file for each one
print('')
print('##### Writing sbatch files for {}'.format(track))
for index, row in df.iterrows():
    step_script = row['Step']
    step_name   = step_script[7:] # Strip number
    step_num    = step_script[4:6]

    # Get the number of commands in the script
    cmd_num = len(open(step_script).readlines(  ))

    # TODO Move these checks to outside the loop so we run them before writing any files
    # Check limits
    cpus_per_node = row['Ntasks']*row['Ncpus_per_task']/row['Nodes']
    if cpus_per_node > cpus_per_node_lim:
        raise Exception('Do not exceed {} cpus per node'.format(cpus_per_node_lim))

    if step_name == 'unwrap':
        if cpus_per_node > cpus_per_node_lim/4:
            raise Exception('Do not exceed {} cpus per node for unwrapping stage due to memory issues'.format(cpus_per_node_lim))
            # TODO I think this isn't a problem when we're using arrays
            # NOTE - this will vary a lot depending on the size of the region that's being processed
            # Should experiment with this depending on your situation
            # I think unwrapping stage can only use 1 CPU, but needs a lot of memory


    log_name = 'slurm-{}-%A_%a.out'.format(step_script)
#SBATCH --output=slurm-%j_%n_%t.out     # Format of output file (job_node_task)
    sbatch_name = '{}.sbatch'.format(step_script)

    context = {
            "time":row['Time'],
            "nodes":row['Nodes'],
            # "ntasks_per_node":row['Ntasks_per_node'],
            "ntasks":row['Ntasks'],
            "ncpus_per_task":row['Ncpus_per_task'],
            "log_name":log_name,
            "track":track,
            "step_name":step_name,
            "step_num":step_num,
            "step_script":step_script,
            "step_index":index+1,
            "cmd_num":cmd_num,
            "gres":row['Gres'],
            "mem":row['Mem_per_cpu']
            }
    # Made sure to add a comma when adding a line here
    #TODO - deal with Gres (GPU usage)

# Put variables from context dic into the sbatch template
    template = \
"""#!/bin/bash

# Slurm script for tops stack processing, step {step_name}
# Submit this script with: sbatch <this-filename>
# For topsStack processing, submit all stages using submit_chained_dependencies.sh script

#SBATCH -A simonsgroup                              # pocket to charge
#SBATCH --time={time}                               # walltime (days-hours:minutes:seconds)
#SBATCH --nodes={nodes}                             # number of nodes
#SBATCH --ntasks={ntasks}                           # Total number of tasks
#SBATCH --cpus-per-task={ncpus_per_task}	        # CPU cores/threads per task
#SBATCH --gres=gpu:{gres}                           # number of GPUs per node (used for geo2rdr steps)
#SBATCH --mem-per-cpu={mem}                         # memory per CPU core (Need to fix by trial and error)
#SBATCH -J "{step_index}_{step_name}_{track}"	    # job name
#SBATCH --output={log_name}                         # Format of output file (%j = job id)
#SBATCH --mail-user=ykliu@caltech.edu               # my email address
#SBATCH --mail-type=FAIL
#SBATCH --array=1-{cmd_num}


# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
module load cuda/11.2
module load gcc/7.3.0
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

### Any deletion statements get added here by 'stack_sentinel_cmd.sh'
#_deletion_here

# Store dates/times in different formats
start_time=`date '+%T'`
step_start=`date +%s`


# Central logfile needs to be supplied as a command line argument via --export when calling sbatch
# Avoid writing too much to it, issues when multiple jobs are trying to write at the same time
printf "##########################################################################################\\n" | tee -a $logfile
printf "####     RUNSTEP {step_num}:  {step_name} \\n" | tee -a $logfile
printf "####     Step start time:     `date`         \\n" | tee -a $logfile
printf "####     SLURM_JOB_ID:        $SLURM_JOB_ID    \\n" | tee -a $logfile
printf "####     SLURM_ARRAY_JOB_ID:  $SLURM_ARRAY_JOB_ID    \\n" | tee -a $logfile
printf "####     SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID \\n" | tee -a $logfile
printf "##########################################################################################\\n" | tee -a $logfile

######### Calculate file sizes
# Just run du for some tasks, to avoid massive slowdown when running hundreds of jobs with 10s of TB of data
# TODO - need to be careful for jobs with small walltimes - the jobs that are running du can take much longer
# TODO - can probably just run this for a single job, don't need to do it for multiple array elements
if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]] || [[ $SLURM_ARRAY_TASK_ID -eq 300 ]] || [[ $SLURM_ARRAY_TASK_ID -eq 600 ]]
then
    # Calculate how much data we have at this stage
    printf "####################\\n"
    printf "####### File sizes\\n"
    srun du -ch --max-depth=1 ../ # we're executing from 'run_files', use srun for better logging
    printf "####################\\n"

    # Just output total size of files at this stage to a separate log
    total_size=$(eval du -ch --max-depth=1 ../ | tail -1 | cut -f 1)
    fmt_fs="%-35s%-12s%-12s%-12s%-12s\\n"
    printf "$fmt_fs" "{step_name}"  "{step_num}" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$total_size" >> total_file_sizes.txt
else
    echo "Not cacluating file sizes for SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"
fi

########## Execute topsStack commands
# Read a line from the command file, using the array task ID as index
cmd=$(sed "${{SLURM_ARRAY_TASK_ID}}q;d" {step_script})
# Run command
echo "Running: ${{cmd}}" | tee -a $logfile
srun $cmd 2>&1 || scancel $SLURM_JOB_ID # If srun returns an error, we cancel the job
# This stops the chained jobs from carrying on
# TODO this isn't the best way of reporting errors - we don't get the actual error status reported
# 2>&1 redirects stderr to stdout,
# Not writing main output to a central logfile to avoid overlapping output - every array element gets its own file


########### Log timings
step_end=`date +%s`
step_time=$( echo "$step_end - $step_start" | bc -l )
Elapsed="$(($step_time / 3600))hrs $((($step_time / 60) % 60))min $(($step_time % 60))sec"

printf "####    Step end time: `date` \\n" | tee -a $logfile
printf "####    SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID \\n" | tee -a $logfile
printf "####    Total elapsed: $Elapsed \\n" | tee -a $logfile

## Log timings
# Timings file is created by submit_chained_dependencies.sh (headers are written there)
finish_time=`date '+%T'`
fmt="%-35s%-12s%-12s%-12s%-12s%-12s\\n"
printf "$fmt" "{step_name}" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$start_time" "$finish_time" "$Elapsed" >> timings.txt
# Log timings in Unix format
printf "$fmt" "{step_name}" "$SLURM_ARRAY_JOB_ID" "$SLURM_ARRAY_TASK_ID" "$step_start" "$step_end" "$step_time" >> time_unix.txt

"""


    # Write sbatch file
    with open(sbatch_name,'w') as myfile:
        myfile.write(template.format(**context))

print('Sbatch files written for {}'.format(track))

# Other things we could put into sbatch file
    ###  #SBATCH --mem-per-cpu=16G                      # memory per CPU core
    ###  --ntasks=2                                     # number of processor cores (i.e. tasks)
    ###  #SBATCH --gres=gpu:1                           # number of GPU per node
    ###  SBATCH --ntasks-per-node={ntasks_per_node}	    # tasks per node
    ###  #SBATCH --exclusive                            # Reserve whole node
