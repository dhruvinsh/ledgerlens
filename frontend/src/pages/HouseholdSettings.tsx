import { useState } from "react";
import { motion } from "motion/react";
import { Copy, UserMinus, Users } from "lucide-react";
import { useHousehold, useCreateHousehold, useCreateInvite, useRemoveMember } from "@/hooks/useHousehold";
import { useAppStore } from "@/stores/appStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

export default function HouseholdSettings() {
  const user = useAppStore((s) => s.user);
  const { data: household, isLoading, error } = useHousehold();
  const createHousehold = useCreateHousehold();
  const createInvite = useCreateInvite();
  const removeMember = useRemoveMember();
  const [name, setName] = useState("");
  const [inviteUrl, setInviteUrl] = useState("");

  if (isLoading) return <Spinner className="mt-20" />;

  const isOwner = household && household.owner_id === user?.id;

  // No household yet
  if (error || !household) {
    return (
      <div className="space-y-6 p-6 pb-24 md:pb-6">
        <h1 className="font-serif text-2xl">Household</h1>
        <Card>
          <CardContent className="space-y-4 py-6">
            <p className="text-sm text-text-muted">
              You don&apos;t belong to a household yet. Create one to share receipts with family.
            </p>
            <div className="flex gap-3">
              <Input
                placeholder="Household name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Button
                onClick={() => createHousehold.mutate({ name })}
                disabled={!name.trim() || createHousehold.isPending}
              >
                Create
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleInvite = async () => {
    const result = await createInvite.mutateAsync();
    setInviteUrl(`${window.location.origin}${result.invite_url}`);
  };

  const copyInvite = () => {
    navigator.clipboard.writeText(inviteUrl);
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Household</h1>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        {/* Household info */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Users size={18} className="text-accent" />
              <h2 className="font-medium">{household.name}</h2>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-text-muted">
              Sharing mode: <span className="capitalize">{household.sharing_mode}</span>
            </p>

            {isOwner && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleInvite}>
                  Generate Invite Link
                </Button>
                {inviteUrl && (
                  <Button variant="ghost" size="sm" onClick={copyInvite}>
                    <Copy size={14} /> Copy
                  </Button>
                )}
              </div>
            )}

            {inviteUrl && (
              <div className="rounded-sm bg-accent/5 px-3 py-2">
                <p className="break-all font-mono text-xs">{inviteUrl}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Members */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-medium text-text-muted">
              Members ({household.users.length})
            </h2>
          </CardHeader>
          <div className="divide-y divide-border">
            {household.users.map((member) => (
              <div key={member.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="text-sm font-medium">
                    {member.display_name || member.email}
                    {member.id === household.owner_id && (
                      <span className="ml-2 text-xs text-accent">Owner</span>
                    )}
                  </p>
                  <p className="text-xs text-text-muted">{member.email}</p>
                </div>
                {isOwner && member.id !== user?.id && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeMember.mutate(member.id)}
                  >
                    <UserMinus size={14} className="text-text-muted" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
