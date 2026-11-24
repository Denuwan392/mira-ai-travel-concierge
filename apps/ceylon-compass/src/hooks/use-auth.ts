import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/live/service";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: "guest" | "traveller" | "staff" | "approver" | "admin" | string;
  status: "active" | "deactivated" | string;
  phone: string;
  preferences: Record<string, unknown>;
  created_at: string;
};

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      const data = await api<AuthUser>("/auth/me");
      setUser(data);
      setError(null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      // Ignore network failure on logout
    } finally {
      setUser(null);
      window.dispatchEvent(new CustomEvent("cch:auth", { detail: null }));
    }
  }, []);

  useEffect(() => {
    fetchUser();

    const handleAuthChange = () => {
      fetchUser();
    };

    window.addEventListener("cch:auth", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);
    return () => {
      window.removeEventListener("cch:auth", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, [fetchUser]);

  const isStaff = user?.role === "staff" || user?.role === "approver" || user?.role === "admin";
  const isApprover = user?.role === "approver" || user?.role === "admin";
  const isAdmin = user?.role === "admin";

  return {
    user,
    loading,
    error,
    refresh: fetchUser,
    logout,
    isAuthenticated: !!user,
    isStaff,
    isApprover,
    isAdmin,
  };
}
