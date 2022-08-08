# Python script to analyse topsStack run times, based on output timings files for Caltech HPC processing
# 
# Relies on other analysis scripts written by Ollie 

# TODO 
# This script fails if we we run it on a job where we've restarted the processing at some point - could adjust code to deal with this

import pandas as pd 
import datetime
import numpy as np
from datetime import timedelta
import matplotlib.pyplot as plt 

def format_td(seconds, digits=1):
    ''' Function for formatting digits on timedeltas'''
    # Deal with Not a Times 
    if seconds == pd.NaT:
        return pd.NaT
    isec, fsec = divmod(round(seconds*10**digits), 10**digits)
    if digits == 0:
        out = f'{timedelta(seconds=isec)}' 
    elif digits > 0:
        out = f'{timedelta(seconds=isec)}.{fsec:0{digits}.0f}' 
    else:
        raise Exception('{} digits not allowed'.format(digits))
    return out 




# Input timings in unix time (seconds since 1970)
infile = './log_files/time_unix.txt'
# infile = '/central/groups/simonsgroup/olstephe/insar/makran/T115a/process_stack_small_cto_2/run_files/time_unix.txt'

# Read the start time 
with open(infile) as f:
    firstline = f.readline().rstrip()
sub_time = firstline[20:]

# Convert to datetime
sub_time = pd.to_datetime(sub_time,unit='s')

df = pd.read_table(infile,names=['Step','Job ID','Slurm array','Start','Finish','Elapsed'],delim_whitespace=True,skiprows=2)
# df.columns = df.columns.str.replace('#', '') # Remove comment character from column names

# Convert unix timestamps to datetime objects 
df['Start']=pd.to_datetime(df['Start'],unit='s')
df['Finish']=pd.to_datetime(df['Finish'],unit='s')
df['Elapsed']=pd.to_timedelta(df['Elapsed'],unit='s')

# Calculate the run time for each stage 

stages = df['Step'].unique()
stage_elapsed = []
stage_std = []
stage_mean = [] # If mean + std is very different from elapsed that suggests lots of arrays have been queuing 
stage_start = []
stage_finish = []
stage_queue_time = []
stage_num_jobs = []
job_ids = []

for stage in stages:
    stage_df = df.loc[df['Step']==stage]
    num_jobs = len(stage_df.index)
    
    # Get Job ID for each stage
    job_ids.append(stage_df['Job ID'].unique()[0])

    # Find the earliest start and latest finish for each stage
    start = stage_df['Start'].min()
    finish = stage_df['Finish'].max()
    elapsed = finish - start
    std = stage_df['Elapsed'].std()
    mean = stage_df['Elapsed'].mean()

    # Save 
    stage_elapsed.append(elapsed)
    stage_start.append(start)
    stage_finish.append(finish)
    stage_std.append(std)
    stage_mean.append(mean)
    stage_num_jobs.append(num_jobs)

# Store summary data for each stage in a new dataframe
data = {'Step':stages,
        'Start':stage_start,
        'Finish':stage_finish,
        'Total elapsed':stage_elapsed,
        'Array mean':stage_mean,
        'Array std':stage_std,
        'Num jobs':stage_num_jobs,
        'Job ID':job_ids
        }

summary_df = pd.DataFrame(data)


# We want to calculate the wait time for each stage to start 
# Note that we can have many wait times - every element of the array has to wait 
# We can compare the total elapsed to the mean and std for the array elements to see how long the stage took compared to the individual elements 
# This can tell us how many elements were running at one time on average



# Calculate total run time
total_run_time = summary_df['Total elapsed'].sum()

# Calculate time from submission to completion
end_time=summary_df.iloc[-1]['Finish']
total_time = end_time-sub_time

# Calculate the total queue time 
total_queue_time = total_time-total_run_time

# Calculate the queue time for each stage

# Initial queue time 
init_q = summary_df.iloc[0]['Start']-sub_time

# Calculate start of row - finish of previous row 
# NOTE - this is just the queue time between stages. It doesn't take into account the queue time for each array element during processing 
# So this is basically the time where nothing is running at all
summary_df['Queue time'] = summary_df['Start']-summary_df['Finish'].shift()
summary_df.at[0,'Queue time'] = init_q



# # Write total run time to file in a convenient format 
# fname='simple_runtime_summary.txt'

# # Convert timedelta into string
# summary_df['elapsed string'] = summary_df['Total elapsed'].apply(
#         lambda x: f'{x.components.hours:02d}:{x.components.minutes:02d}:{x.components.seconds:02d}'
#             if not pd.isnull(x) else '')
# out_df = pd.concat([summary_df['elapsed string'],pd.Series(total_run_time)])
# out_df.to_csv(fname, header=False, index=False)

# #Save pandas dataframe to file
# summary_df.to_csv('./log_files/summary_timings.csv',sep='\t')
# # summary_df.to_pickle('./log_files/summary_timings.pkl')



## Calculate resources used
# Computation rate (cost for 1 hour of CPU?)
# See https://www.hpc.caltech.edu/rates
rate = 0.008

# Load resources file
res_infile = 'resources_array.cfg'

res_df = pd.read_table(res_infile,header=0,delim_whitespace=True)
res_df.columns = res_df.columns.str.replace('#', '') # Remove comment character from column names
summary_df['CPUs'] = np.nan
summary_df['GPUs'] = np.nan
summary_df['CPU Units'] = np.nan
summary_df['Cost ($)'] = np.nan

## Loop through the stages and calculate the cost for each one
# Need summary_df and res_df to have corresponding rows - both referring to the same step of the procesing
for index, row in res_df.iterrows():
    summary_df.loc[index,'CPUs'] = int(row['Ncpus_per_task'])
    # TODO - read this automatically from the resources table rather than hardcoding the steps which use a GPU
    # Stages 5 and 9 can use the GPU currently
    if index == 4 or index == 8:
        summary_df.loc[index,'GPUs'] = 1
    else:
        summary_df.loc[index,'GPUs'] = 0

    hours = summary_df.loc[index,'Array mean'].seconds/3600
    num_jobs = summary_df.loc[index,'Num jobs']
    cpu_units = (row['Ncpus_per_task'] + summary_df.loc[index,'GPUs']*10)*num_jobs*hours 
    summary_df.loc[index,'CPU Units'] = cpu_units
    summary_df.loc[index,'Cost ($)'] = cpu_units*rate 

total_cost = summary_df['Cost ($)'].sum()
summary_df['CPUs'] = summary_df['CPUs'].astype(int)
summary_df['GPUs'] = summary_df['GPUs'].astype(int)


    # step_script = row['Step']
    # step_name = step_script[7:] # Strip number
    # step_num = step_script[4:6]


## Print summaries
outfile='formatted_summary_timings.txt'
# Print timings:
# TODO convert UTC to pacific time 
print('#####################################################')
print('# Summary timings')
print('# Job submitted at:    {} (UTC)'.format(sub_time))
print('# Total time:          {}'.format(total_time))
print('# Total run time:      {}'.format(total_run_time))
print('# Total queue time:    {}'.format(total_queue_time))
print('# Esimated cost:       ${:.2f}'.format(total_cost))
print('#####################################################')

# Save timings to file 
with open(outfile,'w') as f:
    f.write('#####################################################\n')
    f.write('# Summary timings\n')
    f.write('# Job submitted at:    {} (UTC)\n'.format(sub_time))
    f.write('# Total time:          {}\n'.format(total_time))
    f.write('# Total run time:      {}\n'.format(total_run_time))
    f.write('# Total queue time:    {}\n'.format(total_queue_time))
    f.write('# Esimated cost:       ${:.2f}\n'.format(total_cost))
    f.write('#####################################################\n')
    f.write('\n')

# Change formatting of timedeltas
for index, row in summary_df.iterrows():
    summary_df.loc[index,'Array mean'] = format_td(row['Array mean'].seconds,digits=0)
    # Replace NaTs with 0 
    if pd.isnull(row['Array std']):
        summary_df.loc[index,'Array std'] = 0
    else:
        summary_df.loc[index,'Array std'] = format_td(row['Array std'].seconds,digits=0)

# Write to formatted table 
use_cols = ['Step','Num jobs', 'Start', 'Finish', 'Total elapsed', 'Queue time', 'Array mean', 'Array std', 'CPUs', 'GPUs', 'Cost ($)']
with open(outfile,'a') as f:
    summary_df.to_string(f,columns=use_cols)


# Plot some figures

fig,ax1 = plt.subplots()
ax2=ax1.twinx()
width=0.4
summary_df['CPU Units'].plot(x='Step',kind='bar',color='red',ax=ax1,width=0.4,position=0)
# ax1.set_xticklabels(summary_df['Step'],rotation=45)
# summary_df['Total elapsed'].plot(kind='bar',color='blue',ax=ax2,width=0.4,position=1)
(summary_df['Total elapsed'].astype('timedelta64[s]')/3600).plot(x='Step',kind='bar',color='blue',ax=ax2,width=0.4,position=1)
ax1.set_ylabel('CPU Hours',color='red')
ax1.tick_params(axis='y',labelcolor='red')
ax2.set_ylabel('Wall time (Hours)',color='blue')
ax2.tick_params(axis='y',labelcolor='blue')
ax2.set_xticklabels(summary_df['Step'],rotation=45)
# plt.bar(x=summary_df.index+1,height=summary_df['CPU Units'])

plt.tight_layout()
plt.savefig('cpu_wall_time.pdf')
