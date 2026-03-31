import { NavLink } from 'react-router-dom';

export const SECTORS = [
  "Tech", "Finance", "Healthcare", "Energy", "Consumer", "Industrials", "Materials"
];

export const SECTOR_COLORS = {
  "Tech": "#3b82f6",
  "Finance": "#10b981",
  "Healthcare": "#ec4899",
  "Energy": "#f59e0b",
  "Consumer": "#8b5cf6",
  "Industrials": "#64748b",
  "Materials": "#f97316"
};

export default function Sidebar() {
  return (
    <aside className="w-64 bg-surface border-r border-slate-700 min-h-screen p-4 flex flex-col">
      <div className="font-mono text-xl text-primary font-bold mb-8 tracking-tighter">
        News<span className="text-slate-100">Alpha</span>
      </div>
      
      <nav className="flex-1 space-y-2">
        <NavLink 
          to="/"
          className={({isActive}) => `block px-3 py-2 rounded-md font-sans text-sm ${isActive ? 'bg-primary/20 text-primary' : 'text-slate-300 hover:bg-slate-700'}`}
        >
          Signal Feed
        </NavLink>
        <NavLink 
          to="/search"
          className={({isActive}) => `block px-3 py-2 rounded-md font-sans text-sm ${isActive ? 'bg-primary/20 text-primary' : 'text-slate-300 hover:bg-slate-700'}`}
        >
          Semantic Search
        </NavLink>
        
        <div className="pt-6 pb-2">
          <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">Sectors</p>
        </div>
        
        {SECTORS.map(sector => (
          <NavLink
            key={sector}
            to={`/sector/${sector}`}
            className={({isActive}) => `flex items-center gap-2 px-3 py-2 rounded-md font-sans text-sm ${isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
          >
            <span 
              className="w-2 h-2 rounded-full" 
              style={{backgroundColor: SECTOR_COLORS[sector]}}
            />
            {sector}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
