export default function ModeSwitch({ mode, onModeChange }) {
  return (
    <div className="flex items-center justify-center">
      <div className="inline-flex items-center bg-white/50 backdrop-blur-md shadow-sm rounded-xl p-1.5 border border-white/60">
        <button
          id="mode-summarize"
          onClick={() => onModeChange('summarize')}
          className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
            mode === 'summarize'
              ? 'bg-white text-ink-900 shadow-sm'
              : 'text-ink-500 hover:text-ink-700 hover:bg-white/40'
          }`}
        >
          Summarize
        </button>
        <button
          id="mode-resume"
          onClick={() => onModeChange('resume')}
          className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
            mode === 'resume'
              ? 'bg-white text-ink-900 shadow-sm'
              : 'text-ink-500 hover:text-ink-700 hover:bg-white/40'
          }`}
        >
          Resume Mode
        </button>
      </div>
    </div>
  );
}
