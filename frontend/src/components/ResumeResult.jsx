import { useState } from 'react';

function ScoreBar({ score }) {
  const color = score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-ink-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-ink-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-mono font-semibold text-ink-600 w-10 text-right">{score.toFixed(0)}%</span>
    </div>
  );
}

export default function ResumeResult({ data }) {
  const [expanded, setExpanded] = useState({});
  if (!data) return null;
  const { profile, top_matches, processing_time_ms, filename } = data;
  const toggle = (i) => setExpanded(p => ({ ...p, [i]: !p[i] }));

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="text-xs text-ink-400 font-mono">{filename} · {processing_time_ms}ms</div>

      {/* Profile Card */}
      <div className="card">
        <p className="section-title">Extracted Profile</p>
        {profile.name && <p className="text-lg font-bold text-ink-900 mb-3">{profile.name}</p>}
        {profile.skills?.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-ink-500 mb-1.5">Skills</p>
            <div className="flex flex-wrap gap-1.5">{profile.skills.map((s,i) => <span key={i} className="tag">{s}</span>)}</div>
          </div>
        )}
        {profile.tools?.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-ink-500 mb-1.5">Tools</p>
            <div className="flex flex-wrap gap-1.5">{profile.tools.map((t,i) => <span key={i} className="tag-dark">{t}</span>)}</div>
          </div>
        )}
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-500 mt-3">
          {profile.experience_years != null && <span>Experience: <strong className="text-ink-700">{profile.experience_years} yrs</strong></span>}
          {profile.domains?.length > 0 && <span>Domains: <strong className="text-ink-700">{profile.domains.join(', ')}</strong></span>}
        </div>
        {profile.education?.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-semibold text-ink-500 mb-1">Education</p>
            {profile.education.map((e,i) => <p key={i} className="text-xs text-ink-600">{e}</p>)}
          </div>
        )}
      </div>

      {/* Job Matches */}
      {top_matches?.length > 0 && (
        <div>
          <p className="section-title">Top Job Matches</p>
          <div className="space-y-3">
            {top_matches.map((match, i) => (
              <div key={i} className="card-hover cursor-pointer" onClick={() => toggle(i)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-ink-900">{match.role_title}</p>
                    <p className="text-xs text-ink-400 mt-0.5">{match.company}</p>
                  </div>
                  <svg className={`w-4 h-4 text-ink-400 shrink-0 mt-1 transition-transform ${expanded[i] ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                <div className="mt-3"><ScoreBar score={match.match_score} /></div>

                {expanded[i] && (
                  <div className="mt-4 space-y-3 pt-3 border-t border-ink-100">
                    {match.why_it_matches && (
                      <div>
                        <p className="text-xs font-semibold text-ink-500 mb-1">Why it matches</p>
                        <p className="text-sm text-ink-600 leading-relaxed">{match.why_it_matches}</p>
                      </div>
                    )}
                    {match.missing_skills?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-ink-500 mb-1.5">Missing Skills</p>
                        <div className="flex flex-wrap gap-1.5">{match.missing_skills.map((s,j) => <span key={j} className="tag-red">{s}</span>)}</div>
                      </div>
                    )}
                    {match.suggested_next_steps?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-ink-500 mb-1">Next Steps</p>
                        <ul className="space-y-1">{match.suggested_next_steps.map((s,j) => (
                          <li key={j} className="text-xs text-ink-600 flex items-start gap-1.5">
                            <span className="text-ink-400 mt-0.5">→</span>{s}
                          </li>
                        ))}</ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
