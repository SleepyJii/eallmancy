import { useGlobalStore } from '../../state/globalStore';
import { useMemo } from 'react';

export default function NodeInspector() {
  const global = useGlobalStore(state => state.global);
  const selectedId = global.ui.selected_node_id;

  const selectedNode = useMemo(() => {
    return global.trace.graph.nodes.find(n => n.id === selectedId);
  }, [selectedId, global.trace.graph.nodes]);

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
      <details open>
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

      <details>
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
