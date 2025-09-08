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
      graph: {'nodes': [], 'edges': []},
      analysis: {'segment': null, 'pairwise': null},
    },
    ui: {
      selected_node_id: -1,
      selected_segm_id: 'ALL',
      min_fitness: 0,
      max_fitness: 0,
      selected_algo_type: 'GitDiff',
      selected_config_tab: 'Problem',
      analysis_mode: false,
    },
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
        evalScript: '/root/testevolve/ecoli/eval.py',
        description: 'Find the mathematical function skeleton that represents E. Coli bacterial growth rate, given data on population density, substrate concentration, temperature, and pH level. Implement it as a Python function called `equation`.',
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
  setSelectedSegmId: (val) => {
    console.log('setting selected_segm_id to',val);
    set((s) => ({ global: { ...s.global, ui: { ...s.global.ui, selected_segm_id: val } } }));
  },

  // NEW: set explicitly
  setAnalysisMode: (on) =>
    set((state) => ({
      global: {
        ...state.global,
        ui: { ...state.global.ui, analysis_mode: true },
      },
    })),

  // NEW: convenient toggle
  toggleAnalysisMode: () =>
    set((state) => ({
      global: {
        ...state.global,
        ui: { ...state.global.ui, analysis_mode: !(state.global.ui.analysis_mode ?? false) },
      },
    })),


  setField: (path, value) => {
    setState((state) => {
      const newGlobal = structuredClone(state.global); // deep copy (modern alternative to JSON.parse(JSON.stringify()))
      const cleanPath = path.startsWith('global.') ? path.slice(7) : path;
      set(newGlobal, cleanPath, value);
      return { global: newGlobal };
    });
  }

}));


