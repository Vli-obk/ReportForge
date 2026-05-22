'use client';

import { useState, useEffect, useRef } from 'react';

interface JobEvent {
  job_id: string;
  status: string;
  progress: number;
  filename: string;
}

interface JobState {
  status: string;
  progress: number;
  filename: string;
  justCompleted: boolean;
}

export function usePipelineStream() {
  const [jobs, setJobs] = useState<Map<string, JobState>>(new Map());
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const justCompletedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const token = localStorage.getItem('pdf_analytics_token');
    if (!token) {
      setConnected(false);
      return;
    }
    const streamUrl = `/api/v1/pipeline/stream?token=${encodeURIComponent(token)}`;

    // Create EventSource connection
    const eventSource = new EventSource(streamUrl);

    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      console.log('SSE connection opened');
    };

    eventSource.onmessage = (event) => {
      try {
        const data: JobEvent = JSON.parse(event.data);
        
        setJobs((prevJobs) => {
          const newJobs = new Map(prevJobs);
          const existingJob = newJobs.get(data.job_id);
          
          // Check if this job just completed (transition from processing to done)
          const justCompleted = existingJob?.status === 'processing' && data.status === 'done';
          
          if (justCompleted) {
            justCompletedRef.current.add(data.job_id);
            // Remove the flag after animation
            setTimeout(() => {
              justCompletedRef.current.delete(data.job_id);
              setJobs((currentJobs) => {
                const updated = new Map(currentJobs);
                const job = updated.get(data.job_id);
                if (job) {
                  job.justCompleted = false;
                  return updated;
                }
                return currentJobs;
              });
            }, 2000); // 2 second flash animation
          }

          newJobs.set(data.job_id, {
            status: data.status,
            progress: data.progress,
            filename: data.filename,
            justCompleted,
          });

          return newJobs;
        });
      } catch (error) {
        console.error('Error parsing SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      setConnected(false);
    };

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
    };
  }, []);

  return {
    jobs,
    connected,
  };
}
