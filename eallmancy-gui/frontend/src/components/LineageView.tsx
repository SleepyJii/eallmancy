
import React, { useCallback, useState, useEffect, useMemo } from 'react';
import { useGlobalStore } from '../state/globalStore';

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

function getFitnessColor(value, value_rank, min, max) {
  const v = parseFloat(value_rank);
  if (isNaN(parseFloat(value))) return '#000';

  const t = (v - min) / (max - min); // normalize to [0, 1]
  const _LOW_COLOR  = [0, 128, 0];     // green
  const _MID_COLOR  = [224, 150, 31];   // yellow
  const _HIGH_COLOR = [220, 20, 60];   // crimson/red

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


function DotNode({ data, selected }) {
  const global = useGlobalStore(state => state.global);
  const selectedNodeId = useGlobalStore(state => state.global.ui.selected_node_id);
  const isSelected = selectedNodeId == data.id;

  const minFitness = useGlobalStore(state => state.global.ui.min_fitness);
  const maxFitness = useGlobalStore(state => state.global.ui.max_fitness);

  const color = getFitnessColor(data.evaluation.fitness, data.evaluation.fitness_rank, minFitness, maxFitness);

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
};



export default function LineageView() {
  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);
  const traceTimestamp = useGlobalStore(state => state.global.trace.timestamp);


  const handleNodeClick = useCallback((event, node) => {
    setGlobalField('ui', { ...global.ui, selected_node_id: node.id });
  }, [setGlobalField]);


  const traceGraph = useGlobalStore(state => state.global.trace.graph);
  const defaultNodeProps = {
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    type: 'dot',
  };

  const nodes = useMemo(() => {
    return traceGraph.nodes.map(node => ({
      ...node,
      position: {
        x: node.position.x_rank * 50 + 50,
        y: node.position.y_rank * 50 + 50,
      },
      data: node,
      ...defaultNodeProps,
    }));
  }, [traceTimestamp]);

  // const edges = traceGraph.edges.map((edge, i) => ({
  //   id: `e${i}`,
  //   source: edge.source,
  //   target: edge.target,
  //   type: 'smooth',
  // }));

  const edges = useMemo(() => {
    return traceGraph.edges.map((edge, i) => ({
      id: `e${i}`,
      source: edge.source,
      target: edge.target,
      type: 'smooth',
    }));
  }, [traceTimestamp]);

  // color calcs
  useEffect(() => {
    const nodes = useGlobalStore.getState().global.trace.graph.nodes;
    if (!nodes || nodes.length === 0) return;
    const fitnessValues = nodes
      .map(n => parseFloat(n.evaluation.fitness_rank))
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


  console.log('rendering...:')
  console.log(nodes);

  return (
    <div style={{
       width: 'min(600px, 50%)',
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
