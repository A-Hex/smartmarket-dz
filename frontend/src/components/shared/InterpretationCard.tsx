// frontend/src/components/shared/InterpretationCard.tsx
import { Lightbulb } from 'lucide-react';

import { cn } from '@/lib/utils';

/** A plain-language interpretation callout — every statistical result must ship with one. */
export function InterpretationCard({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn('flex gap-3 rounded-lg border border-accent/30 bg-accent/10 p-4', className)}>
      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-accent-foreground" strokeWidth={1.75} />
      <p className="text-sm leading-relaxed text-foreground">{text}</p>
    </div>
  );
}
