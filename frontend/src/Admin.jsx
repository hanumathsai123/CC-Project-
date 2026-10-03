import { useCallback, useEffect, useState } from 'react';
import { Activity, ArrowLeft, Check, CircleAlert, Dna, Image, LogOut, RefreshCw, ShieldCheck, Users, X } from 'lucide-react';
import './admin.css';

const API = import.meta.env.VITE_API_URL || '';

export default function Admin() {
  const [token, setToken] = useState(() => sessionStorage.getItem('geosight-admin-token') || '');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [satelliteRuns, setSatelliteRuns] = useState([]);
  const [satelliteSummary, setSatelliteSummary] = useState(null);
  const [catalogSearches, setCatalogSearches] = useState([]);
  const [satelliteView, setSatelliteView] = useState('images');
  const [activeProject, setActiveProject] = useState('biology');
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const signOut = useCallback(() => {
    sessionStorage.removeItem('geosight-admin-token');
    setToken('');
    setSummary(null);
    setRuns([]);
    setSelected(null);
  }, []);

  const loadRuns = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [biologyResponse, satelliteResponse] = await Promise.all([
        fetch(`${API}/api/admin/biology/runs`, { headers }),
        fetch(`${API}/api/admin/satellite/runs`, { headers }),
      ]);
      const [biologyData, satelliteData] = await Promise.all([biologyResponse.json(), satelliteResponse.json()]);
      if (biologyResponse.status === 401 || satelliteResponse.status === 401) {
        signOut();
        throw new Error('Your admin session expired. Please sign in again.');
      }
      if (!biologyResponse.ok) throw new Error(biologyData.detail || 'Unable to load Biology analyses.');
      if (!satelliteResponse.ok) throw new Error(satelliteData.detail || 'Unable to load Geo Science analyses.');
      setSummary(biologyData.summary);
      setRuns(biologyData.runs);
      setSatelliteSummary(satelliteData.summary);
      setSatelliteRuns(satelliteData.runs);
      setCatalogSearches(satelliteData.searches || []);
    } catch (cause) {
      setError(cause.message || 'Unable to connect to the admin API.');
    } finally {
      setLoading(false);
    }
  }, [token, signOut]);

  async function loadRun(runId, project = activeProject) {
    setError('');
    try {
      const response = await fetch(`${API}/api/admin/${project === 'biology' ? 'biology' : 'satellite'}/runs/${encodeURIComponent(runId)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (response.status === 401) {
        signOut();
        throw new Error('Your admin session expired. Please sign in again.');
      }
      if (!response.ok) throw new Error(data.detail || 'Unable to load sample predictions.');
      setSelected(data);
      setActiveProject(project);
    } catch (cause) {
      setError(cause.message || 'Unable to load sample predictions.');
    }
  }

  useEffect(() => {
    loadRuns();
    const timer = setInterval(loadRuns, 15000);
    return () => clearInterval(timer);
  }, [loadRuns]);

  async function signIn(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Admin sign-in failed.');
      sessionStorage.setItem('geosight-admin-token', data.token);
      setToken(data.token);
      setPassword('');
    } catch (cause) {
      setError(cause.message || 'Admin sign-in failed.');
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <main className="admin-login-page">
        <a className="admin-back" href="/"><ArrowLeft size={16} /> All projects</a>
        <form className="admin-login-card" onSubmit={signIn}>
          <span className="admin-login-icon"><ShieldCheck size={24} /></span>
          <p className="admin-kicker">PRIVATE WORKSPACE</p>
          <h1>Admin portal</h1>
          <p className="admin-login-copy">Review Biology predictions and Geo Science satellite image analyses.</p>
          <label htmlFor="admin-email">Admin email</label>
          <input id="admin-email" type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} required />
          <label htmlFor="admin-password">Password</label>
          <input id="admin-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required />
          {error && <p className="admin-error" role="alert">{error}</p>}
          <button className="admin-primary" disabled={loading}>{loading ? 'Signing in…' : 'Sign in securely'}</button>
          <small>Uses the administrator credentials configured for the backend.</small>
        </form>
      </main>
    );
  }

  return (
    <main className="admin-page">
      <header className="admin-header">
        <a href="/" className="admin-brand"><span><Dna size={19} /></span><b>BioInsight Admin</b></a>
        <div className="admin-header-actions">
          <button onClick={loadRuns} disabled={loading}><RefreshCw size={15} className={loading ? 'admin-rotating' : ''} /> Refresh</button>
          <button onClick={signOut}><LogOut size={15} /> Sign out</button>
        </div>
      </header>
      <section className="admin-content">
        <div className="admin-title">
          <div><p className="admin-kicker">ANALYSIS OVERSIGHT</p><h1>Project dashboard</h1><p>Review Biology predictions and Geo Science satellite analysis results.</p></div>
          <span className="admin-live"><i /> LIVE DATA</span>
        </div>
        {error && <p className="admin-error" role="alert">{error}</p>}
        <div className="admin-project-tabs">
          <button className={activeProject === 'biology' ? 'active' : ''} onClick={() => { setActiveProject('biology'); setSelected(null); }}><Dna size={15} /> Biology</button>
          <button className={activeProject === 'satellite' ? 'active' : ''} onClick={() => { setActiveProject('satellite'); setSelected(null); }}><Image size={15} /> Geo Science</button>
        </div>
        {activeProject === 'biology' ? <>
        <section className="admin-stat-grid">
          <article><span className="admin-stat-icon purple"><Activity size={18} /></span><small>Analysis runs</small><b>{summary?.run_count ?? '—'}</b></article>
          <article><span className="admin-stat-icon blue"><Users size={18} /></span><small>Samples reviewed</small><b>{summary?.sample_count ?? '—'}</b></article>
          <article><span className="admin-stat-icon green"><Check size={18} /></span><small>Correct predictions</small><b>{summary?.correct_count ?? '—'}</b></article>
          <article><span className="admin-stat-icon amber"><Dna size={18} /></span><small>Overall accuracy</small><b>{summary ? `${summary.overall_accuracy_percent}%` : '—'}</b></article>
        </section>

        <section className="admin-panel">
          <div className="admin-panel-heading"><div><h2>Recent Biology analyses</h2><p>Accuracy = correct leave-one-out predictions ÷ total labeled samples.</p></div><span>{runs.length} shown</span></div>
          {runs.length === 0 && !loading
            ? <div className="admin-empty"><Dna size={27} /><b>No analysis runs yet</b><span>New Biology uploads will appear here as soon as they are analyzed.</span></div>
            : <div className="admin-table-wrap"><table className="admin-runs"><thead><tr><th>Run / time</th><th>Samples</th><th>Genes</th><th>Correct</th><th>Accuracy</th><th>Groups</th></tr></thead><tbody>
              {runs.map(run => <tr key={run.run_id} className={selected?.run_id === run.run_id ? 'selected' : ''} onClick={() => loadRun(run.run_id)}>
                <td><b>{run.run_id}</b><small>{new Date(run.created_at).toLocaleString()}</small></td><td>{run.sample_count}</td><td>{run.gene_count}</td><td>{run.correct_count}/{run.sample_count}</td><td><strong>{run.accuracy_percent}%</strong></td><td>{run.groups.map(group => group.name).join(' / ')}</td>
              </tr>)}
            </tbody></table></div>}
        </section>

        {selected && <section className="admin-panel prediction-panel">
          <div className="admin-panel-heading"><div><h2>Sample-level predictions</h2><p>Run {selected.run_id} · exact match is labeled correct; score is the classifier’s relative ranking score.</p></div><button className="admin-close" onClick={() => setSelected(null)} aria-label="Close sample results"><X size={17} /></button></div>
          <div className="admin-correctness"><span><Check size={15} /> {selected.correct_count} correct</span><span><CircleAlert size={15} /> {selected.sample_count - selected.correct_count} incorrect</span><b>{selected.accuracy_percent}% accuracy</b></div>
          <div className="admin-table-wrap"><table className="admin-predictions"><thead><tr><th>Sample ID</th><th>Actual</th><th>Predicted</th><th>Prediction score</th><th>Result</th></tr></thead><tbody>
            {selected.predictions.map((prediction, index) => <tr key={`${prediction.sample_id}-${index}`}><td>{prediction.sample_id}</td><td>{prediction.actual}</td><td>{prediction.predicted}</td><td>{prediction.score_percent}%</td><td><span className={`admin-result-pill ${prediction.correct ? 'match' : 'mismatch'}`}>{prediction.correct ? 'Correct' : 'Incorrect'}</span></td></tr>)}
          </tbody></table></div>
        </section>}
        </> : <>
          <section className="admin-stat-grid satellite-admin-stats">
            <article><span className="admin-stat-icon blue"><Image size={18} /></span><small>Images analyzed</small><b>{satelliteSummary?.images_analyzed ?? '—'}</b></article>
            <article><span className="admin-stat-icon purple"><Activity size={18} /></span><small>Analysis runs</small><b>{satelliteSummary?.run_count ?? '—'}</b></article>
            <article><span className="admin-stat-icon green"><Check size={18} /></span><small>Most recent storage</small><b>{satelliteRuns[0]?.storage ?? '—'}</b></article>
            <article><span className="admin-stat-icon amber"><Activity size={18} /></span><small>Catalog searches</small><b>{satelliteSummary?.catalog_search_count ?? 0}</b></article>
          </section>
          <div className="admin-project-tabs satellite-subtabs">
            <button className={satelliteView === 'images' ? 'active' : ''} onClick={() => { setSatelliteView('images'); setSelected(null); }}><Image size={15} /> Image analyses</button>
            <button className={satelliteView === 'catalog' ? 'active' : ''} onClick={() => { setSatelliteView('catalog'); setSelected(null); }}><Activity size={15} /> Sentinel-2 searches</button>
          </div>
          {satelliteView === 'images' ? <>
          <section className="admin-panel">
            <div className="admin-panel-heading"><div><h2>Satellite image analyses</h2><p>Uploaded image classification results, cover metrics, and storage status.</p></div><span>{satelliteRuns.length} shown</span></div>
            {satelliteRuns.length === 0 && !loading
              ? <div className="admin-empty"><Image size={27} /><b>No satellite image analyses yet</b><span>Geo Science image uploads will appear here after analysis.</span></div>
              : <div className="admin-table-wrap"><table className="admin-runs"><thead><tr><th>Image / time</th><th>Vegetation</th><th>Water</th><th>Built-up</th><th>Other</th><th>Storage</th></tr></thead><tbody>
                {satelliteRuns.map(run => <tr key={run.run_id} className={selected?.run_id === run.run_id ? 'selected' : ''} onClick={() => loadRun(run.run_id, 'satellite')}>
                  <td><b>{run.filename}</b><small>{new Date(run.created_at).toLocaleString()} · {run.run_id}</small></td><td>{run.metrics.vegetation}%</td><td>{run.metrics.water}%</td><td>{run.metrics.built_up}%</td><td>{run.metrics.other}%</td><td>{run.storage}</td>
                </tr>)}
              </tbody></table></div>}
          </section>
          {selected?.source_url && <section className="admin-panel prediction-panel">
            <div className="admin-panel-heading"><div><h2>Satellite analysis details</h2><p>{selected.filename} · {new Date(selected.created_at).toLocaleString()} · {selected.storage}</p></div><button className="admin-close" onClick={() => setSelected(null)} aria-label="Close satellite details"><X size={17} /></button></div>
            <div className="admin-satellite-images">
              <a href={`${API}${selected.source_url}`} target="_blank" rel="noreferrer"><img src={`${API}${selected.source_url}`} alt="Original satellite upload" /><span>Original image</span></a>
              <a href={`${API}${selected.result_url}`} target="_blank" rel="noreferrer"><img src={`${API}${selected.result_url}`} alt="Classified satellite result" /><span>Classified result</span></a>
            </div>
            <div className="satellite-metrics">{Object.entries(selected.metrics).map(([name, value]) => <div key={name}><small>{name.replace('_', ' ')}</small><b>{value}%</b></div>)}</div>
          </section>}
          </> : <section className="admin-panel">
            <div className="admin-panel-heading"><div><h2>Sentinel-2 catalog searches</h2><p>Search parameters and product metadata returned by the live catalog or demo fallback.</p></div><span>{catalogSearches.length} shown</span></div>
            {catalogSearches.length === 0 && !loading
              ? <div className="admin-empty"><Activity size={27} /><b>No catalog searches yet</b><span>Geo Science live searches will be listed here.</span></div>
              : <div className="admin-table-wrap"><table className="admin-runs"><thead><tr><th>Search / time</th><th>Source</th><th>Date range</th><th>Cloud filter</th><th>Products</th></tr></thead><tbody>
                {catalogSearches.map(search => <tr key={search.search_id}>
                  <td><b>{search.search_id}</b><small>{new Date(search.created_at).toLocaleString()} · bbox {search.bbox.join(', ')}</small></td><td>{search.source}</td><td>{search.start_date} – {search.end_date}</td><td>≤ {search.cloud_cover}%</td><td>{search.items.length}{search.warning ? ' · fallback' : ''}</td>
                </tr>)}
              </tbody></table>
                {catalogSearches.map(search => <div className="catalog-products" key={`${search.search_id}-products`}><b>Products · {search.search_id}</b>{search.items.map(item => <span key={item.id}>{item.id} · {item.date || 'date unavailable'} · {item.cloud_cover ?? '—'}% cloud</span>)}</div>)}
              </div>}
          </section>}
        </>}
        <p className="admin-footnote">{activeProject === 'biology' ? 'The dashboard stores summary metrics and sample-level predictions, not raw gene-expression values. Validation accuracy is not clinical diagnostic performance.' : satelliteView === 'images' ? 'Geo Science uploads are kept in the local data folder and their classification metrics are recorded here. Images are viewable to anyone who can access their existing static file URLs.' : 'Sentinel-2 search parameters and returned product metadata are recorded for admin review. Demo fallback products are labeled separately from live catalog results.'}</p>
      </section>
    </main>
  );
}
