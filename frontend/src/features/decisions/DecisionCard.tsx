// frontend/src/features/decisions/DecisionCard.tsx
'use client';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Decision } from '@/types/api';

const PRIORITY_VARIANT: Record<Decision['priority'], 'destructive' | 'warning' | 'secondary'> = {
  high: 'destructive',
  medium: 'warning',
  low: 'secondary',
};

const PRIORITY_LABEL: Record<Decision['priority'], string> = {
  high: 'Priorite haute',
  medium: 'Priorite moyenne',
  low: 'Priorite basse',
};

export function DecisionCard({ decision }: { decision: Decision }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={PRIORITY_VARIANT[decision.priority]}>{PRIORITY_LABEL[decision.priority]}</Badge>
          <Badge variant="outline">{decision.category}</Badge>
          <Badge variant="secondary" className="ml-auto">
            Confiance : {decision.confidence}
          </Badge>
        </div>
        <h3 className="pt-1 font-semibold">{decision.title}</h3>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        <p className="text-sm text-muted-foreground">{decision.description}</p>
        <div className="rounded-md bg-secondary p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Action recommandee</p>
          <p className="text-sm">{decision.recommended_action}</p>
        </div>
      </CardContent>
    </Card>
  );
}
