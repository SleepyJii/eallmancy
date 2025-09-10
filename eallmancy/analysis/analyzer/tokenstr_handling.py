
def find_nth(haystack: str, needle: str, n: int) -> int:
    start = 0
    while start >= 0 and n >= 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start
    
def find_token_substr(program_str, token_dd):
    _linestidx = find_nth(program_str, '\n', token_dd['line']-1)
    return program_str[_linestidx + token_dd['column']:_linestidx + token_dd['column']+token_dd['length']]

def _find_line_stidx(program_str, line):
    if line == 0:
        _linestidx = 0 # jplag columns start at 1
    else:
        _linestidx = find_nth(program_str, '\n', line)+1
    return _linestidx

def _find_line_enidx(program_str, line):
    if line < 0:
        return None
    stidx = _find_line_stidx(program_str, line)
    return stidx + program_str[stidx:].find('\n')

def find_line_stidx(program_str, token_dd):
    if token_dd['line'] == 1:
        _linestidx = 0 # jplag columns start at 1
    else:
        _linestidx = find_nth(program_str, '\n', token_dd['line']-1)+1
    return _linestidx

def find_token_stidx(program_str, token_dd):
    return find_line_stidx(program_str, token_dd) - 1 + token_dd['column']



def find_tokenrange_substr(program_str, st_tkn, en_tkn, tkn_list):
    start_idx = find_token_stidx(program_str, tkn_list[st_tkn])
    if en_tkn == len(tkn_list)-1:
        end_idx = len(program_str)
    else:
        end_idx = find_token_stidx(program_str, tkn_list[en_tkn+1])
    return program_str[start_idx:end_idx]


def find_tokenrange_substrs(program_str, st_tkn, en_tkn, tkn_list):
    token_start_idxs = [find_token_stidx(program_str, tkn_list[idx]) for idx in range(st_tkn, en_tkn+1)]
    if en_tkn == len(tkn_list)-1:
        final_idx = len(program_str)
    else:
        final_idx = find_token_stidx(program_str, tkn_list[en_tkn+1])
    token_start_idxs.append(final_idx)
    return [program_str[st:en] for st, en in zip(token_start_idxs, token_start_idxs[1:])]

def _find_token_line_indices(program_str, st_tkn, en_tkn, tkn_list):
    st_tkn_linestart = _find_line_stidx(program_str,tkn_list[st_tkn]['line']-1)
    en_tkn_lineend = _find_line_enidx(program_str,tkn_list[en_tkn]['line']-1)

    if en_tkn_lineend is None:
        en_tkn_lineend = len(program_str)
    return st_tkn_linestart, en_tkn_lineend


def _find_token_line_nums(prgrm, st_tkn, en_tkn, tkn_list):
    st_tkn_cidx, en_tkn_cidx = _find_token_line_indices(
        prgrm, st_tkn, en_tkn, tkn_list
    )
    return len(prgrm[:st_tkn_cidx].split('\n')), len(prgrm[:en_tkn_cidx].split('\n'))



def _simple_segm_substr(program_str, st_tkn, en_tkn, tkn_list):
    st_tkn_linestart, en_tkn_lineend = _find_token_line_indices(program_str, st_tkn, en_tkn, tkn_list)
    nx_tkn_linestart = _find_line_stidx(program_str, tkn_list[min(en_tkn+1, len(tkn_list)-1)]['line']-1)
    return program_str[
    st_tkn_linestart:max(en_tkn_lineend,nx_tkn_linestart)
    ]



def _find_programbody_start(prog):
    fsig_idx = prog.find('def ')
    programbody_idx = fsig_idx + prog[fsig_idx:].find('\n')+1
    return programbody_idx

def grab_programbody(prog):
    return prog[_find_programbody_start(prog):]

def simple_segm_substr(trace, s_entry, tcmp):
    program_str = grab_programbody(trace[s_entry.soln_id].program)
    st_tkn, en_tkn = s_entry.start_token, s_entry.end_token
    tkn_list = tcmp['submissions'][s_entry.soln_id]['tokenList']
    st_tkn_linestart, en_tkn_lineend = _find_token_line_indices(program_str, st_tkn, en_tkn, tkn_list)
    nx_tkn_linestart = _find_line_stidx(program_str, tkn_list[min(en_tkn+1, len(tkn_list)-1)]['line']-1)
    treated_tkn_end = max(en_tkn_lineend,nx_tkn_linestart)
    # programbody_start = _find_programbody_start(program_str)
    return program_str[
    # max(st_tkn_linestart, programbody_start):max(treated_tkn_end, programbody_start)
    st_tkn_linestart:treated_tkn_end
    ]

# def simple_atom_substrs(atm, ttrace, subm_stats):
#     substrs = dict()
#     for xxx, s_entry in enumerate(atm.entries):
#         substrs.update({
#             s_entry.soln_id: simple_segm_substr(ttrace, s_entry, subm_stats)
#         })
#     return substrs




# def print_atom(atm, ttrace, subm_stats):
#     for xxx, s_entry in enumerate(atm.entries):
#         if not xxx==0:
#             print('------------------------------')
#         text = (_simple_segm_substr(
#             ttrace[s_entry.soln_id].program,
#             s_entry.start_token, s_entry.end_token,
#             subm_stats['submissions'][s_entry.soln_id]['tokenList']
#         ))
#         print(text)




# %%time

# has_printed = False
# for center_node, matching_nodes in centered_clusters.items():
#     subm_stats = clean_compare_many(**{str(mn): ttrace[mn].program for mn, _ in matching_nodes + [(center_node, None)]})
#     c_atoms = cluster_atoms[center_node]
#     for aid, atm in enumerate(c_atoms):
#         if atm.token_length() < 8:
#             continue
#         if has_printed:
#             print('=========================='*2)
#             print('=========================='*2)
#         has_printed=True
#         print_atom(atm, ttrace, subm_stats)
        
#         # for s_entry in atm.entries:
#         #     print_atom
#         #     s_entry.text = text

    