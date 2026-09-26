import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Analyze } from "./pages/Analyze";
import { DevDashboard } from "./pages/DevDashboard";
import { DevMyReports, DevReport } from "./pages/DevReport";
import { Home } from "./pages/Home";
import { HotspotDetail } from "./pages/HotspotDetail";
import { Languages } from "./pages/Languages";
import { SchemeDetail } from "./pages/SchemeDetail";
import { SchemesAsk } from "./pages/SchemesAsk";
import { SchemesDiscover } from "./pages/SchemesDiscover";
import { StaySafe } from "./pages/StaySafe";

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/schemes" element={<SchemesAsk />} />
        <Route path="/schemes/discover" element={<SchemesDiscover />} />
        <Route path="/schemes/:id" element={<SchemeDetail />} />
        <Route path="/dev" element={<DevDashboard />} />
        <Route path="/dev/report" element={<DevReport />} />
        <Route path="/dev/my-reports" element={<DevMyReports />} />
        <Route path="/dev/hotspots/:id" element={<HotspotDetail />} />
        <Route path="/languages" element={<Languages />} />
        <Route path="/safety" element={<StaySafe />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
