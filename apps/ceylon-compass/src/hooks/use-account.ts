import { useEffect, useState } from "react";
import { getAccount, type DemoAccount } from "@/lib/trip/storage";

export function useAccount() {
  const [account, setAccount] = useState<DemoAccount | null>(null);
  useEffect(() => {
    const update = () => setAccount(getAccount());
    update();
    window.addEventListener("cch:storage", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("cch:storage", update);
      window.removeEventListener("storage", update);
    };
  }, []);
  return account;
}
