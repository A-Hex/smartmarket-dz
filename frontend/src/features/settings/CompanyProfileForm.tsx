// frontend/src/features/settings/CompanyProfileForm.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuthStore } from '@/stores/auth-store';

import { useUpdateCompany } from './use-settings';

export function CompanyProfileForm() {
  const company = useAuthStore((s) => s.company);
  const user = useAuthStore((s) => s.user);
  const isOwner = user?.role === 'owner';
  const updateCompany = useUpdateCompany();
  const [name, setName] = useState(company?.name ?? '');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (company?.name) setName(company.name);
  }, [company?.name]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(false);
    await updateCompany.mutateAsync(name);
    setSaved(true);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Profil de l&apos;entreprise</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="max-w-sm space-y-4">
          <div className="space-y-2">
            <Label htmlFor="company-name">Nom de l&apos;entreprise</Label>
            <Input
              id="company-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!isOwner}
            />
          </div>
          <div className="space-y-1 text-sm text-muted-foreground">
            <p>Identifiant : {company?.slug}</p>
            <p>Pays : {company?.country}</p>
          </div>
          {isOwner && (
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={updateCompany.isPending || name === company?.name}>
                {updateCompany.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Enregistrer
              </Button>
              {saved && !updateCompany.isPending && (
                <span className="text-sm text-success">Enregistré.</span>
              )}
            </div>
          )}
          {!isOwner && (
            <p className="text-sm text-muted-foreground">
              Seul le propriétaire de l&apos;entreprise peut modifier ce profil.
            </p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
