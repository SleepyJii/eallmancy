

import numpy as np
import math
import networkx as nx



def _children(gr: nx.DiGraph, nds, n):
    res = []
    for kn in gr.successors(n):
        res.append(nds[kn])
    return res

def _parents(gr: nx.DiGraph, nds, n):
    res = []
    for kn in gr.predecessors(n):
        res.append(nds[kn])
    return res

def ancestor_mapdists(lineage_graph):
    return {
        n: {
            b: nx.shortest_path_length(lineage_graph, source=b, target=n)
            for b in nx.ancestors(lineage_graph, n).union({n})
        }
        for n in lineage_graph.nodes
    }

def latest_common_ancestor(G, u, v, ancestor_map=None):
    if ancestor_map is None:
        ancestor_map = {n: nx.ancestors(G, n).union({n}) for n in G.nodes}

    common = ancestor_map[u] & ancestor_map[v]
    if not common:
        return []  # No shared ancestors

    # The "latest" ones have no descendants in the common set
    latest = []
    for a in common:
        # If any descendant of a is also in common, a is not latest
        descendants = nx.descendants(G, a)
        if not any(d in common for d in descendants):
            latest.append(a)

    # Return set of latest common ancestors (can be multiple)
    return latest

def heritage_distance(lineage_graph, ancestor_mapdists, n, m):
    ancestor_map = {n: {xn for xn in ls.keys()} for n, ls in ancestor_mapdists.items()}
    lcas = latest_common_ancestor(lineage_graph, n, m, ancestor_map=ancestor_map)
    if lcas == []:
        return float('inf')
    else:
        # TODO: do something more careful than min
        lca, _ = min({(lca, ancestor_mapdists[n][lca]+ancestor_mapdists[m][lca]) for lca in lcas}, key=lambda ts: ts[1])
        return ancestor_mapdists[n][lca]+ancestor_mapdists[m][lca]

def heritage_distances(lineage_graph, _ancestor_mapdists=None):
    if _ancestor_mapdists is None:
        _ancestor_mapdists = ancestor_mapdists(lineage_graph)
    distances = dict()
    for ii, n in enumerate(lineage_graph.nodes):
        for m in list(lineage_graph.nodes)[:ii]:
            distances[(n,m)] = heritage_distance(lineage_graph, _ancestor_mapdists, n, m)
    return distances

