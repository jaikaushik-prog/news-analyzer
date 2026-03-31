import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchSignals } from '../api/client';

export default function SearchResults() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 400);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchSignals(debouncedQuery),
    enabled: debouncedQuery.length >= 3,
  });

  return (
    <div className="p-8 max-w-4xl mx-auto pb-20">
      <h1 className="text-2xl font-bold font-sans text-slate-100 mb-6">Semantic Search</h1>
      
      <input
        type="text"
        placeholder="Search for semantic market events (e.g. 'unexpected CEO resignation')..."
        className="w-full bg-surface border border-slate-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary rounded p-4 text-slate-100 font-sans shadow-sm mb-8 placeholder-slate-500"
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      
      {isLoading && debouncedQuery && (
        <div className="text-slate-400 font-mono animate-pulse">
          Searching semantically across headlines...
        </div>
      )}
      
      {data && !isLoading && (
        <div className="space-y-4">
          <p className="text-sm font-mono text-slate-400">Found {data.results?.length || 0} results</p>
          {data.results?.map((res, i) => (
            <div key={i} className="p-4 bg-surface border border-slate-700 rounded shadow-sm">
              <p className="text-slate-200">{res.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
