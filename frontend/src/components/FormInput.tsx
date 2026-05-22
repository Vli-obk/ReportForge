'use client';

import { ReactNode } from 'react';

interface FormInputProps {
  label: string;
  type?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function FormInput({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  disabled,
}: FormInputProps) {
  return (
    <div className="flex flex-col gap-2">
      <label
        style={{
          fontSize: '0.875rem',
          color: 'var(--aluminum-dim)',
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {label}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
      />
      {error && (
        <span
          style={{
            fontSize: '0.75rem',
            color: '#FF6B6B',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          {error}
        </span>
      )}
    </div>
  );
}
