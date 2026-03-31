export default function LayerBars({ layers }) {
  const getWidth = (val) => `${Math.min(100, Math.max(0, val * 100))}%`;
  const getColor = (val) => {
    if (val < 0.5) return 'bg-slate-500';
    if (val < 0.7) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-2 mt-4">
      <div className="flex items-center text-xs">
        <span className="w-20 text-slate-400 font-mono">LEXICAL</span>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-600 ease-out ${getColor(layers.lexical)}`}
            style={{ width: getWidth(layers.lexical) }}
          />
        </div>
      </div>
      <div className="flex items-center text-xs">
        <span className="w-20 text-slate-400 font-mono">SEMANTIC</span>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-600 ease-out ${getColor(layers.semantic)}`}
            style={{ width: getWidth(layers.semantic) }}
          />
        </div>
      </div>
      <div className="flex items-center text-xs">
        <span className="w-20 text-slate-400 font-mono">EVENT</span>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className={`h-full transition-all duration-600 ease-out ${getColor(layers.event)}`}
            style={{ width: getWidth(layers.event) }}
          />
        </div>
      </div>
    </div>
  );
}
