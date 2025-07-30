#!/bin/bash

exec /vol/bitbucket/jpk24/venvs/gputraining/bin/python \
	/homes/jpk24/workkit/generalized_worker.py \
		--sqlite_path sqlite:////vol/bitbucket/jpk24/eallm_jobs.sqlite \
		--backoff_min 0 \
		--idle_backoff_min 20 $@

