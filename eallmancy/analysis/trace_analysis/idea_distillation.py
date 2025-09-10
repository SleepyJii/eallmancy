
import re
import math
from typing import Dict, List
import networkx as nx
from statistics import median

from eallmancy.artifacts.artifact import Artifact
from eallmancy.analysis.trace_analysis.atomization import MatchAtom
from eallmancy.analysis.trace_analysis.segm_printing import simple_segm_substr



class DistilledIdeaClusters(Artifact):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.is_solution = False
        
        self.clusters = self._parse_md_block(response)
    
    @staticmethod
    def _parse_md_block(rawtxt):
        
        md_blocks = re.findall(r'```[^\n]*\n(.*?)```', rawtxt, re.DOTALL)
        if len(md_blocks) == 0:
            return dict()
        md_block = md_blocks.pop()
        entries = []
        # iterate through MD list entries, expecting - [1,23] descr
        for grp_ls, grp_descr in re.findall(r'- (\[[^\]]*\])([^\-]*)[\n,$]', md_block):

            if len(grp_descr) < 10:
                raise Exception('debug')

            try:
                # scrape out ints in a [1,2,3] list
                grp_ids = re.findall(r'^\[([^\]]+)', grp_ls).pop().replace(' ','').split(',')
                grp_ids = list(map(int, grp_ids))
                
                entries.append( (frozenset(grp_ids), grp_descr.replace("\n","")) )
            except Exception as e:
                continue
        
            
        return {k:v for k,v in entries}
    
    @property
    def entries(self):
        return self.clusters

def _prmpt_print_atom(atm, ttrace, subm_stats):

    str_lines = []
    for xxx, s_entry in enumerate(atm.entries):
        if not xxx==0:
            str_lines.append('------------------------------'*2)

        prelude = f"Solution {s_entry.soln_id}"
        text = (simple_segm_substr(
            ttrace[s_entry.soln_id].program,
            s_entry.start_token, s_entry.end_token,
            subm_stats['submissions'][s_entry.soln_id]['tokenList']
        ))
        str_lines.append(prelude)
        str_lines.append(text)
    return ('\n'.join(str_lines))


def distill_atom_clusters(atm, ttrace, engine, tcmp: Dict):

    emptyidc = DistilledIdeaClusters("")
    emptyidc.clusters = {frozenset(atm.solution_members()): ''}
    return emptyidc

    prmpt = f"""
A team of scientists have been working on implementations of the following function:
```\n{engine._problem_spec.template}```

After some analysis, we have noticed some similar code segments across several solutions:
{_prmpt_print_atom(atm, ttrace, tcmp)}

Analyzing the code segments above, provide a list of clustered similar code segments and a summary of their unifying ideas.
This list should be in markdown format starting with solution indices in a code block, like in the example below (with lorem ipsum taking the spot of the verbal analysis)
```
- [22,37,45] lorem ipsum dolor sit amit
```
"""
    art, _ = engine.build_artifact(prmpt, DistilledIdeaClusters, register=False)
    return art


NEWL_ = "\n"

def _snippet_tag(solnid, snip):
    return f"Solution {solnid} [SNIPPET]{NEWL_}```{snip}```"

class DistilledIdea(Artifact):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, **kwargs)

        self.is_solution = False
        self.solution_members = []
        self.originating_atom = None
        self.snippets = dict()
    
    @property
    def snippets_str(self):
        return '\n'.join([_snippet_tag(k, v) for k, v in self.snippets.items()])
        # return '\n'.join(list(self.snippets.values()))

    @property
    def analysis(self):
        return self.raw_resp
    
    def proxy_fitness(self, graph_nodes) -> float:
        # figure out how we should consider the 'fitness' of this distilled idea
        # naive float return, treated like a fitness for purposes of scievo parent selection
        ftns = [graph_nodes[m]['artifact'].fitness for m in self.solution_members]
        ftns = [f for f in ftns if not math.isinf(f)]
        if len(ftns) == 0:
            return median([d['artifact'].fitness for n,d in graph_nodes.items()])
        else:
            return sum(ftns) * 1.0 / len(ftns)

    def __str__(self):
        return f"""
[[DistilledIdea {self.trace_id}]]

[Code]
{self.snippets_str}

[Analysis]
{self.analysis}
"""

def build_idea_distillation(atm, ttrace, engine, tcmp):

    def _grab_snippet(s_entry):
        return (simple_segm_substr(
            ttrace[s_entry.soln_id].program,
            s_entry.start_token, s_entry.end_token,
            tcmp['submissions'][s_entry.soln_id]['tokenList']
        ))
    
    # pprint = _prmpt_print_atom(atm, ttrace, tcmp)
    all_snippets = {e.soln_id: _grab_snippet(e) for e in atm.entries}
    pprint = NEWL_.join([_snippet_tag(k, v) for k, v in all_snippets.items()])
    prmpt = f"""
A team has been working on implementations of the following function:
```\n{engine._problem_spec.template}```

They have produced many prototypes, see pertinent examples below:
{NEWL_.join([f'{ttrace[sidx]}' for sidx in atm.solution_members()])}

After some analysis, we have noticed the following code snippets are very similar:
{pprint}

Without referencing any specific solutions by id, specify the core formulas or algorithmic concepts present in the code snippets as a cluster of implementation concepts.
You should specify any commonly appearing formulas - assume the reader cannot see the original snippets. 
Your explanation should make clear how implementations containing a matching code snippet would differ from other implementations, and the role that the similar code snippets have with regards to their originating prototypes. Do not give qualitative feedback.

EXAMPLE1 (your answer can be longer than these as necessary, but with similar content):
```
The cluster's members use SOME_FUNCTION to adjust SOME_PARAMETER in the following form `EQUATION_HERE`.
Variations can include SOME_MODIFICATION, SOME_OTHER_MOD, or SOMETHING_ELSE.
```

EXAMPLE2
```
The cluster's members are implemented as SOME_CODE_STRUCTURE, where SOME_CHARACTERISTIC is frequently present.
Examples for SOME_DETAIL include SOME_METHOD_A, SOME_METHOD_B, or SOME_METHOD_C.
```

Make sure to keep your focus on the content of the code snippets, using the overall solutions only for contextual details.
Do not give markdown headers, just provide your analysis in several or fewer short paragraphs along with equations or short code examples.
"""
    art, _ = engine.build_artifact(prmpt, DistilledIdea, register=False)
    art.solution_members = atm.solution_members()
    art.originating_atom = atm.copy()
    art.snippets = all_snippets

    # TODO: remove registration! really should be handled elsewhere...

    # keep it, gives trace_id's
    engine.register_artifact(art, parents=[ttrace[p] for p in art.solution_members], disable_hooks=True, operation_name="IdeaDistillation")

    return art


