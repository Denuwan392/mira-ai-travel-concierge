import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { AuthField } from "@/components/auth/AuthField";
import { AuthSplitLayout } from "@/components/auth/AuthSplitLayout";
import { PasswordField } from "@/components/auth/PasswordField";
import { api } from "@/lib/live/service";
import { photos } from "@/lib/photos";

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setStatus("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setStatus("");

    try {
      const res = await api<{ id: string; role: string; full_name: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          phone: phone.trim(),
          preferences: {},
        }),
      });
      window.dispatchEvent(new CustomEvent("cch:auth", { detail: res }));
      setStatus("Account created successfully! Preparing your notebook…");
      setTimeout(() => {
        router.navigate({ to: "/profile" });
      }, 400);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const isSuccess = status.includes("successfully");

  return (
    <AuthSplitLayout
      imageSrc={photos.nineArchesTrain.src}
      imageAlt={photos.nineArchesTrain.alt}
      eyebrow="CEYLON COMPASS HOLIDAYS"
      headline="Your bespoke Sri Lanka journey awaits."
      subtext="Personalised itineraries, guaranteed transparent rates, and dedicated human concierge support every step of the way."
    >
      <div className="text-left">
        <h1 className="text-[23px] sm:text-[25px] font-bold text-[#111111] tracking-[-0.03em] leading-tight">
          Create your account
        </h1>
        <p className="text-[13px] text-[#5F5F5F] mt-1 leading-normal">
          Keep your journeys, saved quotes, and travel preferences together.
        </p>

        {status && (
          <div
            role={isSuccess ? "status" : "alert"}
            className={`my-3 p-3 rounded-[8px] text-[12.5px] font-medium flex items-start gap-2.5 transition-all duration-150 ${
              isSuccess
                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {isSuccess ? (
              <CheckCircle2 className="size-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="size-4 text-red-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">{status}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-2.5">
          <AuthField
            id="reg-fullname"
            label="Full name"
            type="text"
            required
            autoComplete="name"
            value={fullName}
            disabled={busy}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g. Saman Perera"
          />

          <AuthField
            id="reg-email"
            label="Email address"
            type="email"
            required
            autoComplete="email"
            value={email}
            disabled={busy}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="traveller@example.com"
          />

          <PasswordField
            id="reg-password"
            label="Password"
            required
            autoComplete="new-password"
            minLength={8}
            hint="Min. 8 characters"
            value={password}
            disabled={busy}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />

          <AuthField
            id="reg-phone"
            label="Contact phone"
            type="tel"
            autoComplete="tel"
            hint="Optional"
            value={phone}
            disabled={busy}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+94 77 123 4567"
          />

          <button
            type="submit"
            disabled={busy}
            className="w-full h-[42px] rounded-full bg-[#F26B1D] hover:bg-[#d95a12] active:bg-[#c44f0e] text-white text-[13.5px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] focus-visible:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed mt-2"
          >
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                <span>Creating account…</span>
              </>
            ) : (
              <span>Create account</span>
            )}
          </button>
        </form>

        <p className="text-[12.5px] text-[#5F5F5F] text-center mt-3.5">
          Already travelling with us?{" "}
          <Link
            to="/login"
            className="font-semibold text-[#F26B1D] hover:underline focus:outline-none focus-visible:ring-1 focus-visible:ring-[#F26B1D] rounded"
          >
            Sign in
          </Link>
        </p>

        <div className="mt-4 pt-3 border-t border-[#E6E6E6] text-[11px] text-[#5F5F5F] text-center leading-normal">
          By signing up, your verified quotes and trip notebooks will sync securely across your devices.
        </div>
      </div>
    </AuthSplitLayout>
  );
}
