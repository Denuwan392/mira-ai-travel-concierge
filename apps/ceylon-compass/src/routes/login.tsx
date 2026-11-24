import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { AuthField } from "@/components/auth/AuthField";
import { AuthSplitLayout } from "@/components/auth/AuthSplitLayout";
import { PasswordField } from "@/components/auth/PasswordField";
import { api } from "@/lib/live/service";
import { photos } from "@/lib/photos";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setStatus("");

    try {
      const res = await api<{ id: string; role: string; full_name: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password, remember }),
      });
      window.dispatchEvent(new CustomEvent("cch:auth", { detail: res }));
      setStatus("Signed in successfully. Redirecting…");

      const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const redirect = params?.get("redirect");
      const safeRedirect = redirect && redirect.startsWith("/") && !redirect.startsWith("//") ? redirect : null;

      setTimeout(() => {
        if (safeRedirect) {
          router.navigate({ to: safeRedirect });
        } else if (["staff", "editor", "approver", "admin"].includes(res.role)) {
          router.navigate({ to: "/staff" });
        } else {
          router.navigate({ to: "/profile" });
        }
      }, 400);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed to sign in. Please verify your credentials.");
    } finally {
      setBusy(false);
    }
  }

  const isSuccess = status.includes("successfully");

  return (
    <AuthSplitLayout
      imageSrc={photos.sigiriyaAerial.src}
      imageAlt={photos.sigiriyaAerial.alt}
      eyebrow="CEYLON COMPASS HOLIDAYS"
      headline="Your next story begins in Sri Lanka."
      subtext="Discover remarkable places, thoughtful journeys, and experiences designed around you."
      cardClassName="md:min-h-[580px] lg:min-h-[584px]"
    >
      <div className="text-left flex flex-col justify-center py-2 sm:py-3">
        <h1 className="text-[24px] sm:text-[26px] font-bold text-[#111111] tracking-[-0.03em] leading-tight">
          Welcome back
        </h1>
        <p className="text-[13px] text-[#5F5F5F] mt-1.5 leading-normal">
          Sign in to continue your Sri Lanka journey.
        </p>

        {status && (
          <div
            role={isSuccess ? "status" : "alert"}
            className={`my-3.5 p-3 rounded-[8px] text-[12.5px] font-medium flex items-start gap-2.5 transition-all duration-150 ${
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

        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          <AuthField
            id="login-email"
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
            id="login-password"
            label="Password"
            required
            autoComplete="current-password"
            value={password}
            disabled={busy}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />

          <div className="pt-0.5">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                className="size-3.5 rounded-[4px] border-[#E6E6E6] text-[#F26B1D] accent-[#F26B1D] focus:ring-[#F26B1D]/20 cursor-pointer"
                checked={remember}
                disabled={busy}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <span className="text-[12.5px] text-[#5F5F5F]">Remember this browser for 30 days</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full h-[43px] rounded-full bg-[#F26B1D] hover:bg-[#d95a12] active:bg-[#c44f0e] text-white text-[13.5px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] focus-visible:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed mt-2.5"
          >
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                <span>Signing in…</span>
              </>
            ) : (
              <span>Sign in</span>
            )}
          </button>
        </form>

        <p className="text-[12.5px] text-[#5F5F5F] text-center mt-5">
          New to Ceylon Compass?{" "}
          <Link
            to="/register"
            className="font-semibold text-[#F26B1D] hover:underline focus:outline-none focus-visible:ring-1 focus-visible:ring-[#F26B1D] rounded"
          >
            Create an account
          </Link>
        </p>

        <div className="mt-6 pt-3.5 border-t border-[#E6E6E6] text-[11px] text-[#5F5F5F] text-center leading-normal">
          Staff, Approvers, and Admins can sign in here to access the Staff Console.
        </div>
      </div>
    </AuthSplitLayout>
  );
}
