import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

// --- Shared types & helpers (mirroring SearchTools.tsx) ---

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

interface Notification {
  id: number;
  type: string;
  title: string;
  message?: string;
  body?: string;
  read: boolean;
  created_at: string;
  link?: string;
}

interface UserProfile {
  username: string;
  display_name: string;
  email: string;
  joined_at: string;
}

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

// --- StarButton (same pattern as SearchTools.tsx) ---

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

// --- Tool Row (explore-style layout with optional Edit link) ---

function ToolRow({ tool, showEdit }: { tool: Tool; showEdit: boolean }) {
  return (
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
              className="font-mono text-[11px] font-medium text-secondary px-1.5 py-0.5 border border-rule rounded">{tag}</span>
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

      {/* Col 3: star + date + edit */}
      <div className="flex flex-col items-end self-center gap-1">
        <StarButton slug={tool.slug} count={tool.vote_count} initialVoted={tool.user_voted} />
        <div className="text-[13px] text-quiet">{relDate(tool.created_at)}</div>
        {showEdit && (
          <span
            onClick={(e) => { e.preventDefault(); window.location.href = `/tools/${tool.slug}/edit`; }}
            className="text-[13px] text-emphasis hover:opacity-70 cursor-pointer transition-opacity"
          >
            Edit
          </span>
        )}
      </div>
    </a>
  );
}

// --- Main Dashboard ---

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.05, duration: 0.4, ease: 'easeOut' },
  }),
};

export default function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [allTools, setAllTools] = useState<Tool[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'tools' | 'starred' | 'notifications'>('tools');

  useEffect(() => {
    Promise.all([
      fetch('/api/auth/me').then((r) => {
        if (r.status === 401) throw new Error('unauthorized');
        if (!r.ok) throw new Error('Failed to load profile');
        return r.json();
      }),
      fetch('/api/tools/?per_page=100').then((r) => {
        if (!r.ok) return { tools: [] };
        return r.json();
      }),
      fetch('/api/notifications/')
        .then((r) => (r.ok ? r.json() : { notifications: [] }))
        .catch(() => ({ notifications: [] })),
    ])
      .then(([userData, toolsData, notifData]) => {
        setUser(userData);
        setAllTools(toolsData.tools || []);
        setNotifications(notifData.notifications || []);
      })
      .catch((err) => {
        if (err.message === 'unauthorized') {
          window.location.href = '/api/auth/login';
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const markAsRead = async (id: number) => {
    try {
      await fetch(`/api/user/notifications/${id}/read`, { method: 'POST' });
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    } catch {
      // silently fail
    }
  };

  const markAllRead = async () => {
    try {
      await fetch('/api/user/notifications/read-all', { method: 'POST' });
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch {
      // silently fail
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-20 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emphasis animate-pulse" />
          <span className="text-[13px] text-secondary">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-20 text-center">
        <h2 className="text-xl font-semibold text-primary mb-2">Sign in required</h2>
        <p className="text-secondary text-sm mb-6">You need to be signed in to view your dashboard.</p>
        <a
          href="/api/auth/login"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary font-medium text-sm rounded-md hover:opacity-90 transition-opacity no-underline" style={{color:'#ffffff'}}
        >
          Sign in
        </a>
      </div>
    );
  }

  const myTools = allTools.filter((t) => t.author?.username === user.username);
  const starredTools = allTools.filter((t) => t.user_voted);
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <motion.div
      className="max-w-5xl mx-auto px-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* User header */}
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-bold text-primary tracking-tight">{user.display_name}</h1>
          <p className="text-secondary text-sm mt-1">@{user.username}</p>
        </div>
        <a
          href="/submit"
          className="flex items-center gap-2 px-5 py-2.5 bg-primary font-medium text-sm rounded-md hover:opacity-90 transition-opacity no-underline" style={{color:'#ffffff'}}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Submit Tool
        </a>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-6 mb-8 border-b border-rule">
        <button
          onClick={() => setActiveTab('tools')}
          className={`pb-3 text-sm font-medium transition-colors ${
            activeTab === 'tools'
              ? 'text-primary border-b-2 border-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          My Tools ({myTools.length})
        </button>
        <button
          onClick={() => setActiveTab('starred')}
          className={`pb-3 text-sm font-medium transition-colors ${
            activeTab === 'starred'
              ? 'text-primary border-b-2 border-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          Starred ({starredTools.length})
        </button>
        <button
          onClick={() => setActiveTab('notifications')}
          className={`pb-3 text-sm font-medium transition-colors relative ${
            activeTab === 'notifications'
              ? 'text-primary border-b-2 border-primary'
              : 'text-secondary hover:text-primary'
          }`}
        >
          Notifications
          {unreadCount > 0 && (
            <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-primary text-canvas rounded-full">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* My Tools tab */}
      {activeTab === 'tools' && (
        <div>
          {myTools.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-secondary text-lg mb-2">No tools yet</p>
              <p className="text-quiet text-sm mb-6">Submit your first tool to the registry.</p>
              <a
                href="/submit"
                className="text-sm text-emphasis hover:opacity-70 transition-opacity"
              >
                Submit a tool
              </a>
            </div>
          ) : (
            <div>
              {myTools.map((tool) => (
                <ToolRow key={tool.slug} tool={tool} showEdit={true} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Starred tab */}
      {activeTab === 'starred' && (
        <div>
          {starredTools.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-secondary text-lg mb-2">No starred tools</p>
              <p className="text-quiet text-sm mb-6">Star tools you find useful and they'll appear here.</p>
              <a
                href="/explore"
                className="text-sm text-emphasis hover:opacity-70 transition-opacity"
              >
                Explore tools
              </a>
            </div>
          ) : (
            <div>
              {starredTools.map((tool) => (
                <ToolRow key={tool.slug} tool={tool} showEdit={false} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Notifications tab */}
      {activeTab === 'notifications' && (
        <div>
          {notifications.length > 0 && unreadCount > 0 && (
            <div className="flex justify-end mb-4">
              <button
                onClick={markAllRead}
                className="text-sm text-emphasis hover:opacity-70 transition-opacity"
              >
                Mark all as read
              </button>
            </div>
          )}

          {notifications.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-secondary text-lg mb-2">No notifications</p>
              <p className="text-quiet text-sm">You're all caught up.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((notif, i) => (
                <motion.div
                  key={notif.id}
                  custom={i}
                  variants={fadeUp}
                  initial="hidden"
                  animate="visible"
                  onClick={() => {
                    if (!notif.read) markAsRead(notif.id);
                    if (notif.link) window.location.href = notif.link;
                  }}
                  className={`p-4 rounded border transition-colors cursor-pointer ${
                    notif.read
                      ? 'border-rule hover:bg-surface'
                      : 'border-rule-strong bg-surface'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {!notif.read && <div className="w-2 h-2 rounded-full bg-emphasis shrink-0 mt-1.5" />}
                    <div className="flex-1">
                      <p className={`text-sm ${notif.read ? 'text-secondary' : 'text-primary'}`}>
                        {notif.title || notif.message}
                      </p>
                      <span className="text-[13px] text-quiet mt-1 block">
                        {new Date(notif.created_at).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Account management */}
      <div className="mt-16 pt-8 border-t border-rule">
        <h2 className="text-base font-semibold text-primary mb-4">Account</h2>
        <div className="flex items-center gap-6">
          <a href="/api/users/me/data" className="text-sm text-secondary hover:text-primary transition-colors">
            Download my data
          </a>
          <button
            onClick={async () => {
              if (!confirm('This will permanently delete your account and anonymize all your content. This cannot be undone. Are you sure?')) return;
              const res = await fetch('/api/users/me', { method: 'DELETE' });
              if (res.ok) {
                await fetch('/api/auth/logout', { method: 'POST' });
                window.location.href = '/';
              }
            }}
            className="text-sm text-secondary hover:text-error transition-colors"
          >
            Delete my account
          </button>
          <button
            onClick={async () => {
              await fetch('/api/auth/logout', { method: 'POST' });
              window.location.href = '/';
            }}
            className="text-sm text-secondary hover:text-primary transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </motion.div>
  );
}
