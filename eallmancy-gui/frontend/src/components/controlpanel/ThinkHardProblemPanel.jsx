import { useState, useRef } from 'react';
import { useGlobalStore } from '../../state/globalStore';
import { submitConfig, askAlgos } from '../../connection/SocketManager';

export function ThinkHardProblemPanel() {
  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);
  const configRegisteredRef = useRef(global.status.has_config);

  const [validation, setValidation] = useState({
    description: 'valid',
    algorithm: 'valid',
  });

  const allValid = Object.values(validation).every(v => v === 'valid');

  const borderStyle = field =>
    validation[field] === 'invalid'
      ? '2px solid red'
      : validation[field] === 'pending'
      ? '2px dashed orange'
      : undefined;

  const handleChange = (field, value) => {
    setGlobalField(field, value);
  };

  const handleEvalChange = (idx, subfield, value) => {
    const newPrompts = [...global.config.thinkhard.evaluation_prompts];
    newPrompts[idx][subfield] = value;
    setGlobalField('config.thinkhard.evaluation_prompts', newPrompts);
  };

  const handleAddPrompt = () => {
    const newPrompts = [...global.config.thinkhard.evaluation_prompts, { name: '', description: '' }];
    setGlobalField('config.thinkhard.evaluation_prompts', newPrompts);
  };

  const handleRemovePrompt = (idx) => {
    const newPrompts = global.config.thinkhard.evaluation_prompts.filter((_, i) => i !== idx);
    setGlobalField('config.thinkhard.evaluation_prompts', newPrompts);
  };

  const handleSubmit = () => {
    if (!allValid) return;
    console.log('Final config:', global.config.thinkhard);
    submitConfig(JSON.stringify(global.config.thinkhard));
  };

  if (global.config.thinkhard.algos.length === 0) {
    askAlgos('thinkhard');
  }

  return (
    <div style={{ padding: '20px', width: 'min(60%, 800px)' }}>
      <label>Problem Description:</label><br />
      <textarea
        value={global.config.thinkhard.description}
        onChange={e => handleChange('config.thinkhard.description', e.target.value)}
        rows={4}
        cols={60}
        style={{ border: borderStyle('description') }}
        placeholder="Describe what the model is trying to achieve..."
      /><br /><br />

      <div>
        <label>Evaluation Prompts:</label><br />
        <p><i>prompt an evaluator LLM to give real valued scores by varied criteria</i></p>
        {global.config.thinkhard.evaluation_prompts.map((prompt, idx) => (
          <div key={idx} style={{ marginBottom: '10px', paddingLeft: '10px', borderLeft: '2px solid #ccc' }}>
            <input
              type="text"
              value={prompt.name}
              onChange={e => handleEvalChange(idx, 'name', e.target.value)}
              placeholder="criterion alias"
              style={{ width: '150px', marginRight: '10px' }}
            />
            <input
              type="text"
              value={prompt.description}
              onChange={e => handleEvalChange(idx, 'description', e.target.value)}
              placeholder="criterion description"
              style={{ width: '650px' }}
            />
            <button onClick={() => handleRemovePrompt(idx)} style={{ marginLeft: '10px' }}>−</button>
          </div>
        ))}
        <button onClick={handleAddPrompt}>+ Add Prompt</button>
      </div>
        <p></p>
    <div>
        <label>Score Combination</label><br />
        <select
        value={global.config.thinkhard.score_combination}
        onChange={e => handleChange('config.thinkhard.score_combination', e.target.value)}
        >
        <option value="ADD">ADD</option>
        <option value="MIN">MIN</option>
        <option value="MAX">MAX</option>
        </select>
    </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '40px', marginTop: '20px' }}>
        <div>
          <label>Algorithm</label><br />
          <select
            value={global.config.thinkhard.algorithm}
            onChange={e => handleChange('config.thinkhard.algorithm', e.target.value)}
          >
            {global.config.thinkhard.algos.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!allValid}
          style={{ fontSize: '1.2em', padding: '10px 20px' }}
        >
          Confirm
        </button>
      </div>
    </div>
  );
}
