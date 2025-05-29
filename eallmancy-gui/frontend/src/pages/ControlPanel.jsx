// src/pages/ControlPanel.jsx
import { useState, useEffect, useRef } from 'react';
import { useGlobalStore } from '../state/globalStore';

import { submitConfig, askAlgos } from '../connection/SocketManager';

import { GitProblemPanel } from '../components/controlpanel/GitProblemPanel';
import { ThinkHardProblemPanel } from '../components/controlpanel/ThinkHardProblemPanel';



function ModeSelector({ selected, onChange }) {
  const modes = ['GitDiff', 'ThinkHard'];

  return (
    <div style={{
      display: 'flex',
      border: '1px solid #ccc',
      borderRadius: '8px',
      overflow: 'hidden',
      width: 'fit-content'
    }}>
      {modes.map(mode => (
        <button
          key={mode}
          onClick={() => onChange(mode)}
          style={{
            padding: '8px 20px',
            backgroundColor: selected === mode ? '#1c1c1c' : '#f5f5f5',
            color: selected === mode ? 'white' : '#555',
            border: 'none',
            cursor: 'pointer',
            fontWeight: selected === mode ? 'bold' : 'normal'
          }}
        >
          {mode}
        </button>
      ))}
    </div>
  );
}

function ModeAwareProblemPanel({mode}) {
  if (mode == "GitDiff") {
    return <GitProblemPanel/>;
  } else if (mode == "ThinkHard") {
    return <ThinkHardProblemPanel/>;
  } else {
    return <div> UNKNOWN MODE SELECTED </div>
  }

}


export default function ControlPanel() {


  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);

  const configRegisteredRef = useRef(global.status.has_config);
  const [mode, setMode] = useState('GitDiff');


  const handleChange = (field, value) => {
    console.log('setting',field,'to',value)
    setGlobalField(field, value);
  };

  return (
    <div>
      <ModeSelector selected={global.ui.selected_algo_type} 
              onChange={e => handleChange('global.ui.selected_algo_type', e)} />
      <ModeAwareProblemPanel mode={global.ui.selected_algo_type}/>
    </div>

  );
}
