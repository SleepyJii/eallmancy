// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ControlPanel from './pages/ControlPanel';
import TraceView from './pages/TraceView';
import { useState, useEffect } from 'react';

import Banner from './components/Banner';
import SocketTest from './pages/SocketTest';

import { startWebSocket } from './connection/SocketManager';

console.log("App is rendering");



function App() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/eruda';
    script.onload = () => window.eruda && window.eruda.init();
    document.body.appendChild(script);
  }, []);

  
  try {
    startWebSocket(); // whatever might be throwing
  } catch (err) {
    console.error("Function threw an error:", err);
    // Optionally: update state, show a fallback, etc.
  }
  return (
    <div>
    <Router>
      <Banner />
      <Routes>
        <Route path="/" element={<ControlPanel />}/>
        <Route path="/config" element={<ControlPanel />} />
        <Route path="/traceview" element={<TraceView />} />
        <Route path="/" element={<SocketTest />} />
      </Routes>
    </Router>
    </div>
  );
}
export default App;

// javascript:(function () { var script = document.createElement('script'); script.src="https://cdn.jsdelivr.net/npm/eruda"; document.body.append(script); script.onload = function () { eruda.init(); } })();
