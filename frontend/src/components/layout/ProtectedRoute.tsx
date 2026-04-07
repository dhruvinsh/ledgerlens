import { useEffect } from "react";
import { Navigate, Outlet } from "react-router";
import { useAppStore } from "@/stores/appStore";
import { Spinner } from "@/components/ui/spinner";

export function ProtectedRoute() {
  const { user, loading, fetchMe } = useAppStore();

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export function AdminRoute() {
  const { user, loading } = useAppStore();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
