'use client';

interface FormCheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export default function FormCheckbox({
  label,
  checked,
  onChange,
  disabled = false,
}: FormCheckboxProps) {
  return (
    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        id={`checkbox-${label}`}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="w-4 h-4 rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed accent-orange"
        style={{
          background: checked ? 'var(--orange)' : 'var(--titanium)',
          borderColor: checked ? 'var(--orange)' : 'var(--titanium)',
        }}
      />
      <label
        htmlFor={`checkbox-${label}`}
        className="cursor-pointer text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        style={{
          color: 'var(--aluminum-dim)',
          fontFamily: 'JetBrains Mono, monospace',
        }}
      >
        {label}
      </label>
    </div>
  );
}
