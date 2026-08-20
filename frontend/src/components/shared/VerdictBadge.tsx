// frontend/src/components/shared/VerdictBadge.tsx
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import type { Verdict } from '@/types/api';

const CONFIG: Record<Verdict, { variant: 'success' | 'warning' | 'destructive'; icon: typeof CheckCircle2; label: string }> = {
  pass: { variant: 'success', icon: CheckCircle2, label: 'PASS' },
  warn: { variant: 'warning', icon: AlertTriangle, label: 'WARN' },
  fail: { variant: 'destructive', icon: XCircle, label: 'FAIL' },
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const { variant, icon: Icon, label } = CONFIG[verdict];
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}
