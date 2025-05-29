// src/state/globalStore.js
import { create } from 'zustand';

import set from 'lodash/set';



export const useGlobalStore = create((setState, getState) => ({
  global: {
    status: {
      timestamp: 0,
      has_config: false,
      is_running: false,
      has_trace: false,
      trace_is_live: false
    },
    trace: {
      timestamp: 0,
      graph: {'nodes': [], 'edges': []}
    },
    ui: {
      selected_node_id: -1,
      min_fitness: 0,
      max_fitness: 0,
      selected_algo_type: 'GitDiff'
    },
    // config: {
    //   repoPath: '/root/testevolve',
    //   evalScript: '/root/testevolve/poetry_ex/eval.py',
    //   description: 'Write a mysterious poem about apples',
    //   algorithm: null,
    //   overwrite: false,
    //   algos: [],
    //   timestamp: 0,
    // },
    config: {
      llm: {
        api_server: '',
        api_model: '',
        api_key: ''
      },
      gitdiff: {
        repoPath: '/root/testevolve',
        evalScript: '/root/testevolve/poetry_ex/eval.py',
        description: 'Write a mysterious poem about apples',
        algorithm: null,
        overwrite: false,
        algos: [],
        is_selected: true,
        algo_type: 'gitdiff'
      },
      thinkhard: {
        description: 'Write a mysterious poem about apples',
        evaluation_prompts: [
          {},
        ],
        score_combination:'ADD',
        algorithm: null,
        algos: [],
        is_selected: false,
        algo_type: 'thinkhard'
      },
      timestamp: 0,
    }
  },


  setField: (path, value) => {
    setState((state) => {
      const newGlobal = structuredClone(state.global); // deep copy (modern alternative to JSON.parse(JSON.stringify()))
      const cleanPath = path.startsWith('global.') ? path.slice(7) : path;
      set(newGlobal, cleanPath, value);
      return { global: newGlobal };
    });
  }

}));


