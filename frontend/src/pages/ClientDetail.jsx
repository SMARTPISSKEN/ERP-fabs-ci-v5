import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Pencil, PowerOff, Phone, Mail, MapPin, Wallet, FileText, ShoppingCart,
  CreditCard, History, AlertCircle, Calendar,
} from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import ClientFormDialog from "../components/clients/ClientFormDialog";
import { getClient, disableClient, TYPE_COLOR } from "../services/clientsApi";
import { formatFCFA } from "../utils/format";
import { useAuth } from "../hooks/useAuth";

const TABS = [
  { key: "info",      label: "Informations", icon: FileText },
  { key: "commandes", label: "Commandes",    icon: ShoppingCart },
  { key: "factures",  label: "Factures",     icon: FileText },
  { key: "paiements", label: "Paiements",    icon: CreditCard },
  { key: "historique",label: "Historique",   icon: History },
];

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { role } = useAuth();
  const canWrite = ["super_admin", "directeur_general", "directeur_commercial", "secretariat"].includes(role);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("info");
  const [edit, setEdit] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await getClient(id);
      setClient(r);
    } catch (e) {
      setError(e?.response?.data?.detail || "Client introuvable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleDisable = async () => {
    if (!window.confirm(`Désactiver le client "${client.nom}" ?`)) return;
    try {
      const updated = await disableClient(client.client_id);
      toast.success(`${updated.nom} désactivé`);
      setClient(updated);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Échec de la désactivation");
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="text-sm text-gray-500 dark:text-white/50 p-8">Chargement…</div>
      </DashboardLayout>
    );
  }

  if (error || !client) {
    return (
      <DashboardLayout>
        <div className="bg-red-50 border border-[#C62828]/30 text-[#C62828] rounded-lg p-4 text-sm flex items-center gap-2 max-w-2xl">
          <AlertCircle className="w-4 h-4" />
          {error || "Client introuvable"}
          <button onClick={() => navigate("/clients")} className="ml-auto text-xs font-semibold underline">
            ← Retour à la liste
          </button>
        </div>
      </DashboardLayout>
    );
  }

  const type = TYPE_COLOR[client.type_client] || TYPE_COLOR.particulier;
  const encours = client.solde || 0;

  return (
    <DashboardLayout>
      <div data-testid="client-detail-page" className="max-w-6xl mx-auto">
        {/* Back */}
        <button
          data-testid="client-detail-back"
          onClick={() => navigate("/clients")}
          className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-white/50 hover:text-[#FF6200] transition-colors mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Liste des clients
        </button>

        {/* Header card */}
        <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-6 shadow-sm">
          <div className="flex flex-wrap items-start gap-4 justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center flex-wrap gap-3">
                <span
                  className="inline-flex items-center text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded"
                  style={{ background: type.bg, color: type.color }}
                >
                  {type.label}
                </span>
                <span className="font-mono text-xs text-gray-500 dark:text-white/50">
                  {client.reference}
                </span>
                {!client.actif && (
                  <span className="text-[10px] uppercase tracking-wider bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-white/60 px-2 py-0.5 rounded">
                    Désactivé
                  </span>
                )}
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-[#0A2540] dark:text-white mt-2">
                {client.nom}
              </h1>
              <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-600 dark:text-white/70">
                {client.telephone && (
                  <span className="inline-flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-[#FF6200]" />
                    {client.telephone}
                  </span>
                )}
                {client.email && (
                  <span className="inline-flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-[#FF6200]" />
                    {client.email}
                  </span>
                )}
                {client.ville && (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[#FF6200]" />
                    {client.ville}
                  </span>
                )}
              </div>
            </div>
            {canWrite && client.actif && (
              <div className="flex gap-2">
                <button
                  data-testid="client-detail-edit"
                  onClick={() => setEdit(true)}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-[#0A2540] dark:text-white bg-gray-100 dark:bg-white/10 hover:bg-gray-200 dark:hover:bg-white/20"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  Modifier
                </button>
                <button
                  data-testid="client-detail-disable"
                  onClick={handleDisable}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-[#C62828] bg-[#C62828]/10 hover:bg-[#C62828]/20"
                >
                  <PowerOff className="w-3.5 h-3.5" />
                  Désactiver
                </button>
              </div>
            )}
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-100 dark:border-white/10">
            <KPI icon={Wallet} accent="#C62828" label="Encours total" value={formatFCFA(encours)} />
            <KPI icon={CreditCard} accent="#2E7D32" label="Plafond crédit" value={formatFCFA(client.plafond_credit)} />
            <KPI icon={Calendar} accent="#0A2540" label="Créé le" value={new Date(client.created_at).toLocaleDateString("fr-FR")} />
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-6">
          <div data-testid="client-detail-tabs" className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-white/10">
            {TABS.map(({ key, label, icon: Icon }) => {
              const active = key === tab;
              return (
                <button
                  key={key}
                  data-testid={`client-detail-tab-${key}`}
                  onClick={() => setTab(key)}
                  className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
                    active
                      ? "border-[#FF6200] text-[#FF6200]"
                      : "border-transparent text-gray-500 dark:text-white/60 hover:text-[#0A2540] dark:hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              );
            })}
          </div>

          <div className="mt-5">
            {tab === "info" && <InfoTab client={client} />}
            {tab !== "info" && (
              <div
                data-testid={`client-detail-empty-${tab}`}
                className="bg-white dark:bg-white/5 rounded-xl border border-dashed border-gray-200 dark:border-white/10 p-10 text-center"
              >
                <p className="text-[11px] uppercase tracking-[0.2em] text-[#FF6200] font-semibold">
                  Bientôt
                </p>
                <p className="text-sm text-gray-600 dark:text-white/60 mt-2">
                  Cet onglet sera alimenté par le module {TABS.find((t) => t.key === tab).label} (Sprints suivants).
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <ClientFormDialog
        open={edit}
        onClose={() => setEdit(false)}
        client={client}
        onSaved={(saved) => {
          setClient(saved);
          setEdit(false);
        }}
      />
    </DashboardLayout>
  );
}

function KPI({ icon: Icon, accent, label, value }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center"
        style={{ background: `${accent}18` }}
      >
        <Icon className="w-5 h-5" style={{ color: accent }} />
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-white/50">
          {label}
        </p>
        <p className="text-base font-bold text-[#0A2540] dark:text-white mt-0.5">{value}</p>
      </div>
    </div>
  );
}

function InfoTab({ client }) {
  const rows = [
    ["Référence", client.reference],
    ["Type",      TYPE_COLOR[client.type_client]?.label || client.type_client],
    ["Téléphone", client.telephone || "—"],
    ["Email",     client.email || "—"],
    ["Adresse",   client.adresse || "—"],
    ["Ville",     client.ville || "—"],
    ["Plafond crédit", formatFCFA(client.plafond_credit)],
    ["Solde / Encours", formatFCFA(client.solde)],
    ["Notes",     client.notes || "—"],
    ["Créé le",   new Date(client.created_at).toLocaleString("fr-FR")],
    ["Mis à jour le", new Date(client.updated_at).toLocaleString("fr-FR")],
  ];
  return (
    <div
      data-testid="client-detail-info"
      className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-6 shadow-sm"
    >
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 dark:text-white/50">
              {k}
            </dt>
            <dd className="text-sm text-[#0A2540] dark:text-white mt-1 break-words">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
