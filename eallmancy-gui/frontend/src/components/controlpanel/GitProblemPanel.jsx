// src/components/controlpanel/GitProblemPanel.jsx
import { useState, useEffect, useRef } from 'react';
import { useGlobalStore } from '../../state/globalStore';

import { submitConfig, askAlgos } from '../../connection/SocketManager';




export function GitProblemPanel() {

  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);

  const configRegisteredRef = useRef(global.status.has_config);

  const [validation, setValidation] = useState({
    repoPath: 'valid',
    evalScript: 'valid',
    description: 'valid',
    algorithm: 'valid',
    overwrite: 'valid',
  });

  const handleChange = (field, value) => {
    setGlobalField(field, value);
  };

  const handleCheckbox = (field, checked) => {
    setGlobalField(field, checked);
  };

  const allValid = Object.values(validation).every(v => v === 'valid');

  const borderStyle = field =>
    validation[field] === 'invalid'
      ? '2px solid red'
      : validation[field] === 'pending'
      ? '2px dashed orange'
      : undefined;

  const handleSubmit = () => {
    if (!allValid) return;

    console.log('Final config:', global.config.gitdiff);
    submitConfig(JSON.stringify(global.config.gitdiff));
  };

  if (global.config.gitdiff.algos.length == 0) {
    askAlgos('gitdiff');
  }

  return (
    <div style={{ padding: '20px', width: 'min(40%, 600px)' }}>

      <div>
        <label>Git Repo Path:</label><br />
        <input
          type="text"
          value={global.config.gitdiff.repoPath}
          onChange={e => handleChange('config.gitdiff.repoPath', e.target.value)}
          style={{ border: borderStyle('repoPath'), width: '400px' }}
          placeholder="/path/to/evolve/target/gitrepo"
        /><br /><br />

        <label>Eval Script Path:</label><br />
        <input
          type="text"
          value={global.config.gitdiff.evalScript}
          onChange={e => handleChange('config.gitdiff.evalScript', e.target.value)}
          style={{ border: borderStyle('evalScript'), width: '400px' }}
          placeholder="/path/to/eval/script.sh"
        /><br /><br />

        <label>Problem Description:</label><br />
        <textarea
          value={global.config.gitdiff.description}
          onChange={e => handleChange('config.gitdiff.description', e.target.value)}
          rows={4}
          cols={60}
          style={{ border: borderStyle('description') }}
          placeholder="We want to edit these sections of code to maximize a real-valued black box criteria"
        /><br />
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '70px', marginTop: '20px' }}>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '40px' }}>
          {/* <div>
            <label>Algorithm</label><br />
            <select
              value={global.config.gitdiff.algorithm}
              onChange={e => handleChange('config.gitdiff.algorithm', e.target.value)}
            >
              {global.config.gitdiff.algos.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div> */}

          <div>
            <label>LiveOverwrite</label><br />
            <input
              type="checkbox"
              checked={global.config.gitdiff.overwrite}
              onChange={e => handleCheckbox('config.gitdiff.overwrite', e.target.checked)}
            />
          </div>

        </div>
      </div>

    </div>

  );
}

