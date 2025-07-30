#!/bin/bash

#watch -n30 
optuna trials --study-name jobs --storage sqlite:////vol/bitbucket/jpk24/eallm_jobs.sqlite -f table $@

