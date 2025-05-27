// src/state/configStore.js
import { create } from 'zustand';

import set from 'lodash/set';


export const useConfigStore = create((setState, getState) => ({
  config: {
    repoPath: '/root/testevolve',
    evalScript: '/root/testevolve/poetry_ex/eval.py',
    description: 'Write a mysterious poem about apples',
    algorithm: null,
    overwrite: false,
    algos: [],
  },
  
  setField: (path, value) => {
    setState((state) => {
      const newGlobal = structuredClone(state.config); // deep copy (modern alternative to JSON.parse(JSON.stringify()))
      const cleanPath = path.startsWith('config.') ? path.slice(7) : path;
      set(newGlobal, cleanPath, value);
      return { config: newGlobal };
    });
  }
}));


