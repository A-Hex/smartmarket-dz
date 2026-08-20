// frontend/src/features/analytics/SegmentationTab.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts';

import { Button } from '@/components/ui/button';
import { InterpretationCard } from '@/components/shared/InterpretationCard';
import { ApiClientError } from '@/lib/api-client';

import { ColumnMultiSelect } from './ColumnMultiSelect';
import { useRunSegmentation } from './use-analytics';

const CLUSTER_COLORS = [
  'hsl(178, 68%, 34%)', 'hsl(32, 58%, 55%)', 'hsl(5, 65%, 55%)',
  'hsl(260, 45%, 55%)', 'hsl(152, 45%, 40%)', 'hsl(200, 60%, 50%)',
];

export function SegmentationTab({ datasetId, columns }: { datasetId: string; columns: string[] }) {
  const [features, setFeatures] = useState<string[]>([]);
  const runSegmentation = useRunSegmentation();
  const result = runSegmentation.data;

  const clusterIds = result ? [...new Set(result.pca_points.map((p) => p.cluster))].sort((a, b) => a - b) : [];

  return (
    <div className="space-y-6">
      <div className="space-y-2 rounded-lg border border-border p-4">
        <p className="text-sm font-medium">Variables de segmentation</p>
        <ColumnMultiSelect columns={columns} selected={features} onChange={setFeatures} />
      </div>

      <Button
        onClick={() => runSegmentation.mutate({ dataset_id: datasetId, features, algorithm: 'kmeans' })}
        disabled={features.length < 2 || runSegmentation.isPending}
      >
        {runSegmentation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Lancer la segmentation
      </Button>

      {runSegmentation.isError && (
        <p className="text-sm text-destructive">
          {runSegmentation.error instanceof ApiClientError ? runSegmentation.error.message : 'Une erreur est survenue.'}
        </p>
      )}

      {result && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border p-4">
              <p className="mb-2 text-sm font-medium">Methode du coude et silhouette</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={result.elbow} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="k" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="right" orientation="right" domain={[0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line yAxisId="left" dataKey="inertia" name="Inertie" stroke="hsl(var(--primary))" dot />
                  <Line yAxisId="right" dataKey="silhouette" name="Silhouette" stroke="hsl(var(--accent))" dot />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-lg border border-border p-4">
              <p className="mb-2 text-sm font-medium">
                Projection PCA ({((result.pca_explained_variance[0] ?? 0) * 100).toFixed(0)}% + {((result.pca_explained_variance[1] ?? 0) * 100).toFixed(0)}% variance)
              </p>
              <ResponsiveContainer width="100%" height={220}>
                <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="x" type="number" name="PC1" tick={{ fontSize: 11 }} />
                  <YAxis dataKey="y" type="number" name="PC2" tick={{ fontSize: 11 }} />
                  <ZAxis range={[20, 20]} />
                  <Tooltip contentStyle={{ fontSize: 12 }} cursor={{ strokeDasharray: '3 3' }} />
                  {clusterIds.map((cid) => (
                    <Scatter
                      key={cid}
                      data={result.pca_points.filter((p) => p.cluster === cid)}
                      fill={CLUSTER_COLORS[cid % CLUSTER_COLORS.length]}
                      name={cid === -1 ? 'Bruit' : `Cluster ${cid}`}
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold">Profils des segments</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {result.clusters.map((c) => (
                <div key={c.cluster} className="rounded-lg border border-border p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: CLUSTER_COLORS[c.cluster % CLUSTER_COLORS.length] }}
                    />
                    <p className="font-medium">{c.name}</p>
                  </div>
                  <p className="mb-2 text-xs text-muted-foreground">
                    {c.size} observations ({(c.share * 100).toFixed(0)}%)
                  </p>
                  <ul className="space-y-0.5 text-xs">
                    {Object.entries(c.feature_means).map(([feat, mean]) => (
                      <li key={feat} className="flex justify-between">
                        <span className="truncate">{feat}</span>
                        <span className="font-mono-data text-muted-foreground">{mean.toFixed(1)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          <InterpretationCard text={result.interpretation} className="border-primary/30 bg-primary/5" />
        </div>
      )}
    </div>
  );
}
