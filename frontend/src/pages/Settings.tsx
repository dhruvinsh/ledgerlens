import { Link } from "react-router";
import { motion } from "motion/react";
import { User, Users, Cpu, LogOut, Palette } from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ThemeToggle } from "@/components/ui/theme-toggle";

export default function Settings() {
  const { user, logout } = useAppStore();

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Settings</h1>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        {/* Profile */}
        <Card>
          <CardContent className="flex items-center gap-4 py-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10">
              <User size={24} className="text-accent" />
            </div>
            <div>
              <p className="font-medium">{user?.display_name || user?.email}</p>
              <p className="text-sm text-text-muted">{user?.email}</p>
              <p className="text-xs text-text-muted capitalize">Role: {user?.role}</p>
            </div>
          </CardContent>
        </Card>

        {/* Theme */}
        <Card>
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Palette size={20} className="text-accent" />
              <div>
                <p className="text-sm font-medium">Theme</p>
                <p className="text-xs text-text-muted">Light, dark, or match system</p>
              </div>
            </div>
            <ThemeToggle />
          </CardContent>
        </Card>

        {/* Navigation */}
        <Link to="/settings/household">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-3 py-4">
              <Users size={20} className="text-accent" />
              <div>
                <p className="text-sm font-medium">Household</p>
                <p className="text-xs text-text-muted">Manage household members and sharing</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        {user?.role === "admin" && (
          <Link to="/admin/models">
            <Card className="transition-shadow hover:shadow-md">
              <CardContent className="flex items-center gap-3 py-4">
                <Cpu size={20} className="text-accent" />
                <div>
                  <p className="text-sm font-medium">LLM Models</p>
                  <p className="text-xs text-text-muted">Configure OCR extraction models</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        )}

        <Button variant="outline" className="w-full" onClick={handleLogout}>
          <LogOut size={16} /> Sign Out
        </Button>
      </motion.div>
    </div>
  );
}
