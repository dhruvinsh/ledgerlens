import { Suspense } from "react";
import { Outlet, NavLink } from "react-router";
import {
  LayoutDashboard,
  Receipt,
  Package,
  TrendingUp,
  Store,
  Settings,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { useJobNotifications } from "@/hooks/useJobNotifications";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/receipts", label: "Receipts", icon: Receipt },
  { to: "/items", label: "Products", icon: Package },
  { to: "/price-tracker", label: "Prices", icon: TrendingUp },
  { to: "/stores", label: "Stores", icon: Store },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  useJobNotifications();

  return (
    <div className="flex h-screen">
      {/* Sidebar — desktop */}
      <aside className="hidden w-56 flex-col border-r border-border bg-sidebar md:flex">
        <div className="p-5">
          <h1 className="font-serif text-xl tracking-tight text-sidebar-foreground">
            LedgerLens
          </h1>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-sm px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent/10 text-accent"
                    : "text-text-muted hover:bg-accent/5 hover:text-text",
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Suspense
          fallback={
            <div className="flex h-full items-center justify-center">
              <Spinner />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>

      {/* Tab bar — mobile */}
      <nav className="fixed inset-x-0 bottom-0 z-50 flex border-t border-border bg-surface md:hidden">
        {navItems.slice(0, 5).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px]",
                isActive ? "text-accent" : "text-text-muted",
              )
            }
          >
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
