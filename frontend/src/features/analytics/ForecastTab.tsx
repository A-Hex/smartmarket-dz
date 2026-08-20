// frontend/src/features/analytics/ForecastTab.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { ApiClientError } from '@/lib/api-client';

import { useRunForecast } from './use-analytics';

export function ForecastTab({ datasetId, columns }: { datasetId: string; columns: string[] }) {
  const [timeColumn, setTimeColumn] = useState('');
  const [target, setTarget] = useState('');
  const [horizon, setHorizon] = useState(14);
  const runForecast = useRunForecast();
  const result = runForecast.data;

  const canSubmit = timeColumn && target;

  const chartData = result
    ? [
        ...result.history.dates.slice(-60).map((d, i) => {
          const offset = result.history.dates.length - 60 > 0 ? result.history.dates.length - 60 : 0;
          return {
            date: d,
            actual: result.history.actual[offset + i],
            forecast: null as number | null,
            ci_lower: null as number | null,
            ci_band: null as number | null,
          };
        }),
        ...result.forecast.dates.map((d, i) => ({
          date: d,
          actual: null as number | null,
          forecast: result.forecast.point[i],
          ci_lower: result.forecast.ci_lower_95[i],
          ci_band: (result.forecast.ci_upper_95[i] ?? 0) - (result.forecast.ci_lower_95[i] ?? 0),
        })),
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 rounded-lg border border-border p-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label>Colonne date</Label>
          <Select value={timeColumn} onValueChange={setTimeColumn}>
            <SelectTrigger><SelectValue placeholder="Choisir" /></SelectTrigger>
            <SelectContent>
              {columns.map((col) => <SelectItem key={col} value={col}>{col}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Variable a prevoir</Label>
          <Select value={target} onValueChange={setTarget}>
            <SelectTrigger><SelectValue placeholder="Choisir" /></SelectTrigger>
            <SelectContent>
              {columns.filter((c) => c !== timeColumn).map((col) => <SelectItem key={col} value={col}>{col}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Horizon (jours)</Label>
          <Input type="number" min={1} max={365} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} />
        </div>
      </div>

      <Button
        onClick={() => runForecast.mutate({ dataset_id: datasetId, time_column: timeColumn, target, horizon })}
        disabled={!canSubmit || runForecast.isPending}
      >
        {runForecast.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer la prevision
      </Button>

      {runForecast.isError && (
        <p className="text-sm text-destructive">
          {runForecast.error instanceof ApiClientError ? runForecast.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm">Meilleur modele :</p>
            <Badge>{result.best_model.toUpperCase()}</Badge>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {[
              ['ARIMA MAE', result.arima_metrics.mae.toFixed(2)],
              ['ARIMA RMSE', result.arima_metrics.rmse.toFixed(2)],
              ['ARIMA MAPE', `${result.arima_metrics.mape.toFixed(1)}%`],
              ['ETS MAE', result.ets_metrics.mae.toFixed(2)],
              ['ETS RMSE', result.ets_metrics.rmse.toFixed(2)],
              ['ETS MAPE', `${result.ets_metrics.mape.toFixed(1)}%`],
            ].map(([label, val]) => (
              <div key={label} className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-mono-data text-lg font-semibold">{val}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-border p-4">
            <p className="mb-2 text-sm font-medium">Historique et prevision (IC 95%)</p>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={30} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Area dataKey="ci_lower" stackId="ci" stroke="none" fill="transparent" />
                <Area dataKey="ci_band" stackId="ci" stroke="none" fill="hsl(var(--accent))" fillOpacity={0.15} />
                <Line dataKey="actual" stroke="hsl(var(--primary))" dot={false} strokeWidth={2} connectNulls={false} />
                <Line dataKey="forecast" stroke="hsl(var(--accent))" dot={false} strokeWidth={2} strokeDasharray="4 3" connectNulls={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <InterpretationCard text={result.interpretation} className="border-primary/30 bg-primary/5" />
        </div>
      )}
    </div>
  );
}
