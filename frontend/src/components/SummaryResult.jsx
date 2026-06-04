import { useState } from 'react';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className="p-1.5 rounded-md hover:bg-ink-100 transition-colors text-ink-400 hover:text-ink-600" title="Copy">
      {copied ? (
        <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
      )}
    </button>
  );
}

export default function SummaryResult({ data }) {
  const [showDetailed, setShowDetailed] = useState(false);
  if (!data) return null;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Meta */}
      <div className="flex items-center justify-between text-xs text-ink-400">
        <span className="font-mono">{data.filename} · {data.processing_time_ms}ms{data.metadata?.used_rag ? ' · RAG' : ''}</span>
        <span className="tag">{data.metadata?.doc_type || 'document'}</span>
      </div>

      {/* Short summary */}
      <div className="card">
        <div className="flex items-start justify-between gap-2">
          <p className="section-title">Summary</p>
          <CopyButton text={data.short_summary} />
        </div>
        <p className="text-sm text-ink-700 leading-relaxed">{data.short_summary}</p>
      </div>

      {/* Detailed summary */}
      {data.detailed_summary && (
        <div className="card">
          <button onClick={() => setShowDetailed(!showDetailed)} className="flex items-center justify-between w-full">
            <p className="section-title mb-0">Detailed Summary</p>
            <svg className={`w-4 h-4 text-ink-400 transition-transform duration-200 ${showDetailed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showDetailed && (
            <div className="mt-3">
              <div className="flex justify-end mb-1"><CopyButton text={data.detailed_summary} /></div>
              <p className="text-sm text-ink-600 leading-relaxed whitespace-pre-wrap">{data.detailed_summary}</p>
            </div>
          )}
        </div>
      )}

      {/* Key points */}
      {data.key_points?.length > 0 && (
        <div className="card">
          <p className="section-title">Key Points</p>
          <ul className="space-y-2">
            {data.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-ink-700">
                <span className="w-5 h-5 rounded-full bg-ink-100 flex items-center justify-center text-xs font-medium text-ink-500 shrink-0 mt-0.5">{i + 1}</span>
                <span className="leading-relaxed">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Keywords */}
      {data.keywords?.length > 0 && (
        <div className="card">
          <p className="section-title">Keywords</p>
          <div className="flex flex-wrap gap-2">
            {data.keywords.map((kw, i) => <span key={i} className="tag">{kw}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}
