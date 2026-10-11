import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';

const Overview = lazy(() => import('./pages/Overview'));
const FloodRiskMap = lazy(() => import('./pages/FloodRiskMap'));
const WardDetail = lazy(() => import('./pages/WardDetail'));
const Forecast = lazy(() => import('./pages/Forecast'));
const Evidence = lazy(() => import('./pages/Evidence'));
const RCA = lazy(() => import('./pages/RCA'));
const Recommendation = lazy(() => import('./pages/Recommendation'));
const Routing = lazy(() => import('./pages/Routing'));
const Audit = lazy(() => import('./pages/Audit'));
const DataModelQuality = lazy(() => import('./pages/DataModelQuality'));
const HumanReview = lazy(() => import('./pages/HumanReview'));
const AlertSimulation = lazy(() => import('./pages/AlertSimulation'));

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<Suspense fallback={<PageLoading />}><Overview /></Suspense>} />
        <Route path="map" element={<Suspense fallback={<PageLoading />}><FloodRiskMap /></Suspense>} />
        <Route path="wards/:wardId" element={<Suspense fallback={<PageLoading />}><WardDetail /></Suspense>} />
        <Route path="forecast" element={<Suspense fallback={<PageLoading />}><Forecast /></Suspense>} />
        <Route path="evidence/:assessmentId?" element={<Suspense fallback={<PageLoading />}><Evidence /></Suspense>} />
        <Route path="rca/:assessmentId?" element={<Suspense fallback={<PageLoading />}><RCA /></Suspense>} />
        <Route path="recommendations" element={<Suspense fallback={<PageLoading />}><Recommendation /></Suspense>} />
        <Route path="routing" element={<Suspense fallback={<PageLoading />}><Routing /></Suspense>} />
        <Route path="review" element={<Suspense fallback={<PageLoading />}><HumanReview /></Suspense>} />
        <Route path="alerts" element={<Suspense fallback={<PageLoading />}><AlertSimulation /></Suspense>} />
        <Route path="audit" element={<Suspense fallback={<PageLoading />}><Audit /></Suspense>} />
        <Route path="quality" element={<Suspense fallback={<PageLoading />}><DataModelQuality /></Suspense>} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}

function PageLoading() {
  return (
    <div className="rounded-2xl border border-sky-200 bg-white/90 p-8 text-sm text-sky-950 font-bold shadow-sm flex items-center justify-center gap-3" role="status" aria-live="polite">
      <div className="animate-spin rounded-full h-5 w-5 border-2 border-sky-600 border-t-transparent"></div>
      Loading console view…
    </div>
  );
}
