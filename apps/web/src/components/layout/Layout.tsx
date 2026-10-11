import { Link, Outlet, useLocation } from 'react-router-dom';

const navGroups = [
  {
    name: 'Explore Chennai',
    paths: [
      { name: 'Flood Risk Map', path: '/map' },
      { name: 'Response Routes', path: '/routing' },
    ],
  },
  {
    name: 'Analysis',
    paths: [
      { name: 'Forecast', path: '/forecast' },
      { name: 'RCA', path: '/rca' },
      { name: 'Recommendations', path: '/recommendations' },
    ],
  },
  {
    name: 'Data & Records',
    paths: [
      { name: 'Data Quality', path: '/quality' },
      { name: 'Evidence', path: '/evidence' },
      { name: 'Audit Trail', path: '/audit' },
    ],
  },
  {
    name: 'Governance & Response',
    paths: [
      { name: 'Human Review Gate', path: '/review' },
      { name: 'Alert Gateway', path: '/alerts' },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  
  return (
    <div className="flex h-screen bg-slate-100/70 text-slate-900 font-sans antialiased">
      {/* Light Blue Sidebar Navigation Panel */}
      <aside className="w-64 border-r border-sky-200/80 flex flex-col bg-sky-50/95 backdrop-blur shadow-sm">
        <div className="p-5 border-b border-sky-200/70 flex flex-col gap-2 bg-gradient-to-b from-sky-100/60 to-transparent">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white font-bold text-lg shadow-sm">
              🌊
            </span>
            <div>
              <h1 className="text-xl font-black text-sky-950 tracking-tight leading-none">AquaRizz</h1>
              <span className="text-[11px] font-semibold text-sky-700 tracking-wide uppercase">Chennai Flood Ops</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-2.5" aria-label="Main navigation">
          <Link
            to="/overview"
            aria-current={location.pathname === '/overview' ? 'page' : undefined}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold transition ${
              location.pathname === '/overview'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-700 hover:bg-sky-100/80 hover:text-sky-950'
            }`}
          >
            <span>📊</span> Overview
          </Link>

          {navGroups.map((group) => (
            <details
              key={group.name}
              open={group.paths.some(({ path }) => location.pathname.startsWith(path))}
              className="group rounded-lg"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-sky-900/70 hover:bg-sky-100/60 transition select-none">
                {group.name}
                <span aria-hidden="true" className="text-sky-600 transition-transform group-open:rotate-90">›</span>
              </summary>
              <div className="mt-1 space-y-0.5 pl-2">
                {group.paths.map((item) => {
                  const active = location.pathname.startsWith(item.path);
                  return (
                    <Link
                      key={item.name}
                      to={item.path}
                      aria-current={active ? 'page' : undefined}
                      className={`block rounded-lg px-3 py-2 text-sm font-medium transition ${
                        active
                          ? 'bg-sky-500 text-white shadow-xs font-semibold'
                          : 'text-slate-600 hover:bg-sky-100/70 hover:text-sky-950'
                      }`}
                    >
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            </details>
          ))}
        </nav>
      </aside>

      <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-50/70">
        <Outlet />
      </main>
    </div>
  );
}
