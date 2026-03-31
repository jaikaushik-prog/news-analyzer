import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchSectorData } from '../api/client';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

export default function SectorView() {
  const { sectorName } = useParams();
  
  const { data, isLoading } = useQuery({
    queryKey: ['sector', sectorName],
    queryFn: () => fetchSectorData(sectorName),
    refetchInterval: 30000, // Refresh every 30s
  });

  const chartData = data?.sentiment_trend || [];

  return (
    <div className="p-8 max-w-5xl mx-auto pb-20">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold font-sans text-slate-100">{sectorName} Overview</h1>
          <p className="text-slate-400 mt-1">7-Day Aggregated Intelligence</p>
        </div>
        <div className="text-right">
          <div className="text-xs font-mono text-slate-500 uppercase tracking-widest">Market Status</div>
          <div className="text-emerald-400 font-mono flex items-center gap-2 justify-end">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            LIVE
          </div>
        </div>
      </div>
      
      {isLoading ? (
        <div className="text-slate-400 animate-pulse font-mono">CALCULATING SECTOR ANALYTICS...</div>
      ) : (
        <>
          <div className="bg-surface border border-slate-700 p-6 rounded-lg mb-8 shadow-xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-sm font-mono text-slate-400 uppercase tracking-widest">Sentiment & Surprise Trend</h2>
              <div className="flex gap-4 text-xs font-mono">
                <div className="flex items-center gap-1.5 text-emerald-400">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full"></div> SENTIMENT
                </div>
                <div className="flex items-center gap-1.5 text-blue-400">
                  <div className="w-2 h-2 bg-blue-400 rounded-full"></div> SURPRISE
                </div>
              </div>
            </div>
            
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorSent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSurp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    stroke="#64748b" 
                    fontSize={10} 
                    tickFormatter={(str) => {
                      const d = new Date(str);
                      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
                    }} 
                  />
                  <YAxis stroke="#64748b" fontSize={10} domain={[-1, 1]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }}
                    itemStyle={{ fontSize: '12px', fontFamily: 'monospace' }}
                    labelStyle={{ color: '#94a3b8', marginBottom: '4px', fontSize: '10px' }}
                  />
                  <ReferenceLine y={0} stroke="#475569" strokeDasharray="3 3" />
                  <Area 
                    type="monotone" 
                    dataKey="sentiment" 
                    stroke="#10b981" 
                    fillOpacity={1} 
                    fill="url(#colorSent)" 
                    strokeWidth={2}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="surprise" 
                    stroke="#3b82f6" 
                    fillOpacity={1} 
                    fill="url(#colorSurp)" 
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
             <div className="p-4 bg-surface border border-slate-700 rounded flex flex-col gap-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Avg Sentiment</span>
                <span className="text-xl font-bold text-emerald-400">
                  {(chartData[chartData.length-1]?.sentiment || 0).toFixed(2)}
                </span>
             </div>
             <div className="p-4 bg-surface border border-slate-700 rounded flex flex-col gap-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Avg Surprise</span>
                <span className="text-xl font-bold text-blue-400">
                  {(chartData[chartData.length-1]?.surprise || 0).toFixed(2)}
                </span>
             </div>
             <div className="p-4 bg-surface border border-slate-700 rounded flex flex-col gap-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Coverage</span>
                <span className="text-xl font-bold text-slate-100">{data?.recent_headlines?.length || 0} pps</span>
             </div>
          </div>
          
          <h2 className="text-sm font-mono text-slate-400 uppercase tracking-widest mt-12 mb-6">Recent Sector Activity</h2>
          <div className="space-y-3">
            {data?.recent_headlines?.length > 0 ? data.recent_headlines.map((h, i) => (
              <div key={i} className="group p-5 bg-surface border border-slate-700 hover:border-slate-500 transition-colors rounded flex gap-5 items-start">
                <div className="w-1 h-full bg-slate-700 group-hover:bg-primary transition-colors rounded-full self-stretch" />
                <div className="flex-1">
                  <p className="text-slate-200 text-sm font-medium leading-relaxed">{h.text}</p>
                  <div className="text-[10px] font-mono text-slate-500 mt-2 uppercase tracking-tight">
                    {new Date(h.date).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                  </div>
                </div>
              </div>
            )) : (
              <div className="p-10 text-center border border-dashed border-slate-700 rounded text-slate-500 italic text-sm">
                No recent sector headlines found in the ingestion buffer.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
