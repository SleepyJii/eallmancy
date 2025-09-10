import { useGlobalStore } from '../../state/globalStore';
import { useMemo } from 'react';
import CodeViewer from './CodeViewer.tsx';
import { colorForIndex } from '../../utils/colors';




export const parseIntFromTag = (v: unknown): number => {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const m = v.match(/-?\d+/);
    if (m) return Number(m[0]);
  }
  return NaN;
};


export function segmIdsForAll(templates: any, solnIdx: number): number[] {
  if (!templates || !Number.isFinite(solnIdx)) return [];
  return Object.keys(templates)
    .map(Number)
    .filter((segmId) => {
      const bucket = templates[segmId];
      const ranges =
        bucket?.[solnIdx] ??
        bucket?.[String(solnIdx)] ??
        (Array.isArray(bucket) ? bucket : undefined);
      return Array.isArray(ranges) && ranges.length > 0;
    });
}

export function activeSegmIds(
  templates: any,
  solnIdx: number,
  selected: number[]
): number[] {
  return selected && selected.length ? selected : [];
}

/** Decide which segmIds to highlight. Prefer templates; fall back to lookup. */
export function segmentsToHighlight(
  templates: any,
  soln_lookup: any,
  selectedSolutionTag: string | undefined,
  selectedSegmId: 'ALL' | number | undefined
): number[] {
  const solnIdx = parseIntFromTag(selectedSolutionTag);

  console.log('parsed solnIdx', solnIdx, 'segm', selectedSegmId);
  if (selectedSegmId === 'ALL') {
    // Use templates so ALL means “all segments that have ranges for this soln”
    const ids = segmIdsForAll(templates, solnIdx);
    console.log('segm lookup using', templates, solnIdx, 'gave', ids);
    if (ids.length) return ids;

    // Fallback: try soln_lookup if templates didn’t yield anything
    const node = soln_lookup?.[solnIdx];
    if (node instanceof Map) return Array.from(node.keys()).map(Number);
    if (Array.isArray(node)) return node.map(Number);
    if (node && typeof node === 'object') return Object.keys(node).map(Number);
    return [];
  }

  if (typeof selectedSegmId === 'number') return [selectedSegmId];
  return [];
}

export type ColoredRange = { start: number; end: number; color: string, segmId: number };

export function coloredRangesForSegments(
  templates: any,
  segmIds: number[],
  selectedSolutionTag: string | undefined
): ColoredRange[] {
  const solnIdx = parseIntFromTag(selectedSolutionTag);
  if (!Number.isFinite(solnIdx) || !templates) return [];
  const out: ColoredRange[] = [];
  for (const segmId of segmIds) {
    const bucket = templates?.[segmId];
    const ranges =
      bucket?.[solnIdx] ??
      bucket?.[String(solnIdx)] ??
      (Array.isArray(bucket) ? bucket : []);
    if (!Array.isArray(ranges)) continue;
    for (const r of ranges) {
      const start = Number(r?.start_line);
      const end = Number(r?.end_line);
      if (Number.isFinite(start) && Number.isFinite(end)) {
        out.push({
          start: Math.max(1, start),
          end: Math.max(start, end),
          color: colorForIndex(segmId),
          segmId: segmId
        });
      }
    }
  }
  return out;
}

export function toLineColorMap(ranges: ColoredRange[]): Map<number,string> {
  const m = new Map<number,string>();
  for (const { start, end, color } of ranges) {
    for (let i = start; i <= end; i++) m.set(i, color);
  }
  return m;
}


/** Build a map: line -> array of colors (deduped, stable order by segmId). */
export function toLineGutterColors(ranges: ColoredRange[]): Map<number, string[]> {
  const m = new Map<number, string[]>();
  // stable order by segmId to keep the same strip order each render
  const sorted = [...ranges].sort((a, b) => a.segmId - b.segmId);
  for (const { start, end, color } of sorted) {
    for (let i = start; i <= end; i++) {
      const arr = m.get(i) ?? [];
      if (!arr.includes(color)) arr.push(color);
      m.set(i, arr);
    }
  }
  return m;
}



type Props = {
  indices: number[];               // all available segmIds for current solution
  selected: number[];              // currently active segmIds
  onChange: (next: number[]) => void;
  title?: string;
  maxHeight?: number;
};

export function AnalysisColorButtons({
  indices,
  selected,
  onChange,
  title = 'Segments',
  maxHeight = 140,
}: Props) {
  const sel = new Set(selected);

  const toggle = (id: number) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    console.log('setting selected to', Array.from(next).sort((a, b) => a - b));
    onChange(Array.from(next).sort((a, b) => a - b));
  };

  const selectAll = () => {
    console.log('setting selected to',[...indices].sort((a, b) => a - b));
    onChange([...indices].sort((a, b) => a - b));
  }
  const selectNone = () => {
    console.log('setting selected to',[]);
    onChange([]);
  }
  const btnStyle = (active: boolean) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    lineHeight: 1,
    padding: '4px 6px',
    borderRadius: 6,
    border: active ? '1px solid #6b7280' : '1px solid #d1d5db',
    background: active ? '#eef2ff' : '#ffffff',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  });

  return (
    <div>
      <div style={{ marginBottom: 6, fontSize: '0.9em', color: '#555' }}>{title}</div>
      <div
        role="group"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 6,
          alignItems: 'center',
          maxHeight,
          overflow: 'auto',
          padding: 4,
          border: '1px solid #ddd',
          borderRadius: 8,
          background: '#fafafa',
        }}
      >
        <button type="button" onClick={selectAll} style={btnStyle(false)}>(ALL)</button>
        <button type="button" onClick={selectNone} style={btnStyle(selected.length === 0)}>(NONE)</button>

        {indices.length === 0 ? (
          <div style={{ color: '#999', fontSize: 12 }}>No items</div>
        ) : (
          indices.map((idx) => (
            <button
              key={idx}
              type="button"
              aria-pressed={sel.has(idx)}
              onClick={() => toggle(idx)}
              title={`Segment ${idx}`}
              style={btnStyle(sel.has(idx))}
            >
              (<span style={{ fontVariantNumeric: 'tabular-nums' }}>{idx}</span>
              <span
                aria-hidden
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: 2,
                  background: colorForIndex(idx),
                  border: '1px solid rgba(0,0,0,0.15)',
                  display: 'inline-block',
                }}
              />
              )
            </button>
          ))
        )}
      </div>
    </div>
  );
}



export default function NodeInspector() {
  const global = useGlobalStore((s) => s.global);
  const setSelectedSegms = useGlobalStore((s) => s.setSelectedSegms); // add this setter
  const selectedSegms = global.ui?.selected_segms;              // number[]
  console.log('SELECTED SEGMENTS',selectedSegms);

  const selectedId = global.ui.selected_node_id;
  const selectedNode = useMemo(
    () => global.trace.graph.nodes.find((n) => n.id === selectedId),
    [selectedId, global.trace.graph.nodes]
  );

  const analysisMode = global.ui?.analysis_mode ?? false;

  const templates   = global?.trace?.analysis?.segment?.templates;
  const selectedTag = selectedId; // could be 'A7' or 7
  const solnIdx     = parseIntFromTag(selectedTag);

  // All segmIds available for this solution (for the button list & ALL action)
  const allSegmIds = useMemo(
    () => segmIdsForAll(templates, solnIdx),
    [templates, solnIdx]
  );

  // Active segmIds
  const segmIds = useMemo(
    () => activeSegmIds(templates, solnIdx, selectedSegms),
    [templates, solnIdx, selectedSegms]
  );

  // Build highlight maps whenever selection or node changes
  const [lineMap, gutterLineMap] = useMemo(() => {
    if (!selectedNode || !Number.isFinite(solnIdx)) return [undefined, undefined] as const;
    const ranges = coloredRangesForSegments(templates, segmIds, String(solnIdx));
    return [toLineColorMap(ranges), toLineGutterColors(ranges)] as const;
  }, [templates, segmIds, selectedNode, solnIdx]);


  if (selectedId === -1 || !selectedNode) return null;



  return (
    <div style={{
      flex: 1,
      padding: '12px',
      borderLeft: '1px solid #ccc',
      backgroundColor: '#f9f9f9',
      overflowY: 'auto',
      width: 'min(450px, 35%)',
    }}>
      <h3>Node {selectedId}</h3>
      <h4>{'<'+selectedNode.artifact_type+'>'}</h4>

      {analysisMode && selectedNode.is_solution && (
        <details open>
          <summary>Code Analysis</summary>
          <div style={{ backgroundColor: '#f0f0f0', padding: 10, borderRadius: 4 }}>
            <AnalysisColorButtons
              indices={allSegmIds}                // the “universe” for this solution
              selected={selectedSegms}            // what’s currently active
              onChange={setSelectedSegms}         // updates store immutably
              title="Segments"
              maxHeight={180}
            />
            <CodeViewer
              lines={selectedNode.program_lines}
              lineColors={lineMap}
              lineGutterColors={gutterLineMap}
              gutterPosition="left"
              gutterWidth={10}
            />
          </div>
        </details>
      )}

      <details open={!(analysisMode && selectedNode.is_solution) ? 'true' : 'false' }>
        <summary>Summary</summary>
            <pre style={{
            backgroundColor: '#f0f0f0',
            padding: '10px',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
            fontSize: '0.85em'
            }}>
            <code>{selectedNode.artifact_repr}</code>
            </pre>
      </details>

      <details open={(analysisMode && selectedNode.is_solution) ? 'true' : 'false' } >
        <summary>Evaluation</summary>
        <pre>{JSON.stringify(selectedNode.evaluation, null, 2)}</pre>
      </details>

      {selectedNode.solution_parts && (
        <details>
          <summary>Solution Parts</summary>
          <ul>
            {selectedNode.solution_parts.map((part, i) => (
              <li key={i}>{part}</li>
            ))}
          </ul>
        </details>
      )}
      <details>
        <summary>Raw Prompt</summary>
            <pre style={{
            backgroundColor: '#f0f0f0',
            padding: '10px',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
            fontSize: '0.85em'
            }}>
            <code>{selectedNode.raw_prompt}</code>
            </pre>
      </details>
      <details>
        <summary>Raw Response</summary>
            <pre style={{
            backgroundColor: '#f0f0f0',
            padding: '10px',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
            fontSize: '0.85em'
            }}>
            <code>{selectedNode.raw_response}</code>
            </pre>
      </details>
    </div>
  );
}
