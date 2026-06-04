import { useState, useCallback } from 'react';
import { summarizeDocument, matchResume } from '../utils/api';

/**
 * Custom hook for file upload and processing.
 * Manages loading, error, and result state.
 */
export function useUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [step, setStep] = useState('');

  const processFile = useCallback(async (file, mode) => {
    setLoading(true);
    setError(null);
    setResult(null);

    // Simulate agent steps for loading UI
    const steps = mode === 'summarize'
      ? ['Parsing document...', 'Analyzing structure...', 'Generating summary...', 'Checking quality...']
      : ['Parsing resume...', 'Extracting profile...', 'Matching jobs...', 'Generating advice...'];

    let stepIndex = 0;
    setStep(steps[0]);
    const stepInterval = setInterval(() => {
      stepIndex = Math.min(stepIndex + 1, steps.length - 1);
      setStep(steps[stepIndex]);
    }, 3000);

    try {
      let data;
      if (mode === 'summarize') {
        data = await summarizeDocument(file);
      } else {
        data = await matchResume(file);
      }
      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      clearInterval(stepInterval);
      setLoading(false);
      setStep('');
    }
  }, []);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    setResult(null);
    setStep('');
  }, []);

  return { loading, error, result, step, processFile, reset };
}
