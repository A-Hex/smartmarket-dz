// frontend/src/app/[locale]/(app)/settings/page.tsx
import { CompanyProfileForm } from '@/features/settings/CompanyProfileForm';
import { UserManagement } from '@/features/settings/UserManagement';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Paramètres</h1>
        <p className="text-muted-foreground">Profil de l&apos;entreprise et gestion des utilisateurs.</p>
      </div>
      <CompanyProfileForm />
      <UserManagement />
    </div>
  );
}
