import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchSignals } from '../api/client';
import SignalCard from '../components/SignalCard';

export default function SignalFeed() {
  const [sector, setSector] = useState('');
  const [conviction, setConviction] = useState('');

  const { data: signals, isLoading, error, refetch } = useQuery({
    queryKey: ['signals', sector, conviction],
    queryFn: () => fetchSignals(sector, conviction),
    refetchInterval: 300000, // 5 min
  });

  return (
    <div className="p-8 max-w-4xl mx-auto pb-20">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold font-sans text-slate-100 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
          Live Signal Feed
        </h1>
        <div className="text-xs text-slate-400 font-mono">
          Auto-updating every 5m
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex justify-center my-10 text-primary">Loading signals...</div>
      ) : error ? (
        <div className="text-red-400">Error loading signals. Ensure backend is running.</div>
      ) : signals?.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-surface border border-slate-700 rounded-lg text-slate-400 mt-8 shadow-sm">
          <span className="text-4xl mb-4">✨</span>
          <p className="font-mono text-sm">No significant market anomalies detected.</p>
          <p className="text-xs mt-2 text-slate-500">All sectors operating within expected variance.</p>
        </div>
      ) : (
        <div className="space-y-4 shadow-sm">
          {signals.map(s => <SignalCard key={s.id} signal={s} />)}
        </div>
      )}
    </div>
  );
}
