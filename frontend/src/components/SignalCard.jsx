import { useState } from 'react';
import LayerBars from './LayerBars';
import { SECTOR_COLORS } from './Sidebar';
import { fetchSignalRationale } from '../api/client';
import { useQuery } from '@tanstack/react-query';

export default function SignalCard({ signal }) {
  const [expanded, setExpanded] = useState(false);
  
  const { data, isLoading } = useQuery({
    queryKey: ['rationale', signal.id],
    queryFn: () => fetchSignalRationale(signal.id),
    enabled: expanded && !signal.rationale,
    staleTime: Infinity,
  });

  const rationale = signal.rationale || data?.rationale;

  const getConvictionColor = (c) => {
    if (c === 'high') return 'text-red-400 bg-red-400/10 border-red-400/20';
    if (c === 'medium') return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
    return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
  };

  return (
    <div className="bg-surface border border-slate-700 rounded-lg p-5 mb-4 shadow-sm hover:border-slate-600 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <span 
            className="px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider text-slate-100"
            style={{ backgroundColor: SECTOR_COLORS[signal.sector] || '#334155' }}
          >
            {signal.sector}
          </span>
          <span className={`px-2 py-0.5 rounded border text-xs uppercase tracking-wider ${getConvictionColor(signal.conviction)}`}>
            {signal.conviction} CONVICTION
          </span>
        </div>
        
        <div className="text-right">
          <div className="text-2xl font-mono font-bold text-slate-100">
            {signal.surprise_val.toFixed(2)}
          </div>
          <div className="text-xs text-slate-400 font-mono uppercase tracking-widest">
            Surprise
          </div>
        </div>
      </div>
      
      <div className="text-sm text-slate-400 mb-2 font-mono">
        {new Date(signal.triggered_at).toLocaleString()}
      </div>

      <div className="text-lg font-semibold text-slate-100 mb-4 leading-tight">
        {signal.headline_text || "Complex Multi-Source Event Detected"}
      </div>

      <LayerBars layers={signal.layers || {lexical: 0, semantic: 0, event: 0}} />
      
      <div className="mt-5 border-t border-slate-700/50 pt-4">
        <button 
          onClick={() => setExpanded(!expanded)}
          className="text-sm font-semibold text-primary hover:text-blue-400 focus:outline-none"
        >
          {expanded ? '▲ Hide Analysis' : '▼ Read Thesis Analysis'}
        </button>
        
        {expanded && (
          <div className="mt-3 p-4 bg-slate-800/50 rounded-md border border-slate-700/50">
            {isLoading ? (
              <div className="animate-pulse flex space-x-4">
                <div className="flex-1 space-y-3 py-1">
                  <div className="h-2 bg-slate-700 rounded w-3/4"></div>
                  <div className="h-2 bg-slate-700 rounded"></div>
                  <div className="h-2 bg-slate-700 rounded w-5/6"></div>
                </div>
              </div>
            ) : (
              <p className="text-slate-300 text-sm leading-relaxed">
                {rationale || (
                  <span className="text-slate-500 italic">
                    Heuristic Analysis: This signal was triggered by a significant divergence from the 30-day sector baseline. 
                    Upgrade to a live LLM key for an automated investment thesis.
                  </span>
                )}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
