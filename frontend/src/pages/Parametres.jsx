/**
 * Page Paramètres — Sprint 13
 * Édition des paramètres système (super_admin uniquement pour write)
 */
import React, { useState, useEffect } from "react";
import { Settings, Edit, Save, X } from "lucide-react";
import { toast } from "sonner";

import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { Label } from "../components/ui/label";

import { getParametres, updateParametre } from "../services/parametresApi";
import { useAuth } from "../hooks/useAuth";

export default function Parametres() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";

  const [params, setParams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState({}); // { cle: nouvelle_valeur }
  const [saving, setSaving] = useState({});

  const fetch = async () => {
    setLoading(true);
    try {
      setParams(await getParametres());
    } catch (e) { toast.error("Erreur chargement paramètres"); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetch(); }, []);

  const handleSave = async (cle) => {
    const valeur = editing[cle];
    if (!valeur && valeur !== "0") { toast.error("Valeur vide"); return; }
    setSaving({ ...saving, [cle]: true });
    try {
      await updateParametre(cle, valeur);
      toast.success(`Paramètre "${cle}" mis à jour`);
      const newEditing = { ...editing }; delete newEditing[cle]; setEditing(newEditing);
      fetch();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Erreur");
    } finally {
      setSaving({ ...saving, [cle]: false });
    }
  };

  const startEdit = (p) => setEditing({ ...editing, [p.cle]: p.valeur });
  const cancelEdit = (cle) => {
    const newEditing = { ...editing }; delete newEditing[cle]; setEditing(newEditing);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="parametres-page">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">Paramètres système</h1>
          <p className="text-gray-600 dark:text-white/60 mt-1">
            Configuration entreprise, TVA, banques, seuils
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center"><Settings className="h-5 w-5 mr-2" /> Liste des paramètres</CardTitle>
            <CardDescription>{isSuperAdmin ? "Modifiable par le super_admin." : "Lecture seule."}</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-32 w-full" /> : params.length === 0 ? (
              <div className="text-center py-12 text-gray-500">Aucun paramètre</div>
            ) : (
              <div className="space-y-3">
                {params.map((p) => {
                  const isEditing = p.cle in editing;
                  return (
                    <div key={p.cle} className="border rounded-lg p-4" data-testid={`param-${p.cle}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <Label className="font-mono text-xs text-gray-500">{p.cle}</Label>
                          <p className="text-sm text-gray-600 dark:text-white/60">{p.description}</p>
                        </div>
                        {isSuperAdmin && !isEditing && (
                          <Button size="sm" variant="ghost" onClick={() => startEdit(p)} data-testid={`btn-edit-${p.cle}`}>
                            <Edit className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                      {isEditing ? (
                        <div className="flex gap-2">
                          <Input
                            value={editing[p.cle]}
                            onChange={(e) => setEditing({ ...editing, [p.cle]: e.target.value })}
                            className="flex-1"
                            data-testid={`input-${p.cle}`}
                          />
                          <Button size="sm" onClick={() => handleSave(p.cle)} disabled={saving[p.cle]} className="bg-[#FF6200] hover:bg-[#E55900]" data-testid={`btn-save-${p.cle}`}>
                            <Save className="h-3 w-3" />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => cancelEdit(p.cle)}>
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ) : (
                        <div className="font-medium text-[#0A2540] dark:text-white">{p.valeur}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
