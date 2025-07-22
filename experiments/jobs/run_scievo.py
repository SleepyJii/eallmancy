#!/bin/bash

""":"

extendPYTHONPATH() { PYTHONPATH="$1:$PYTHONPATH";export PYTHONPATH; }

# make tmp dir
WORKDIR=$(mktemp -d -t eallmantic)
trap "rm -rf '$WORKDIR'" EXIT
if [[ ! "$WORKDIR" || ! -d "$WORKDIR" ]]; then
  echo "Could not create temp dir"
  exit 1
fi

# clone target branch to tmp dir
git clone --branch main /homes/jpk24/eallmancy "$WORKDIR/eallmancy"

# move into tmp dir
SCRIPT="$(readlink -f $0)" # gotta do this before changing directories
cd $WORKDIR

# update PYTHONPATH?
extendPYTHONPATH "$WORKDIR/eallmancy"
extendPYTHONPATH "$WORKDIR/eallmancy/experiments"

## LAUNCHING JPLAG API FOR SCRIPT
/homes/jpk24/jplag-api/bg-jplag-api.sh "$$" &

# become a python script now
exec /vol/bitbucket/jpk24/venvs/eallmancy/bin/python3 $SCRIPT $@
" """


print('running sim in Python')

import sys
import os


from experiments.toyeoh import ToyEoH
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

GEMINI_25FLASH_API = dict(
            base_url='https://generativelanguage.googleapis.com/v1beta',
#            api_key=os.environ.get('GEMINI_API_KEY'),
            model='gemini-2.0-flash',
            timeout=20,
            openai_format=True
        )


llms_to_run = {
    '4omini': CHATGPT_4OMINI_API,
    # 'gemini25f': GEMINI_25FLASH_API
}

ps_to_test = [

    CarMountainProblemSpec(maximization=True),
]

import asyncio
from experiments.scievo2 import SciEvo

async def scievo_proto(problem_spec, api, max_samples=200):
    eallm = SciEvo(
        api=api,
        ps=problem_spec,
        config=dict(
            max_samples=max_samples,
            min_match_members=2,
            min_match_tokens=5
        )
    )

    best_soln, fancypop, trace = await eallm.run()
    return best_soln, fancypop, trace


ps = CarMountainProblemSpec(maximization=True)
# ps = StressTrainProblemSpec(maximization=True)
temp = 0.75
llm_api = CHATGPT_4OMINI_API


#with timeme():
print('starting simulation')
best_soln, pop, trace = asyncio.run(
        scievo_proto(ps, api=dict(temperature=temp, **llm_api), max_samples=20,)
    )


trace.save(f'/vol/bitbucket/jpk24/test_trace2.pk')


