// src/state/globalStore.js
import { create } from 'zustand';



export const useGlobalStore = create(set => ({
  global: {
    has_config: false
  },
  setField: (field, value) =>
    set(state => ({
      global: { ...state.global, [field]: value }
    }))
}));


