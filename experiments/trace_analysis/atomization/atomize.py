
import numpy as np
from typing import Optional, List
from dataclasses import dataclass
from trace_analysis.atomization.match_atom import MatchAtom
from trace_analysis.atomization.solution_segment import SolutionSegment



def marginal_atomize_match(persp_id: int, existing_matches: List[MatchAtom], new_atom: MatchAtom):

    merging_atoms = [new_atom]
    while merging_atoms != []:
        new_atom = merging_atoms.pop()
        if new_atom.is_empty:
            continue
        
        new_atoms = []
        for eidx, e_matchatom in enumerate(existing_matches):
            e_segment = e_matchatom.get(persp_id)
            new_segment = new_atom.get(persp_id)

            if e_segment is None or new_segment is None:
                continue
            
            if new_segment.start_token > e_segment.end_token or new_segment.end_token < e_segment.start_token:
                continue

            if new_segment.start_token < e_segment.start_token:

                # splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.end_token)
                merging_atoms.append( new_atom.copy().set(persp_id, start_token=e_segment.start_token) )
                merging_atoms.append( new_atom.copy().set(persp_id, end_token=e_segment.start_token-1) )
                new_atoms = existing_matches #unchanged
                # print('\t',1)
                break # force loop restart
                
            elif new_segment.start_token > e_segment.start_token:
                splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.start_token-1)
                merging_atoms.append( new_atom )
                new_atoms.extend(existing_matches[:eidx]+[splitatom_b, splitatom_c]+existing_matches[eidx+1:])
                # print('\t',2)
                break
                
            else:
                # start tokens match, consider end tokens
                if new_segment.end_token < e_segment.end_token:
    
                    splitatom_b, splitatom_c = e_matchatom.split(new_segment.soln_id, new_segment.end_token)
                    merging_atoms.append( new_atom )
                    new_atoms.extend(existing_matches[:eidx]+[splitatom_b, splitatom_c]+existing_matches[eidx+1:])
                    # print('\t',3)
                    break
                    
                elif new_segment.end_token > e_segment.end_token:
                    merging_atoms.append( new_atom.copy().set(persp_id, end_token=e_segment.end_token) )
                    merging_atoms.append( new_atom.copy().set(persp_id, start_token=e_segment.end_token+1) )
                    new_atoms = existing_matches #unchanged
                    # print('\t',4)
                    break
            
                else:
                    # must have equality
                    e_matchatom.extend(new_atom)
                    new_atoms = existing_matches
                    # print('\t',5)
                    break
        else:
            # new segment has no overlap with existing atoms
            new_atoms = existing_matches
            new_atoms.append(new_atom)

        existing_matches = new_atoms

    return [em for em in existing_matches if em.get(persp_id) is not None]



def build_atomized_segments(tcmp):
    
    soln_atoms = {
        nn: [MatchAtom(entries=[
            SolutionSegment(nn, soln_length=nndd['numberOfTokens'], start_token=0, end_token=nndd['numberOfTokens']-1)
        ])]
        for nn, nndd in tcmp['submissions'].items()
    }
    soln_segms = {idx: segmddx for idx, segmddx in tcmp['comparisons'].items()}
    for (fn, sn), segm in tcmp['comparisons'].items():
        for segm_match in segm['matches']:
            new_atom = MatchAtom(entries=[
                SolutionSegment(
                    fn,
                    soln_length=tcmp['submissions'][fn]['numberOfTokens'],
                    start_token=segm_match['startOfFirst'],
                    end_token=segm_match['startOfFirst']+segm_match['length']-1,
                    original_segid=segm_match['id']
                ),
                SolutionSegment(
                    sn,
                    soln_length=tcmp['submissions'][sn]['numberOfTokens'],
                    start_token=segm_match['startOfSecond'],
                    end_token=segm_match['startOfSecond']+segm_match['length']-1,
                    original_segid=segm_match['id']
                ),
        
            ])
            # print(new_atom)
            soln_atoms[fn] = marginal_atomize_match(
                fn,
                soln_atoms[fn],
                new_atom
            )
            soln_atoms[sn] = marginal_atomize_match(
                sn,
                soln_atoms[sn],
                new_atom
            )
    return soln_atoms, soln_segms

