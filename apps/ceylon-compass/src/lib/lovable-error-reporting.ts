export function reportLovableError() {
  if (typeof window === "undefined") return;
  // The editor receives a fixed diagnostic without the original exception or URL.
  const editor = window as Window & {
    __lovableReportRuntimeError?: (payload: { message: string }) => void;
  };
  editor.__lovableReportRuntimeError?.({ message: "A traveller page could not render." });
}
