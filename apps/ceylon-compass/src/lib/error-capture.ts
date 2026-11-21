const events = ["ssr.failed", "ssr.invalid_response", "proxy.failed"] as const;
type Event = typeof events[number];

export function reportFailure(event: Event, requestId?: string, status?: number) {
  // Avoid exception messages, request URLs and payloads in both browser and server logs.
  console.error(JSON.stringify({
    component: "WEB",
    level: "ERROR",
    event,
    ...(requestId && /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(requestId) && { request_id: requestId }),
    ...(status !== undefined && { status }),
  }));
}
