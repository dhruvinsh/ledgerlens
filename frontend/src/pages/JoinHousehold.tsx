import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import { Users } from "lucide-react";
import { useJoinHousehold } from "@/hooks/useHousehold";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function JoinHousehold() {
  const { token } = useParams();
  const navigate = useNavigate();
  const join = useJoinHousehold();

  const handleJoin = async () => {
    if (!token) return;
    await join.mutateAsync(token);
    navigate("/settings/household");
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-8">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
              <Users size={28} className="text-accent" />
            </div>
            <h1 className="font-serif text-xl">Join Household</h1>
            <p className="text-center text-sm text-text-muted">
              You&apos;ve been invited to join a household. Click below to accept.
            </p>

            {join.isError && (
              <p className="text-sm text-destructive">
                {join.error instanceof Error ? join.error.message : "Failed to join"}
              </p>
            )}

            {join.isSuccess ? (
              <p className="text-sm text-success">Joined successfully! Redirecting...</p>
            ) : (
              <Button onClick={handleJoin} disabled={join.isPending} className="w-full">
                {join.isPending ? "Joining..." : "Accept Invite"}
              </Button>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
