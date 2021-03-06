"""
PsyTrack to get time-varying psychophysical weights for each subject over learning
From: https://github.com/nicholas-roy/psytrack by Nick Roy and Jonathan Pillow
Ported to datajoint by Anne Urai, CSHL, 2020
"""

import pandas as pd
import numpy as np
import time
import datajoint as dj
from IPython import embed as shell

# import wrappers etc
from ibl_pipeline import subject, behavior, acquisition

# install this from https://github.com/nicholas-roy/psytrack
import psytrack

# ============================= #
# make a new custom schema for this
schema = dj.schema('group_shared_anneurai_psytrack')

@schema
class PsyTrack(dj.Computed):
    definition = """
    -> behavior.TrialSet.Trial()
    ---
    weight_bias:                         float
    weight_contrastleft:                 float
    weight_contrastright:                float 
    """

    # compute the model for each subject that has trials
    # for now, only subjects for which we expect no more data
    key_source = subject.Subject & subject.Death \
                 & (subject.SubjectProject &
                    'subject_project = "ibl_neuropixel_brainwide_01" OR subject_project = '
                    '"churchland_learninglifespan"') \
                 & behavior.TrialSet.Trial

    def make(self, key):

        print((subject.Subject & key).fetch1('subject_nickname'))

        # grab all trials for this subject & session
        trials = ((behavior.TrialSet.Trial & 'trial_response_choice != "No Go"') \
                 * acquisition.Session) & key

        stim_left, stim_right, resp, feedback, session_start_time, trial_id = trials.fetch(
            'trial_stim_contrast_left', 'trial_stim_contrast_right',
            'trial_response_choice', 'trial_feedback_type',
            'session_start_time', 'trial_id')

        # =================================== #
        # convert to psytrack format
        D = {'y': pd.DataFrame(resp)[0].replace({'CCW': 2, 'No Go': np.nan, 'CW': 1}).values}

        # inputs is itself another dictionary, containing arbitrary keys.
        # Each of these keys represents a potential input into the model and must be a
        # 2D array of shape $(N, M)$ where $N$ is the number of trials.
        # The number of columns $M$ is arbitrary, and the $i^{th}$ column is
        # typically used to encode information from $i$ time steps previous.
        p = 5
        D.update({'inputs': {'contrast_left': np.array(np.tanh(p * stim_left) / np.tanh(p))[:, None],
                             'contrast_right': np.array(np.tanh(p * stim_right) / np.tanh(p))[:, None]}})
        # grab the day boundaries to estimate that sigDay
        D.update({'dayLength': np.array(pd.DataFrame({'session_start_time':
                                                          session_start_time}).groupby(['session_start_time']).size())})
        print(D)

        # =================================== #
        # specify the weights to fit and hyperparameters
        weights = {'bias': 1, 'contrast_left': 1, 'contrast_right': 1}
        K = np.sum([weights[i] for i in weights.keys()])
        hyper_guess = {'sigma': [2 ** -5] * K, 'sigInit': 2 ** 5, 'sigDay': [2 ** -5] * K}
        optList = ['sigma']

        # =================================== #
        # FIT THE ACTUAL MODEL
        t = time.time()
        hyp, evd, wMode, hess_info = psytrack.hyperOpt(D, hyper_guess, weights, optList)
        elapsed = time.time() - t
        print('Elapsed time %fs' % elapsed)

        # =================================== #
        # INSERT INTO THE KEY FOR EACH TRIAL

        weights = []
        for i, days in enumerate(session_start_time):
            key.update(
                session_start_time = session_start_time[i],
                trial_id = trial_id[i],
                weight_bias = wMode[0][i],
                weight_contrastleft = wMode[1][i],
                weight_contrastright = wMode[2][i])
            weights.append(key.copy())

        print(weights)
        self.insert(weights)

# ============================= #
# POPULATE
PsyTrack.populate((subject.SubjectLab & 'lab_name = "churchlandlab"'), display_progress=True)
