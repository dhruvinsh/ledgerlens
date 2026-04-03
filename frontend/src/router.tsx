import { lazy } from "react";
import { createBrowserRouter, Navigate } from "react-router";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import { RouteError } from "@/components/layout/RouteError";

const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Receipts = lazy(() => import("@/pages/Receipts"));
const AddReceipt = lazy(() => import("@/pages/AddReceipt"));
const ManualEntry = lazy(() => import("@/pages/ManualEntry"));
const ReceiptDetail = lazy(() => import("@/pages/ReceiptDetail"));
const Items = lazy(() => import("@/pages/Items"));
const ProductDetail = lazy(() => import("@/pages/ProductDetail"));
const PriceTracker = lazy(() => import("@/pages/PriceTracker"));
const Review = lazy(() => import("@/pages/Review"));
const Stores = lazy(() => import("@/pages/Stores"));
const StoreDetail = lazy(() => import("@/pages/StoreDetail"));
const Settings = lazy(() => import("@/pages/Settings"));
const HouseholdSettings = lazy(() => import("@/pages/HouseholdSettings"));
const AdminModels = lazy(() => import("@/pages/AdminModels"));
const JoinHousehold = lazy(() => import("@/pages/JoinHousehold"));

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        errorElement: <RouteError />,
        children: [
          { path: "/dashboard", element: <Dashboard /> },
          { path: "/receipts", element: <Receipts /> },
          { path: "/receipts/add", element: <AddReceipt /> },
          { path: "/receipts/manual", element: <ManualEntry /> },
          { path: "/receipts/:id", element: <ReceiptDetail /> },
          { path: "/review", element: <Review /> },
          { path: "/items", element: <Items /> },
          { path: "/items/:id", element: <ProductDetail /> },
          { path: "/price-tracker", element: <PriceTracker /> },
          { path: "/stores", element: <Stores /> },
          { path: "/stores/:id", element: <StoreDetail /> },
          { path: "/settings", element: <Settings /> },
          { path: "/settings/household", element: <HouseholdSettings /> },
          { path: "/admin/models", element: <AdminModels /> },
          { path: "/join/:token", element: <JoinHousehold /> },
        ],
      },
    ],
  },
]);
