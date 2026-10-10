import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Overview from './pages/Overview';
import FloodRiskMap from './pages/FloodRiskMap';
import WardDetail from './pages/WardDetail';
import Forecast from './pages/Forecast';
import Evidence from './pages/Evidence';
import RCA from './pages/RCA';
import Recommendation from './pages/Recommendation';
import HumanReview from './pages/HumanReview';
import AlertSimulation from './pages/AlertSimulation';
import Routing from './pages/Routing';
import Audit from './pages/Audit';
import DataModelQuality from './pages/DataModelQuality';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<Overview />} />
        <Route path="map" element={<FloodRiskMap />} />
        <Route path="wards/:wardId" element={<WardDetail />} />
        <Route path="forecast" element={<Forecast />} />
        <Route path="evidence/:assessmentId?" element={<Evidence />} />
        <Route path="rca/:assessmentId?" element={<RCA />} />
        <Route path="recommendations" element={<Recommendation />} />
        <Route path="review" element={<HumanReview />} />
        <Route path="alerts" element={<AlertSimulation />} />
        <Route path="routing" element={<Routing />} />
        <Route path="audit" element={<Audit />} />
        <Route path="quality" element={<DataModelQuality />} />
      </Route>
    </Routes>
  );
}
