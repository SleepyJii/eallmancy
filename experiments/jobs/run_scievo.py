#!/bin/bash

""":"

extendPYTHONPATH() { PYTHONPATH="$1:$PYTHONPATH";export PYTHONPATH; }

# make tmp dir
WORKDIR=$(mktemp -d /tmp/eallmancy.XXXXXXXXXXX)
if [[ ! "$WORKDIR" || ! -d "$WORKDIR" ]]; then
  echo "Could not create temp dir"
  exit 1
fi

# clone target branch to tmp dir
git clone --branch thesis /homes/jpk24/eallmancy "$WORKDIR/eallmancy"

# move into tmp dir
SCRIPT="$(readlink -f $0)" # gotta do this before changing directories
cd $WORKDIR
echo "now running job from $WORKDIR"

# update PYTHONPATH?
extendPYTHONPATH "/homes/jpk24/eallmancy"
extendPYTHONPATH "$WORKDIR/eallmancy"
extendPYTHONPATH "$WORKDIR/eallmancy/experiments"

## LAUNCHING JPLAG API FOR SCRIPT
/homes/jpk24/jplag-api/bg-jplag-api.sh "$$" &

## load in API keys
source /homes/jpk24/api_aliases

# run myself in python now
/vol/bitbucket/jpk24/venvs/eallmancy/bin/python3 $SCRIPT $@
jobstatus=$?

rm -rf $WORKDIR
echo "deleted $WORKDIR"
exit $jobstatus

" """


print('running sim in Python')

import sys
import os
print(os.getcwd())


from experiments.toyeoh import ToyEoH
import problems
from problems.llm4ad import (
    CarMountainProblemSpec,
    PendulumProblemSpec,


    StressTrainProblemSpec,
    BactGrowProblemSpec,

    AdmissibleSetProblemSpec,
    VRPTWProblemSpec
)






CHATGPT_4OMINI_API = dict(
            host="api.openai.com",
            key=os.environ.get('OPENAI_API_KEY'),
            model="gpt-4o-mini",
            timeout=20
        )
CHATGPT_4O_API = dict(
            host="api.openai.com",
            key=os.environ.get('OPENAI_API_KEY'),
            model="gpt-4o",
            timeout=20
        )
CHATGPT_41_API = dict(
            host="api.openai.com",
            key=os.environ.get('OPENAI_API_KEY'),
            model="gpt-4.1-2025-04-14",
            timeout=20
        )
GEMINI_25FLASH_API = dict(
            base_url='https://generativelanguage.googleapis.com/v1beta',
           api_key=os.environ.get('GEMINI_API_KEY', ''),
            model='gemini-2.0-flash',
            timeout=20,
            openai_format=True
        )
llms_to_run = {
    '4omini': CHATGPT_4OMINI_API,
    '4o': CHATGPT_4O_API,
    '4.1': CHATGPT_41_API,
    'gemini25f': GEMINI_25FLASH_API,
}

def fetch_problem(pname):
    return getattr(problems, pname)(maximization=True)


## ARGS FOR JOB HOOKUPS
import argparse

parser = argparse.ArgumentParser()
DEFAULT_OUTP_PATH = f'/vol/bitbucket/jpk24/trace.pk'
parser.add_argument('problem', type=str)
parser.add_argument('--max_samples', type=int, default=20)
parser.add_argument('--max_generations', type=int, default=int(1e9))
parser.add_argument('--population_size', type=int, default=10)
parser.add_argument('--temperature', type=float, default=0.75)
parser.add_argument('--llm', type=str, default='4omini')
parser.add_argument('--output_path', type=str, default=DEFAULT_OUTP_PATH,)
args, _ = parser.parse_known_args()


## SIMULATION TIME
import asyncio
from experiments.scievo2.main import SciEvo


temp = args.temperature
llm_api = llms_to_run.get(args.llm)#CHATGPT_4OMINI_API



async def scievo_proto(problem_spec, api, max_samples=200, **kwargs):
    eallm = SciEvo(
        api=api,
        ps=problem_spec,
        config=dict(
            max_samples=max_samples,
            min_match_members=2,
            min_match_tokens=5,
            **kwargs
        )
    )

    best_soln, fancypop, trace = await eallm.run()
    return best_soln, fancypop, trace

print('starting simulation')
best_soln, pop, trace = asyncio.run(
        scievo_proto(
            problem_spec=fetch_problem(args.problem),
            api=dict(temperature=temp, **llm_api),
            max_samples=args.max_samples,
        )
    )

## SAVE RESULTS
from pathlib import Path
Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
trace.save(args.output_path)


