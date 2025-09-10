
import React, { useCallback, useState, useEffect, useMemo } from 'react';
import dagre from '@dagrejs/dagre';
import { useGlobalStore } from '../../state/globalStore';
import { colorForIndex } from '../../utils/colors';


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




// robust id → number
const parseIntFromTag = (v: unknown): number => {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') { const m = v.match(/-?\d+/); if (m) return Number(m[0]); }
  return NaN;
};

// does this segm have ranges for this solution?
const segHasRanges = (templates: any, segmId: number, solnIdx: number) => {
  const bucket = templates?.[segmId];
  if (!bucket) return false;
  const ranges = bucket?.[solnIdx] ?? bucket?.[String(solnIdx)] ?? (Array.isArray(bucket) ? bucket : undefined);
  return Array.isArray(ranges) && ranges.length > 0;
};


const conicFrom = (colors: string[]) => {
  if (!colors.length) return 'transparent';
  const step = 100 / colors.length;
  const stops = colors.map((c, i) => `${c} ${i * step}% ${(i + 1) * step}%`).join(', ');
  return `conic-gradient(${stops})`;
};



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
  const selectedNodeId = useGlobalStore((s) => s.global.ui.selected_node_id);
  const isSelected = selectedNodeId == data.id;

  // Keep your original footprint math (slightly smaller than 20x20)
  const OUTER_BOX = Math.round(20 * 0.7);        // visible footprint ~14px
  const RING_SIDE = Math.round(OUTER_BOX / Math.SQRT2); // ~10px selection ring box
  const NODE_SIDE = Math.round(RING_SIDE * 0.7);        // inner diamond side (~7px)
  const BORDER = 3; // thickness of the black outline

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
      {/* keep your selected glow ring */}
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            width: RING_SIDE,
            height: RING_SIDE,
            transform: 'rotate(45deg)',
            border: `2px solid ${GLOW_COLOR}`,
            boxSizing: 'border-box',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* white-filled diamond with thick black border */}
      <div
        style={{
          width: NODE_SIDE,
          height: NODE_SIDE,
          transform: 'rotate(45deg)',
          backgroundColor: '#fff',          // white interior
          border: `${BORDER}px solid #000`, // thick black outline
          boxSizing: 'border-box',
          position: 'relative',
        }}
      >
        {/* invisible handles (keep flow connectivity) */}
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Top}    style={{ opacity: 0, pointerEvents: 'none' }} />
      </div>
    </div>
  );
}


function DotNode({ data }: { data: any; selected: boolean }) {
  const selectedNodeId = useGlobalStore((s) => s.global.ui.selected_node_id);
  const isSelected = selectedNodeId == data.id;

  const minFitness = useGlobalStore((s) => s.global.ui.min_fitness);
  const maxFitness = useGlobalStore((s) => s.global.ui.max_fitness);

  const baseColor = getSolutionFitnessColor(
    data.evaluation.fitness,
    data.evaluation.fitness_rank,
    minFitness,
    maxFitness
  );

  const segColors: string[] = Array.isArray(data?.segColors) ? data.segColors : [];
  const originSegColors: string[] = Array.isArray(data?.originSegColors) ? data.originSegColors : [];

  // visual constants
  const SIZE = 20;       // node box
  const DOT = 12;        // inner circle
  const RING = 16;       // conic ring diameter
  const BORDER = 2;      // square halo border thickness

  // concentric square sizing: start outside the node and grow outward
  const ORIGIN_BASE = 22;  // first (smallest) square side length (px) — bigger than RING/DOT
  const ORIGIN_STEP = 4;   // growth per additional origin segment (px)

  // conic ring from segment membership (unchanged)
  const step = segColors.length ? 100 / segColors.length : 0;
  const ring =
    segColors.length > 0
      ? `conic-gradient(${segColors
          .map((c, i) => `${c} ${i * step}% ${(i + 1) * step}%`)
          .join(', ')})`
      : 'transparent';

  return (
    <div
      style={{
        position: 'relative',
        width: SIZE,
        height: SIZE,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        // ensure halos can extend outside without eating pointer events
        pointerEvents: 'auto',
      }}
    >
      {/* selection glow on top */}
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            width: SIZE,
            height: SIZE,
            borderRadius: '50%',
            border: `2px solid ${GLOW_COLOR}`,
            boxSizing: 'border-box',
            zIndex: 4,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* NEW: stacked concentric square halos (one per origin segment) */}
      {originSegColors.map((c, i) => {
        const side = ORIGIN_BASE + i * ORIGIN_STEP;
        return (
          <div
            key={`origin-${i}`}
            aria-hidden
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              width: side,
              height: side,
              border: `${BORDER}px solid ${c}`,
              borderRadius: 3,
              background: 'transparent',
              boxSizing: 'border-box',
              zIndex: 1,           // below ring/dot, above canvas
              pointerEvents: 'none',
            }}
          />
        );
      })}

      {/* outer conic ring showing segment membership */}
      <div
        aria-hidden
        style={{
          position: 'absolute',
          width: RING,
          height: RING,
          borderRadius: '50%',
          background: ring,
          zIndex: 2,
          pointerEvents: 'none',
        }}
      />

      {/* inner fitness dot */}
      <div
        style={{
          width: DOT,
          height: DOT,
          borderRadius: '50%',
          backgroundColor: baseColor,
          position: 'relative',
          zIndex: 3,
        }}
      >
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
      </div>
    </div>
  );
}


// function DotNode({ data }: { data: any; selected: boolean }) {
//   const selectedNodeId = useGlobalStore((s) => s.global.ui.selected_node_id);
//   const isSelected = selectedNodeId == data.id;

//   const minFitness = useGlobalStore((s) => s.global.ui.min_fitness);
//   const maxFitness = useGlobalStore((s) => s.global.ui.max_fitness);
//   const baseColor = getSolutionFitnessColor(
//     data.evaluation.fitness,
//     data.evaluation.fitness_rank,
//     minFitness,
//     maxFitness
//   );

//   const segColors: string[] = Array.isArray(data?.segColors) ? data.segColors : [];
//   const originSegColors: string[] = Array.isArray(data?.originSegColors) ? data.originSegColors : [];

//   const ring = segColors.length ? conicFrom(segColors) : 'transparent';

//   const SIZE = 20;
//   const RING_OUTER = 16;  // conic ring
//   const DOT = 12;

//   return (
//     <div style={{ position: 'relative', width: SIZE, height: SIZE, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
//       {/* circular selection glow */}
//       {isSelected && (
//         <div style={{ position: 'absolute', width: SIZE, height: SIZE, borderRadius: '50%', border: `2px solid ${GLOW_COLOR}`, boxSizing: 'border-box' }} />
//       )}

//       {/* NEW: square halo for origin nodes */}
//       {originSegColors.length > 0 && (
//         <div
//           aria-hidden
//           style={{
//             position: 'absolute',
//             width: SIZE + 2,
//             height: SIZE + 2,
//             borderRadius: 2,
//             border: `2px solid ${originSegColors.length === 1 ? originSegColors[0] : '#000000'}`,
//             boxSizing: 'border-box',
//           }}
//         >
//           {/* Optional tiny color ticks along the top edge when multiple origins */}
//           {originSegColors.length > 1 && (
//             <div style={{ position: 'absolute', top: -2, left: 2, right: 2, height: 2, display: 'flex' }}>
//               {originSegColors.map((c, i) => (
//                 <div key={i} style={{ flex: 1, background: c }} />
//               ))}
//             </div>
//           )}
//         </div>
//       )}

//       {/* outer conic ring (segment membership) */}
//       <div
//         aria-hidden
//         style={{
//           position: 'absolute',
//           width: RING_OUTER,
//           height: RING_OUTER,
//           borderRadius: '50%',
//           background: ring,
//         }}
//       />

//       {/* inner dot (fitness color) */}
//       <div
//         style={{
//           width: DOT,
//           height: DOT,
//           borderRadius: '50%',
//           backgroundColor: baseColor,
//           position: 'relative',
//         }}
//       >
//         <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
//         <Handle type="target" position={Position.Top}    style={{ opacity: 0, pointerEvents: 'none' }} />
//       </div>
//     </div>
//   );
// }


// function DotNode({ data }: { data: any; selected: boolean }) {
//   const selectedNodeId = useGlobalStore((s) => s.global.ui.selected_node_id);
//   const isSelected = selectedNodeId == data.id;

//   const minFitness = useGlobalStore((s) => s.global.ui.min_fitness);
//   const maxFitness = useGlobalStore((s) => s.global.ui.max_fitness);
//   const baseColor = getSolutionFitnessColor(data.evaluation.fitness, data.evaluation.fitness_rank, minFitness, maxFitness);

//   const segColors: string[] = Array.isArray(data?.segColors) ? data.segColors : [];
//   const ring = segColors.length ? conicFrom(segColors) : 'transparent';

//   return (
//     <div style={{ position: 'relative', width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
//       {isSelected && (
//         <div style={{ position: 'absolute', width: 20, height: 20, borderRadius: '50%', border: `2px solid ${GLOW_COLOR}`, boxSizing: 'border-box' }} />
//       )}

//       {/* outer ring (2px) using conic-gradient */}
//       <div
//         aria-hidden
//         style={{
//           position: 'absolute',
//           width: 16, height: 16, borderRadius: '50%',
//           background: ring,
//         }}
//       />

//       {/* inner dot */}
//       <div
//         style={{
//           width: 12,
//           height: 12,
//           borderRadius: '50%',
//           backgroundColor: baseColor,
//           position: 'relative',
//         }}
//       >
//         <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
//         <Handle type="target" position={Position.Top}    style={{ opacity: 0, pointerEvents: 'none' }} />
//       </div>
//     </div>
//   );
// }


function BezierGlowEdge({ id, source, target, sourceX, sourceY, targetX, targetY, data }: any) {
  const selectedId = useGlobalStore((s) => s.global.ui.selected_node_id);
  const isHighlighted = source === selectedId || target === selectedId;

  const [edgePath] = getBezierPath({ sourceX, sourceY, targetX, targetY });
  const colors: string[] = Array.isArray(data?.colors) ? data.colors : [];

  return (
    <>
      {/* base */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ stroke: isHighlighted ? GLOW_COLOR : '#999', strokeWidth: isHighlighted ? 1.75 : 1 }}
        markerEnd="url(#arrowhead)"
      />
      {/* overlays: staggered dashed colors so multiple can be seen */}
      {colors.map((c, i) => (
        <path
          key={`${id}-seg-${i}`}
          d={edgePath}
          fill="none"
          stroke={c}
          strokeWidth={4}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray="10 8"
          strokeDashoffset={i * 6}   // stagger
          opacity={0.95}
          pointerEvents="none"
        />
      ))}
    </>
  );
}


// function BezierGlowEdge({ id, source, target, sourceX, sourceY, targetX, targetY }) {
//   const selectedId = useGlobalStore(state => state.global.ui.selected_node_id);
//   const isHighlighted = source === selectedId || target === selectedId;

//   const [edgePath, labelX, labelY] = getBezierPath({
//     sourceX,
//     sourceY,
//     targetX,
//     targetY,
//   });

//   return (
    
//       <BaseEdge
//         id={id}
//         path={edgePath}
//         style={{
//           stroke: isHighlighted ? GLOW_COLOR : '#999',
//           strokeWidth: isHighlighted ? 1.75 : 1.0,
//         }}
//         markerEnd="url(#arrowhead)"
//       />
    
//   );
// }




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
  const analysisMode  = useGlobalStore((s) => s.global.ui.analysis_mode);
  const selectedSegms = useGlobalStore((s) => s.global.ui.selected_segms);   // [] means NONE
  const templates     = useGlobalStore((s) => s.global.trace.analysis.segment?.templates);



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
    // 1) dagre positions
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'TB', nodesep: 20, ranksep: 120 });

    traceGraph.nodes.forEach((n) => dagreGraph.setNode(n.id, { width: 20, height: 20 }));
    traceGraph.edges.forEach((e) => dagreGraph.setEdge(e.source, e.target));
    dagre.layout(dagreGraph);

    // 2) precompute per-node segment IDs + colors (only if active)
    const active = analysisMode && Array.isArray(selectedSegms) && selectedSegms.length > 0 && templates;
    const nodeSegmIds = new Map<any, number[]>();
    const nodeSegmColors = new Map<any, string[]>();

    if (active) {
      for (const n of traceGraph.nodes) {
        if (!n.is_solution) continue;
        const solnIdx = parseIntFromTag(n.id);
        if (!Number.isFinite(solnIdx)) continue;
        const segs = selectedSegms.filter((segmId) => segHasRanges(templates, segmId, solnIdx));
        if (segs.length) {
          nodeSegmIds.set(n.id, segs);
          nodeSegmColors.set(n.id, segs.map((id) => colorForIndex(id)));
        }
      }
    }
    
    // NEW: predecessor map (incoming neighbors)
    const preds = new Map<any, any[]>();
    for (const e of traceGraph.edges) {
      const arr = preds.get(e.target) ?? [];
      arr.push(e.source);
      preds.set(e.target, arr);
    }

    // NEW: for each node, which of its selected segments are "origin" (no parent in same seg)
    const nodeOriginSegColors = new Map<any, string[]>();
    if (active) {
      for (const n of traceGraph.nodes) {
        const segs = nodeSegmIds.get(n.id) ?? [];
        if (!segs.length) continue;
        const parents = preds.get(n.id) ?? [];
        const originSegs = segs.filter((segId) => {
          // true if NO parent carries segId
          return !parents.some((pId) => (nodeSegmIds.get(pId) ?? []).includes(segId));
        });
        if (originSegs.length) {
          console.log('registering originator node',n.id,'for segments',originSegs);
          nodeOriginSegColors.set(n.id, originSegs.map((id) => colorForIndex(id)));
        }
      }
    }

    // 3) nodes with XYFlow props + data.segColors (for DotNode ring)
    const solutionNodeProps = { sourcePosition: Position.Bottom, targetPosition: Position.Top, type: 'dot' as const };
    const artifactNodeProps = { sourcePosition: Position.Bottom, targetPosition: Position.Top, type: 'diamond' as const };

    const layoutedNodes = traceGraph.nodes.map((node) => {
      const pos = dagreGraph.node(node.id);
      return {
        ...node,
        position: { x: pos.x - 10, y: pos.y - 10 },
        data: {
          ...node,
          segColors: nodeSegmColors.get(node.id) ?? [],   // <-- new: [] when inactive/no match
          originSegColors: nodeOriginSegColors.get(node.id) ?? [],
        },
        ...(node.is_solution ? solutionNodeProps : artifactNodeProps),
      };
    });

    // 4) edges; compute shared segment colors (intersection) if active
    const layoutedEdges = traceGraph.edges.map((edge, i) => {
      let colors: string[] = [];
      if (active) {
        const a = nodeSegmIds.get(edge.source) ?? [];
        const b = nodeSegmIds.get(edge.target) ?? [];
        if (a.length && b.length) {
          const setB = new Set(b);
          const sharedSegmIds = a.filter((id) => setB.has(id));
          if (sharedSegmIds.length) colors = sharedSegmIds.map((id) => colorForIndex(id));
        }
      }
      return {
        id: `e${i}`,
        source: edge.source,
        target: edge.target,
        type: 'smooth',
        data: { colors },                               // <-- new
      };
    });

    return { nodes: layoutedNodes, edges: layoutedEdges };
  }, [traceGraph, analysisMode, selectedSegms, templates, traceTimestamp]);


  // const layoutedGraph = useMemo(() => {
  //   const dagreGraph = new dagre.graphlib.Graph();
  //   dagreGraph.setDefaultEdgeLabel(() => ({}));
  //   dagreGraph.setGraph({ rankdir: 'TB', nodesep: 20, ranksep: 120 });

  //   traceGraph.nodes.forEach((node) => {
  //     dagreGraph.setNode(node.id, { width: 20, height: 20 });
  //   });

  //   traceGraph.edges.forEach((edge) => {
  //     dagreGraph.setEdge(edge.source, edge.target);
  //   });

  //   dagre.layout(dagreGraph);

  //   const layoutedNodes = traceGraph.nodes.map((node) => {
  //     const pos = dagreGraph.node(node.id);
  //     return {
  //       ...node,
  //       position: {
  //         x: pos.x - 10,
  //         y: pos.y - 10,
  //       },
  //       data: node,
  //       ...(node.is_solution ? solutionNodeProps : artifactNodeProps),
  //     };
  //   });

  //   const layoutedEdges = traceGraph.edges.map((edge, i) => ({
  //     id: `e${i}`,
  //     source: edge.source,
  //     target: edge.target,
  //     type: 'smooth',
  //   }));

  //   return { nodes: layoutedNodes, edges: layoutedEdges };
  // }, [traceTimestamp]);



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
