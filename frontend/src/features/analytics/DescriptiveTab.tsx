// frontend/src/features/analytics/DescriptiveTab.tsx
'use client';

import { Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { ApiClientError } from '@/lib/api-client';

import { useRunDescriptive } from './use-analytics';

export function DescriptiveTab({ datasetId }: { datasetId: string }) {
  const runDescriptive = useRunDescriptive();
  const result = runDescriptive.data;

  return (
    <div className="space-y-6">
      <Button onClick={() => runDescriptive.mutate(datasetId)} disabled={runDescriptive.isPending}>
        {runDescriptive.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer les statistiques descriptives
      </Button>

      {runDescriptive.isError && (
        <p className="text-sm text-destructive">
          {runDescriptive.error instanceof ApiClientError ? runDescriptive.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">
            {result.row_count} lignes analysees - {result.target_candidates.length} variable(s) cible candidate(s) :{' '}
            {result.target_candidates.join(', ') || 'aucune'}
          </p>

          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-secondary-foreground">
                <tr>
                  {['Colonne', 'Moyenne', 'Mediane', 'Ecart-type', 'Asymetrie', 'Aplatissement', 'Min', 'Max', 'Manquants'].map((h) => (
                    <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.numeric_columns.map((col) => (
                  <tr key={col.column} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{col.column}</td>
                    <td className="px-3 py-2 font-mono-data">{col.mean?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.median?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.std?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.skewness?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.kurtosis?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.min?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.max?.toFixed(2) ?? '-'}</td>
                    <td className="px-3 py-2 font-mono-data">{col.missing}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {result.categorical_columns.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">Variables categorielles</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {result.categorical_columns.map((col) => (
                  <div key={col.column} className="rounded-lg border border-border p-3">
                    <p className="mb-1 font-medium">{col.column}</p>
                    <p className="mb-2 text-xs text-muted-foreground">{col.unique} valeurs uniques - {col.missing} manquants</p>
                    <ul className="space-y-0.5 text-xs">
                      {Object.entries(col.top_values).slice(0, 5).map(([val, count]) => (
                        <li key={val} className="flex justify-between">
                          <span className="truncate">{val}</span>
                          <span className="font-mono-data text-muted-foreground">{count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.correlation && (
            <div>
              <h3 className="mb-2 text-sm font-semibold">Matrice de correlation (Pearson)</h3>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-xs">
                  <thead className="bg-secondary text-secondary-foreground">
                    <tr>
                      <th className="px-2 py-1" />
                      {result.correlation.columns.map((c) => (
                        <th key={c} className="px-2 py-1 text-start font-medium">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.correlation.columns.map((rowCol, i) => (
                      <tr key={rowCol} className="border-t border-border">
                        <td className="px-2 py-1 font-medium">{rowCol}</td>
                        {result.correlation!.pearson[i]?.map((val, j) => (
                          <td
                            key={j}
                            className="px-2 py-1 font-mono-data"
                            style={{
                              backgroundColor: `hsla(178, 68%, 40%, ${Math.min(Math.abs(val), 1) * 0.5})`,
                            }}
                          >
                            {val.toFixed(2)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <InterpretationCard
            text={`${result.numeric_columns.length} variable(s) numerique(s) et ${result.categorical_columns.length} variable(s) categorielle(s) analysees. Consultez les candidats de variable cible ci-dessus pour choisir une variable a expliquer dans l'onglet Regression.`}
          />
        </div>
      )}
    </div>
  );
}
