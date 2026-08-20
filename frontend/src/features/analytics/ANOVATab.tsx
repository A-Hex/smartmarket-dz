// frontend/src/features/analytics/ANOVATab.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { ApiClientError } from '@/lib/api-client';

import { useRunAnova } from './use-analytics';

export function ANOVATab({ datasetId, columns }: { datasetId: string; columns: string[] }) {
  const [factor, setFactor] = useState('');
  const [response, setResponse] = useState('');
  const runAnova = useRunAnova();
  const result = runAnova.data;

  const canSubmit = factor && response;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 rounded-lg border border-border p-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Facteur (groupes)</Label>
          <Select value={factor} onValueChange={setFactor}>
            <SelectTrigger>
              <SelectValue placeholder="Choisir une variable categorielle" />
            </SelectTrigger>
            <SelectContent>
              {columns.map((col) => (
                <SelectItem key={col} value={col}>{col}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Reponse (numerique)</Label>
          <Select value={response} onValueChange={setResponse}>
            <SelectTrigger>
              <SelectValue placeholder="Choisir une variable numerique" />
            </SelectTrigger>
            <SelectContent>
              {columns.filter((c) => c !== factor).map((col) => (
                <SelectItem key={col} value={col}>{col}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Button
        onClick={() => runAnova.mutate({ dataset_id: datasetId, factor, response })}
        disabled={!canSubmit || runAnova.isPending}
      >
        {runAnova.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer l&apos;ANOVA
      </Button>

      {runAnova.isError && (
        <p className="text-sm text-destructive">
          {runAnova.error instanceof ApiClientError ? runAnova.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ['F', result.f_statistic.toFixed(3)],
              ['p-value', result.p_value.toFixed(4)],
              ['eta2', result.eta_squared.toFixed(3)],
              ['Groupes', String(result.groups.length)],
            ].map(([label, val]) => (
              <div key={label} className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-mono-data text-xl font-semibold">{val}</p>
              </div>
            ))}
          </div>

          {result.tukey.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">Post-hoc de Tukey HSD</h3>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-secondary text-secondary-foreground">
                    <tr>
                      {['Groupe 1', 'Groupe 2', 'Diff. moyenne', 'p (ajuste)', 'Significatif'].map((h) => (
                        <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.tukey.map((t, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="px-3 py-2">{t.group1}</td>
                        <td className="px-3 py-2">{t.group2}</td>
                        <td className="px-3 py-2 font-mono-data">{t.mean_diff.toFixed(3)}</td>
                        <td className="px-3 py-2 font-mono-data">{t.p_adj.toFixed(4)}</td>
                        <td className="px-3 py-2">
                          {t.reject_null ? <Badge variant="success">Oui</Badge> : <Badge variant="secondary">Non</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <InterpretationCard text={result.interpretation} className="border-primary/30 bg-primary/5" />
        </div>
      )}
    </div>
  );
}
