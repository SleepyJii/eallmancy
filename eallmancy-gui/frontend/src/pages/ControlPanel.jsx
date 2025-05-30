// src/pages/ControlPanel.jsx
import { useState, useEffect, useRef } from 'react';
import { useGlobalStore } from '../state/globalStore';

import { submitConfig, askAlgos } from '../connection/SocketManager';

import { GitProblemPanel } from '../components/controlpanel/GitProblemPanel';
import { ThinkHardProblemPanel } from '../components/controlpanel/ThinkHardProblemPanel';
import { LLMConfigPanel } from '../components/controlpanel/LLMConfigPanel';
import { AlgorithmConfigPanel } from '../components/controlpanel/AlgorithmConfigPanel';



const _MODE_ALIASES = {
  GitDiff: 'Quantitative',
  ThinkHard: 'Qualitative'
}

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
            backgroundColor: selected === mode ? '#333' : '#f5f5f5',
            color: selected === mode ? 'white' : '#555',
            border: 'none',
            cursor: 'pointer',
            fontWeight: selected === mode ? 'bold' : 'normal'
          }}
        >
          {_MODE_ALIASES[mode]}
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

function ProblemConfigPanel() {

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
      Problem Type: <ModeSelector selected={global.ui.selected_algo_type} 
              onChange={e => handleChange('global.ui.selected_algo_type', e)} />
      <ModeAwareProblemPanel mode={global.ui.selected_algo_type}/>
    </div>

  );
}

function renderTabContent() {

  const global = useGlobalStore.getState().global;
  const tab = global.ui.selected_config_tab;
  switch (tab) {
    case 'Problem':
      return (
        <ProblemConfigPanel/>
      );
    case 'Algorithm':
      return (
        <AlgorithmConfigPanel/>
      );
    case 'LLM':
      return (
        <LLMConfigPanel/>
      );
    default:
      return <div>Unknown Tab</div>;
  }

}

export default function ControlPanel() {


  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);
  const tab = global.ui.selected_config_tab;


  const handleChange = (field, value) => {
    console.log('setting',field,'to',value)
    setGlobalField(field, value);
  };

  return (

    <div style={{ display: 'flex', minHeight: '400px', padding: '20px' }}>
      {/* Tabs sidebar */}
      <div style={{ display: 'flex', flexDirection: 'column', marginRight: '40px' }}>
        {['Problem', 'Algorithm', 'LLM'].map(t => (
          <button
            key={t}
            onClick={() => handleChange('global.ui.selected_config_tab', t)}
            style={{
              padding: '10px 20px',
              width: '85%',
              justifyContent: 'center',
              display: 'flex',
              marginBottom: '12px',
              backgroundColor: tab === t ? '#333' : '#f5f5f5',
              color: tab === t ? '#fff' : '#555',
              fontWeight: tab === t ? 'bold' : 'normal',
              border: 'none',
              borderRadius: '12px',
              boxShadow: tab === t ? '0 2px 6px rgba(0,0,0,0.15)' : 'none',
              cursor: 'pointer',
              transition: 'all 0.2s ease-in-out',
            }}
          >
            {t}
          </button>
        ))}
          <div style={{ flexGrow: 1 }} />  {/* Spacer pushes button down */}
          <button
            onClick={() => {
              submitConfig(JSON.stringify({
                ...global.config[global.ui.selected_algo_type.toLowerCase()],
                 'algo_settings': JSON.parse(global.config.algo.settings)
              }));
            }}
            style={{ fontSize: '1.1em', padding: '10px 20px' }}
          >
            Submit Config
          </button>
      </div>

      {/* Right-side tab content */}
      <div style={{ flex: 1 }}>
        {renderTabContent()}
        <div style={{ marginTop: '30px' }}>
        </div>
      </div>
    </div>
  );
}
