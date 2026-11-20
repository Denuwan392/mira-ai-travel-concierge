"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

const Assistant = dynamic(() => import("./assistant"), { ssr: false });
export type Launch = { id: number; prompt?: string; browse?: boolean };
const Launcher = createContext<(prompt?: string, browse?: boolean) => void>(
  () => {},
);
export const useMira = () => useContext(Launcher);

export function MiraShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [request, setRequest] = useState<Launch>();
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const trigger = useRef<HTMLElement | null>(null);
  const previousPath = useRef(path);
  const open = useCallback((prompt?: string, browse = false) => {
    trigger.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setVisible(true);
    setRequest((last) => ({ id: (last?.id ?? 0) + 1, prompt, browse }));
  }, []);
  const close = useCallback(() => {
    setVisible(false);
    requestAnimationFrame(
      () =>
        trigger.current?.isConnected &&
        trigger.current.focus({ preventScroll: true }),
    );
  }, []);
  useEffect(() => {
    if (previousPath.current !== path) {
      setVisible(false);
      previousPath.current = path;
    }
    if (path === "/plan" && location.hash === "#destinations")
      open(undefined, true);
  }, [path, open]);
  return (
    <Launcher.Provider value={open}>
      <div
        className={"mira-site" + (visible ? " with-assistant" : "")}
        inert={visible && expanded}
      >
        {children}
      </div>
      {request && path !== "/staff" && (
        <Assistant
          visible={visible}
          request={request}
          close={close}
          onExpansion={setExpanded}
        />
      )}
    </Launcher.Provider>
  );
}
