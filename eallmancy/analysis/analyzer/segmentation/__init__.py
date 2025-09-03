
import requests
import backoff
import numpy as np
from collections import defaultdict
import itertools
from itertools import chain, count
import os
import re
from typing import Dict, List



def distinct_subsegments(atom_list, persp_id, soln_filter=None, neg_filter=False):
    """
    Yields contiguous sequences of atoms where:
      - the solution memberships intersect (non-trivially) with `soln_filter` (if provided),
      - and the combination of token interval & membership set is unique.
    """

    atom_list = sorted(atom_list, key=lambda a: a.get(persp_id).start_token)

    if soln_filter is None:
        matching_solns = [list({a.soln_id for a in a.entries}) for a in atom_list]
        all_matching_solns = set(chain(*matching_solns))
        soln_filter = all_matching_solns
    else:
        soln_filter = set(soln_filter).union({persp_id})

    def atom_memberships(atom):
        return set(e.soln_id for e in atom.entries if e.soln_id in soln_filter)

    seen_memberset_endings = defaultdict(lambda : [])
    last_membership = frozenset({})
    n = len(atom_list)

    for start in range(n):
        memberships = atom_memberships(atom_list[start])

        if neg_filter and min(atom_list[start].solution_members()) < 0:
            continue

        curr_memberships = frozenset(memberships.copy())
        
        if start <= max(seen_memberset_endings[frozenset(curr_memberships)], default=-1):
            # we've already seen an ending with these members in the future, so we are within old seg --> skip
            continue

        # extend until we see loss of a member
        for end in range(start+1, n):
            if len(curr_memberships) == 1:
                continue
            
            breakages = {
                m: (float('inf') if atom_list[end].get(m) is None else atom_list[end].get(m).start_token - atom_list[end-1].get(m).end_token - 1)
                for m in curr_memberships
            }
            lost_seg_members = { m for m, bv in breakages.items() if bv != 0 }
            if len(lost_seg_members) > 0:
                seen_memberset_endings[curr_memberships].append(end-1)
                yld_seq = [a.filter_solutions(soln_filter) for a in atom_list[start:end]]
                yield yld_seq, curr_memberships # these are solutions again.

                curr_memberships = curr_memberships.difference(lost_seg_members)
        else:
            if len(curr_memberships) != 1:
                end = min(end+1,n)
                seen_memberset_endings[curr_memberships].append(end)
                yld_seq = [a.filter_solutions(soln_filter) for a in atom_list[start:end]]
                yield yld_seq, list(set.intersection(*[set(a.solution_members()) for a in yld_seq]))

