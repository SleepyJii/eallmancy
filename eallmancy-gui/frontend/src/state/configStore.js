// src/state/configStore.js
import { create } from 'zustand';



export const useConfigStore = create(set => ({
  config: {
    repoPath: '',
    evalScript: '',
    description: '',
    algorithm: 'algo1',
    overwrite: false
  },
  setField: (field, value) =>
    set(state => ({
      config: { ...state.config, [field]: value }
    }))
}));


