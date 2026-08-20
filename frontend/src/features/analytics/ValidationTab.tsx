// frontend/src/features/analytics/ValidationTab.tsx
'use client';

import { Loader2 } from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts';

import { Button } from '@/components/ui/button';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { VerdictBadge } from '@/components/shared/VerdictBadge';
import { ApiClientError } from '@/lib/api-client';
import type { TestResult } from '@/types/api';

import { useRunValidation } from './use-analytics';

function TestCard({ label, test }: { label: string; test: TestResult }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-medium">{label}</p>
        <VerdictBadge verdict={test.verdict} />
      </div>
      <p className="font-mono-data text-sm text-muted-foreground">
        stat={test.statistic.toFixed(3)}
        {test.p_value !== null && <> &middot; p={test.p_value.toFixed(4)}</>}
      </p>
      <p className="mt-2 text-sm">{test.meaning}</p>
    </div>
  );
}

export function ValidationTab({ modelId }: { modelId: string | null }) {
  const runValidation = useRunValidation();
  const result = runValidation.data;

  if (!modelId) {
    return (
      <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Ajustez d&apos;abord un modele de regression dans l&apos;onglet Regression pour pouvoir le valider ici.
      </p>
    );
  }

  const residualScatter = result?.residual_vs_fitted.fitted.map((f, i) => ({
    fitted: f,
    residual: result.residual_vs_fitted.residuals[i],
  }));

  const histogramData = result?.residual_histogram.counts.map((count, i) => ({
    bin: `${result.residual_histogram.bin_edges[i]?.toFixed(1)}`,
    count,
  }));

  return (
    <div className="space-y-6">
      <Button onClick={() => runValidation.mutate(modelId)} disabled={runValidation.isPending}>
        {runValidation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer la suite de validation
      </Button>

      {runValidation.isError && (
        <p className="text-sm text-destructive">
          {runValidation.error instanceof ApiClientError ? runValidation.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <div className="flex items-center gap-3 rounded-lg border border-border p-4">
            <p className="font-medium">Verdict global</p>
            <VerdictBadge verdict={result.overall_verdict} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <TestCard label="Normalite des residus" test={result.normality} />
            <TestCard label="Heteroscedasticite" test={result.heteroscedasticity} />
            <TestCard label="Autocorrelation (Durbin-Watson)" test={result.autocorrelation} />
            <TestCard
              label="Points influents (Cook)"
              test={{
                statistic: result.influence.influential_ratio,
                p_value: null,
                threshold: String(result.influence.threshold),
                verdict: result.influence.verdict,
                meaning: result.influence.meaning,
              }}
            />
          </div>

          <div className="rounded-lg border border-border p-4">
            <div className="mb-2 flex items-center justify-between">
              <p className="font-medium">Multicolinearite (VIF)</p>
              <VerdictBadge verdict={result.multicollinearity.verdict} />
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {result.multicollinearity.vif.map((v) => (
                <div key={v.feature} className="rounded-md bg-secondary p-2">
                  <p className="truncate text-xs text-muted-foreground">{v.feature}</p>
                  <div className="flex items-center justify-between">
                    <p className="font-mono-data font-semibold">{v.vif.toFixed(1)}</p>
                    <VerdictBadge verdict={v.verdict} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border p-4">
              <p className="mb-2 text-sm font-medium">Residus vs valeurs ajustees</p>
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="fitted" type="number" name="Ajuste" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="residual" type="number" name="Residu" tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Scatter data={residualScatter} fill="hsl(var(--primary))" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="mb-2 text-sm font-medium">Histogramme des residus</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={histogramData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Bar dataKey="count" fill="hsl(var(--accent))" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {result.remediation.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">Recommandations de correction</h3>
              {result.remediation.map((r, i) => (
                <InterpretationCard key={i} text={r} className="border-warning/30 bg-warning/5" />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
