// src/state/globalStore.js
import { create } from 'zustand';



export const useGlobalStore = create(set => ({
  global: {
    status: {
      timestamp: 0,
      has_config: false,
      is_running: false,
      has_trace: false,
    },
    trace: {
      timestamp: 0,
      graph: {'nodes': [], 'edges': []}
    },
  },
  setField: (field, value) =>
    set(state => ({
      global: { ...state.global, [field]: value }
    }))
}));


