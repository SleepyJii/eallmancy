// src/state/globalStore.js
import { create } from 'zustand';

import set from 'lodash/set';


const initialAlgoSettings = `
{
"num_initial_samples":5, "pop_size":10, "max_samples":30, "max_generations":1000,
"num_e1":1, "num_e2":1, "num_m1":1, "num_m2":1, "num_e1_parents":3, "num_e2_parents":3
}
`;


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
      selected_algo_type: 'GitDiff',
      selected_config_tab: 'Problem'
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
      algo: {
        settings: initialAlgoSettings
      },
      llm: {
        api_server: "https://api.openai.com",
        model: 'gpt-4o-mini',
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
          {'name': 'fluency', 'description': 'score the output in terms of its writing quality between 0 (worst) and 100 (best)'},
          {'name': 'originality', 'description': 'score the poem on its original creativity between 0 (worst) and 100 (best)'},
          {'name': 'structure', 'description': 'score the poem on the appealingness of its structure, rhymes, and symmetries between 0 (worst) and 100 (best)'},
        ],
        score_combination:'SUM',
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


