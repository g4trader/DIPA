
import React, { useState } from 'react';

export default function DipaPanel() {
  const [question, setQuestion] = useState('Mostre o comparativo de meta vs realizado de 2025-11 por região e vendedor');
  const [answers, setAnswers] = useState<string[]>([]);

  const ask = () => {
    setAnswers(a => [...a, 'Você: ' + question, 'DIPA: (substitua este stub pelo componente completo do canvas)']);
  };

  return (
    <div style={{padding: 24, fontFamily: 'Inter, ui-sans-serif'}}>
      <h1>DIPA – Dipam Intelligence & Performance Assistant</h1>
      <p>Stub do painel. Substitua por <strong>DipaPanel.tsx</strong> completo do canvas.</p>
      <div style={{display:'flex', gap:8, marginTop: 12}}>
        <input style={{flex:1, padding:8}} value={question} onChange={e=>setQuestion(e.target.value)} />
        <button onClick={ask}>Perguntar</button>
      </div>
      <div style={{marginTop:16}}>
        {answers.map((t,i)=>(<div key={i} style={{padding:'6px 0'}}>{t}</div>))}
      </div>
    </div>
  );
}
