import { useState, useRef, useCallback } from 'react';

const SUPPORTED_TYPES = {
  summarize: {
    extensions: ['.pdf', '.docx', '.txt', '.csv', '.xlsx', '.json'],
    mimeTypes: [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'text/csv',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/json',
    ],
  },
  resume: {
    extensions: ['.pdf', '.docx', '.txt'],
    mimeTypes: [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
    ],
  },
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  const icons = {
    pdf: '📄', docx: '📝', txt: '📃',
    csv: '📊', xlsx: '📊', json: '{ }',
  };
  return icons[ext] || '📁';
}

export default function FileUpload({ mode, file, onFileSelect, onUpload, loading }) {
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const inputRef = useRef(null);

  const supportedExts = SUPPORTED_TYPES[mode]?.extensions || [];
  const supportedMimes = SUPPORTED_TYPES[mode]?.mimeTypes || [];
  const acceptString = [...supportedExts, ...supportedMimes].join(',');

  const validateFile = useCallback((f) => {
    const ext = '.' + (f.name.split('.').pop()?.toLowerCase() || '');
    if (!supportedExts.includes(ext)) {
      return `Unsupported file type: ${ext}. Supported: ${supportedExts.join(', ')}`;
    }
    if (f.size > MAX_FILE_SIZE) {
      return `File too large (${formatFileSize(f.size)}). Maximum: 10MB`;
    }
    if (f.size === 0) {
      return 'File is empty';
    }
    return null;
  }, [supportedExts]);

  const handleFile = useCallback((f) => {
    const error = validateFile(f);
    setValidationError(error);
    if (!error) {
      onFileSelect(f);
    }
  }, [validateFile, onFileSelect]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files?.[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const clearFile = () => {
    onFileSelect(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="w-full">
      {/* Drop zone */}
      <div
        id="file-upload-zone"
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 backdrop-blur-sm
          ${dragActive
            ? 'border-indigo-400 bg-indigo-50/60 shadow-inner'
            : file
              ? 'border-ink-300 bg-white/60'
              : 'border-ink-200 hover:border-indigo-300 hover:bg-white/60 bg-white/40 shadow-sm hover:shadow-md'
          }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={acceptString}
          onChange={handleInputChange}
          onClick={(e) => { e.target.value = null; }}
          className="hidden"
          id="file-input"
        />

        {file ? (
          /* File selected state */
          <div className="flex items-center justify-center gap-4">
            <span className="text-3xl">{getFileIcon(file.name)}</span>
            <div className="text-left">
              <p className="font-medium text-ink-900 text-sm">{file.name}</p>
              <p className="text-xs text-ink-400 mt-0.5">{formatFileSize(file.size)}</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); clearFile(); }}
              className="ml-4 p-1.5 rounded-lg hover:bg-ink-200 transition-colors text-ink-400 hover:text-ink-600"
              title="Remove file"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ) : (
          /* Empty state */
          <div>
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-ink-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-ink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-sm font-medium text-ink-700">
              Drop your {mode === 'resume' ? 'resume' : 'document'} here
            </p>
            <p className="text-xs text-ink-400 mt-1">
              or click to browse · {supportedExts.join(', ')} · max 10MB
            </p>
          </div>
        )}
      </div>

      {/* Validation error */}
      {validationError && (
        <p className="mt-2 text-xs text-red-600 flex items-center gap-1">
          <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          {validationError}
        </p>
      )}

      {/* Upload button */}
      {file && !loading && (
        <button
          id="upload-button"
          onClick={onUpload}
          className="btn-primary w-full mt-4"
        >
          {mode === 'summarize' ? 'Summarize Document' : 'Match Resume'}
          <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      )}
    </div>
  );
}
