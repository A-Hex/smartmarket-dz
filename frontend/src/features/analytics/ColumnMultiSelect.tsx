// frontend/src/features/analytics/ColumnMultiSelect.tsx
'use client';

interface Props {
  columns: string[];
  selected: string[];
  onChange: (next: string[]) => void;
  excludeSelected?: string[];
}

export function ColumnMultiSelect({ columns, selected, onChange, excludeSelected = [] }: Props) {
  const toggle = (col: string) => {
    if (selected.includes(col)) {
      onChange(selected.filter((c) => c !== col));
    } else {
      onChange([...selected, col]);
    }
  };

  const available = columns.filter((c) => !excludeSelected.includes(c));

  return (
    <div className="grid max-h-48 grid-cols-2 gap-1 overflow-y-auto rounded-md border border-input p-2 sm:grid-cols-3">
      {available.map((col) => (
        <label key={col} className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-secondary">
          <input
            type="checkbox"
            checked={selected.includes(col)}
            onChange={() => toggle(col)}
            className="h-3.5 w-3.5 accent-primary"
          />
          <span className="truncate">{col}</span>
        </label>
      ))}
    </div>
  );
}
