

# from base.config import Config
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path
import asyncio


async def _start_evolve(app_state):
    print("EALLMancy STARTING")
    print('config is ',app_state.config)
    asyncio.create_task(app_state.eallmancer.run(app_state.config))
    return {'status': 'success'}

async def _stop_evolve(app_state):
    print("EALLMancy STOPPING")
    await app_state.eallmancer.kill()
    return {'status': 'success'}


async def _get_timestamps(app_state):
    _ema_timestamp = await app_state.eallmancer.get_trace_timestamp()
    trace_timestamp = _ema_timestamp
    status_timestamp = max(_ema_timestamp, app_state.config_updated_timestamp)
    res = {
        "status": {"timestamp": status_timestamp},
        "trace": {"timestamp": trace_timestamp},
    }
    return res




async def _get_status(app_state):
    # _trace = await app_state.eallmancer.get_trace()
    return {
        "timestamp": datetime.utcnow().timestamp(),
        "has_config": app_state.config is not None,
        "is_running": await app_state.eallmancer.is_running(),
        "has_trace": await app_state.eallmancer.has_trace(),
        "trace_is_live": await app_state.eallmancer.trace_is_live()
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


async def _get_trace(app_state):
    _empty_trace = { # default empty trace
            "timestamp": datetime.utcnow().timestamp(),
            "graph": {"nodes": [], "edges": []},
        }

    # TODO: uncomment after testing
    if not await app_state.eallmancer.has_trace():
        return _empty_trace
    
    tracegraph = await app_state.eallmancer.get_trace()
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


_ALGOS = {
    "gitdiff": ["EOH_git"],
    "thinkhard": ["EOH_git"]
}

def _get_algorithms(algo_type):
    print('looking for', algo_type,'in',_ALGOS)
    return _ALGOS.get(algo_type, None)

def _submit_config(app_state, payload):
    payload = json.loads(payload)
    descr = payload.get('description', '')
    algo = payload.get('algorithm', '')
    algo_type = payload.get('algo_type', '')
    
    errors = {}

    if algo_type == 'gitdiff':
        repo_path = payload.get('repoPath', '')
        evalscript = payload.get('evalScript', '')
        
        if repo_path.strip() == '' or not Path(repo_path.strip()).exists():
            errors["repoPath"] = f"`{repo_path}` is not a valid directory"
        if evalscript.strip() == '' or not Path(evalscript.strip()).is_file():
            errors["evalScript"] = f"`{evalscript}` is not a valid file"

    elif algo_type == 'thinkhard':
        evaluation_prompts = payload.get('evaluation_prompts', [])
        evaluation_prompts = [ep for ep in evaluation_prompts if ep['description']!='']
        evaluation_prompts = [ep for ep in evaluation_prompts if ep['name']!='']
        if evaluation_prompts == []:
            errors['evaluation_prompts'] = "No non-empty evaluation prompts provided"

    if len(descr.strip()) == 0:
        errors["description"] = "No description provided"
    if algo not in _ALGOS[algo_type]:
        errors["algorithm"] = f"Unknown algorithm {algo}"
    
    if errors:
        raise Exception(str(errors))
    

    app_state.config = payload
    app_state.config_updated_timestamp = datetime.utcnow().timestamp()

    print("CONFIG SET SUCCESSFULLY")
    return {"status": "success"}




async def msg_worker(msg_q, app_state):
    _conn_manager = app_state.conn_manager
    worker_id = id(asyncio.current_task())

    try:
        while True:
            task = await msg_q.get()

            client_id = task.get('client_id', None)
            msg_type = task['type']
            msg_payload = task.get('payload', None)
            print(f'[W{worker_id}]',task)

            if msg_type == 'GET_TIMESTAMPS':
                pl = await _get_timestamps(app_state)
                await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=pl))
            elif msg_type == 'GET_STATUS':
                pl = await _get_status(app_state)
                await _conn_manager.send_to(client_id, dict(type='STATUS_UPDATE', payload=pl))
            elif msg_type == 'GET_TRACE':
                pl = await _get_trace(app_state)
                await _conn_manager.send_to(client_id, dict(type='FULL_TRACE_UPDATE', payload=pl))
            elif msg_type == 'GET_ALGOS':
                algo_type = msg_payload.get('algo_type', 'gitdiff')
                await _conn_manager.send_to(
                    client_id,
                    dict(
                        type='ALGORITHMS_UPDATE',
                        payload={'algo_type':algo_type, 'algos':_get_algorithms(algo_type)}
                    )
                )
            elif msg_type == 'START_EA':
                await _start_evolve(app_state)
                await msg_q.put({'client_id': client_id, 'type': 'GET_STATUS'})
                # await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_status(app_state)))
            elif msg_type == 'STOP_EA':
                await _stop_evolve(app_state)
                await msg_q.put({'client_id': client_id, 'type': 'GET_STATUS'})
                # await _conn_manager.send_to(client_id, dict(type='TIMESTAMP_UPDATE', payload=_get_status(app_state)))
            elif msg_type == 'SUBMIT_CONFIG':
                try:
                    _submit_config(app_state, msg_payload)
                    await _conn_manager.send_to(client_id, dict(type='CONFIG_UPDATE', payload=[]))
                    print("initiated CONFIG_UPDATE ping")
                except Exception as e:
                    print(e)
                    print('config submit failed')
                    
            else:
                print('unknown msg type',msg_type)
    except Exception as e:
        print('failed with',e)

