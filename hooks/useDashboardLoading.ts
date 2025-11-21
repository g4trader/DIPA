"use client";

import { useState, useEffect, useRef } from "react";

type LoadingState = {
  isLoading: boolean;
  bigNumberReady: boolean;
  tableReady: boolean;
  error: Error | null;
};

/**
 * useDashboardLoading - Hook para gerenciar estados de loading do dashboard
 */
export function useDashboardLoading() {
  const [state, setState] = useState<LoadingState>({
    isLoading: true,
    bigNumberReady: false,
    tableReady: false,
    error: null,
  });

  const bigNumberStartTime = useRef<number | null>(null);
  const tableStartTime = useRef<number | null>(null);

  useEffect(() => {
    bigNumberStartTime.current = performance.now();
  }, []);

  const markBigNumberReady = () => {
    if (bigNumberStartTime.current) {
      const duration = performance.now() - bigNumberStartTime.current;
      setState((prev) => ({
        ...prev,
        bigNumberReady: true,
      }));
      return duration;
    }
    return 0;
  };

  const markTableReady = () => {
    if (tableStartTime.current) {
      const duration = performance.now() - tableStartTime.current;
      setState((prev) => ({
        ...prev,
        tableReady: true,
        isLoading: false,
      }));
      return duration;
    }
    return 0;
  };

  const startTableLoading = () => {
    tableStartTime.current = performance.now();
  };

  const setError = (error: Error) => {
    setState((prev) => ({
      ...prev,
      error,
      isLoading: false,
    }));
  };

  return {
    ...state,
    markBigNumberReady,
    markTableReady,
    startTableLoading,
    setError,
  };
}

