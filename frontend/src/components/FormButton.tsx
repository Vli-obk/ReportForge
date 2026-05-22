'use client';

interface FormButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
  loading?: boolean;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: () => void;
  fullWidth?: boolean;
}

export default function FormButton({
  children,
  variant = 'primary',
  loading = false,
  disabled = false,
  type = 'button',
  onClick,
  fullWidth = false,
}: FormButtonProps) {
  const buttonClass = variant === 'primary' ? 'btn-primary' : 'btn-secondary';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      className={`${buttonClass} ${fullWidth ? 'w-full' : ''} disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}
