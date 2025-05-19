import networkx as nx
import matplotlib.pyplot as plt
# from algorithms.reevo import Reflection, DistilledReflection, Solution 

import matplotlib.patches as mpatches
from matplotlib.pyplot import get_cmap
import matplotlib.colors as mcolors

from eallmancy.engine_trace import EngineTrace


def _plot_graph(tg, node_colors=None):

    
    fig, ax = plt.subplots(figsize=(8, 6))
    pos = nx.circular_layout(tg)  # layout can be changed
    nx.draw(tg, pos, ax=ax, with_labels=True, node_color=node_colors, edge_color='black', node_size=300)
    plt.close(fig)
    
    return fig, ax


def plot_graph_typecolors(tg, colormap=dict()):
    artifact_classes = list({
        type(data['artifact'])
        for _, data in tg.nodes(data=True)
    })
    
    cmap = get_cmap('tab10', len(artifact_classes))  # or 'tab20', 'Set3', etc.
    class_to_color = {
        cls: mcolors.to_hex(cmap(i))
        for i, cls in enumerate(artifact_classes)
    }
    class_to_color.update(colormap) # user specified color overrides go here
    
    node_colors = [
        class_to_color[type(data['artifact'])] for _, data in tg.nodes(data=True)
    ]

    fig, ax = _plot_graph(tg, node_colors=node_colors)

    legend_handles = [
        mpatches.Patch(color=color, label=cls.__name__)
        for cls, color in class_to_color.items()
    ]
    ax.legend(handles=legend_handles, title="Artifact Type")
    ax.set_title(f"Graph Colored by Artifact Type")
    return fig
