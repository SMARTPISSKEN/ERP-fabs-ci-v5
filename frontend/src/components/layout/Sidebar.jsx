import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  BookOpen,
  ShoppingCart,
  FileText,
  CreditCard,
  Truck,
  RotateCcw,
  Package,
  Calculator,
  BarChart3,
  UserCog,
  Settings,
  X,
} from "lucide-react";
import Logo from "../Logo";
import { COMPANY } from "../../constants/company";
import { visibleModulesFor } from "../../constants/permissions";
import { useAuth } from "../../hooks/useAuth";

const ICONS = {
  LayoutDashboard, Users, BookOpen, ShoppingCart, FileText, CreditCard,
  Truck, RotateCcw, Package, Calculator, BarChart3, UserCog, Settings,
};

export default function Sidebar({ mobileOpen = false, onMobileClose }) {
  const { role } = useAuth();
  const modules = visibleModulesFor(role);

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          aria-label="Fermer le menu"
          onClick={onMobileClose}
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          data-testid="sidebar-backdrop"
        />
      )}

      <aside
        data-testid="sidebar"
        className={`w-60 fixed inset-y-0 left-0 z-40 bg-[#0A2540] text-white flex flex-col transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="px-5 py-5 border-b border-white/10 flex items-center justify-between">
          <Logo variant="dark" size="sm" />
          <button
            onClick={onMobileClose}
            aria-label="Fermer le menu"
            className="md:hidden p-1.5 rounded-md hover:bg-white/10"
            data-testid="sidebar-close-mobile"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3">
          <p className="px-3 text-[10px] uppercase tracking-[0.18em] text-white/40 mb-2">
            Modules
          </p>
          <ul className="space-y-1">
            {modules.map((m) => {
              const Icon = ICONS[m.icon] || LayoutDashboard;
              return (
                <li key={m.key}>
                  <NavLink
                    to={m.path}
                    data-testid={`nav-${m.key}`}
                    onClick={onMobileClose}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                        isActive
                          ? "bg-[#FF6200] text-white font-semibold shadow-sm"
                          : "text-white/80 hover:bg-white/10"
                      }`
                    }
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{m.label}</span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="px-5 py-4 border-t border-white/10 text-[11px] text-white/50 leading-relaxed">
          <p className="font-semibold text-white/70">{COMPANY.nom}</p>
          <p>Bingerville · BP 693</p>
          <p className="mt-1 text-[10px] italic">« {COMPANY.slogan} »</p>
        </div>
      </aside>
    </>
  );
}
