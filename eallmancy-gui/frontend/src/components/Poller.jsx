
import { useEffect, useRef } from 'react';
import { useGlobalStore } from '../state/globalStore';


export default function Poller() {
  const global = useGlobalStore(state => state.global);
  const setField = useGlobalStore(state => state.setField);

  const statusRef = useRef(global.status.timestamp);
  const traceRef = useRef(global.trace.timestamp);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch('/api/timestamps')
        .then(res => res.json())
        .then(remote => {
          if (remote.status.timestamp > statusRef.current) {
            fetch('/api/view/status')
              .then(res => res.json())
              .then(data => {
                setField('status', data);
                statusRef.current = data.timestamp;
                console.log('UPDATED STATUS', data);
              });
          }
          if (remote.trace.timestamp > traceRef.current) {
            fetch('/api/view/trace')
              .then(res => res.json())
              .then(data => {
                setField('trace', data);
                traceRef.current = data.timestamp;
                console.log('UPDATED TRACE', data);
              });
          }
        })
        .catch(err => console.error('Polling error:', err));
    }, 5000);

    return () => clearInterval(interval);
  }, [setField]);

  return null;
}
