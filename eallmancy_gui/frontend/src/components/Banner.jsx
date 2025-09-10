// src/components/Banner.jsx


import { Link } from 'react-router-dom';
import { useGlobalStore } from '../state/globalStore';
import { startEvolution, askTimestamps, stopEvolution } from '../connection/SocketManager';




function AnalysisSwitch({ checked, onChange }) {
  return (
    <label
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginLeft: '20px',
        userSelect: 'none',
        cursor: 'pointer',
        fontSize: '0.95em',
      }}
    >
      Analysis Mode
      {/* Visually hidden checkbox for a11y and reliable toggling */}
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ position: 'absolute', opacity: 0, width: 0, height: 0 }}
      />
      <span
        aria-hidden="true"
        style={{
          position: 'relative',
          width: '46px',
          height: '24px',
          borderRadius: '999px',
          background: checked ? '#044bbd' : '#aaa',
          transition: 'background 150ms',
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: '3px',
            left: checked ? '24px' : '3px',
            width: '18px',
            height: '18px',
            borderRadius: '50%',
            background: '#fff',
            transition: 'left 150ms',
            boxShadow: '0 1px 3px rgba(0,0,0,0.35)',
          }}
        />
      </span>
    </label>
  );
}




function EngineIndicator({ status }) {
  let label = 'Ready';
  let color = '#adb300';

  if (!status.has_config) {
    label = 'Unconfigured';
    color = '#888';
  } else if (status.is_running) {
    label = 'Running';
    color = '#029909';
  } else if (status.has_trace & !status.is_running) {
    label = 'Standby';
    color = '#ad7005';
  }

  return (
    <div style={{
      marginLeft: '20px',
      padding: '4px 10px',
      borderRadius: '8px',
      backgroundColor: color,
      color: 'white',
      fontSize: '0.9em',
      fontWeight: 'bold'
    }}>
      {label}
    </div>
  );
}

function TraceIndicator({ status, configTime, traceTime, traceNodes }) {
  let label = 'NoTrace';
  let color = '#888';
  console.log('indicator sees nodelen', status, configTime, traceTime, traceNodes.length);
  if (status.trace_is_live && traceNodes.length == 0) {
    label = 'Waiting';
    color = '#adb300';
  } else if (traceTime < configTime) {
    label = 'StaleTrace';
    color = '#adb300';
  } else if (status.trace_is_live) {
    label = 'LiveTrace';
    color = '#044bbd';
  } else if (status.has_trace) {
    label = 'CachedTrace';
    color = '#0028b8';
  }

  return (
    <div style={{
      marginLeft: '20px',
      marginRight: '20px',
      padding: '4px 10px',
      borderRadius: '8px',
      backgroundColor: color,
      color: 'white',
      fontSize: '0.9em',
      fontWeight: 'bold'
    }}>
      {label}
    </div>
  );
}

function BannerButton({ label, enabled, onClick }) {
  return (
    <button
      onClick={enabled ? onClick : undefined}
      title={enabled ? '' : 'Unavailable due to system state'}
      style={{
        marginRight: '10px',
        opacity: enabled ? 1 : 0.5,
        pointerEvents: enabled ? 'auto' : 'none',
        cursor: enabled ? 'pointer' : 'default',
      }}
    >
      {label}
    </button>
  );
}

export default function Banner() {
  const global = useGlobalStore(state => state.global);
  const isReady = global.status.has_config && !global.status.is_running;
  const isRunning = global.status.is_running;

  const trace = useGlobalStore(state => state.global.trace);
  const traceNodes = trace.graph.nodes;
  const traceTime = trace.timestamp;
  const config = useGlobalStore(state => state.global.config);
  const configTime = config.timestamp;

  const analysisMode = useGlobalStore((state) => state.global.ui?.analysis_mode ?? false);
  // const toggleAnalysisMode = useGlobalStore((state) => state.toggleAnalysisMode);

  const toggleAnalysisMode = () => {
    const state = useGlobalStore.getState();
    console.log('switching analysis_mode to ',!state.global.ui.analysis_mode);
    state.setField(`global.ui.analysis_mode`, !state.global.ui.analysis_mode);
  };
  

  const handleStart = () => {
    startEvolution();
  };

  const handleStop = () => {
    stopEvolution();
  };

  return (
    <div style={{ marginBottom: '20px' }}>
      {/* Top banner: title + links */}
      <div style={{
        padding: '10px',
        background: '#eee',
        display: 'flex',
        alignItems: 'center'
      }}>
        <h1 style={{ display: 'inline', marginRight: '100px' }}>EALLMancy</h1>
        <Link to="/config" style={{ marginRight: '30px' }}>Configuration</Link>
        <Link to="/traceview">TraceView</Link>
      </div>

      {/* Sub-banner: control buttons */}
      <div style={{
        padding: '6px 10px',
        background: '#ddd',
        borderTop: '1px solid #ccc',
        display: 'flex',
        justifyContent: 'flex-start'
      }}>
        <BannerButton label="START" enabled={isReady} onClick={handleStart} />
        <BannerButton label="STOP" enabled={isRunning} onClick={handleStop} />
        <AnalysisSwitch checked={analysisMode} onChange={toggleAnalysisMode} />
        <EngineIndicator status={global.status} />
        <TraceIndicator  status={global.status} configTime={configTime} traceTime={traceTime} traceNodes={traceNodes}/>
        <BannerButton label="refresh" enabled={true} onClick={askTimestamps} />
      </div>
    </div>
  );
}



