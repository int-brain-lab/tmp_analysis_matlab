"""
Plot full psychometric functions as a function of choice history,
and separately for 20/80 and 80/20 blocks
"""

import pandas as pd
import numpy as np
import sys, os, time
import matplotlib.pyplot as plt
import seaborn as sns
import datajoint as dj
from IPython import embed as shell # for debugging
from scipy.special import erf # for psychometric functions
import datetime

## INITIALIZE A FEW THINGS
sns.set(style="darkgrid", context="paper", font='Arial')
sns.set(style="darkgrid", context="paper")
sns.set(style="darkgrid", context="paper", font_scale=1.3)

# import wrappers etc
from ibl_pipeline import reference, subject, action, acquisition, data, behavior
from ibl_pipeline.utils import psychofit as psy
from ibl_pipeline.analyses import behavior as behavioral_analyses
from dj_tools import *
import training_criteria_schemas as criteria_urai 

figpath  = os.path.join(os.path.expanduser('~'), 'Data/Figures_IBL')

# ================================= #
# 1. get training status from original DJ table
# ================================= #

use_subjects = subject.Subject() & 'subject_birth_date between "2018-09-01" and "2019-02-01"' & 'subject_line IS NULL OR subject_line="C57BL/6J"'
sess = behavioral_analyses.SessionTrainingStatus() \
 * use_subjects * subject.SubjectLab * subject.Subject.aggr(behavior.TrialSet, session_start_time='max(session_start_time)')

df = pd.DataFrame(sess.fetch(as_dict=True))
df2 = df.groupby(['training_status'])['subject_uuid'].count().reset_index()
# remove the erroneous mice
df2 = df2[~df2.training_status.str.contains("wrong session type run")]
df2 = df2.replace({'over40days': 'untrainable'})
df2 = df2.sort_values('training_status')
print(df2)

# QUICK PIE PLOT
plt.pie(df2['subject_uuid'], labels=df2['training_status'], autopct='%1.2f%%')
plt.suptitle('Total n = %d'%df2['subject_uuid'].sum())
plt.savefig(os.path.join(figpath, "training_success_original.pdf"))
plt.close('all')

# ================================= #
# 2. now do the same for my newly defined table
# ================================= #

sess = criteria_urai.SessionTrainingStatus() \
 * use_subjects * subject.SubjectLab * subject.Subject.aggr(behavior.TrialSet, session_start_time='max(session_start_time)')
df = pd.DataFrame(sess.fetch(as_dict=True))
df2 = df.groupby(['training_status'])['subject_uuid'].count().reset_index()
df2 = df2.sort_values('training_status')
print(df2)

plt.pie(df2['subject_uuid'], autopct='%1.2f%%', labels=df2['training_status'])
plt.suptitle('Total n = %d'%df2['subject_uuid'].sum())
plt.savefig(os.path.join(figpath, "training_success_urai.pdf"))
plt.close('all')
