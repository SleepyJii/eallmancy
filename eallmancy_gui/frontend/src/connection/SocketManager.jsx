// websocketManager.js
import { useGlobalStore } from '../state/globalStore';
import { useEffect, useRef } from 'react';

// dynamically point at host WebSocket endpoint
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const host = window.location.host;  // includes hostname and port


// WebSocket maintenance

let ws = null;


const WS_URL = (() => {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host;
  return `${protocol}://${host}/ws`;
})();



function handle_message(event) {
  const { type, payload } = JSON.parse(event.data);
  
  // TODO: *think*, what kinds of feedback might come from the backend
  switch (type) {
    case 'TIMESTAMP_UPDATE':

      // mimicking Poller logic, though I don't expect to ever ask for timestamps...
      const st_timestamp = payload.status.timestamp;
      const st_knowntime = useGlobalStore.getState().global.status.timestamp;
      const tr_timestamp = payload.trace.timestamp;
      const tr_knowntime = useGlobalStore.getState().global.trace.timestamp;
      console.log('recv timestamp update', payload, 'old sttime',st_knowntime,' old_trtime', tr_knowntime);

      if (st_timestamp > st_knowntime) {
        askStatus();
      }
      if (tr_timestamp > tr_knowntime) {
        askTrace();
      }
      break;

    case 'STATUS_UPDATE':
      console.log('recv status update', payload);
      useGlobalStore.getState().setField('global.status', payload);
      useGlobalStore.getState().setField('global.status.timestamp', payload.timestamp);
      break;

    case 'FULL_TRACE_UPDATE':
      console.log('recv trace update', payload);
      useGlobalStore.getState().setField('global.trace', payload);
      useGlobalStore.getState().setField('global.trace.timestamp', payload.timestamp);
      console.log(useGlobalStore.getState().global.trace);
      // setField('global.trace', payload);
      // traceRef.current = payload.timestamp;
      break;
    
    case 'CONFIG_UPDATE':
      console.log('recv config update', payload);
      useGlobalStore.getState().setField('global.config.timestamp', Date.now() / 1e3);
      askStatus();
      break;

    case 'ALGORITHMS_UPDATE':
      // TODO: handle different config types!
      console.log('recv algo update', payload);
      const algo_type = payload.algo_type;
      const algos = payload.algos;
      useGlobalStore.getState().setField(`global.config.${algo_type}.algos`, algos);
      if (useGlobalStore.getState().global.config[algo_type].algorithm === null && algos.length > 0)  {
        useGlobalStore.getState().setField(`global.config.${algo_type}.algorithm`, algos[0]);
        console.log('algo is now', useGlobalStore.getState().global.config[algo_type].algorithm);
        console.log(useGlobalStore.getState().global.config);
      }
      break;

    default:
      console.warn('Unknown WebSocket message type:', type);
  }
}


export function startWebSocket() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log('[WS] Connected');
    // reconnectAttempts = 0;
    // Flush queued messages
    // while (messageQueue.length > 0) {
    //   socket.send(messageQueue.shift());
    // }
  };

  ws.onmessage = (event) => {
    handle_message(event);
  };

  ws.onclose = () => {
    console.warn('[WS] Disconnected. Reconnecting...');
    // scheduleReconnect();
  };

  ws.onerror = (err) => {
    console.error('[WS] Error', err);
    ws.close();
  };
}


export function sendMessage(type, payload) {
  const msg = JSON.stringify({ type, payload });
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(msg);
  } else {
    console.warn('[WS] Not connected — message not sent');
    // messageQueue.push(msg);
  }
}

// getTimestamps
export const askTimestamps = () => {
  sendMessage("GET_TIMESTAMPS", []);
};

// getStatus
export const askStatus = () => {
  sendMessage("GET_STATUS", []);
};

// getTrace
export const askTrace = () => {
  sendMessage("GET_TRACE", []);
};

// getTrace
export const askAlgos = (algo_type) => {
  sendMessage("GET_ALGOS", {algo_type: algo_type});
};

export const startEvolution = () => {
  sendMessage("START_EA", []);
};

export const stopEvolution = () => {
  sendMessage("STOP_EA", []);
};

export const submitConfig = (cfg) => {
  sendMessage("SUBMIT_CONFIG", cfg);
};

