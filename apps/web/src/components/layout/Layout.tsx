import { Link, Outlet, useLocation } from 'react-router-dom';
import SimulatedBadge from '../common/SimulatedBadge';

const navItems = [
  { name: 'Overview', path: '/overview' },
  { name: 'Flood Risk Map', path: '/map' },
  { name: 'Forecast', path: '/forecast' },
  { name: 'Evidence', path: '/evidence' },
  { name: 'RCA', path: '/rca' },
  { name: 'Recommendations', path: '/recommendations' },
  { name: 'Human Review', path: '/review' },
  { name: 'Alerts', path: '/alerts' },
  { name: 'Routing', path: '/routing' },
  { name: 'Audit', path: '/audit' },
  { name: 'Quality', path: '/quality' },
];

export default function Layout() {
  const location = useLocation();
  
  return (
    <div className="flex h-screen bg-slate-900 text-slate-200">
      <aside className="w-64 border-r border-slate-700 flex flex-col bg-slate-900">
        <div className="p-4 border-b border-slate-700 flex flex-col gap-2">
          <h1 className="text-xl font-bold text-white">AquaRizz</h1>
          <span className="text-xs text-slate-400">Flood Early Warning System</span>
          <SimulatedBadge />
        </div>
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`block px-3 py-2 rounded-md text-sm font-medium ${
                location.pathname.startsWith(item.path)
                  ? 'bg-aqua-900 text-white'
                  : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              {item.name}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
