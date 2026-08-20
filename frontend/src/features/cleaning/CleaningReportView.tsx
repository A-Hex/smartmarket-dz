// frontend/src/features/cleaning/CleaningReportView.tsx
'use client';

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { CleaningReport } from './use-cleaning';

export function CleaningReportView({ report }: { report: CleaningReport }) {
  const missingnessData = report.per_column.map((c) => ({
    column: c.column,
    avant: c.null_count_before,
    apres: c.null_count_after,
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ['Lignes avant', report.rows_before],
          ['Lignes apres', report.rows_after],
          ['Colonnes avant', report.columns_before],
          ['Colonnes apres', report.columns_after],
        ].map(([label, val]) => (
          <div key={label} className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="font-mono-data text-xl font-semibold">{val}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-border p-4">
        <p className="mb-2 text-sm font-medium">Valeurs manquantes avant / apres</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={missingnessData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="column" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="avant" fill="hsl(var(--destructive))" fillOpacity={0.6} name="Avant" />
            <Bar dataKey="apres" fill="hsl(var(--success))" fillOpacity={0.7} name="Apres" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-secondary text-secondary-foreground">
            <tr>
              {['Colonne', 'Strategie appliquee', 'Manquants avant', 'Manquants apres', 'Aberrantes detectees', 'Aberrantes traitees'].map((h) => (
                <th key={h} className="px-3 py-2 text-start font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.per_column.map((c) => (
              <tr key={c.column} className="border-t border-border">
                <td className="px-3 py-2 font-medium">{c.column}</td>
                <td className="px-3 py-2">{c.strategy_applied}</td>
                <td className="px-3 py-2 font-mono-data">{c.null_count_before}</td>
                <td className="px-3 py-2 font-mono-data">{c.null_count_after}</td>
                <td className="px-3 py-2 font-mono-data">{c.outliers_detected}</td>
                <td className="px-3 py-2 font-mono-data">{c.outliers_handled}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
