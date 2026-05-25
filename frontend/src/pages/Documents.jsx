import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  FileText, 
  Upload, 
  Search, 
  Filter,
  Eye,
  Download,
  Share2,
  BarChart3,
  Plus,
  Trash2,
  FileCheck,
  FileWarning,
  Clock
} from "lucide-react";
import { toast } from "sonner";
import DashboardLayout from "../components/layout/DashboardLayout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { documentsAiApi } from "../services/documentsAiApi";

export default function Documents() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    traites: 0,
    en_attente: 0,
  });

  // Filtres
  const [filters, setFilters] = useState({
    recherche: "",
    type_document: "",
    statut: "",
    page: 1,
    limit: 20
  });

  useEffect(() => {
    fetchTypes();
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [filters]);

  const fetchTypes = async () => {
    try {
      const data = await documentsAiApi.getTypes();
      setTypes(data.types || []);
    } catch (error) {
      console.error("Erreur lors du chargement des types:", error);
    }
  };

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const data = await documentsAiApi.getDocuments(filters);
      setDocuments(data.items || []);
      
      // Calculer les stats
      const total = data.total || 0;
      const traites = data.items?.filter(d => d.statut === "traite").length || 0;
      const en_attente = data.items?.filter(d => d.statut === "en_attente").length || 0;
      
      setStats({ total, traites, en_attente });
    } catch (error) {
      console.error("Erreur lors du chargement des documents:", error);
      toast.error("Erreur lors du chargement des documents");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    setFilters({ ...filters, recherche: e.target.value, page: 1 });
  };

  const handleTypeFilter = (value) => {
    setFilters({ ...filters, type_document: value === "__all__" ? "" : value, page: 1 });
  };

  const handleStatutFilter = (value) => {
    setFilters({ ...filters, statut: value === "__all__" ? "" : value, page: 1 });
  };

  const handleViewDocument = (documentId) => {
    navigate(`/documents/${documentId}`);
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer ce document ?")) {
      return;
    }

    try {
      await documentsAiApi.deleteDocument(documentId);
      toast.success("Document supprimé avec succès");
      fetchDocuments();
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      toast.error("Erreur lors de la suppression du document");
    }
  };

  const getTypeLabel = (code) => {
    const type = types.find(t => t.code === code);
    return type ? type.label : code;
  };

  const getTypeBadgeColor = (code) => {
    const colors = {
      BON_LIVRAISON: "bg-blue-500",
      FACTURE: "bg-green-500",
      COMMANDE: "bg-orange-500",
      LISTE_CLIENTS: "bg-purple-500",
      AUTRE: "bg-gray-500"
    };
    return colors[code] || "bg-gray-500";
  };

  const getStatutBadge = (statut) => {
    const badges = {
      traite: { icon: FileCheck, color: "bg-green-500", label: "Traité" },
      en_attente: { icon: Clock, color: "bg-orange-500", label: "En attente" },
      erreur: { icon: FileWarning, color: "bg-red-500", label: "Erreur" }
    };
    
    const badge = badges[statut] || badges.en_attente;
    const Icon = badge.icon;
    
    return (
      <Badge className={`${badge.color} text-white`}>
        <Icon className="w-3 h-3 mr-1" />
        {badge.label}
      </Badge>
    );
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "-";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <DashboardLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#0A2540] dark:text-white">
              Documents Intelligents
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Gestion automatisée des documents avec extraction de données
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={() => navigate("/documents/analytics")}
              variant="outline"
              className="gap-2"
            >
              <BarChart3 className="w-4 h-4" />
              Analytics
            </Button>
            <Button
              onClick={() => navigate("/documents/upload")}
              className="bg-[#FF6200] hover:bg-[#E55900] gap-2"
            >
              <Upload className="w-4 h-4" />
              Importer
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-[#0A2540] dark:text-white" />
                <p className="text-3xl font-bold text-[#0A2540] dark:text-white">
                  {stats.total}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Documents Traités
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <FileCheck className="w-8 h-8 text-green-600" />
                <p className="text-3xl font-bold text-green-600">
                  {stats.traites}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                En Attente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Clock className="w-8 h-8 text-orange-600" />
                <p className="text-3xl font-bold text-orange-600">
                  {stats.en_attente}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filtres */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filtres
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="Rechercher par nom, référence ou client..."
                    value={filters.recherche}
                    onChange={handleSearch}
                    className="pl-10"
                  />
                </div>
              </div>

              <Select value={filters.type_document || "__all__"} onValueChange={handleTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Type de document" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">Tous les types</SelectItem>
                  {types.map((type) => (
                    <SelectItem key={type.code} value={type.code}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={filters.statut || "__all__"} onValueChange={handleStatutFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">Tous les statuts</SelectItem>
                  <SelectItem value="traite">Traité</SelectItem>
                  <SelectItem value="en_attente">En attente</SelectItem>
                  <SelectItem value="erreur">Erreur</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Liste des documents */}
        <Card>
          <CardHeader>
            <CardTitle>Documents ({stats.total})</CardTitle>
            <CardDescription>
              Liste de tous vos documents importés et analysés
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <p className="text-gray-500">Chargement...</p>
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">Aucun document trouvé</p>
                <Button
                  onClick={() => navigate("/documents/upload")}
                  className="mt-4 bg-[#FF6200] hover:bg-[#E55900]"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Importer des documents
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Nom du fichier
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Type
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Référence
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Client
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Statut
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Taille
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Date
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 dark:text-gray-300 uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {documents.map((doc) => (
                      <tr
                        key={doc.document_id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                        onClick={() => handleViewDocument(doc.document_id)}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-gray-400" />
                            <span className="font-medium text-gray-900 dark:text-white">
                              {doc.nom_fichier}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={`${getTypeBadgeColor(doc.type_document)} text-white`}>
                            {getTypeLabel(doc.type_document)}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-mono text-gray-600 dark:text-gray-300">
                            {doc.reference || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm text-gray-600 dark:text-gray-300">
                            {doc.donnees_extraites?.client || "-"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {getStatutBadge(doc.statut)}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm text-gray-600 dark:text-gray-300">
                            {formatFileSize(doc.taille_fichier)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm text-gray-600 dark:text-gray-300">
                            {formatDate(doc.created_at)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewDocument(doc.document_id);
                              }}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteDocument(doc.document_id);
                              }}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
