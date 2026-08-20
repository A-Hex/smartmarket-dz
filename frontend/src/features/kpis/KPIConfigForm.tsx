// frontend/src/features/kpis/KPIConfigForm.tsx
'use client';

import { Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const NONE = '__none__';

function ColumnField({
  label, columns, value, onChange,
}: { label: string; columns: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select value={value || NONE} onValueChange={(v) => onChange(v === NONE ? '' : v)}>
        <SelectTrigger><SelectValue placeholder="Non fourni" /></SelectTrigger>
        <SelectContent>
          <SelectItem value={NONE}>Non fourni</SelectItem>
          {columns.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );
}

export interface KPIConfigValues {
  date_column?: string;
  customer_id_column?: string;
  revenue_column?: string;
  cost_column?: string;
  marketing_spend_column?: string;
}

export function KPIConfigForm({
  columns, onSubmit, isPending,
}: { columns: string[]; onSubmit: (values: KPIConfigValues) => void; isPending: boolean }) {
  const [dateColumn, setDateColumn] = useState('');
  const [customerIdColumn, setCustomerIdColumn] = useState('');
  const [revenueColumn, setRevenueColumn] = useState('');
  const [costColumn, setCostColumn] = useState('');
  const [marketingSpendColumn, setMarketingSpendColumn] = useState('');

  const handleSubmit = () => {
    onSubmit({
      date_column: dateColumn || undefined,
      customer_id_column: customerIdColumn || undefined,
      revenue_column: revenueColumn || undefined,
      cost_column: costColumn || undefined,
      marketing_spend_column: marketingSpendColumn || undefined,
    });
  };

  return (
    <div className="space-y-4 rounded-lg border border-border p-4">
      <p className="text-sm text-muted-foreground">
        Indiquez quelles colonnes correspondent a quoi. Les KPI dont les colonnes ne sont pas fournies
        s&apos;afficheront comme &laquo;&nbsp;donnees insuffisantes&nbsp;&raquo; plutot que d&apos;empecher le calcul des autres.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ColumnField label="Colonne date" columns={columns} value={dateColumn} onChange={setDateColumn} />
        <ColumnField label="Identifiant client" columns={columns} value={customerIdColumn} onChange={setCustomerIdColumn} />
        <ColumnField label="Revenu / montant" columns={columns} value={revenueColumn} onChange={setRevenueColumn} />
        <ColumnField label="Cout" columns={columns} value={costColumn} onChange={setCostColumn} />
        <ColumnField label="Depenses marketing" columns={columns} value={marketingSpendColumn} onChange={setMarketingSpendColumn} />
      </div>
      <Button onClick={handleSubmit} disabled={isPending}>
        {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        Calculer les KPI
      </Button>
    </div>
  );
}
