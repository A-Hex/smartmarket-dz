// frontend/src/app/[locale]/(app)/decisions/page.tsx
'use client';

import { Lightbulb, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DatasetPicker } from '@/components/shared/DatasetPicker';
import { EmptyState } from '@/components/shared/EmptyState';
import { useGenerateDecisions } from '@/features/analytics/use-analytics';
import { DecisionCard } from '@/features/decisions/DecisionCard';
import { ApiClientError } from '@/lib/api-client';

const ALL = '__all__';

export default function DecisionsPage() {
  const [datasetId, setDatasetId] = useState('');
  const [priorityFilter, setPriorityFilter] = useState(ALL);
  const generate = useGenerateDecisions();

  const decisions = generate.data?.decisions ?? [];
  const filtered =
    priorityFilter === ALL ? decisions : decisions.filter((d) => d.priority === priorityFilter);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Decisions</h1>
        <p className="text-muted-foreground">
          Recommandations priorisees et etayees par les preuves, generees a partir des dernieres analyses completees.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <DatasetPicker value={datasetId} onChange={setDatasetId} />
        <Button onClick={() => generate.mutate(datasetId)} disabled={!datasetId || generate.isPending}>
          {generate.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Generer les recommandations
        </Button>
        {decisions.length > 0 && (
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Toutes priorites</SelectItem>
              <SelectItem value="high">Haute</SelectItem>
              <SelectItem value="medium">Moyenne</SelectItem>
              <SelectItem value="low">Basse</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>

      {generate.isError && (
        <p className="text-sm text-destructive">
          {generate.error instanceof ApiClientError ? generate.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {generate.data && decisions.length === 0 && (
        <EmptyState
          icon={Lightbulb}
          title="Aucune recommandation pour l'instant"
          description="Lancez d'abord des analyses (regression, prevision, KPI...) sur ce jeu de donnees : le moteur de decision s'appuie sur leurs resultats."
        />
      )}

      {filtered.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {filtered.map((d) => <DecisionCard key={d.id} decision={d} />)}
        </div>
      )}

      {!generate.data && (
        <EmptyState
          icon={Lightbulb}
          title="Pret a generer des recommandations"
          description="Choisissez un jeu de donnees puis cliquez sur Generer les recommandations."
        />
      )}
    </div>
  );
}
