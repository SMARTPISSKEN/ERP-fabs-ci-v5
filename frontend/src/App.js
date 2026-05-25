import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth";
import ProtectedRoute from "./components/ProtectedRoute";

// Pages
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import ClientDetail from "./pages/ClientDetail";
import Produits from "./pages/Produits";
import ProduitDetail from "./pages/ProduitDetail";
import Commandes from "./pages/Commandes";
import CommandeDetail from "./pages/CommandeDetail";
import Factures from "./pages/Factures";
import FactureDetail from "./pages/FactureDetail";
import Paiements from "./pages/Paiements";
import PaiementDetail from "./pages/PaiementDetail";
import Stock from "./pages/Stock";
import BonsLivraison from "./pages/BonsLivraison";
import BonsRetour from "./pages/BonsRetour";
import Comptabilite from "./pages/Comptabilite";
import AnalyticsReports from "./pages/AnalyticsReports";
import Utilisateurs from "./pages/Utilisateurs";
import Parametres from "./pages/Parametres";
import Documents from "./pages/Documents";
import DocumentDetail from "./pages/DocumentDetail";
import NotFound from "./pages/NotFound";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            
            {/* Protected Routes */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            
            {/* Clients */}
            <Route
              path="/clients"
              element={
                <ProtectedRoute moduleKey="clients">
                  <Clients />
                </ProtectedRoute>
              }
            />
            <Route
              path="/clients/:id"
              element={
                <ProtectedRoute moduleKey="clients">
                  <ClientDetail />
                </ProtectedRoute>
              }
            />
            
            {/* Produits */}
            <Route
              path="/produits"
              element={
                <ProtectedRoute moduleKey="produits">
                  <Produits />
                </ProtectedRoute>
              }
            />
            <Route
              path="/produits/:id"
              element={
                <ProtectedRoute moduleKey="produits">
                  <ProduitDetail />
                </ProtectedRoute>
              }
            />
            
            {/* Commandes */}
            <Route
              path="/commandes"
              element={
                <ProtectedRoute moduleKey="commandes">
                  <Commandes />
                </ProtectedRoute>
              }
            />
            <Route
              path="/commandes/:id"
              element={
                <ProtectedRoute moduleKey="commandes">
                  <CommandeDetail />
                </ProtectedRoute>
              }
            />
            
            {/* Factures */}
            <Route
              path="/factures"
              element={
                <ProtectedRoute moduleKey="factures">
                  <Factures />
                </ProtectedRoute>
              }
            />
            <Route
              path="/factures/:id"
              element={
                <ProtectedRoute moduleKey="factures">
                  <FactureDetail />
                </ProtectedRoute>
              }
            />
            
            {/* Paiements */}
            <Route
              path="/paiements"
              element={
                <ProtectedRoute moduleKey="paiements">
                  <Paiements />
                </ProtectedRoute>
              }
            />
            <Route
              path="/paiements/:id"
              element={
                <ProtectedRoute moduleKey="paiements">
                  <PaiementDetail />
                </ProtectedRoute>
              }
            />
            
            {/* Stock */}
            <Route
              path="/stock"
              element={
                <ProtectedRoute moduleKey="stock">
                  <Stock />
                </ProtectedRoute>
              }
            />
            
            {/* Bons de Livraison */}
            <Route
              path="/livraisons"
              element={
                <ProtectedRoute moduleKey="livraisons">
                  <BonsLivraison />
                </ProtectedRoute>
              }
            />
            
            {/* Bons de Retour */}
            <Route
              path="/retours"
              element={
                <ProtectedRoute moduleKey="retours">
                  <BonsRetour />
                </ProtectedRoute>
              }
            />
            
            {/* Comptabilité */}
            <Route
              path="/comptabilite"
              element={
                <ProtectedRoute moduleKey="comptabilite">
                  <Comptabilite />
                </ProtectedRoute>
              }
            />
            
            {/* Rapports & Analytics */}
            <Route
              path="/rapports"
              element={
                <ProtectedRoute>
                  <AnalyticsReports />
                </ProtectedRoute>
              }
            />
            
            {/* Utilisateurs */}
            <Route
              path="/utilisateurs"
              element={
                <ProtectedRoute moduleKey="utilisateurs">
                  <Utilisateurs />
                </ProtectedRoute>
              }
            />
            
            {/* Paramètres */}
            <Route
              path="/parametres"
              element={
                <ProtectedRoute moduleKey="parametres">
                  <Parametres />
                </ProtectedRoute>
              }
            />
            
            {/* Documents AI */}
            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <Documents />
                </ProtectedRoute>
              }
            />
            <Route
              path="/documents/:id"
              element={
                <ProtectedRoute>
                  <DocumentDetail />
                </ProtectedRoute>
              }
            />
            
            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
