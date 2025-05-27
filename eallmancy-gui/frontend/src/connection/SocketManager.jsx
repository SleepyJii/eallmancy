// websocketManager.js
import { useGlobalStore } from '../state/globalStore';
import { useConfigStore } from '../state/configStore';
import { useEffect, useRef } from 'react';

// dynamically point at host WebSocket endpoint
const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const host = window.location.host;  // includes hostname and port


// WebSocket maintenance

let ws = null;
// let ws = new WebSocket(`${protocol}://${host}/ws`);
// let reconnectAttempts = 0;


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
      console.log('recv timestamp update', payload);

      // mimicking Poller logic, though I don't expect to ever ask for timestamps...
      const st_timestamp = payload.status.timestamp;
      const tr_timestamp = payload.trace.timestamp;

      if (st_timestamp > useGlobalStore.getState().global.status.timestamp) {
        askStatus();
      }
      if (tr_timestamp > useGlobalStore.getState().global.trace.timestamp) {
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

    case 'ALGORITHMS_UPDATE':
      console.log('recv algo update', payload);
      // useConfigStore.getState().setConfigField('algos', payload);
      useConfigStore.getState().setField('algos', payload);
      console.log(useConfigStore.getState().algos);
      if (useConfigStore.getState().config.algorithm === null && payload.length > 0)  {
        useConfigStore.getState().setField('algorithm', payload[0]);
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
export const askAlgos = () => {
  sendMessage("GET_ALGOS", []);
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

