# hpc_isce_stack


############################################################
# Author: Oliver Stephenson, 2021                          #
############################################################


Scripts for submitting tops stack stages as a series of chained SLURM jobs
Each job uses SLURM arrays to manage the processing that can be done in parallel
Avoids the issue with wasting resources, hopefully deals better with very large numbers of jobs

The 'resources_array.cfg' file gives the resources allocated to each array element, not to the whole job step combined

Different resource files are for different sized jobs - resources_array_full_eff.cfg is the efficient ('eff') allocation of resources for the full T115a track (25 to 32N)


:: Notes before running processing codes ::
(ykliu 2022-03-08)

0. run `s1_select_ion.py` to get the starting ranges for each subswath for each frame (SLC). Save output to a txt file.
        This is only for information, the output does not serve directly as input to stackSentinel.py

1. Use the appropriate .cfg for resourse allocation. Copy the customed .cfg to overwrite 'resources_array.cfg'

    - run_16_unwrap         set to 3 hr for long tracks
    - run_20_unwrap_ion     set to 3 hr for long tracks
    - run_23_filtIon        set memory usage to 30G

2. `stack_sentinel_cmd.sh`: the bbox `-b` is smaller than the image overlapping area in the SN direction

3. Remove the pairs with gaps using `-x` option in `stackSentienl-.py`from `S1_version.py` output

4. `stack_sentinel_cmd.sh`: add  `--polarization hh` for Antartica data (HH polarization)

5. `analysis_time.py`: If re-submitting jobs, go ahead and erase the redundant header rows in the log files `time_unix.txt` and `timing.txt`.

