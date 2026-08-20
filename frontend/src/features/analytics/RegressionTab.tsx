// frontend/src/features/analytics/RegressionTab.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { ApiClientError } from '@/lib/api-client';

import { ColumnMultiSelect } from './ColumnMultiSelect';
import { useRunRegression } from './use-analytics';

export function RegressionTab({
  datasetId,
  columns,
  onModelFitted,
}: {
  datasetId: string;
  columns: string[];
  onModelFitted: (modelId: string) => void;
}) {
  const [target, setTarget] = useState<string>('');
  const [features, setFeatures] = useState<string[]>([]);
  const [logTarget, setLogTarget] = useState(false);
  const runRegression = useRunRegression();
  const result = runRegression.data;

  const canSubmit = target && features.length > 0;

  const handleSubmit = () => {
    runRegression.mutate(
      { dataset_id: datasetId, target, features, log_target: logTarget },
      { onSuccess: (data) => onModelFitted(data.model_id) }
    );
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 rounded-lg border border-border p-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Variable cible</Label>
          <Select value={target} onValueChange={setTarget}>
            <SelectTrigger>
              <SelectValue placeholder="Choisir une variable" />
            </SelectTrigger>
            <SelectContent>
              {columns.map((col) => (
                <SelectItem key={col} value={col}>{col}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 pt-1 text-sm">
            <input type="checkbox" checked={logTarget} onChange={(e) => setLogTarget(e.target.checked)} className="h-3.5 w-3.5 accent-primary" />
            Transformation logarithmique (log(y))
          </label>
        </div>
        <div className="space-y-2">
          <Label>Variables explicatives</Label>
          <ColumnMultiSelect columns={columns} selected={features} onChange={setFeatures} excludeSelected={target ? [target] : []} />
        </div>
      </div>

      <Button onClick={handleSubmit} disabled={!canSubmit || runRegression.isPending}>
        {runRegression.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer la regression
      </Button>

      {runRegression.isError && (
        <p className="text-sm text-destructive">
          {runRegression.error instanceof ApiClientError ? runRegression.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ['R2', result.r_squared.toFixed(3)],
              ['R2 ajuste', result.adj_r_squared.toFixed(3)],
              ['AIC', result.aic.toFixed(1)],
              ['BIC', result.bic.toFixed(1)],
            ].map(([label, val]) => (
              <div key={label} className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-mono-data text-xl font-semibold">{val}</p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-secondary-foreground">
                <tr>
                  {['Variable', 'Coefficient', 'Erreur std', 't', 'p-value', 'Significatif'].map((h) => (
                    <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.coefficients.map((c) => (
                  <tr key={c.term} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{c.term}</td>
                    <td className="px-3 py-2 font-mono-data">{c.coefficient.toFixed(4)}</td>
                    <td className="px-3 py-2 font-mono-data">{c.std_error.toFixed(4)}</td>
                    <td className="px-3 py-2 font-mono-data">{c.t_stat.toFixed(2)}</td>
                    <td className="px-3 py-2 font-mono-data">{c.p_value.toFixed(4)}</td>
                    <td className="px-3 py-2">
                      {c.significant ? <Badge variant="success">Oui</Badge> : <Badge variant="secondary">Non</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2">
            {result.coefficients.map((c) => (
              <InterpretationCard key={c.term} text={c.interpretation} />
            ))}
          </div>

          <InterpretationCard text={result.interpretation} className="border-primary/30 bg-primary/5" />

          <p className="text-xs text-muted-foreground">
            Modele enregistre (id: {result.model_id}). Passez a l&apos;onglet Validation pour executer la suite de diagnostics complete.
          </p>
        </div>
      )}
    </div>
  );
}
