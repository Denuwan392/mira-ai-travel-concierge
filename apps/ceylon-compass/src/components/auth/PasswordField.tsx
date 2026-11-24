import { Eye, EyeOff } from "lucide-react";
import { useState, type ChangeEvent } from "react";

interface PasswordFieldProps {
  id?: string;
  name?: string;
  label: string;
  value: string;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
  disabled?: boolean;
  minLength?: number;
  hint?: string;
  error?: string;
}

export function PasswordField({
  id = "password",
  name = "password",
  label,
  value,
  onChange,
  placeholder = "••••••••",
  autoComplete = "current-password",
  required = true,
  disabled = false,
  minLength,
  hint,
  error,
}: PasswordFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="space-y-1 text-left">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="block text-[12.5px] font-semibold text-[#111111]">
          {label}
        </label>
        {hint && <span className="text-[11.5px] text-[#5F5F5F]">{hint}</span>}
      </div>

      <div className="relative">
        <input
          id={id}
          name={name}
          type={showPassword ? "text" : "password"}
          required={required}
          disabled={disabled}
          autoComplete={autoComplete}
          minLength={minLength}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          className={`w-full h-[40px] pl-3 pr-10 rounded-[8px] border text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed ${
            error
              ? "border-red-400 focus:border-red-500 focus:ring-red-200"
              : "border-[#E6E6E6] focus:border-[#F26B1D] focus:ring-[#F26B1D]/20"
          }`}
        />

        <button
          type="button"
          tabIndex={-1}
          disabled={disabled}
          onClick={() => setShowPassword((prev) => !prev)}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-[#5F5F5F] hover:text-[#111111] focus:text-[#111111] focus:outline-none rounded transition-colors duration-150"
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>

      {error && (
        <p id={`${id}-error`} className="text-[11.5px] text-red-600 font-medium">
          {error}
        </p>
      )}
    </div>
  );
}
