#!/bin/bash

~/bitbucket/venvs/gputraining/bin/python /homes/jpk24/workkit/submit_job.py $@ --optuna_db sqlite:////vol/bitbucket/jpk24/eallm_jobs.sqlite
