export default function Header() {
  return (
    <header className="border-b border-ink-200">
      <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">
            Saransh
          </h1>
          <p className="text-xs font-mono text-ink-400 mt-0.5 tracking-wide">
            AI-Powered Document Analysis
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-4 text-xs text-ink-400">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Online
          </span>
        </div>
      </div>
    </header>
  );
}
