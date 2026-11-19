export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : "The service couldn’t complete this request.");
  }
  return response.json();
}

export function money(usd: number) {
  return `USD ${usd.toLocaleString("en-US")}`;
}

export const starters = ["A Sigiriya day trip", "A family adventure", "Design a custom journey"] as const;
