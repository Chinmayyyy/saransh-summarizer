export default function ErrorState({ error, onRetry }) {
  // Detect error type for contextual messaging
  const isRateLimit = error?.includes('too many') || error?.includes('rate limit') || error?.includes('429');
  const isTimeout = error?.includes('timed out') || error?.includes('timeout');
  const isFileError = error?.includes('file') || error?.includes('Unsupported') || error?.includes('empty');

  let title = 'Something went wrong';
  let icon = '⚠️';

  if (isRateLimit) {
    title = 'Too many requests';
    icon = '🚦';
  } else if (isTimeout) {
    title = 'Request timed out';
    icon = '⏱️';
  } else if (isFileError) {
    title = 'File error';
    icon = '📁';
  }

  return (
    <div className="card border-red-200 bg-red-50/30 animate-fade-in">
      <div className="flex items-start gap-3">
        <span className="text-2xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-ink-900">{title}</h3>
          <p className="text-sm text-ink-600 mt-1">{error}</p>
          {isRateLimit && (
            <p className="text-xs text-ink-400 mt-2">Please wait 60 seconds before trying again.</p>
          )}
        </div>
      </div>
      <button
        id="retry-button"
        onClick={onRetry}
        className="btn-secondary mt-4 w-full text-sm"
      >
        Try again
      </button>
    </div>
  );
}
