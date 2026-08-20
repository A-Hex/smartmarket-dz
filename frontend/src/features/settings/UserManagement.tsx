// frontend/src/features/settings/UserManagement.tsx
'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiClientError } from '@/lib/api-client';
import { useAuthStore } from '@/stores/auth-store';
import type { UserRole } from '@/types/api';

import { useCompanyUsers, useInviteUser, useUpdateUser } from './use-settings';

const inviteSchema = z.object({
  email: z.string().email(),
  full_name: z.string().min(2),
  password: z.string().min(8),
  role: z.enum(['owner', 'analyst', 'viewer']),
});
type InviteFormValues = z.infer<typeof inviteSchema>;

const ROLE_LABELS: Record<UserRole, string> = { owner: 'Propriétaire', analyst: 'Analyste', viewer: 'Lecteur' };

function InviteUserForm() {
  const invite = useInviteUser();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({ resolver: zodResolver(inviteSchema), defaultValues: { role: 'analyst' } });

  const onSubmit = async (values: InviteFormValues) => {
    setServerError(null);
    try {
      await invite.mutateAsync(values);
      reset({ email: '', full_name: '', password: '', role: 'analyst' });
    } catch (err) {
      setServerError(err instanceof ApiClientError ? err.message : 'Une erreur est survenue.');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" noValidate>
      <div className="space-y-1">
        <Label htmlFor="invite-name">Nom complet</Label>
        <Input id="invite-name" {...register('full_name')} aria-invalid={!!errors.full_name} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="invite-email">E-mail</Label>
        <Input id="invite-email" type="email" {...register('email')} aria-invalid={!!errors.email} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="invite-password">Mot de passe</Label>
        <Input id="invite-password" type="password" {...register('password')} aria-invalid={!!errors.password} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="invite-role">Rôle</Label>
        <select
          id="invite-role"
          {...register('role')}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="owner">Propriétaire</option>
          <option value="analyst">Analyste</option>
          <option value="viewer">Lecteur</option>
        </select>
      </div>
      <div className="sm:col-span-2 lg:col-span-4">
        {serverError && <p className="mb-2 text-sm text-destructive">{serverError}</p>}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          <UserPlus className="h-4 w-4" />
          Inviter
        </Button>
      </div>
    </form>
  );
}

export function UserManagement() {
  const currentUser = useAuthStore((s) => s.user);
  const isOwner = currentUser?.role === 'owner';
  const { data: users, isLoading } = useCompanyUsers();
  const updateUser = useUpdateUser();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Utilisateurs</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {isOwner && <InviteUserForm />}

        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-start text-muted-foreground">
                  <th className="p-2 text-start font-medium">Nom</th>
                  <th className="p-2 text-start font-medium">E-mail</th>
                  <th className="p-2 text-start font-medium">Rôle</th>
                  <th className="p-2 text-start font-medium">Statut</th>
                  {isOwner && <th className="p-2 text-start font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {(users ?? []).map((u) => (
                  <tr key={u.id} className="border-b border-border last:border-0">
                    <td className="p-2">{u.full_name}</td>
                    <td className="p-2 text-muted-foreground">{u.email}</td>
                    <td className="p-2">
                      {isOwner && u.id !== currentUser?.id ? (
                        <Select
                          value={u.role}
                          onValueChange={(role) => updateUser.mutate({ id: u.id, role: role as UserRole })}
                        >
                          <SelectTrigger className="h-8 w-36"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="owner">Propriétaire</SelectItem>
                            <SelectItem value="analyst">Analyste</SelectItem>
                            <SelectItem value="viewer">Lecteur</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        ROLE_LABELS[u.role]
                      )}
                    </td>
                    <td className="p-2">
                      <Badge variant={u.is_active ? 'success' : 'secondary'}>
                        {u.is_active ? 'Actif' : 'Désactivé'}
                      </Badge>
                    </td>
                    {isOwner && (
                      <td className="p-2">
                        {u.id !== currentUser?.id && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => updateUser.mutate({ id: u.id, is_active: !u.is_active })}
                          >
                            {u.is_active ? 'Désactiver' : 'Réactiver'}
                          </Button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
