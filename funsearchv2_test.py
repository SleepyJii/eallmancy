

from reevo.problems.bpp_offline_aco.eval_jk import BPPoffACOEvaluator, promptdetails as BPPoffACO_prompts
from reevo.problems.cvrp_aco.eval_jk import CVRPACOEvaluator, promptdetails as CVRPACO_prompts
from reevo.problems.mkp_aco.eval_jk import MKPACOEvaluator, promptdetails as MKPACO_prompts
from reevo.problems.op_aco.eval_jk import OPACOEvaluator, promptdetails as OPACO_prompts
from reevo.problems.tsp_aco.eval_jk import TSPACOEvaluator, promptdetails as TSPACO_prompts

tasks = dict(
    bpp_offline_aco=(BPPoffACOEvaluator(), BPPoffACO_prompts),
    cvrp_aco=(CVRPACOEvaluator(), CVRPACO_prompts),
    mkp_aco=(MKPACOEvaluator(), MKPACO_prompts),
    op_aco=(OPACOEvaluator(), OPACO_prompts),
    tsp_aco=(TSPACOEvaluator(), TSPACO_prompts)
)


from algorithms.funsearch import funsearch, engine as fs_engine
import re

from eallmancy import ProblemSpec, evaluator as reallm_evaluator_func

probresults = dict()
for task_name, (task_fitness_evaluator, task_prompts) in tasks.items():

    # if task_name in ['bpp_offline_aco', 'op_aco', 'cvrp_aco', 'tsp_aco']:
    #     continue
    
    print(f'---==== TRYING {task_name} ====---')
    fs_engine.start_trace()

    res = funsearch(
        n_isles=2,
        max_time=60,
        problem_spec=ProblemSpec(
            description=task_prompts["func_desc"],
            template=task_prompts["func_signature"] + '\n\tpass',
            entrypoint="heuristic",
            evaluator=reallm_evaluator_func(task_fitness_evaluator.evaluate)
        )
    )

    tg, tl = fs_engine.dump_trace()
    probresults[task_name] = {
        'bestsoln': res,
        'tracegraph': tg,
        'tracelist': tl
    }
    
for i,j in probresults.items():
    print('PROBLEM',i)
    print(j['bestsoln'])
    print(i,j['bestsoln'].fitness)


