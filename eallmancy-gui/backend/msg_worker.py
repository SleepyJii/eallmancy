

from base.config import Config
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path


def _start_evolve(app_state):
    print("EALLMancy STARTING")
    print('config is ',app_state.config)
    app_state.eallmancer.run(app_state.config)
    return {'status': 'success'}

def _stop_evolve(app_state):
    print("EALLMancy STOPPING")
    app_state.eallmancer.stop()
    return {'status': 'success'}


def _get_timestamps(app_state):
    _ema_timestamp = app_state.eallmancer.get_trace_timestamp()
    trace_timestamp = _ema_timestamp
    status_timestamp = max(_ema_timestamp, app_state.config_updated_timestamp)
    res = {
        "status": {"timestamp": status_timestamp},
        "trace": {"timestamp": trace_timestamp},
    }
    return res




def _get_status(app_state):
    _trace = app_state.eallmancer.get_trace()
    return {
        "timestamp": datetime.utcnow().timestamp(),
        "has_config": app_state.config is not None,
        "is_running": app_state.eallmancer.is_running,
        "has_trace": app_state.eallmancer.has_trace,
        "trace_is_live": app_state.eallmancer.trace_is_live
    }


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
    
    srtd_nodes = list(sorted(list(gr.nodes(data=True)), key=lambda nt: nt[1]['artifact'].fitness))
    # srtd_nodes = [x for x in srtd_nodes if x[1]['fitness'] is not np.nan]
    # nan_nodes = [x for x in srtd_nodes if x[1]['fitness'] is not np.nan]
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
    art.evaluation.fitness *= -1
    js = dict(id = stringify_artid(art.trace_id), artifact_type=str(type(art)).replace("<class '", "").replace("'>",""))
    if art.evaluation is not None:
        # TODO: handle min vs maximization in a better way
        js['evaluation'] = {'fitness': str(art.evaluation.fitness), 'fitness_rank': str(ndd['fitness_rank']), 'errors': str(art.evaluation.errors)}
    if hasattr(art, 'solution_part_strs'):
        js['solution_parts'] = art.solution_part_strs
    js['position'] = {'x_rank': ndd['Xrank'], 'y_rank': ndd['Yrank']}
    js['artifact_repr'] = str(art)
    js['raw_response'] = art.raw_resp
    js['raw_prompt'] = art.raw_query
    return js

def _jsonify_edge(edg):
    source, target = edg
    return {'source': stringify_artid(source), 'target': stringify_artid(target)}


def _get_trace(app_state):
    _empty_trace = { # default empty trace
            "timestamp": datetime.utcnow().timestamp(),
            "graph": {"nodes": [], "edges": []},
        }

    # TODO: uncomment after testing
    if not app_state.eallmancer.has_trace:
        return _empty_trace
    
    tracegraph = app_state.eallmancer.get_trace()
    if tracegraph is None:
        return _empty_trace

    enh_graph = _add_graph_positioning(tracegraph)
    enh_graph = _add_fitness_rank(enh_graph)

    # we need to parse the trace as GUI-friendly JSON
    _nodes = [_jsonify_art(ndd) for _, ndd in enh_graph.nodes(data=True)]
    _edges = [_jsonify_edge(edg) for edg in enh_graph.edges]
    
    res = {
        "timestamp": datetime.utcnow().timestamp(),
        "graph": {"nodes": _nodes, "edges": _edges},
    }
    return res


_ALGOS = ["EOH_git"]


def _get_algorithms():
    return _ALGOS

def _submit_config(app_state, payload):
    print(payload)
    payload = json.loads(payload)
    print(payload)
    repo_path = payload.get('repoPath', '')
    evalscript = payload.get('evalScript', '')
    descr = payload.get('description', '')
    algo = payload.get('algorithm', '')
    
    errors = {}

    # verify repo and evalscript paths are valid
    if repo_path.strip() == '' or not Path(repo_path.strip()).exists():
        errors["repoPath"] = f"`{repo_path}` is not a valid directory"
    if evalscript.strip() == '' or not Path(evalscript.strip()).is_file():
        errors["evalScript"] = f"`{evalscript}` is not a valid file"

    # make sure description is not actually empty
    if len(descr.strip()) == 0:
        errors["description"] = "No description provided"

    # make sure algo is populated
    if algo not in _ALGOS:
        errors["algorithm"] = f"Unknown algorithm {algo}"
    
    if errors:
        raise Exception(str(errors))
    

    app_state.config = Config(
        repoPath=repo_path,
        evalScript=evalscript,
        description=descr,
        algorithm=algo,
        overwrite=payload.get('overwrite', False)
    )
    app_state.config_updated_timestamp = datetime.utcnow().timestamp()

    print("CONFIG SET SUCCESSFULLY:", app_state.config)
    return {"status": "success"}




async def msg_worker(msg_q, app_state):
    _conn_manager = app_state.conn_manager

    while True:
        task = await msg_q.get()

        
        client_id = task.get('client_id', None)
        msg_type = task['type']
        msg_payload = task.get('payload', None)

        if msg_type == 'GET_TIMESTAMPS':
            await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_timestamps(app_state)))
        elif msg_type == 'GET_STATUS':
            await _conn_manager.send_to(client_id, dict(type='STATUS_UPDATE', payload=_get_status(app_state)))
        elif msg_type == 'GET_TRACE':
            await _conn_manager.send_to(client_id, dict(type='FULL_TRACE_UPDATE', payload=_get_trace(app_state)))
        elif msg_type == 'GET_ALGOS':
            await _conn_manager.send_to(client_id, dict(type='ALGORITHMS_UPDATE', payload=_get_algorithms()))
        elif msg_type == 'START_EA':
            _start_evolve(app_state)
            await msg_q.put({
                'type': 'WHILE_RUN_HACK_PING',
                'client_id': client_id,
                'reqtime': (datetime.utcnow() + timedelta(seconds=1)).timestamp()
            })
            # await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_status(app_state)))
        elif msg_type == 'STOP_EA':
            _stop_evolve(app_state)
            # await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_status(app_state)))
        elif msg_type == 'SUBMIT_CONFIG':
            try:
                _submit_config(app_state, msg_payload)
            except Exception as e:
                print(e)
                print('config submit failed')
            else:
                await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_timestamps(app_state)))
        # elif msg_type == 'WHILE_RUN_HACK_PING':
        #     if task['reqtime'] < datetime.utcnow().timestamp():
        #         print('HACKYPOLL during run')
        #         await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_timestamps(app_state)))

        #         # IF STILL RUNNING, REPEAT
        #         if app_state.eallmancer.is_running():
        #             print('\tstill running, hacky poll recurring')
        #             task.update({'reqtime': (datetime.utcnow() + timedelta(seconds=1)).timestamp()})
        #             await msg_q.put(task)
        #         else:
        #             print('\tno longer running, hacky poll ended')
            # else:
            #     await msg_q.put(task)
        else:
            print('unknown msg type',msg_type)


