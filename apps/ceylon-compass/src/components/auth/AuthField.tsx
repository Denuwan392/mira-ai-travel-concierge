import type { ChangeEvent } from "react";

interface AuthFieldProps {
  id: string;
  name?: string;
  label: string;
  type?: "text" | "email" | "tel";
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
  disabled?: boolean;
  hint?: string;
  error?: string;
}

export function AuthField({
  id,
  name = id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
  required = false,
  disabled = false,
  hint,
  error,
}: AuthFieldProps) {
  return (
    <div className="space-y-1 text-left">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="block text-[12.5px] font-semibold text-[#111111]">
          {label} {required && <span className="text-[#F26B1D]">*</span>}
        </label>
        {hint && <span className="text-[11.5px] text-[#5F5F5F]">{hint}</span>}
      </div>

      <input
        id={id}
        name={name}
        type={type}
        required={required}
        disabled={disabled}
        autoComplete={autoComplete}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`w-full h-[40px] px-3 rounded-[8px] border text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed ${
          error
            ? "border-red-400 focus:border-red-500 focus:ring-red-200"
            : "border-[#E6E6E6] focus:border-[#F26B1D] focus:ring-[#F26B1D]/20"
        }`}
      />

      {error && (
        <p id={`${id}-error`} className="text-[11.5px] text-red-600 font-medium">
          {error}
        </p>
      )}
    </div>
  );
}
