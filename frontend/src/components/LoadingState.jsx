export default function LoadingState({ step, mode }) {
  const steps = mode === 'summarize'
    ? ['Parsing document', 'Analyzing structure', 'Generating summary', 'Checking quality']
    : ['Parsing resume', 'Extracting profile', 'Matching jobs', 'Generating advice'];

  // Determine current step index
  const currentIdx = steps.findIndex(s =>
    step.toLowerCase().includes(s.toLowerCase().split(' ')[0].toLowerCase())
  );

  return (
    <div className="card animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-lg bg-ink-900 flex items-center justify-center">
          <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-900">Agents working</p>
          <p className="text-xs text-ink-400 font-mono">{step || 'Initializing...'}</p>
        </div>
      </div>

      {/* Agent pipeline progress */}
      <div className="space-y-3">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 transition-all duration-300 ${
              i < currentIdx
                ? 'bg-ink-900 text-white'
                : i === currentIdx
                  ? 'bg-ink-900 text-white animate-pulse'
                  : 'bg-ink-100 text-ink-400'
            }`}>
              {i < currentIdx ? (
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <span>{i + 1}</span>
              )}
            </div>
            <span className={`text-sm transition-colors duration-300 ${
              i <= currentIdx ? 'text-ink-900 font-medium' : 'text-ink-300'
            }`}>
              {s}
            </span>
          </div>
        ))}
      </div>

      {/* Skeleton preview */}
      <div className="mt-6 space-y-3">
        <div className="skeleton h-4 w-3/4 rounded" />
        <div className="skeleton h-4 w-full rounded" />
        <div className="skeleton h-4 w-5/6 rounded" />
        <div className="skeleton h-4 w-2/3 rounded" />
      </div>
    </div>
  );
}
