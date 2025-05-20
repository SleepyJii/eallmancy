// src/components/Banner.jsx
import { Link } from 'react-router-dom';

export default function Banner() {
  return (
    <div style={{ padding: '10px', background: '#eee', marginBottom: '20px' }}>
      <h1 style={{ display: 'inline', marginRight: '30px' }}>EALLMancy</h1>
      <Link to="/config" style={{ marginRight: '15px' }}>Config</Link>
      <Link to="/controlpanel" style={{ marginRight: '15px' }}>ControlPanel</Link>
      <Link to="/traceview">TraceView</Link>
    </div>
  );
}
