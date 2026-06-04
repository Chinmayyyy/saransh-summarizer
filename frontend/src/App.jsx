import { useState, useCallback } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import ModeSwitch from './components/ModeSwitch';
import FileUpload from './components/FileUpload';
import LoadingState from './components/LoadingState';
import ErrorState from './components/ErrorState';
import SummaryResult from './components/SummaryResult';
import ResumeResult from './components/ResumeResult';
import BackgroundShader from './components/BackgroundShader';
import { useUpload } from './hooks/useUpload';

export default function App() {
  const [mode, setMode] = useState('summarize');
  const [file, setFile] = useState(null);
  const { loading, error, result, step, processFile, reset } = useUpload();

  const handleModeChange = useCallback((newMode) => {
    setMode(newMode);
    setFile(null);
    reset();
  }, [reset]);

  const handleFileSelect = useCallback((f) => {
    setFile(f);
    reset();
  }, [reset]);

  const handleUpload = useCallback(() => {
    if (file) {
      processFile(file, mode);
    }
  }, [file, mode, processFile]);

  const handleRetry = useCallback(() => {
    reset();
    setFile(null);
  }, [reset]);

  return (
    <div className="min-h-screen flex flex-col relative z-0">
      <BackgroundShader />
      <Header />

      <main className="flex-1">
        <div className="max-w-2xl mx-auto px-6 py-10">
          {/* Hero */}
          <div className="text-center mb-10">
            <h2 className="text-3xl sm:text-4xl font-bold text-ink-900 tracking-tight text-balance">
              {mode === 'summarize'
                ? 'Understand any document in seconds'
                : 'Find your perfect role'}
            </h2>
            <p className="text-ink-500 mt-3 text-sm max-w-md mx-auto leading-relaxed">
              {mode === 'summarize'
                ? 'Upload a document and our AI agents will parse, analyze, and summarize it with key insights.'
                : 'Upload your resume and our AI agents will extract your profile and match you to open positions.'}
            </p>
          </div>

          {/* Mode Switch */}
          <div className="mb-8">
            <ModeSwitch mode={mode} onModeChange={handleModeChange} />
          </div>

          {/* File Upload */}
          <div className="mb-6">
            <FileUpload
              mode={mode}
              file={file}
              onFileSelect={handleFileSelect}
              onUpload={handleUpload}
              loading={loading}
            />
          </div>

          {/* Loading */}
          {loading && (
            <div className="mb-6">
              <LoadingState step={step} mode={mode} />
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="mb-6">
              <ErrorState error={error} onRetry={handleRetry} />
            </div>
          )}

          {/* Results */}
          {result && !loading && !error && (
            <div className="mb-6">
              {mode === 'summarize'
                ? <SummaryResult data={result} />
                : <ResumeResult data={result} />
              }
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
