// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ControlPanel from './pages/ControlPanel';
import TraceView from './pages/TraceView';
import Poller from './components/Poller';
import { useState, useEffect } from 'react';

import Banner from './components/Banner';

function App() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/eruda';
    script.onload = () => window.eruda && window.eruda.init();
    document.body.appendChild(script);
  }, []);
  return (
    <Router>
      <Banner />
      <Poller />
      <Routes>
        <Route path="/" element={<ControlPanel />} />
        <Route path="/controlpanel" element={<ControlPanel />} />
        <Route path="/traceview" element={<TraceView />} />
      </Routes>
    </Router>
//    
  );
}

export default App;

