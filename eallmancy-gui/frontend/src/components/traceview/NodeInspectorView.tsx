import { useGlobalStore } from '../../state/globalStore';
import { useMemo } from 'react';
import CodeViewer from './CodeViewer.tsx';
import { colorForIndex } from '../../utils/colors';


export const parseIntFromTag = (s?: string) =>
  Number((s?.match(/-?\d+/) || [])[0]);

/** Get all segmIds that actually have ranges for a given solution index. */
export function segmIdsForAll(
  templates: any,
  solnIdx: number
): number[] {
  if (!templates || !Number.isFinite(solnIdx)) return [];
  return Object.keys(templates)
    .map(Number)
    .filter((segmId) => {
      const bucket = templates[segmId];
      // shapes supported:
      // 1) bucket[solnIdx] -> [{start_line,end_line}, ...]
      // 2) bucket[solnIdxStr]
      // 3) bucket is already an array of ranges (no per-solution split)
      const ranges =
        bucket?.[solnIdx] ??
        bucket?.[String(solnIdx)] ??
        (Array.isArray(bucket) ? bucket : undefined);
      return Array.isArray(ranges) && ranges.length > 0;
    });
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




export function AnalysisColorButtons({
  indices = [],
  value = 'ALL',            // 'ALL' | number
  onChange,                 // (next: 'ALL' | number) => void
  maxHeight = 140,
  title = 'Indices',
}) {
  const isSelected = (item) => item === value;

  const baseBtn = (selected) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    lineHeight: 1,
    padding: '4px 6px',
    borderRadius: 6,
    border: selected ? '1px solid #6b7280' : '1px solid #d1d5db',
    background: selected ? '#eef2ff' : '#ffffff',
    cursor: onChange ? 'pointer' : 'default',
    whiteSpace: 'nowrap',
  });

  return (
    <div>
      <div style={{ marginBottom: 6, fontSize: '0.9em', color: '#555' }}>{title}</div>
      <div
        role="radiogroup"
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px',
          alignItems: 'center',
          maxHeight,
          overflow: 'auto',
          padding: '4px',
          border: '1px solid #ddd',
          borderRadius: 8,
          background: '#fafafa',
        }}
      >
        {/* ALL button */}
        <button
          role="radio"
          aria-checked={isSelected('ALL')}
          onClick={() => onChange?.('ALL')}
          title="All"
          style={baseBtn(isSelected('ALL'))}
        >
          (ALL)
        </button>
        {/* NONE button */}
        <button
          role="radio"
          aria-checked={isSelected(null)}
          onClick={() => onChange?.(null)}
          title="None"
          style={baseBtn(isSelected(null))}
        >
          (NONE)
        </button>

        {/* Index buttons */}
        {indices.length === 0 ? (
          <div style={{ color: '#999', fontSize: 12 }}>No items</div>
        ) : (
          indices.map((idx) => {
            const selected = isSelected(idx);
            return (
              <button
                key={idx}
                role="radio"
                aria-checked={selected}
                onClick={() => onChange?.(idx)}
                title={`Index ${idx}`}
                style={baseBtn(selected)}
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
            );
          })
        )}
      </div>
    </div>
  );
}


export default function NodeInspector() {
  const global = useGlobalStore(state => state.global);
  const selectedId = global.ui.selected_node_id;

  const selectedNode = useMemo(() => {
    return global.trace.graph.nodes.find(n => n.id === selectedId);
  }, [selectedId, global.trace.graph.nodes]);

  const analysisMode = useGlobalStore((state) => state.global.ui?.analysis_mode ?? false);
  const setSelectedSegmId = useGlobalStore(state => state.setSelectedSegmId);


  // inputs you already have
  const templates   = global?.trace?.analysis?.segment?.templates;
  const soln_lookup = global?.trace?.analysis?.segment?.soln_lookup;
  const selectedTag = selectedId;                       // e.g. "A7"
  const selectedSeg = global?.ui?.selected_segm_id;     // 'ALL' | number
  console.log('read hacky state');

  var segmIds, ranges;

  const [lineMap, gutterLineMap] = useMemo(
    () => {
      if (selectedTag == -1) {
        console.log('no tag selected -> no colors');
        return [null, null] ;
      }
      segmIds  = segmentsToHighlight(templates, soln_lookup, selectedTag, selectedSeg);
      console.log('segmIds', segmIds);

      ranges   = coloredRangesForSegments(templates, segmIds, selectedTag);
      console.log('ranges', ranges);

      const newMap = toLineColorMap(ranges);
      const gutterMap = toLineGutterColors(ranges);  // Map<number, string[]>
      console.log('lineMap', newMap, 'gutterMap', gutterMap);

      return [newMap, gutterMap];
    },
    [selectedSeg, selectedTag, templates, soln_lookup]
  );


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

      {analysisMode && selectedNode.is_solution && (<details open>
        <summary>Code Analysis</summary>
            <pre style={{
            backgroundColor: '#f0f0f0',
            padding: '10px',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'monospace',
            fontSize: '0.85em'
            }}>
            <AnalysisColorButtons indices={
                  (() => {
                    const IntId = Number((selectedId.match(/-?\d+/) || [])[0]);
                    const nodeSegments = global.trace.analysis.segment.soln_lookup[IntId];
                    console.log('soln trace lookup of',IntId,'gave', nodeSegments);
                    if (!nodeSegments) return [];
                    return nodeSegments;
                  })()
                }
              onChange={(next) => setSelectedSegmId(next)} />
            <CodeViewer lines={selectedNode.program_lines} lineColors={lineMap} lineGutterColors={gutterLineMap}/>
            </pre>
      </details>)}

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
