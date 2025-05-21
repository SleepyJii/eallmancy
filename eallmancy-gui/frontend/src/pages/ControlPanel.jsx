// src/pages/Config.jsx
import { useState, useEffect, useRef } from 'react';
import { useConfigStore } from '../state/configStore';
import { useGlobalStore } from '../state/globalStore';


// function EalllmancerControlPanel() {
//   const global = useGlobalStore(state => state.config);
//   const setGlobalField = useGlobalStore(state => state.setField);

//   return (
//     <div>

//         <button
//           // onClick={handleSubmit}
//           // disabled={!allValid}
//           style={{ fontSize: '1.2em', padding: '10px 20px' }}
//         >
//           START
//         </button>
//         <p/>
//         <button
//           // onClick={handleSubmit}
//           // disabled={!allValid}
//           style={{ fontSize: '1.2em', padding: '10px 20px' }}
//         >
//           STOP
//         </button>

//     </div>
//   )
// }


export default function ControlPanel() {


  const config = useConfigStore(state => state.config);
  const setConfigField = useConfigStore(state => state.setField);
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

  const [algorithmOptions, setAlgorithmOptions] = useState(['loading...']);

  useEffect(() => {
    fetch('/api/config/algorithms')
      .then(res => res.json())
      .then(data => {
        setAlgorithmOptions(data);
        setConfigField('algorithm', data[0]);
      })
      .catch(() => setAlgorithmOptions(['error']));
  }, []);


  const handleChange = (field, value) => {
    setConfigField(field, value);
  };

  const handleCheckbox = (field, checked) => {
    setConfigField(field, checked);
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

    console.log('Final config:', config);
    {
      fetch('/api/config/submit', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(config) })
      .then(res => {
        if (res.ok) {
          setGlobalField('has_config', true);
        }
      })
      // .catch(() => ERRORALERT)
    };
  };

  return (
    <div style={{ padding: '20px', width: 'min(40%, 600px)' }}>

      <div>
        <label>Git Repo Path:</label><br />
        <input
          type="text"
          value={config.repoPath}
          onChange={e => handleChange('repoPath', e.target.value)}
          style={{ border: borderStyle('repoPath'), width: '400px' }}
          placeholder="/path/to/evolve/target/gitrepo"
        /><br /><br />

        <label>Eval Script Path:</label><br />
        <input
          type="text"
          value={config.evalScript}
          onChange={e => handleChange('evalScript', e.target.value)}
          style={{ border: borderStyle('evalScript'), width: '400px' }}
          placeholder="/path/to/eval/script.sh"
        /><br /><br />

        <label>Problem Description:</label><br />
        <textarea
          value={config.description}
          onChange={e => handleChange('description', e.target.value)}
          rows={4}
          cols={60}
          style={{ border: borderStyle('description') }}
          placeholder="We want to edit these sections of code to maximize a real-valued black box criteria"
        /><br />
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '70px', marginTop: '20px' }}>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '40px' }}>
          <div>
            <label>Algorithm</label><br />
            <select
              value={config.algorithm}
              onChange={e => handleChange('algorithm', e.target.value)}
            >
              {algorithmOptions.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          <div>
            <label>LiveOverwrite</label><br />
            <input
              type="checkbox"
              checked={config.overwrite}
              onChange={e => handleCheckbox('overwrite', e.target.checked)}
            />
          </div>

        </div>

        <button
          onClick={handleSubmit}
          disabled={!allValid}
          style={{ fontSize: '1.2em', padding: '10px 20px' }}
        >
          Confirm
        </button>
      </div>

      {/* <div disabled={configRegisteredRef}>
        <hr class="default"></hr>
        <EalllmancerControlPanel/>
      </div> */}
    </div>

  );
}
