import { useEffect, useState } from 'react';
import { ArrowLeft, Dna, FileSpreadsheet, LoaderCircle } from 'lucide-react';
import './biology.css';

const API = import.meta.env.VITE_API_URL || '';

export default function Biology({ onBack }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [online, setOnline] = useState(false);
  useEffect(() => {
    const check = () => fetch(`${API}/api/health`)
      .then(response => response.json())
      .then(data => {
        setOnline(data.status === 'online');
      })
      .catch(() => { setOnline(false); });
    check();
    const timer = setInterval(check, 10000);
    return () => clearInterval(timer);
  }, []);

  async function analyze(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await fetch(`${API}/api/biology/analyze`, { method: 'POST', body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed.');
      setResult(data);
    } catch (cause) {
      setError(cause.message || 'Could not reach the Biology analysis API.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="biology-page">
      <header className="biology-header">
        <button className="biology-back" onClick={onBack}><ArrowLeft size={17} /> All projects</button>
        <div className="biology-brand"><span><Dna size={21} /></span><div><b>BioInsight</b><small>Gene Expression Analysis</small></div></div>
        <div className="biology-live"><i className={online ? 'is-online' : ''} />{online ? 'API LIVE' : 'API OFFLINE'}</div>
      </header>

      <section className="biology-hero">
        <p className="biology-eyebrow">BIOLOGY • CANCER RESEARCH DEMO</p>
        <h1>Explore gene expression.<br /><em>Get results as you analyze.</em></h1>
        <p>Upload a labeled CSV or TSV dataset. The backend validates the samples, compares expression between the two groups, and returns a leave-one-out baseline score in real time.</p>
        <div className="biology-flow"><span>1. Upload labeled data</span><b>→</b><span>2. Analyze on API</span><b>→</b><span>3. Review predictions</span></div>
      </section>

      <section className="biology-content">
        <form className="biology-upload" onSubmit={analyze}>
          <div className="biology-section-title"><FileSpreadsheet size={20} /><div><h2>Analyze a dataset</h2><p>Rows are samples; columns are numeric genes plus a diagnosis label.</p></div></div>
          <label className="biology-drop">
            <input type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values" onChange={event => { setFile(event.target.files?.[0] || null); setResult(null); setError(''); }} />
            <FileSpreadsheet size={31} />
            <b>{file ? file.name : 'Choose a CSV or TSV file'}</b>
            <span>{file ? `${(file.size / 1024).toFixed(1)} KB · ready to analyze` : 'Maximum 10 MB · UTF-8 · at least 4 labeled samples'}</span>
          </label>
          <div className="biology-format">
            <b>Required format</b>
            <code>sample_id,GENE_A,GENE_B,diagnosis</code>
            <a href="/demo_gene_expression.csv" download>Download demo CSV</a>
          </div>
          <button className="biology-submit" disabled={!file || busy || !online}>
            {busy ? <><LoaderCircle className="biology-spin" size={17} /> Analyzing now…</> : <><Dna size={17} /> Analyze dataset</>}
          </button>
          {error && <p className="biology-error" role="alert">{error}</p>}
        </form>

        <aside className="biology-aside">
          <div className="biology-aside-icon"><Dna size={19} /></div>
          <h2>Prediction method</h2>
          <p>Each sample is predicted by a nearest-centroid classifier with leave-one-out validation. The displayed accuracy compares every prediction with the dataset’s known label.</p>
          <div className="biology-limit">Research evaluation only — not a medical diagnosis.</div>
        </aside>
      </section>

      {result && <section className="biology-results">
        <div className="biology-result-heading"><div><p className="biology-eyebrow">ANALYSIS COMPLETE • {result.job_id}</p><h2>Dataset summary</h2></div></div>
        <div className="biology-metrics">
          <div><small>Samples</small><b>{result.report.sample_count}</b></div>
          <div><small>Gene features</small><b>{result.report.gene_count}</b></div>
          <div><small>Leave-one-out baseline accuracy</small><b>{result.report.leave_one_out_accuracy_percent}%</b></div>
        </div>
        <div className="biology-groups">{result.report.groups.map(group => <span key={group.name}><b>{group.name}</b>{group.sample_count} samples</span>)}</div>
        <div className="biology-genes"><h3>Largest expression differences</h3>
          <div className="biology-table-wrap"><table><thead><tr><th>Gene</th><th>Group means</th><th>Standardized difference</th></tr></thead><tbody>
            {result.report.top_differential_genes.map(gene => <tr key={gene.gene}><td>{gene.gene}</td><td>{result.report.groups.map(group => `${group.name}: ${gene.mean_by_group[group.name]}`).join(' · ')}</td><td>{gene.standardized_difference}</td></tr>)}
          </tbody></table></div>
        </div>
        <div className="biology-genes"><h3>Sample predictions</h3>
          <div className="biology-table-wrap"><table><thead><tr><th>Sample</th><th>Actual</th><th>Predicted</th><th>Score</th><th>Result</th></tr></thead><tbody>
            {result.report.sample_predictions.map((prediction, index) => <tr key={`${prediction.sample_id}-${index}`}><td>{prediction.sample_id}</td><td>{prediction.actual}</td><td>{prediction.predicted}</td><td>{prediction.score_percent}%</td><td>{prediction.correct ? 'Correct' : 'Incorrect'}</td></tr>)}
          </tbody></table></div>
        </div>
      </section>}
      <footer className="biology-footer"><a href="/admin">Admin portal</a></footer>
    </main>
  );
}
