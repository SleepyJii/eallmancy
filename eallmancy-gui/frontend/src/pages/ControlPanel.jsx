// src/pages/ControlPanel.jsx

import { useState, useEffect } from 'react';
import { useConfigStore } from '../state/configStore';
import { useGlobalStore } from '../state/globalStore';


export default function ControlPanel() {

  const config = useConfigStore(state => state.config);
  const setConfigField = useConfigStore(state => state.setField);
  const global = useGlobalStore(state => state.global);
  const setGlobalField = useGlobalStore(state => state.setField);

  if (global.has_config) {

  } else {
    return <h1>no problem config set</h1>;
  }

}