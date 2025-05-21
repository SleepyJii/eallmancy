// src/components/Banner.jsx


import { Link } from 'react-router-dom';
import { useGlobalStore } from '../state/globalStore';


function StatusIndicator({ status }) {
  let label = 'Idle';
  let color = '#999';

  if (!status.has_config) {
    label = 'Unconfigured';
    color = '#888';
  } else if (status.is_running) {
    label = 'Running';
    color = '#2a9d8f';
  } else if (status.has_trace & !status.is_running) {
    label = 'Finished';
    color = '#264653';
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
        <Link to="/controlpanel" style={{ marginRight: '30px' }}>ControlPanel</Link>
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
        <BannerButton label="START" enabled={isReady} onClick={() => console.log('start')} />
        <BannerButton label="STOP" enabled={isRunning} onClick={() => console.log('stop')} />
        <StatusIndicator status={global.status} />
      </div>
    </div>
  );
}





// import { Link } from 'react-router-dom';
// import { useGlobalStore } from '../state/globalStore';



// function BannerButton({ label, enabled, onClick }) {
//   return (
//     <button
//       onClick={enabled ? onClick : undefined}
//       title={enabled ? '' : 'Unavailable due to system state'}
//       style={{
//         marginRight: '10px',
//         opacity: enabled ? 1 : 0.5,
//         pointerEvents: enabled ? 'auto' : 'none',
//         cursor: enabled ? 'pointer' : 'default',
//       }}
//     >
//       {label}
//     </button>
//   );
// }



// export default function Banner() {

//   const global = useGlobalStore(state => state.global);
//   const isReady = global.status.has_config && !global.status.is_running;
//   const isRunning = global.status.is_running;


//   return (
//     <div style={{
//       display: 'flex',
//       justifyContent: 'space-between',
//       alignItems: 'center',
//       padding: '10px',
//       background: '#eee',
//       marginBottom: '20px'
//     }}>
//       <div>
//         <h1 style={{ display: 'inline', marginRight: '30px' }}>EALLMancy</h1>
//         <Link to="/controlpanel" style={{ marginRight: '15px' }}>ControlPanel</Link>
//         <Link to="/traceview">TraceView</Link>
//       </div>
//       <div>
//         <BannerButton label="START" enabled={isReady} onClick={() => console.log('start')} />
//         <BannerButton label="STOP" enabled={isRunning} onClick={() => console.log('stop')} />
//       </div>
//     </div>
//   );
// }
