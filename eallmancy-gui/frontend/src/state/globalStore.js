// src/state/globalStore.js
import { create } from 'zustand';



export const useGlobalStore = create(set => ({
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
      max_fitness: 0
    }
  },
  setField: (field, value) =>
    set(state => ({
      global: { ...state.global, [field]: value }
    }))
}));


