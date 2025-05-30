
import { useState, useEffect } from 'react';

import { useGlobalStore } from '../../state/globalStore';



export function AlgorithmConfigPanel() {

  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);
  const selectedAlgoType = global.ui.selected_algo_type.toLowerCase();

  const handleChange = (field, value) => {
    setGlobalField(field, value);
  };

  const [isValidJson, setIsValidJson] = useState(true);

  const handleJsonChange = (e) => {
    const newText = e.target.value;
    setGlobalField(`global.config.algo.settings`, newText);
    try {
      const parsed = JSON.parse(newText);
      setIsValidJson(true);
    } catch (err) {
      setIsValidJson(false);
    }
  };

  return (
    <div>
        <div>
            <label>Algorithm</label><br />
            <select
                value={global.config[selectedAlgoType].algorithm}
                onChange={e => handleChange(`config.${selectedAlgoType}.algorithm`, e.target.value)}
            >
                {global.config[selectedAlgoType].algos.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
        </div>

        <p/>

      <div>
        <label>Algorithm Settings (JSON):</label><br />
        <textarea
          rows={12}
          cols={60}
          value={global.config.algo.settings}
          onChange={handleJsonChange}
          style={{
            fontFamily: 'monospace',
            border: isValidJson ? '1px solid #ccc' : '2px solid red',
            backgroundColor: isValidJson ? '#fff' : '#ffe6e6',
            padding: '8px',
            width: '100%',
            resize: 'vertical'
          }}
        />
        {!isValidJson && <div style={{ color: 'red' }}>Invalid JSON</div>}
      </div>

    </div>
  )
}

