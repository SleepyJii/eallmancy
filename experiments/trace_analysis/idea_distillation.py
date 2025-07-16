
import re
from typing import Dict, List

from trace_analysis.segm_printing import simple_segm_substr
from eallmancy.artifacts.artifact import Artifact
from eallmancy.engine.llm_solution_engine_v3 import EngineV3



class DistilledIdeaClusters(Artifact):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, **kwargs)
        self.is_solution = False
        
        self.clusters = self._parse_md_block(response)
    
    @staticmethod
    def _parse_md_block(rawtxt):
        
        md_block = re.findall(r'```[^\n]*\n(.*?)```', rawtxt, re.DOTALL).pop()
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


def distill_atom_clusters(atm, ttrace, engine: EngineV3, tcmp: Dict):
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

