import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [status, setStatus] = useState('checking...');

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('backend not reachable'));
  }, []);

  return (
    <div style={{ textAlign: 'center', marginTop: '4rem' }}>
      <h1>Quantum Learning Workspace</h1>
      <p>Backend status : <strong>{status}</strong></p>
    </div>
  );
}

export default App;