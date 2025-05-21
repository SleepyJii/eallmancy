
import React, { useCallback, useState, useEffect } from 'react';
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
  type Node,
  type Edge,
  type OnConnect,
  type ColorMode,

} from '@xyflow/react';


function DotNode() {
  console.log("rendering DotNode");
  return (
    <div
      style={{
        width: 12,
        height: 12,
        backgroundColor: 'black',
        borderRadius: '50%',
      }}
    >
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
      <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
    </div>
  );
}

function WideSmoothEdge(props) {
  return <SmoothStepEdge {...props} borderRadius={20} />;
};

const edgeTypes = {
  smooth: BezierEdge,
};

const nodeTypes = {
  dot: DotNode,
};



export default function LineageView() {
  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);

  const defaultNodeProps = {
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
  };
  const initialNodes = [
    { id: 'a1', position: { x: 50, y: 50 },  data: {}, type: 'dot', ...defaultNodeProps },
    { id: 'b1', position: { x: 50, y: 150 },  data: {}, type: 'dot', ...defaultNodeProps },
    { id: 'b2', position: { x: 150, y: 150 }, data: {}, type: 'dot', ...defaultNodeProps },
    { id: 'c1', position: { x: 150, y: 250 }, data: {}, type: 'dot', ...defaultNodeProps },
  ];
  const initialEdges = [
    { id: 'e1', source: 'a1', target: 'b1', type: 'smooth' },
    { id: 'e2', source: 'a1', target: 'b2', type: 'smooth' },
    { id: 'e3', source: 'b1', target: 'c1', type: 'smooth' },
  ];
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const onConnect: OnConnect = useCallback(
    (params) => setEdges((els) => addEdge(params, els)),
    [],
  );
 
  console.log('rendering...:')
  console.log(nodes);


  const panBounds = { left: 0, right: 300, top: 0, bottom: 500 };
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
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}

        zoomOnScroll={true}
        panOnScroll={false}
        panOnDrag={true}
        nodesDraggable={false}

        // panBoundary={panBounds}
        // nodeExtent={[[0, 0], [300, 500]]} // min and max canvas coords

        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
         <Controls showInteractive={true} />
        <Background />
      </ReactFlow>
    </div>
  );
}
