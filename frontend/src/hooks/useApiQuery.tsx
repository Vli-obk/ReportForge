'use client';

import React, { createContext, useContext, useCallback, useEffect, useRef, useState } from 'react';
import { AxiosResponse } from 'axios';

type QueryFn<T> = (signal: AbortSignal) => Promise<AxiosResponse<T>>;

interface QueryOptions {
  enabled?: boolean;
  pollMs?: number;
  retries?: number;
}

interface QueryState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  success: boolean;
  responseTime: number | null;
  updatedAt: Date | null;
  refetch: () => Promise<void>;
}

interface CacheEntry {
  data: any;
  error: string | null;
  loading: boolean;
  responseTime: number | null;
  updatedAt: Date | null;
  failureCount: number;
  lastRunAt: number;
  controller: AbortController | null;
  promise: Promise<any> | null;
  subscribers: Set<() => void>;
}

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string; error?: string } } }).response;
    return response?.data?.detail || response?.data?.error || 'Request failed';
  }
  if (error instanceof Error) return error.message;
  return 'Request failed';
};

const ApiQueryContext = createContext<{
  getEntry: (key: string) => CacheEntry;
  subscribe: (key: string, callback: () => void) => () => void;
  runQuery: (key: string, queryFn: QueryFn<any>, options: QueryOptions) => Promise<void>;
  resetFailure: (key: string) => void;
} | null>(null);

export function ApiQueryProvider({ children }: { children: React.ReactNode }) {
  const cache = useRef<Map<string, CacheEntry>>(new Map());

  const getEntry = useCallback((key: string): CacheEntry => {
    if (!cache.current.has(key)) {
      cache.current.set(key, {
        data: null,
        error: null,
        loading: false,
        responseTime: null,
        updatedAt: null,
        failureCount: 0,
        lastRunAt: 0,
        controller: null,
        promise: null,
        subscribers: new Set(),
      });
    }
    return cache.current.get(key)!;
  }, []);

  const subscribe = useCallback((key: string, callback: () => void) => {
    const entry = getEntry(key);
    entry.subscribers.add(callback);
    return () => {
      entry.subscribers.delete(callback);
      if (entry.subscribers.size === 0) {
        if (entry.controller) {
          entry.controller.abort();
        }
        cache.current.delete(key);
      }
    };
  }, [getEntry]);

  const resetFailure = useCallback((key: string) => {
    const entry = getEntry(key);
    entry.failureCount = 0;
    entry.lastRunAt = 0;
    entry.error = null;
    entry.subscribers.forEach((sub) => sub());
  }, [getEntry]);

  const runQuery = useCallback(async (
    key: string,
    queryFn: QueryFn<any>,
    options: QueryOptions
  ) => {
    const { enabled = true, pollMs, retries = 1 } = options;
    const entry = getEntry(key);

    if (!enabled || document.hidden) return;
    
    // Prevent duplicate executions for the same key
    if (entry.promise) return;

    const now = Date.now();
    const minInterval = pollMs ? Math.max(pollMs, 1000) : 500;
    if (now - entry.lastRunAt < minInterval) return;
    entry.lastRunAt = now;

    // Create new AbortController for this request
    const controller = new AbortController();
    entry.controller = controller;
    entry.loading = true;
    entry.subscribers.forEach((sub) => sub());

    const started = performance.now();
    let attempt = 0;

    const execute = async () => {
      while (attempt <= retries) {
        try {
          if (controller.signal.aborted) return;
          
          const response = await queryFn(controller.signal);

          if (controller.signal.aborted) return;

          entry.data = response.data;
          entry.error = null;
          entry.responseTime = Math.round(performance.now() - started);
          entry.updatedAt = new Date();
          entry.loading = false;
          entry.failureCount = 0;
          return;
        } catch (err) {
          if (controller.signal.aborted) return;

          const axiosError = err as any;
          
          // Handle 404 errors - allow retry on refetch()
          if (axiosError?.response?.status === 404) {
            entry.error = `404 Not Found: ${axiosError?.config?.url}`;
            entry.loading = false;
            return;
          }

          // Max retries exceeded
          if (attempt >= retries) {
            entry.failureCount++;
            entry.error = getErrorMessage(err);
            entry.loading = false;
            return;
          }

          // Exponential backoff: 1s, 2s, 4s... up to 10s
          const backoffDelay = Math.min(1000 * Math.pow(2, attempt), 10000);
          await new Promise(resolve => setTimeout(resolve, backoffDelay));
          attempt += 1;
        }
      }
    };

    entry.promise = execute().finally(() => {
      entry.promise = null;
      entry.controller = null;
      entry.subscribers.forEach((sub) => sub());
    });

    await entry.promise;
  }, [getEntry]);

  return (
    <ApiQueryContext.Provider value={{ getEntry, subscribe, runQuery, resetFailure }}>
      {children}
    </ApiQueryContext.Provider>
  );
}

export function useApiQuery<T>(
  key: string,
  queryFn: QueryFn<T>,
  options: QueryOptions = {}
): QueryState<T> {
  const context = useContext(ApiQueryContext);
  if (!context) {
    throw new Error('useApiQuery must be used within an ApiQueryProvider');
  }

  const { getEntry, subscribe, runQuery, resetFailure } = context;
  const [, forceUpdate] = useState({});

  useEffect(() => {
    return subscribe(key, () => forceUpdate({}));
  }, [key, subscribe]);

  const entry = getEntry(key);

  // Use a ref for queryFn to prevent re-creating 'run' callback and re-triggering useEffect
  const queryFnRef = useRef(queryFn);
  queryFnRef.current = queryFn;

  // Destructure options to prevent object-reference changes from re-triggering effects
  const { pollMs, enabled, retries } = options;

  const run = useCallback(async () => {
    await runQuery(key, queryFnRef.current, { pollMs, enabled, retries });
  }, [key, pollMs, enabled, retries, runQuery]);

  useEffect(() => {
    if (enabled === false) return;

    run(); // Initial run

    let intervalId: number | null = null;

    const startPolling = () => {
      if (pollMs && !intervalId && !document.hidden) {
        const actualPollMs = Math.max(pollMs, 1000);
        intervalId = window.setInterval(run, actualPollMs);
      }
    };

    const stopPolling = () => {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    };

    startPolling();

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [enabled, pollMs, run]);

  const refetch = useCallback(async () => {
    resetFailure(key);
    await run();
  }, [key, resetFailure, run]);

  return {
    data: entry.data,
    error: entry.error,
    loading: entry.loading,
    success: !!entry.data && !entry.error,
    responseTime: entry.responseTime,
    updatedAt: entry.updatedAt,
    refetch,
  };
}
