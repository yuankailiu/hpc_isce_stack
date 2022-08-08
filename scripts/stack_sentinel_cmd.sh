# Run stack sentinel for T115a with ionospheric corrections
set -e
echo 'Running stackSentinel.py. Make sure that ISCE is loaded'

###################################################################################
# LIST OF THINGS TO EDIT
# - Bounding box
# - Start and stop dates
# - NUM_PROCESS_4_TOPO
# - resources_array.cfg for NCPUS_PER_TASK for run_01 (depends on NUM_PROCESS_4_TOPO)
# - resources_array.cfg for wall time for each stage (remember that this is just for each array element)
# - email in write_sbatch_files_array.py (if you're not Ollie)
# - input files below (if not working in the Makran)
# - reference date (earlier dates will sometimes have less spatial coverage, need to decide whether or not to throw them out)
# - if using a different processing chain (e.g. no ESD) will need to change stage numbering (TODO remove stage number hardcoding)
# - in order to make adding new pairs easier, set the reference to the most recent SLC in the stack
#   - this means that we can just process the new pairs and register everything to the same SLC
###################################################################################



########################
# Edit these files
TRACK='a087'
SLC_DIR=/central/groups/simonsgroup/ykliu/aqaba/${TRACK}/data/slc/s1a/tmp_add
DEM=/central/groups/simonsgroup/ykliu/aqaba/broad_dem/dem_1_arcsec/demLat_N25_N35_Lon_E032_E040.dem.wgs84
ORBITS_DIR=/central/groups/simonsgroup/ykliu/z_common_data/aux_poeorb
AUX_DIR=/central/groups/simonsgroup/ykliu/z_common_data/aux_cal
########################
# TODO - for some reason can't pass BBOX argument list this - probably a simple fix
# BBOX="'25.5 27.5 64 66'" # Argument needs to be passed in quotes
# NUM_PROCESS=30 # Number of commands between 'wait' statements in run files
# NOw that we're using SLURM arrays, we don't need to use & and wait
# I think we should set this to larger than the largest number of commands in an individual step, then let srun sort the starting of tasks
CPUS_PER_TASK_TOPO=4  # For each python process in the pool, how many CPUs to use
NUM_PROCESS_4_TOPO=12 # MAX limited by no. of CPUs per node on HPC
# It looks like this variable gets passed to a python multiprocessing pool, where it's used to process the number of bursts we have in the reference SLC (see topsStack/topo.py). In theory this means we'll get the fastest speeds if we set it equal to the number of bursts
# But NOTE - the relevant step (run_01_unpack_topo_reference) has to be run on a single node, so we can't use more than 28 (or 32?) CPUs
# If CPUS_PER_TASK=4, max NUM_PROCESS_4_TOPO=7 or 8
# This variable gets passed to python multiprocess pool. We should give it the same number of CPUs I think?
# If we don't set it, it's automatically set to NUM_PROCESS by ISCE
AZIMUTH_LOOKS=5
RANGE_LOOKS=20
# c=No. of pairs per slc in igram network
# num_connections_ion=no. of pairs in ionospehre igram network
stackSentinel.py -s $SLC_DIR \
    -d $DEM \
    -o $ORBITS_DIR \
    -a $AUX_DIR \
    -b '26.6 33.9 33.5 37.9' \
    -c 3 \
    --filter_strength 0 \
    --azimuth_looks $AZIMUTH_LOOKS \
    --range_looks $RANGE_LOOKS \
    --num_process4topo $NUM_PROCESS_4_TOPO \
    --stop_date 2022-07-01 \
    --reference_date 20220102 \
    --param_ion ./ion_param.txt \
    --num_connections_ion 3 \
    --useGPU

# --start_date 2021-01-01 \
# --reference_date 20210503 \
# Reference date needs YYYYMMDD format, rather than YYYY-MM-DD for some reason

# Small bbox
    # -b '26.0 29.0 33.9 36.7' \
# Medium bbox
    # -b '28.0 30.3 33.9 36.7' \
# Full extent for d021
    # -b '26.6 33.9 33.5 37.9' \
# NB for full track in the Makran (up to 32N) the unwrapping stage needs ~16GB of memory
# Sed statement below is used to edit the relevant sbatch file

# If we have this flag on but don't reserve a GPU using SLURM sbatch script, it will still use a GPU - want to avoid this
# If using GPU, need to put flag on here and request a GPU in SBATCH

## Move relevant scripts for running the tops stack processing chain into run_files
# For writing the sbatch files for each stage
mv write_sbatch_files_array.py ./run_files/write_sbatch_files_array.py
# Table logging the resources for each stage
mv resources_array*.cfg ./run_files/
# For submitting the sbatch files
mv submit_chained_dependencies.sh ./run_files/submit_chained_dependencies.sh
# For erasing data during processing
mv clean_topsStack_files.sh ./run_files
# For analysing timings after processing
mv analyse_timings.py ./run_files

cwd=$(pwd)
cd ./run_files


## Write sbatch files for submitting each stage separately
python write_sbatch_files_array.py $TRACK
echo 'Editing sbatch files'
## Edit sbatch files
# Change number of OpenMP threads for topo stage
# We havea python multiprocessing pool of resources, each of which can use OpenMP
# The number of python multiprocessing processes is controlled by num_process4topo
sed -i "s/OMP_NUM_THREADS=\$SLURM_CPUS_PER_TASK/OMP_NUM_THREADS=$CPUS_PER_TASK_TOPO/g" run_01_unpack_topo_reference.sbatch

# Get an email when the final step finishes
sed 's/--mail-type=FAIL/--mail-type=FAIL,END/' -i run_24_invertIon.sbatch

#TODO - can remove these
# Add a GPU for the two stages that use geo2rdr
# Use sed to uncomment the gpu line
# Must also enable '--useGPU' when calling the stackSentinel.py command above
# sed 's/###  #SBATCH --gres=gpu:1/#SBATCH --gres=gpu:1/g' -i run_05_overlap_geo2rdr.sbatch
# sed 's/###  #SBATCH --gres=gpu:1/#SBATCH --gres=gpu:1/g' -i run_09_fullBurst_geo2rdr.sbatch

# For unwrapping stage, when unwrapping long tracks we need large memory
# sed 's/###  #SBATCH --mem-per-cpu=16G/#SBATCH --mem-per-cpu=16G/g' -i run_16_unwrap.sbatch

## File deletion
# Add deleting scripts to sbatch files (NB need to edit them to turn off the dry run)
# Choose what to delete by passing command line arguments
# NB - when using slurm arrays we move the deletion to one stage later, to avoid one job deleting the files needed by another running job with a different array index
# Replace the line '#_deletion_here' in sbatch statement
# Use the if statement to just do the deletion using the first slurm array, we don't want to repeat this from every array element
# Need to espace '/' for sed
# Calling with 'srun' gives us more informative logs when looking at 'sacct' output
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --esd --coreg_overlap; fi/g' -i run_09_fullBurst_geo2rdr.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --geom_reference; fi/g' -i run_13_generate_burst_igram.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --coarse_igram; fi/g' -i run_14_merge_burst_igram.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --burst_igram; fi/g' -i run_15_filter_coherence.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --burst_slc; fi/g' -i run_16_unwrap.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --ion_burst_slc; fi/g' -i run_19_mergeBurstsIon.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --ion_burst_igram; fi/g' -i run_20_unwrap_ion.sbatch
sed 's/#_deletion_here/if [[ $SLURM_ARRAY_TASK_ID -eq 1 ]]; then srun .\/clean_topsStack_files.sh --ion_split_igram --coreg_offset; fi/g' -i run_23_filtIon.sbatch

# Reminder to not leave the script on 'dry_run'
echo "Make sure to switch on deleting in the clean_topsStack_files.sh script"

# Make a place to store log files
mkdir log_files
# Move all logs to the directory as the last action (could lead to issues if we're trying to write to 'run_24'?
# TODO Better to make this a separate sbatch job, along with time calculation - this only works when the final command has a single array element
echo 'mv *.out *.txt *.log log_files' >> run_24_invertIon.sbatch
# Use reportseff to look at resource usage for every step
# This calls reportseff on all log files in ./log_files
echo 'reportseff ./log_files --no-color > reportseff_all.txt' >> run_24_invertIon.sbatch
# Add timings analysis as the final step
# This looks at the log files, so make sure we've moved them to where we expect them to be
echo 'python analyse_timings.py' >> run_24_invertIon.sbatch

# Write header for file size log
# fmt_fs="%-35s%-12s%-12s%-12s\\n"
fmt_fs="%-35s%-12s%-12s%-12s%-12s\\n"
printf "$fmt_fs" "Step"  "Step number" "Job ID" "Task ID" "Total size" > total_file_sizes.txt

# Go back to process dir
cd $cwd
echo 'Finished stack_sentinel_cmd.sh'
