

import { useGlobalStore } from '../../state/globalStore';





export function LLMConfigPanel() {

  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);

  const handleChange = (field, value) => {
    setGlobalField(field, value);
  };

  return (
    <div style={{ maxWidth: '500px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <label>Host URL:</label><br />
        <input
          type="text"
          value={global.config.llm.api_server}
          onChange={e => handleChange(`config.llm.api_server`, e.target.value)}
          style={{ width: '100%', padding: '8px' }}
        />
      </div>

      <div>
        <label>Model:</label><br />
        <input
          type="text"
          placeholder="gpt-4"
          value={global.config.llm.model}
          onChange={e => handleChange('config.llm.model', e.target.value)}
          style={{ width: '100%', padding: '8px' }}
        />
      </div>

      <div>
        <label>API Key:</label><br />
        <input
          type="password"
          placeholder="sk-..."
          value={global.config.llm.api_key}
          onChange={e => handleChange('config.llm.api_key', e.target.value)}
          style={{ width: '100%', padding: '8px' }}
        />
      </div>
    </div>
  );
}


