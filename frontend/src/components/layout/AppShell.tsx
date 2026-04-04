import { Suspense, useEffect } from "react";
import { Outlet, NavLink } from "react-router";
import {
  LayoutDashboard,
  Receipt,
  GitMerge,
  Package,
  TrendingUp,
  Store,
  Settings,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils";
import { useJobNotifications } from "@/hooks/useJobNotifications";
import { useJobUpdates } from "@/hooks/useProcessingJobs";
import { useReviewCounts } from "@/hooks/useReview";
import { wsService } from "@/services/websocket";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/receipts", label: "Receipts", icon: Receipt },
  { to: "/review", label: "Review", icon: GitMerge },
  { to: "/items", label: "Products", icon: Package },
  { to: "/stores", label: "Stores", icon: Store },
  { to: "/price-tracker", label: "Prices", icon: TrendingUp },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  useJobNotifications();
  useJobUpdates();

  const { data: counts } = useReviewCounts();
  const reviewBadge =
    (counts?.match_suggestions ?? 0) + (counts?.store_merges ?? 0);

  // Connect WebSocket on mount (auth via httpOnly cookie)
  useEffect(() => {
    wsService.connect();
    return () => wsService.disconnect();
  }, []);

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
              <div className="relative">
                <Icon size={18} />
                {to === "/review" && reviewBadge > 0 && (
                  <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[9px] font-bold text-white">
                    {reviewBadge > 99 ? "99+" : reviewBadge}
                  </span>
                )}
              </div>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-border px-3 py-4">
          <ThemeToggle className="w-full" />
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar — mobile */}
        <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
          <h1 className="font-serif text-lg tracking-tight text-foreground">
            LedgerLens
          </h1>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              cn(
                "rounded-md p-1.5 transition-colors",
                isActive
                  ? "text-accent"
                  : "text-text-muted hover:text-text",
              )
            }
          >
            <Settings size={20} />
          </NavLink>
        </header>

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

      </div>

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
            <div className="relative">
              <Icon size={20} />
              {to === "/review" && reviewBadge > 0 && (
                <span className="absolute -right-2 -top-1 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-accent px-0.5 text-[8px] font-bold text-white">
                  {reviewBadge > 99 ? "99+" : reviewBadge}
                </span>
              )}
            </div>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
