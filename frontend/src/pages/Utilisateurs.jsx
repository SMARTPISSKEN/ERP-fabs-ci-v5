/**
 * Page Utilisateurs — Sprint 13
 * Le super_admin peut créer, modifier le rôle, réinitialiser le mot de passe,
 * activer/désactiver les utilisateurs.
 */
import React, { useState, useEffect } from "react";
import { UserCog, Edit, Plus, KeyRound } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import { Switch } from "../components/ui/switch";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";

import {
  getUtilisateurs,
  updateUtilisateur,
  createUtilisateurWithPassword,
  resetUserPassword,
} from "../services/utilisateursApi";
import { useAuth } from "../hooks/useAuth";

const ROLES = [
  "super_admin",
  "directeur_general",
  "comptable",
  "directeur_commercial",
  "gestionnaire_stock",
  "responsable_magasinier",
  "secretariat",
  "service_logistique",
];
const ROLE_COLORS = {
  super_admin: "bg-red-600",
  directeur_general: "bg-purple-600",
  comptable: "bg-blue-600",
  directeur_commercial: "bg-green-600",
  gestionnaire_stock: "bg-orange-500",
  responsable_magasinier: "bg-yellow-500",
  secretariat: "bg-gray-500",
  service_logistique: "bg-cyan-600",
};

export default function Utilisateurs() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState(null);
  const [resettingUser, setResettingUser] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      setUsers(await getUtilisateurs());
    } catch (e) {
      toast.error("Erreur chargement utilisateurs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleToggleActif = async (u) => {
    try {
      await updateUtilisateur(u.user_id, { actif: !u.actif });
      toast.success(`Utilisateur ${!u.actif ? "activé" : "désactivé"}`);
      fetchUsers();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="utilisateurs-page">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Utilisateurs</h1>
            <p className="text-gray-600 dark:text-white/60 mt-1">
              {users.length} utilisateur·trice·s · {isSuperAdmin ? "Gestion complète" : "Lecture seule"}
            </p>
          </div>
          {isSuperAdmin && (
            <Button
              onClick={() => setShowCreate(true)}
              className="bg-[#FF6200] hover:bg-[#E55900] text-white"
              data-testid="btn-nouvel-utilisateur"
            >
              <Plus className="h-4 w-4 mr-2" /> Nouvel utilisateur
            </Button>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center"><UserCog className="h-5 w-5 mr-2" /> Liste des utilisateurs</CardTitle>
            <CardDescription>
              {isSuperAdmin
                ? "Créez de nouveaux comptes, modifiez les rôles, réinitialisez les mots de passe."
                : "Lecture seule — réservée au super_admin."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-32 w-full" /> : users.length === 0 ? (
              <div className="text-center py-12 text-gray-500">Aucun utilisateur</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left">
                      <th className="pb-3 font-semibold">Nom complet</th>
                      <th className="pb-3 font-semibold">Email</th>
                      <th className="pb-3 font-semibold">Rôle</th>
                      <th className="pb-3 font-semibold">Actif</th>
                      <th className="pb-3 font-semibold">Créé le</th>
                      <th className="pb-3 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.user_id} className="border-b" data-testid={`row-user-${u.email}`}>
                        <td className="py-3 font-medium">{u.nom_complet}</td>
                        <td className="py-3 text-sm text-gray-500">{u.email}</td>
                        <td className="py-3">
                          <Badge className={`${ROLE_COLORS[u.role]} text-white`}>{u.role}</Badge>
                        </td>
                        <td className="py-3">
                          <Switch
                            checked={u.actif}
                            disabled={!isSuperAdmin}
                            onCheckedChange={() => handleToggleActif(u)}
                            data-testid={`switch-actif-${u.email}`}
                          />
                        </td>
                        <td className="py-3 text-sm text-gray-500">{new Date(u.created_at).toLocaleDateString("fr-FR")}</td>
                        <td className="py-3">
                          {isSuperAdmin && (
                            <div className="flex gap-1">
                              <Button size="sm" variant="outline" onClick={() => setEditingUser(u)} data-testid={`btn-edit-${u.email}`}>
                                <Edit className="h-3 w-3 mr-1" /> Modifier
                              </Button>
                              <Button size="sm" variant="outline" onClick={() => setResettingUser(u)} data-testid={`btn-reset-pw-${u.email}`}>
                                <KeyRound className="h-3 w-3 mr-1" /> Mot de passe
                              </Button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {editingUser && (
          <EditUserDialog
            user={editingUser}
            onClose={() => setEditingUser(null)}
            onSaved={() => { setEditingUser(null); fetchUsers(); }}
          />
        )}
        {resettingUser && (
          <ResetPasswordDialog
            user={resettingUser}
            onClose={() => setResettingUser(null)}
          />
        )}
        {showCreate && (
          <CreateUserDialog
            onClose={() => setShowCreate(false)}
            onCreated={() => { setShowCreate(false); fetchUsers(); }}
          />
        )}
      </div>
    </DashboardLayout>
  );
}

function CreateUserDialog({ onClose, onCreated }) {
  const [form, setForm] = useState({
    email: "",
    password: "",
    nom_complet: "",
    role: "secretariat",
    actif: true,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.email || !form.password || !form.nom_complet) {
      toast.error("Email, mot de passe et nom requis"); return;
    }
    if (form.password.length < 6) {
      toast.error("Mot de passe : 6 caractères minimum"); return;
    }
    try {
      setSaving(true);
      await createUtilisateurWithPassword(form);
      toast.success(`Utilisateur ${form.email} créé`);
      onCreated();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur création");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent data-testid="dialog-create-user">
        <DialogHeader>
          <DialogTitle>Nouvel utilisateur</DialogTitle>
          <DialogDescription>
            Créer un compte avec email + mot de passe. L'utilisateur pourra se connecter immédiatement.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Nom complet *</Label>
            <Input
              placeholder="Prénom NOM"
              value={form.nom_complet}
              onChange={(e) => setForm({ ...form, nom_complet: e.target.value })}
              data-testid="create-nom"
            />
          </div>
          <div>
            <Label>Email *</Label>
            <Input
              type="email"
              placeholder="prenom@editionsfabsci.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              data-testid="create-email"
            />
          </div>
          <div>
            <Label>Mot de passe * (6 caractères min)</Label>
            <Input
              type="text"
              placeholder="Mot de passe initial"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              data-testid="create-password"
            />
          </div>
          <div>
            <Label>Rôle *</Label>
            <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
              <SelectTrigger data-testid="create-role"><SelectValue /></SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Annuler</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-create-user">
            {saving ? "Création..." : "Créer l'utilisateur"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditUserDialog({ user, onClose, onSaved }) {
  const [nomComplet, setNomComplet] = useState(user.nom_complet);
  const [role, setRole] = useState(user.role);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    try {
      setSaving(true);
      await updateUtilisateur(user.user_id, { nom_complet: nomComplet, role });
      toast.success("Utilisateur mis à jour");
      onSaved();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent data-testid="dialog-edit-user">
        <DialogHeader>
          <DialogTitle>Modifier l'utilisateur</DialogTitle>
          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Nom complet</Label>
            <Input value={nomComplet} onChange={(e) => setNomComplet(e.target.value)} data-testid="edit-nom" />
          </div>
          <div>
            <Label>Rôle</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger data-testid="edit-role"><SelectValue /></SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Annuler</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-user">
            {saving ? "Enregistrement..." : "Enregistrer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordDialog({ user, onClose }) {
  const [pw, setPw] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (pw.length < 6) {
      toast.error("Mot de passe : 6 caractères minimum"); return;
    }
    try {
      setSaving(true);
      await resetUserPassword(user.user_id, pw);
      toast.success(`Mot de passe réinitialisé pour ${user.email}`);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent data-testid="dialog-reset-pw">
        <DialogHeader>
          <DialogTitle>Réinitialiser le mot de passe</DialogTitle>
          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Nouveau mot de passe (6 caractères min)</Label>
            <Input
              type="text"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              data-testid="reset-pw-input"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Annuler</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid="btn-save-reset-pw">
            {saving ? "Mise à jour..." : "Réinitialiser"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
