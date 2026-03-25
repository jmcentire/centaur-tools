import { useState, useEffect, useRef, useMemo, useCallback } from 'react';

function StarButton({ slug, count, initialVoted = false, size = 16 }: { slug: string; count: number; initialVoted?: boolean; size?: number }) {
  const [votes, setVotes] = useState(count);
  const [voted, setVoted] = useState(initialVoted);
  const [busy, setBusy] = useState(false);

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/tools/${slug}/vote`, { method: voted ? 'DELETE' : 'POST' });
      if (res.status === 401) { window.location.href = '/api/auth/login'; return; }
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'already_voted') {
          setVoted(true);
          if (data.vote_count != null) setVotes(data.vote_count);
        } else if (data.status === 'not_voted') {
          setVoted(false);
          if (data.vote_count != null) setVotes(data.vote_count);
        } else {
          setVotes(data.vote_count ?? votes + (voted ? -1 : 1));
          setVoted(!voted);
        }
      }
    } catch {} finally { setBusy(false); }
  };

  return (
    <button onClick={toggle} disabled={busy}
      className="flex items-center gap-1 text-secondary hover:text-emphasis transition-colors disabled:opacity-50"
      title={voted ? 'Remove vote' : 'Vote useful'}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill={voted ? 'currentColor' : 'none'}
        stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
      </svg>
      <span className="text-[13px] tabular-nums">{votes}</span>
    </button>
  );
}

interface Tool {
  slug: string;
  name: string;
  description: string;
  tags: string[];
  author: { username: string; avatar_url: string | null };
  vote_count: number;
  user_voted: boolean;
  language: string;
  created_at: string;
}

type SortKey = 'newest' | 'votes' | 'name';

const LANG_DOT: Record<string, string> = {
  Python: '#3572a5', Rust: '#dea584', TypeScript: '#3178c6',
  JavaScript: '#f1e05a', Go: '#00add8',
};

function relDate(iso: string) {
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (d === 0) return 'today';
  if (d === 1) return '1d ago';
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export default function SearchTools() {
  // Read initial search query from URL params (?tag=x or ?q=x)
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialQuery = urlParams?.get('tag') || urlParams?.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sort, setSort] = useState<SortKey>('newest');
  const [langFilter, setLangFilter] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const fetchTools = useCallback(async (q?: string) => {
    setLoading(true);
    setError('');
    try {
      const url = q ? `/api/search/?q=${encodeURIComponent(q)}&per_page=100` : '/api/tools/?per_page=100';
      const res = await fetch(url);
      if (!res.ok) throw new Error('Could not load tools');
      const data = await res.json();
      setTools(data.tools || []);
    } catch (e: any) {
      setError(e.message);
      setTools([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTools(initialQuery || undefined); }, [fetchTools]);

  const handleSearch = useCallback((v: string) => {
    setQuery(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchTools(v || undefined), 250);
  }, [fetchTools]);

  const languages = useMemo(() => {
    const c = new Map<string, number>();
    tools.forEach(t => t.language && c.set(t.language, (c.get(t.language) || 0) + 1));
    return [...c.entries()].sort((a, b) => b[1] - a[1]).map(([l]) => l);
  }, [tools]);

  const filtered = useMemo(() => {
    let r = langFilter ? tools.filter(t => t.language === langFilter) : tools;
    if (sort === 'votes') r = [...r].sort((a, b) => b.vote_count - a.vote_count);
    else if (sort === 'name') r = [...r].sort((a, b) => a.name.localeCompare(b.name));
    return r;
  }, [tools, langFilter, sort]);

  return (
    <div>
      {/* Search — underline input, emphasis border on focus */}
      <input
        ref={inputRef}
        type="text"
        placeholder="Search..."
        value={query}
        onChange={e => handleSearch(e.target.value)}
        className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
      />

      {/* Controls — secondary text, emphasis weight on active */}
      {!loading && !error && tools.length > 0 && (
        <div className="flex items-baseline justify-between mt-6 mb-2">
          <div className="flex items-baseline gap-4 text-[13px]">
            <span className="text-secondary tabular-nums">{filtered.length} tools</span>
            {languages.length > 1 && (
              <>
                <button onClick={() => setLangFilter(null)}
                  className={!langFilter ? 'font-semibold text-primary' : 'text-secondary hover:text-primary transition-colors'}>
                  All
                </button>
                {languages.map(lang => (
                  <button key={lang} onClick={() => setLangFilter(langFilter === lang ? null : lang)}
                    className={'flex items-center gap-1.5 ' + (langFilter === lang ? 'font-semibold text-primary' : 'text-secondary hover:text-primary transition-colors')}>
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: LANG_DOT[lang] || '#a3a3a3' }} />
                    {lang}
                  </button>
                ))}
              </>
            )}
          </div>
          <div className="flex items-baseline gap-4 text-[13px]">
            {(['newest', 'votes', 'name'] as SortKey[]).map(k => (
              <button key={k} onClick={() => setSort(k)}
                className={sort === k ? 'font-semibold text-primary' : 'text-secondary hover:text-primary transition-colors'}>
                {k === 'newest' ? 'New' : k === 'votes' ? 'Top' : 'A–Z'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading — quiet, minimal */}
      {loading && <p className="py-16 text-center text-secondary">Loading...</p>}

      {/* Error */}
      {error && (
        <div className="py-16 text-center">
          <p className="text-body mb-3">{error}</p>
          <button onClick={() => fetchTools(query || undefined)} className="text-sm text-link hover:opacity-70 transition-opacity">Retry</button>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && filtered.length === 0 && (
        <div className="py-16 text-center">
          <p className="text-body mb-3">{query ? `No results for "${query}"` : langFilter ? `No ${langFilter} tools` : 'No tools registered yet'}</p>
          {!query && !langFilter && <a href="/submit" className="text-sm text-link hover:opacity-70 transition-opacity">Submit the first</a>}
          {langFilter && <button onClick={() => setLangFilter(null)} className="text-sm text-link hover:opacity-70 transition-opacity">Clear filter</button>}
        </div>
      )}

      {/* Tool list — strict 3-column grid per row */}
      {!loading && !error && filtered.length > 0 && (
        <div>
          {filtered.map(tool => (
            <a key={tool.slug} href={`/tools/${tool.slug}`}
              className="group grid grid-cols-[1fr_140px_100px] gap-6 py-5 border-b border-rule hover:bg-surface transition-colors -mx-4 px-4 rounded no-underline [&_*]:no-underline">

              {/* Col 1: content */}
              <div className="min-w-0">
                <h3 className="text-xl font-semibold text-primary leading-snug group-hover:text-emphasis transition-colors">
                  {tool.name}
                </h3>
                <p className="text-body mt-1 line-clamp-1">{tool.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  {(tool.tags || []).slice(0, 4).map(tag => (
                    <span key={tag}
                      onClick={(e) => { e.preventDefault(); handleSearch(tag); }}
                      className="font-mono text-[11px] font-medium text-secondary px-1.5 py-0.5 border border-rule rounded cursor-pointer hover:border-rule-strong hover:text-primary transition-colors">{tag}</span>
                  ))}
                  {(tool.tags || []).length > 4 && <span className="text-[11px] text-quiet">+{tool.tags.length - 4}</span>}
                </div>
              </div>

              {/* Col 2: language + author */}
              <div className="text-right self-center">
                {tool.language && (
                  <div className="flex items-center justify-end gap-1.5 mb-0.5">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: LANG_DOT[tool.language] || '#a3a3a3' }} />
                    <span className="text-[13px] text-secondary">{tool.language}</span>
                  </div>
                )}
                <span className="text-[13px] text-secondary">{tool.author?.username}</span>
              </div>

              {/* Col 3: star + date */}
              <div className="flex flex-col items-end self-center gap-1">
                <StarButton slug={tool.slug} count={tool.vote_count} initialVoted={tool.user_voted} />
                <div className="text-[13px] text-quiet">{relDate(tool.created_at)}</div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
