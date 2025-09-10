// src/pages/TraceView.jsx
import LineageView from '../components/traceview/LineageView.tsx';
import NodeInspectorView from '../components/traceview/NodeInspectorView.tsx'

export default function TraceView() {
  return (
    <div style={{ display: 'flex', height: '80vh', marginLeft: '30px' }}>
      <LineageView />
      <NodeInspectorView />
    </div>

  );
}