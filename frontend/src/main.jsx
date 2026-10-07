import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
const API_KEY = import.meta.env.VITE_API_KEY || '';
const authHeaders = () => API_KEY ? {'X-API-Key': API_KEY} : {};

async function parseResponse(response) {
  if (response.ok) return response.json();
  let message = `${response.status} ${response.statusText}`;
  try {
    const body = await response.json();
    message = body.detail || JSON.stringify(body);
  } catch {
    const text = await response.text();
    if (text) message = text;
  }
  throw new Error(message);
}

function LineInput({property, category, lineKey, value, onSaved}) {
  const [draft, setDraft] = useState(String(value));
  const [saving, setSaving] = useState(false);

  useEffect(() => setDraft(String(value)), [value]);

  async function save() {
    const numeric = Number(draft);
    if (!Number.isFinite(numeric) || !Number.isInteger(numeric)) {
      setDraft(String(value));
      throw new Error('Values must be whole-dollar integers');
    }
    if (numeric === value) return;
    setSaving(true);
    try {
      await onSaved(property, category, lineKey, numeric);
    } finally {
      setSaving(false);
    }
  }

  return (
    <input
      aria-label={`${property.property_name}-${lineKey}`}
      type="number"
      value={draft}
      disabled={saving}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => save().catch(() => {})}
      onKeyDown={(e) => {
        if (e.key === 'Enter') e.currentTarget.blur();
        if (e.key === 'Escape') setDraft(String(value));
      }}
    />
  );
}

function App() {
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState('');
  const [audit, setAudit] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const id = localStorage.getItem('form8825.lastDocumentId');
    if (!id) return;
    fetch(`${API}/documents/${id}`, {headers: authHeaders()})
      .then(parseResponse)
      .then(setDoc)
      .catch(() => localStorage.removeItem('form8825.lastDocumentId'));
  }, []);

  async function upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const body = await parseResponse(await fetch(`${API}/documents`, {method: 'POST', body: form, headers: authHeaders()}));
      setDoc(body);
      setAudit({});
      localStorage.setItem('form8825.lastDocumentId', String(body.document_id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function edit(property, category, key, value) {
    setError('');
    try {
      const updated = await parseResponse(
        await fetch(`${API}/properties/${property.id}/value`, {
          method: 'PATCH',
          headers: {'Content-Type': 'application/json', ...authHeaders()},
          body: JSON.stringify({category, key, value, expected_version: property.version, reason: 'manual UI edit'}),
        }),
      );
      setDoc((current) => ({
        ...current,
        properties: current.properties.map((p) => (p.id === property.id ? updated : p)),
      }));
      await loadAudit(property.id);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }

  async function loadAudit(propertyId) {
    try {
      const rows = await parseResponse(await fetch(`${API}/properties/${propertyId}/audit`, {headers: authHeaders()}));
      setAudit((current) => ({...current, [propertyId]: rows}));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main>
      <h1>Form 8825 Review</h1>
      <p className="subtitle">Upload, review, correct, recalculate, and audit rental-property values.</p>
      <input data-testid="pdf-upload" type="file" accept="application/pdf" onChange={upload} />
      {busy && <p data-testid="upload-status">Extracting…</p>}
      {error && <pre className="error" data-testid="error-message">{error}</pre>}

      {doc && <p data-testid="document-id">Document #{doc.document_id}</p>}
      {doc?.properties.map((p) => (
        <section key={p.id} data-testid={`property-${p.property_name}`}>
          <h2>Property {p.property_name}</h2>
          <p>{p.property_address}</p>

          {['income_line_items', 'expense_line_items'].map((category) => (
            <div key={category}>
              <h3>{category.replaceAll('_', ' ')}</h3>
              {Object.entries(p[category]).map(([key, value]) => (
                <label key={key}>
                  {key.replaceAll('_', ' ')}
                  <LineInput
                    property={p}
                    category={category}
                    lineKey={key}
                    value={value}
                    onSaved={edit}
                  />
                </label>
              ))}
            </div>
          ))}

          <div className="totals">
            <b>Total income</b>
            <span data-testid={`${p.property_name}-total-income`}>{p.totals.total_rental_income.toLocaleString()}</span>
            <b>Total expense</b>
            <span data-testid={`${p.property_name}-total-expense`}>{p.totals.total_expenses.toLocaleString()}</span>
            <b>Net income</b>
            <span data-testid={`${p.property_name}-net-income`}>{p.totals.net_income.toLocaleString()}</span>
          </div>

          <button type="button" onClick={() => loadAudit(p.id)}>View change history</button>
          {audit[p.id] && (
            <div data-testid={`${p.property_name}-audit`} className="audit">
              <h3>Change history</h3>
              {audit[p.id].length === 0 ? <p>No manual changes.</p> : (
                <ul>
                  {audit[p.id].map((row) => (
                    <li key={row.id}>{row.key}: {row.old_value} → {row.new_value} ({row.reason})</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      ))}
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
