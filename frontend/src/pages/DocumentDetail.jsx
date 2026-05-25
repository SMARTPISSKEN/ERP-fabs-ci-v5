import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Calendar,
  User,
  Phone,
  MapPin,
  Package,
  DollarSign,
  Download,
  Printer,
  Share2,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { documentsAiApi } from "../services/documentsAiApi";

export default function DocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocument();
  }, [id]);

  const fetchDocument = async () => {
    try {
      setLoading(true);
      const data = await documentsAiApi.getDocument(id);
      setDocument(data);
    } catch (error) {
      console.error("Erreur lors du chargement du document:", error);
      toast.error("Erreur lors du chargement du document");
      navigate("/documents");
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = () => {
    toast.info("Génération du PDF en cours...");
    // TODO: Implémenter la génération de PDF
  };

  const handleShareWhatsApp = () => {
    const message = `Document ${document.reference || document.nom_fichier}`;
    const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(url, "_blank");
  };

  const handleDelete = async () => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer ce document ?")) {
      return;
    }

    try {
      await documentsAiApi.deleteDocument(id);
      toast.success("Document supprimé avec succès");
      navigate("/documents");
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      toast.error("Erreur lors de la suppression du document");
    }
  };

  const getTypeBadgeColor = (code) => {
    const colors = {
      BON_LIVRAISON: "bg-blue-500",
      FACTURE: "bg-green-500",
      COMMANDE: "bg-orange-500",
      LISTE_CLIENTS: "bg-purple-500",
      AUTRE: "bg-gray-500",
    };
    return colors[code] || "bg-gray-500";
  };

  const getStatutIcon = (statut) => {
    const icons = {
      traite: CheckCircle,
      en_attente: Clock,
      erreur: AlertCircle,
    };
    return icons[statut] || Clock;
  };

  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatCurrency = (amount) => {
    if (!amount) return "-";
    return new Intl.NumberFormat("fr-FR", {
      style: "decimal",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + " FCFA";
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-screen">
          <p className="text-gray-500">Chargement...</p>
        </div>
      </DashboardLayout>
    );
  }

  if (!document) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-screen">
          <p className="text-gray-500">Document introuvable</p>
        </div>
      </DashboardLayout>
    );
  }

  const data = document.donnees_extraites || {};
  const StatusIcon = getStatutIcon(document.statut);

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between print:hidden">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/documents")}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Retour
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-[#0A2540] dark:text-white">
                {document.nom_fichier}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {document.reference || "Aucune référence"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handlePrint}>
              <Printer className="w-4 h-4 mr-2" />
              Imprimer
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownloadPDF}>
              <Download className="w-4 h-4 mr-2" />
              PDF
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleShareWhatsApp}
              className="bg-green-600 text-white hover:bg-green-700"
            >
              <Share2 className="w-4 h-4 mr-2" />
              WhatsApp
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              className="text-red-600 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Colonne principale */}
          <div className="lg:col-span-2 space-y-6">
            {/* En-tête du document */}
            <Card className="print:shadow-none">
              <CardHeader className="bg-gradient-to-r from-[#0A2540] to-[#0A2540]/80 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-2xl">EDITIONS FABS-CI</CardTitle>
                    <CardDescription className="text-gray-200 mt-1">
                      « Les livres sont des fenêtres par lesquelles on regarde le
                      monde »
                    </CardDescription>
                  </div>
                  <Badge
                    className={`${getTypeBadgeColor(
                      document.type_document
                    )} text-white text-sm px-3 py-1`}
                  >
                    {document.type_document.replace("_", " ")}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Référence
                    </p>
                    <p className="text-lg font-semibold font-mono text-[#0A2540] dark:text-white">
                      {document.reference || "-"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Date
                    </p>
                    <p className="text-lg font-semibold text-[#0A2540] dark:text-white">
                      {data.date || formatDate(document.created_at)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Informations Client */}
            {(data.client || data.type_client || data.representant) && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="w-5 h-5" />
                    Informations Client
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {data.client && (
                    <div className="flex items-center gap-3">
                      <User className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Client
                        </p>
                        <p className="font-semibold text-[#0A2540] dark:text-white">
                          {data.client}
                        </p>
                      </div>
                    </div>
                  )}
                  {data.type_client && (
                    <div className="flex items-center gap-3">
                      <Package className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Type
                        </p>
                        <Badge variant="outline">{data.type_client}</Badge>
                      </div>
                    </div>
                  )}
                  {data.representant && (
                    <div className="flex items-center gap-3">
                      <User className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Représentant
                        </p>
                        <p className="font-semibold text-[#0A2540] dark:text-white">
                          {data.representant}
                        </p>
                      </div>
                    </div>
                  )}
                  {data.telephone && (
                    <div className="flex items-center gap-3">
                      <Phone className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Téléphone
                        </p>
                        <p className="font-semibold text-[#0A2540] dark:text-white">
                          {data.telephone}
                        </p>
                      </div>
                    </div>
                  )}
                  {data.adresse && (
                    <div className="flex items-center gap-3">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Adresse
                        </p>
                        <p className="font-semibold text-[#0A2540] dark:text-white">
                          {data.adresse}
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Tableau des articles */}
            {data.articles && data.articles.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Package className="w-5 h-5" />
                    Articles
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-800">
                        <tr>
                          {data.articles[0].classe && (
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                              Classe
                            </th>
                          )}
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                            Code
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                            Référence
                          </th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                            Qté
                          </th>
                          {data.articles[0].prix_unitaire && (
                            <>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                                P.U
                              </th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                                Total
                              </th>
                            </>
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {data.articles.map((article, index) => (
                          <tr key={index}>
                            {article.classe && (
                              <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
                                {article.classe}
                              </td>
                            )}
                            <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white">
                              {article.code}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                              {article.reference}
                            </td>
                            <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900 dark:text-white">
                              {article.quantite}
                            </td>
                            {article.prix_unitaire && (
                              <>
                                <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-300">
                                  {formatCurrency(article.prix_unitaire)}
                                </td>
                                <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900 dark:text-white">
                                  {formatCurrency(article.total)}
                                </td>
                              </>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Totaux (pour factures) */}
            {data.total_vente && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5" />
                    Totaux
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">
                        Total Vente
                      </span>
                      <span className="font-semibold text-[#0A2540] dark:text-white">
                        {formatCurrency(data.total_vente)}
                      </span>
                    </div>
                    {data.remise_pct > 0 && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">
                            Remise ({data.remise_pct}%)
                          </span>
                          <span className="font-semibold text-red-600">
                            - {formatCurrency(data.remise_montant)}
                          </span>
                        </div>
                        <Separator />
                      </>
                    )}
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">
                        Montant HT
                      </span>
                      <span className="font-semibold text-[#0A2540] dark:text-white">
                        {formatCurrency(data.montant_ht)}
                      </span>
                    </div>
                    <Separator />
                    <div className="flex justify-between text-lg">
                      <span className="font-bold text-gray-900 dark:text-white">
                        Solde Dû
                      </span>
                      <span className="font-bold text-[#FF6200]">
                        {formatCurrency(data.solde_du)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Colonne latérale */}
          <div className="space-y-6 print:hidden">
            {/* Métadonnées */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Métadonnées</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Statut
                  </p>
                  <div className="flex items-center gap-2">
                    <StatusIcon
                      className={`w-5 h-5 ${
                        document.statut === "traite"
                          ? "text-green-600"
                          : document.statut === "erreur"
                          ? "text-red-600"
                          : "text-orange-600"
                      }`}
                    />
                    <span className="font-semibold capitalize">
                      {document.statut.replace("_", " ")}
                    </span>
                  </div>
                </div>

                <Separator />

                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Créé le
                  </p>
                  <p className="text-sm font-semibold">
                    {formatDate(document.created_at)}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Modifié le
                  </p>
                  <p className="text-sm font-semibold">
                    {formatDate(document.updated_at)}
                  </p>
                </div>

                {document.taille_fichier && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                      Taille
                    </p>
                    <p className="text-sm font-semibold">
                      {(document.taille_fichier / 1024).toFixed(1)} KB
                    </p>
                  </div>
                )}

                {document.tags && document.tags.length > 0 && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                      Tags
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {document.tags.map((tag, index) => (
                        <Badge key={index} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions rapides */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  className="w-full justify-start"
                  variant="outline"
                  onClick={handlePrint}
                >
                  <Printer className="w-4 h-4 mr-2" />
                  Imprimer
                </Button>
                <Button
                  className="w-full justify-start"
                  variant="outline"
                  onClick={handleDownloadPDF}
                >
                  <Download className="w-4 h-4 mr-2" />
                  Télécharger PDF
                </Button>
                <Button
                  className="w-full justify-start bg-green-600 text-white hover:bg-green-700"
                  onClick={handleShareWhatsApp}
                >
                  <Share2 className="w-4 h-4 mr-2" />
                  Partager sur WhatsApp
                </Button>
                <Separator className="my-2" />
                <Button
                  className="w-full justify-start text-red-600 hover:bg-red-50"
                  variant="outline"
                  onClick={handleDelete}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Supprimer
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
