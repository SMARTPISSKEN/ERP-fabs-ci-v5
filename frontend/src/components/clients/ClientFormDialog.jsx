import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, X, Save } from "lucide-react";
import { toast } from "sonner";

import { TYPE_CLIENTS, createClient, updateClient } from "../../services/clientsApi";
import DuplicateWarning from "./DuplicateWarning";

const ClientSchema = z.object({
  nom: z.string().min(2, "Nom trop court").max(120),
  type_client: z.enum(["librairie", "ecole", "particulier", "distributeur", "representant"]),
  representant: z.string().min(2, "Le nom du représentant est obligatoire").max(120),
  representative_id: z.string().optional().or(z.literal("")),
  telephone: z.string().max(40).optional().or(z.literal("")),
  email: z.string().email("Email invalide").optional().or(z.literal("")),
  adresse: z.string().max(240).optional().or(z.literal("")),
  ville: z.string().max(80).optional().or(z.literal("")),
  plafond_credit: z.coerce.number().min(0, "Doit être ≥ 0").default(0),
  notes: z.string().max(600).optional().or(z.literal("")),
});

export default function ClientFormDialog({ open, onClose, onSaved, client }) {
  const editing = Boolean(client);
  const [submitting, setSubmitting] = useState(false);
  const [matches, setMatches] = useState([]);
  const [representants, setRepresentants] = useState([]);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(ClientSchema),
    defaultValues: {
      nom: "",
      type_client: "librairie",
      representant: "",
      representative_id: "",
      telephone: "",
      email: "",
      adresse: "",
      ville: "",
      plafond_credit: 0,
      notes: "",
    },
  });

  useEffect(() => {
    if (!open) return;
    reset({
      nom: client?.nom || "",
      type_client: client?.type_client || "librairie",
      representant: client?.representant || "",
      representative_id: client?.representative_id || "",
      telephone: client?.telephone || "",
      email: client?.email || "",
      adresse: client?.adresse || "",
      ville: client?.ville || "",
      plafond_credit: client?.plafond_credit || 0,
      notes: client?.notes || "",
    });
    setMatches([]);
    
    // Charger les représentants
    fetchRepresentants();
  }, [open, client, reset]);

  const fetchRepresentants = async () => {
    try {
      const { listClients } = await import("../../services/clientsApi");
      const data = await listClients({ type_client: "representant", actif: true, page_size: 100 });
      setRepresentants(Array.isArray(data) ? data : (data?.items || []));
    } catch (error) {
      console.error("Erreur chargement représentants:", error);
    }
  };

  if (!open) return null;

  const nomLive = watch("nom") || "";
  const phoneLive = watch("telephone") || "";

  const submit = async (values, { force = false } = {}) => {
    setSubmitting(true);
    try {
      // strip empty strings -> null/undefined
      const payload = Object.fromEntries(
        Object.entries(values).map(([k, v]) => [k, v === "" ? null : v])
      );
      if (editing) {
        const saved = await updateClient(client.client_id, payload);
        toast.success(`Client ${saved.reference} mis à jour`);
        onSaved?.(saved);
      } else {
        const saved = await createClient(payload, { force });
        toast.success(`Client ${saved.reference} créé`);
        onSaved?.(saved);
      }
      onClose?.();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (e?.response?.status === 409 && detail?.code === "DUPLICATE_SUSPECTED") {
        toast.error("Doublon détecté", {
          description: `${detail.matches.length} client(s) similaire(s). Confirmez la création pour passer outre.`,
          action: {
            label: "Créer quand même",
            onClick: () => submit(values, { force: true }),
          },
        });
      } else {
        const msg = typeof detail === "string" ? detail : "Échec de l'enregistrement";
        toast.error(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="client-form-dialog"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/50"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div className="bg-white dark:bg-[#0A2540] w-full sm:max-w-2xl sm:rounded-2xl rounded-t-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-[#0A2540] border-b border-gray-100 dark:border-white/10 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-[#FF6200] font-semibold">
              {editing ? "Modification" : "Nouveau client"}
            </p>
            <h2 className="text-xl font-bold text-[#0A2540] dark:text-white tracking-tight mt-0.5">
              {editing ? client.nom : "Création d'un client"}
            </h2>
          </div>
          <button
            data-testid="client-form-close"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-white/60"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form
          onSubmit={handleSubmit((v) => submit(v))}
          className="px-6 py-5 space-y-5"
          noValidate
        >
          {/* Duplicate live check */}
          <DuplicateWarning
            nom={nomLive}
            telephone={phoneLive}
            excludeId={editing ? client.client_id : null}
            onMatchesChange={setMatches}
          />

          {/* Nom + Type */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Label htmlFor="nom">Nom du client *</Label>
              <input
                id="nom"
                data-testid="client-form-nom"
                {...register("nom")}
                className={inputCls(errors.nom)}
                placeholder="Ex : Librairie de France"
                autoFocus
              />
              {errors.nom && <Err msg={errors.nom.message} />}
            </div>
            <div>
              <Label htmlFor="type_client">Type *</Label>
              <select
                id="type_client"
                data-testid="client-form-type"
                {...register("type_client")}
                className={inputCls(errors.type_client)}
              >
                {TYPE_CLIENTS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Champ Représentant (obligatoire — saisie libre) */}
            <div>
              <Label htmlFor="representant">Représentant *</Label>
              <input
                id="representant"
                data-testid="client-form-representant"
                {...register("representant")}
                className={inputCls(errors.representant)}
                placeholder="Ex : M. KOUASSI"
              />
              {errors.representant && <Err msg={errors.representant.message} />}
            </div>
          </div>

          {/* Représentant lié (legacy — optionnel) */}
          {representants.length > 0 && (
            <div>
              <Label htmlFor="representative_id">Lier à un compte représentant <span className="text-gray-400 text-xs">(optionnel)</span></Label>
              <select
                {...register("representative_id")}
                id="representative_id"
                data-testid="client-form-representative-id"
                className={inputCls(errors.representative_id)}
              >
                <option value="">-- Aucun --</option>
                {representants.map((rep) => (
                  <option key={rep.client_id} value={rep.client_id}>
                    {rep.nom} {rep.reference ? `(${rep.reference})` : ""}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Téléphone + Email */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="telephone">Téléphone</Label>
              <input
                id="telephone"
                data-testid="client-form-telephone"
                {...register("telephone")}
                className={inputCls(errors.telephone)}
                placeholder="+225 07 ..."
              />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <input
                id="email"
                type="email"
                data-testid="client-form-email"
                {...register("email")}
                className={inputCls(errors.email)}
                placeholder="contact@..."
              />
              {errors.email && <Err msg={errors.email.message} />}
            </div>
          </div>

          {/* Adresse + Ville */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Label htmlFor="adresse">Adresse</Label>
              <input
                id="adresse"
                data-testid="client-form-adresse"
                {...register("adresse")}
                className={inputCls(errors.adresse)}
                placeholder="Quartier, immeuble..."
              />
            </div>
            <div>
              <Label htmlFor="ville">Ville</Label>
              <input
                id="ville"
                data-testid="client-form-ville"
                {...register("ville")}
                className={inputCls(errors.ville)}
                placeholder="Abidjan"
              />
            </div>
          </div>

          {/* Plafond crédit */}
          <div>
            <Label htmlFor="plafond_credit">Plafond crédit (FCFA)</Label>
            <input
              id="plafond_credit"
              type="number"
              min={0}
              step={1000}
              data-testid="client-form-plafond"
              {...register("plafond_credit")}
              className={inputCls(errors.plafond_credit)}
            />
            {errors.plafond_credit && <Err msg={errors.plafond_credit.message} />}
          </div>

          {/* Notes */}
          <div>
            <Label htmlFor="notes">Notes</Label>
            <textarea
              id="notes"
              rows={3}
              data-testid="client-form-notes"
              {...register("notes")}
              className={inputCls(errors.notes)}
              placeholder="Informations internes..."
            />
          </div>

          {/* Actions */}
          <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 pt-3 border-t border-gray-100 dark:border-white/10">
            <button
              type="button"
              data-testid="client-form-cancel"
              onClick={onClose}
              className="px-4 py-2.5 rounded-lg text-sm font-semibold text-[#0A2540] dark:text-white hover:bg-gray-100 dark:hover:bg-white/10"
            >
              Annuler
            </button>
            <button
              type="submit"
              data-testid="client-form-submit"
              disabled={submitting}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#FF6200] hover:bg-[#E65800] disabled:opacity-60 text-white text-sm font-semibold shadow-md hover:shadow-lg transition"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {editing ? "Enregistrer" : matches.length ? "Créer malgré l'alerte" : "Créer le client"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const Label = ({ children, htmlFor }) => (
  <label
    htmlFor={htmlFor}
    className="block text-[11px] uppercase tracking-wider font-semibold text-[#0A2540]/70 dark:text-white/60 mb-1.5"
  >
    {children}
  </label>
);

const Err = ({ msg }) => (
  <p className="text-[11px] text-[#C62828] mt-1">{msg}</p>
);

const inputCls = (hasErr) =>
  `w-full px-3 py-2.5 text-sm rounded-lg bg-white dark:bg-white/5 border ${
    hasErr ? "border-[#C62828]" : "border-gray-200 dark:border-white/10"
  } text-[#0A2540] dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200]`;
