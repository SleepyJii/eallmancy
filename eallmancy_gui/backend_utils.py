
import networkx as nx
from collections import defaultdict

def _add_graph_positioning(gr):

    srtd_nodes = list(sorted(list(gr.nodes(data=True)), key=lambda nt: nt[1]['artifact'].timestamp))

    for node in gr.nodes:
        gr.nodes[node]['Yrank'] = -1
    
    _MAX_ROW_WIDTH = 4
    _last_maxed_row = -1
    _row_satur = defaultdict(lambda : 0)
    _last_row = -1
    for nid, ndd in srtd_nodes:
        # must be after all parents
        _max_parent_yrank = max([gr.nodes[parent]['Yrank'] for parent in gr.predecessors(nid)] + [-1])

        # must also be after all maxed out rows
        new_rank = max(_last_maxed_row + 1, _max_parent_yrank + 1, _last_row)

        _row_satur[new_rank] += 1
        if _row_satur[new_rank] == _MAX_ROW_WIDTH:
            _last_maxed_row = new_rank

        gr.nodes[nid]['Yrank'] = new_rank
        _last_row = new_rank
        
    n_r = defaultdict(lambda : 0)
    for nidx, ndd in gr.nodes(data=True):
        gr.nodes[nidx]['Xrank'] = n_r[ndd['Yrank']]
        n_r[ndd['Yrank']] += 1
    return gr


def _add_fitness_rank(gr):
    
    srtd_nodes = list(sorted([(n, dd) for n, dd in gr.nodes(data=True) if dd['artifact'].is_solution], key=lambda nt: nt[1]['artifact'].fitness))
    idx = -1
    last_val = None
    for _, n in enumerate(srtd_nodes):
        this_val = gr.nodes[n[0]]['artifact'].fitness
        if last_val != this_val:
            idx += 1
        gr.nodes[n[0]]['fitness_rank'] = idx
        last_val = this_val
    
    return gr



def stringify_artid(idx: int):
    return f'A{idx}'

def _jsonify_art(ndd):
    art = ndd['artifact']
    # if not hasattr(art, 'is_flipped'): # maximally hacky switch from minimization to maximization
    #     art.is_flipped=True
    #     art.evaluation.fitness *= -1
    js = dict(id = stringify_artid(art.trace_id), artifact_type=str(type(art)).replace("<class '", "").replace("'>",""))

    if art.evaluation is not None:
        # TODO: handle min vs maximization in a better way
        js['evaluation'] = {'fitness': str(art.evaluation.fitness), 'fitness_rank': str(ndd['fitness_rank']), 'errors': str(art.evaluation.errors)}
    js['is_solution'] = art.is_solution
    if art.is_solution:
        js['program_lines'] = art.program.split('\n')

    if hasattr(art, 'solution_part_strs'):
        js['solution_parts'] = art.solution_part_strs

    js['artifact_repr'] = str(art)
    js['raw_response'] = art.raw_resp
    js['raw_prompt'] = art.raw_query
    return js

def _jsonify_edge(edg):
    source, target = edg
    return {'source': stringify_artid(source), 'target': stringify_artid(target)}


def _build_templ_lookup(templs):
    # actually not that hard, just want an index lookup.
    _map = defaultdict(lambda : [])
    for idx, templ in enumerate(templs):
        for sn in templ.solution_members():
            _map[sn].append(idx)
    return _map










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




from eallmancy.analysis.analyzer.tokenstr_handling import grab_programbody, _find_token_line_indices, _find_line_stidx
def _linenums_idx(prg):
    _nums = {0: 0}
    last = 0
    last_idx = 0
    while last+1 < len(prg):
        nxt = prg[last+1:].find('\n')
        if nxt == -1:
            break
        _nums[last_idx+1] = last+1 + nxt
        last_idx += 1
        last = last+1+nxt
    return _nums


def _jsonify_segms(segm_ls, t_idx, tcmp, trace):
    _program_str = trace[t_idx].program
    _linenums = _linenums_idx(_program_str)
    get_idx_linenum = lambda idx: max([k for k,v in _linenums.items() if v <= idx])+1
    program_str = grab_programbody(_program_str)
    bdy_idx = _program_str.find(program_str)
    bdy_offset_lines = get_idx_linenum(bdy_idx)+1
    tkn_list = tcmp['submissions'][t_idx]['tokenList']

    json_ls = []
    for s_entry in segm_ls:
        st_tkn, en_tkn = s_entry.start_token, s_entry.end_token
        st_tkn_linestart, en_tkn_lineend = _find_token_line_indices(program_str, st_tkn, en_tkn, tkn_list)
        nx_tkn_linestart = _find_line_stidx(program_str, tkn_list[min(en_tkn+1, len(tkn_list)-1)]['line']-1)
        treated_tkn_end = max(en_tkn_lineend,nx_tkn_linestart)

        json_ls.append({'start_line': get_idx_linenum(st_tkn_linestart)+bdy_offset_lines, 'end_line': get_idx_linenum(treated_tkn_end)+bdy_offset_lines})
    return json_ls

def _jsonify_segm_templ(templ, tcmp, trace):
    _json = {
        sn: _jsonify_segms(templ.get(sn), sn, tcmp, trace) for sn in templ.solution_members()
    }
    return _json






