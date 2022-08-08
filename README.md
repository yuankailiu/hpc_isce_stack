# HPC_isce_stack


### Author: Oliver Stephenson, 2021


Scripts for submitting tops stack stages as a series of chained SLURM jobs
Each job uses SLURM arrays to manage the processing that can be done in parallel
Avoids the issue with wasting resources, hopefully deals better with very large numbers of jobs

The `resources_array.cfg` file gives the resources allocated to each array element, not to the whole job step combined

Different resource files are for different sized jobs - `resources_array_full_eff.cfg` is the efficient ('eff') allocation of resources for the full T115a track (25 to 32N)


## Optional before running processing codes
(ykliu 2022-03-08)

0. Run [`s1_select_ion.py`](https://github.com/isce-framework/isce2/tree/main/contrib/stack/topsStack#1-select-the-usable-acquistions) to filter your data acquisitions (SLC zip files). Acquisitions not satisfying the requirements would be put into a separate `not_used` folders and they are not used by `stackSentinel.py`. The filering is based on the:
    + IPF versions
    + Frames with different IPF versions
    + gaps between frames
    + starting ranges
    + latitude coverage

1. Use the appropriate .cfg for resourse allocation. Copy the customed .cfg to overwrite `resources_array.cfg`
    + run_16_unwrap         set to 3 hr for long tracks (more than 6~7 latitude degrees)
    + run_20_unwrap_ion     set to 3 hr for long tracks (more than 6~7 latitude degrees)
    + run_23_filtIon        set memory usage to 30G     (more than 6~7 latitude degrees)

2. `stack_sentinel_cmd.sh`: the bbox `-b` corresponds to the `-b` argument in `stackSentinel.py`. It will process all frames that intersect with this bbox.

3. Remove extra pairs by using `-x` option in `stackSentienl.py`.

4. `stack_sentinel_cmd.sh`: add  `--polarization hh` for Antartica data (HH polarization)

5. `analysis_time.py`: If re-submitting jobs, go ahead and erase the redundant header rows in the log files `time_unix.txt` and `timing.txt`.

