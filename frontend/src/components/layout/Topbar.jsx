import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, ChevronDown, Bell, Search, Sun, Moon, Menu, Loader2 } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useDarkMode } from "../../hooks/useDarkMode";
import { COMPANY, ROLES } from "../../constants/company";
import { rechercheGlobale } from "../../services/rechercheApi";

const TYPE_LABEL = {
  client: "Client",
  produit: "Produit",
  commande: "Commande",
  facture: "Facture",
  bon_livraison: "BL",
};

export default function Topbar({ onToggleSidebar }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isDark, toggle: toggleTheme } = useDarkMode();
  const [open, setOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const userRef = useRef(null);
  const notifRef = useRef(null);
  const searchRef = useRef(null);

  // Global search state (Sprint 15)
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const onClick = (e) => {
      if (userRef.current && !userRef.current.contains(e.target)) setOpen(false);
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false);
      if (searchRef.current && !searchRef.current.contains(e.target)) setSearchOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Debounced global search
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    const t = setTimeout(async () => {
      try {
        const data = await rechercheGlobale(searchQuery, 20);
        setSearchResults(data || []);
        setSearchOpen(true);
      } catch (e) {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const handleSelectResult = (r) => {
    setSearchOpen(false);
    setSearchQuery("");
    navigate(r.url);
  };

  if (!user) return null;

  const initials = (user.nom_complet || user.email || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const notifCount = 0;

  return (
    <header
      data-testid="topbar"
      className="h-16 bg-white dark:bg-[#0A2540] border-b border-gray-200 dark:border-white/10 px-4 md:px-6 flex items-center justify-between fixed top-0 right-0 left-0 md:left-60 z-20"
    >
      <div className="flex items-center gap-3">
        <button
          data-testid="topbar-toggle-sidebar"
          onClick={onToggleSidebar}
          aria-label="Ouvrir le menu"
          className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-[#0A2540] dark:text-white"
        >
          <Menu className="w-5 h-5" />
        </button>
        <span
          data-testid="topbar-school-year"
          className="hidden sm:inline-flex text-[11px] uppercase tracking-[0.2em] font-semibold bg-[#0A2540]/5 dark:bg-white/5 text-[#0A2540] dark:text-white/80 px-3 py-1.5 rounded-md border border-[#0A2540]/10 dark:border-white/10"
        >
          {COMPANY.anneeScolaire}
        </span>
      </div>

      {/* CENTER: global search */}
      <div className="flex-1 max-w-xl mx-2 md:mx-6 relative" ref={searchRef}>
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          data-testid="topbar-search"
          type="text"
          placeholder="Rechercher clients, produits, commandes..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => searchResults.length > 0 && setSearchOpen(true)}
          className="w-full pl-9 pr-9 py-2 text-sm bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#FF6200]/40 focus:border-[#FF6200] text-[#0A2540] dark:text-white placeholder:text-gray-400"
        />
        {searchLoading && (
          <Loader2 className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />
        )}

        {searchOpen && searchQuery.length >= 2 && (
          <div
            data-testid="topbar-search-results"
            className="absolute left-0 right-0 mt-2 max-h-96 overflow-y-auto bg-white dark:bg-[#0A2540] shadow-xl rounded-xl border border-gray-200 dark:border-white/10 z-30"
          >
            {searchResults.length === 0 && !searchLoading ? (
              <div className="px-4 py-6 text-center text-sm text-gray-500">
                Aucun résultat pour « {searchQuery} »
              </div>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-white/10">
                {searchResults.map((r) => (
                  <li key={`${r.type}-${r.id}`}>
                    <button
                      onClick={() => handleSelectResult(r)}
                      className="w-full text-left px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                      data-testid={`search-result-${r.type}-${r.reference}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-wider font-semibold text-[#FF6200]">
                          {TYPE_LABEL[r.type] || r.type}
                        </span>
                        <span className="text-xs font-mono text-gray-400">{r.reference}</span>
                      </div>
                      <div className="text-sm font-medium text-[#0A2540] dark:text-white mt-0.5">{r.titre}</div>
                      {r.sous_titre && (
                        <div className="text-xs text-gray-500 dark:text-white/50">{r.sous_titre}</div>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <button
          data-testid="topbar-theme-toggle"
          onClick={toggleTheme}
          aria-label="Basculer le thème"
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-[#0A2540] dark:text-white transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <div className="relative" ref={notifRef}>
          <button
            data-testid="topbar-notifications-btn"
            onClick={() => setNotifOpen((o) => !o)}
            aria-label="Notifications"
            className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-[#0A2540] dark:text-white transition-colors"
          >
            <Bell className="w-4 h-4" />
            {notifCount > 0 && (
              <span
                data-testid="topbar-notif-badge"
                className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#C62828] text-white text-[10px] font-bold flex items-center justify-center"
              >
                {notifCount}
              </span>
            )}
          </button>
          {notifOpen && (
            <div
              data-testid="topbar-notif-dropdown"
              className="absolute right-0 mt-2 w-80 bg-white dark:bg-[#0A2540] shadow-xl rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-gray-100 dark:border-white/10">
                <p className="text-sm font-semibold text-[#0A2540] dark:text-white">
                  Notifications
                </p>
              </div>
              <div className="p-6 text-center text-sm text-gray-500 dark:text-white/50">
                Aucune notification pour le moment.
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={userRef}>
          <button
            data-testid="topbar-user-menu"
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-2 sm:gap-3 hover:bg-gray-100 dark:hover:bg-white/10 rounded-lg px-2 py-1.5 transition-colors"
          >
            <div className="w-9 h-9 rounded-full bg-[#0A2540] dark:bg-[#FF6200] text-white flex items-center justify-center text-sm font-bold">
              {initials}
            </div>
            <div className="text-left hidden lg:block">
              <p className="text-sm font-semibold text-[#0A2540] dark:text-white leading-tight">
                {user.nom_complet}
              </p>
              <p className="text-[11px] text-gray-500 dark:text-white/60 leading-tight">
                {ROLES[user.role] || user.role}
              </p>
            </div>
            <ChevronDown className="w-4 h-4 text-gray-400 dark:text-white/60 hidden sm:block" />
          </button>

          {open && (
            <div
              data-testid="topbar-user-dropdown"
              className="absolute right-0 mt-2 w-64 bg-white dark:bg-[#0A2540] shadow-xl rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-gray-100 dark:border-white/10">
                <p className="text-sm font-semibold text-[#0A2540] dark:text-white">
                  {user.nom_complet}
                </p>
                <p className="text-xs text-gray-500 dark:text-white/60 truncate">{user.email}</p>
                <span className="inline-block mt-2 text-[10px] uppercase tracking-wider bg-[#FF6200]/10 text-[#FF6200] px-2 py-0.5 rounded">
                  {ROLES[user.role] || user.role}
                </span>
              </div>
              <button
                data-testid="topbar-logout-btn"
                onClick={logout}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-[#C62828] hover:bg-red-50 dark:hover:bg-white/5 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Se déconnecter
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
