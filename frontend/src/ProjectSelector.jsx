import { Dna, Globe2, ArrowUpRight, Activity, Cloud, Satellite } from 'lucide-react';
import './projects.css';

export default function ProjectSelector({ onSelect }) {
  return (
    <main className="project-selector">
      <div className="selector-heading">
        <div className="selector-mark"><Globe2 size={22} /></div>
        <p className="selector-kicker">BATCH 10 • PROJECT WORKSPACE</p>
        <h1>Choose a project</h1>
        <p className="selector-subtitle">Select an application to open its live analysis workspace.</p>
      </div>
      <div className="project-options">
        <button className="project-option biology-option" onClick={() => onSelect('biology')}>
          <div className="option-topline"><span className="option-number">PROJECT 01</span><ArrowUpRight size={20} /></div>
          <div className="option-icon"><Dna size={30} /></div>
          <h2>Biology</h2>
          <h3>Gene Expression Data Analysis</h3>
          <p>Explore labeled gene-expression data with a fast, educational cancer-classification baseline.</p>
          <div className="option-tags"><span><Activity size={14} /> Live analysis</span><span><Cloud size={14} /> Optional S3</span></div>
          <span className="option-action">Open Biology project <ArrowUpRight size={16} /></span>
        </button>
        <button className="project-option geoscience-option" onClick={() => onSelect('geoscience')}>
          <div className="option-topline"><span className="option-number">PROJECT 02</span><ArrowUpRight size={20} /></div>
          <div className="option-icon"><Satellite size={30} /></div>
          <h2>Geo Science</h2>
          <h3>Satellite Image Application</h3>
          <p>Analyze satellite imagery, explore Sentinel-2 observations, and use an AWS-ready workflow.</p>
          <div className="option-tags"><span><Activity size={14} /> Live analysis</span><span><Cloud size={14} /> Optional S3</span></div>
          <span className="option-action">Open Geo Science project <ArrowUpRight size={16} /></span>
        </button>
      </div>
      <p className="selector-footnote">Research analysis workspace. <a href="/admin">Open Admin Portal</a></p>
    </main>
  );
}
