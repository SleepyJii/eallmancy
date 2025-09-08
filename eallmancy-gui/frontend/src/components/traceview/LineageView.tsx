
import React, { useCallback, useState, useEffect, useMemo } from 'react';
import dagre from '@dagrejs/dagre';
import { useGlobalStore } from '../../state/globalStore';

// import ReactFlow, { Background, Controls } from 'react-flow-renderer';
// import ReactFlow, { Background, Controls } from '@xyflow/react';

import {
  ReactFlow,
  Controls,
  Background,
  useReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  SmoothStepEdge,
  BezierEdge,
  BaseEdge, getBezierPath,
  type Node,
  type Edge,
  type OnConnect,
  type ColorMode,

} from '@xyflow/react';


function lerp(a, b, t) {
  return a + (b - a) * t;
}

function interpolateColor(c1, c2, t) {
  return [
    Math.round(lerp(c1[0], c2[0], t)),
    Math.round(lerp(c1[1], c2[1], t)),
    Math.round(lerp(c1[2], c2[2], t)),
  ];
}

function getSolutionFitnessColor(value, value_rank, min, max) {
  const v = parseFloat(value_rank);
  if (isNaN(parseFloat(value))) return '#000';


  let t = (v - min) / (max - min); // normalize to [0, 1]
  const _LOW_COLOR = [220, 20, 60];   // crimson/red
  const _MID_COLOR  = [224, 150, 31];   // yellow
  const _HIGH_COLOR = [0, 128, 0];     // green

  if ((max-min) == 0) {
    t = 1; 
  }

  let color;
  if (t <= 0.5) {
    const localT = t / 0.5; // [0, 0.5] → [0, 1]
    color = interpolateColor(_LOW_COLOR, _MID_COLOR, localT);
  } else {
    const localT = (t - 0.5) / 0.5; // (0.5, 1] → [0, 1]
    color = interpolateColor(_MID_COLOR, _HIGH_COLOR, localT);
  }

  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}




export const GLOW_COLOR = '#111'; // or any color you want


function DiamondNode({ data, selected }) {
  const global = useGlobalStore(state => state.global);
  const selectedNodeId = useGlobalStore(state => state.global.ui.selected_node_id);
  const isSelected = selectedNodeId == data.id;

  const color = `rgba(49, 49, 49, 1)`;

  // Scale down 30%
  const OUTER_BOX = Math.round(20 * 0.7);        // 14px visible footprint
  // A square rotated 45° expands by √2, so shrink its side to keep it inside the box.
  const RING_SIDE = Math.round(OUTER_BOX / Math.SQRT2); // ~10px
  const NODE_SIDE = Math.round(RING_SIDE * 0.7);        // inner fill (~7px) for nice padding

  return (
    <div
      style={{
        position: 'relative',
        width: OUTER_BOX,
        height: OUTER_BOX,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            width: RING_SIDE,
            height: RING_SIDE,
            transform: 'rotate(45deg)',
            border: `2px solid ${GLOW_COLOR}`,
            boxSizing: 'border-box',
          }}
        />
      )}

      <div
        style={{
          width: NODE_SIDE,
          height: NODE_SIDE,
          backgroundColor: color,
          transform: 'rotate(45deg)',
          position: 'relative',
        }}
      >
        {/* Keep handles aligned to the unrotated node's top/bottom positions */}
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      </div>
    </div>
  );
}




function DotNode({ data, selected }) {
  const global = useGlobalStore(state => state.global);
  const selectedNodeId = useGlobalStore(state => state.global.ui.selected_node_id);
  const isSelected = selectedNodeId == data.id;

  const minFitness = useGlobalStore(state => state.global.ui.min_fitness);
  const maxFitness = useGlobalStore(state => state.global.ui.max_fitness);

  const color = getSolutionFitnessColor(data.evaluation.fitness, data.evaluation.fitness_rank, minFitness, maxFitness);
  

  return (
    <div
      style={{
        position: 'relative',
        width: 20,
        height: 20,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            width: 20,
            height: 20,
            borderRadius: '50%',
            border: `2px solid ${GLOW_COLOR}`,
            boxSizing: 'border-box',
          }}
        />
      )}
      <div
        style={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: color ,
          position: 'relative',
        }}
      >
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      </div>
    </div>
  );
}


function BezierGlowEdge({ id, source, target, sourceX, sourceY, targetX, targetY }) {
  const selectedId = useGlobalStore(state => state.global.ui.selected_node_id);
  const isHighlighted = source === selectedId || target === selectedId;

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  });

  return (
    
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: isHighlighted ? GLOW_COLOR : '#999',
          strokeWidth: isHighlighted ? 1.75 : 1.0,
        }}
        markerEnd="url(#arrowhead)"
      />
    
  );
}




const edgeTypes = {
  smooth: BezierGlowEdge,
};

const nodeTypes = {
  dot: DotNode,
  diamond: DiamondNode, // TODO: actually implement the small diamond one for non-solutions
};



export default function LineageView() {
  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);
  const traceTimestamp = useGlobalStore(state => state.global.trace.timestamp);


  const handleNodeClick = useCallback((event, node) => {
    setGlobalField('ui', { ...global.ui, selected_node_id: node.id });
  }, [setGlobalField]);


  const traceGraph = useGlobalStore(state => state.global.trace.graph);
  const solutionNodeProps = {
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    type: 'dot',
  };
  const artifactNodeProps = {
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    type: 'diamond',
  };




  const layoutedGraph = useMemo(() => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'TB', nodesep: 20, ranksep: 120 });

    traceGraph.nodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: 20, height: 20 });
    });

    traceGraph.edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = traceGraph.nodes.map((node) => {
      const pos = dagreGraph.node(node.id);
      return {
        ...node,
        position: {
          x: pos.x - 10,
          y: pos.y - 10,
        },
        data: node,
        ...(node.is_solution ? solutionNodeProps : artifactNodeProps),
      };
    });

    const layoutedEdges = traceGraph.edges.map((edge, i) => ({
      id: `e${i}`,
      source: edge.source,
      target: edge.target,
      type: 'smooth',
    }));

    return { nodes: layoutedNodes, edges: layoutedEdges };
  }, [traceTimestamp]);



  // color calcs
  useEffect(() => {
    const nodes = useGlobalStore.getState().global.trace.graph.nodes;
    if (!nodes || nodes.length === 0) return;
    const fitnessValues = nodes
      .map(n => n.is_solution ? parseFloat(n.evaluation.fitness_rank) : NaN )
      .filter(val => !isNaN(val));

    if (fitnessValues.length > 0) {
      const min = Math.min(...fitnessValues);
      const max = Math.max(...fitnessValues);
      setGlobalField('ui', { ...global.ui, min_fitness: min, max_fitness: max });
      console.log('color scale set between', min, max);
    } else {
      console.log('no fitness values yet, not defining color scale');
    }
  }, [global.trace.timestamp]);

  const { nodes, edges } = layoutedGraph;


  console.log('rendering...:')
  console.log(nodes);

  return (
    <div style={{
       width: 'min(750px, 50%)',
        height: '80vh',
        marginLeft: '30px',

        // margin: '0 auto',
        padding: '10px',

        border: '1px solid #ccc',
        borderRadius: '8px',
        boxSizing: 'border-box',
        backgroundColor: '#fafafa'
        }}> 
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}

        zoomOnScroll={true}
          minZoom={0.1}   // allows zooming in further

        panOnScroll={false}
        panOnDrag={true}
        nodesDraggable={false}
        // onNodeClick={handleNodeClick}
        onNodeClick={(e, node) => {
          setGlobalField('ui', { ...global.ui, selected_node_id: node.id });
        }}
        onPaneClick={() => {
          setGlobalField('ui', { ...global.ui, selected_node_id: -1 });
        }}


        fitView
        // fitViewOptions={{ padding: 0.2 }}
      >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="8"
              refX="8"
              refY="4"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L8,4 L0,8" fill="#000" />
            </marker>
          </defs>
        <Controls showInteractive={true} />
        <Background />
      </ReactFlow>
    </div>
  );
}
