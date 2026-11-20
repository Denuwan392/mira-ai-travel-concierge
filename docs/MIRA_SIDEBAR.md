# Mira sidebar and A2UI results

“Plan with Mira”, the homepage prompt and the destination photos open one shared assistant on the left. The homepage stays visible while the assistant is open. When the agent returns a journey, its results open on the right. The standalone `/plan` entrance uses the same assistant and conversation state. On phones, Conversation and Journey switch between the two panes.

The LangGraph response emits A2UI v0.9 `createSurface` and `updateComponents` operations in AG-UI state. The frontend checks the operations and their references against the validated turn, then mounts them with the official `@a2ui/react` and `@a2ui/web_core` 0.15.0 packages. A tour discovery mounts the interactive results list. A selected tour or quote mounts just its detail components. The protocol state travels through the existing CopilotKit runtime.

Example of the layout operations for an Ella discovery, with component data sent in the validated turn:

```json
[
  {"version":"v0.9","createSurface":{"surfaceId":"journey","catalogId":"urn:ceylon-compass:mira:1"}},
  {"version":"v0.9","updateComponents":{"surfaceId":"journey","components":[
    {"id":"root","component":"JourneyColumn","children":["item-0","results"]},
    {"id":"item-0","component":"DestinationHighlight","index":0},
    {"id":"results","component":"JourneyResults"}
  ]}}
]
```

The trusted components handle map filters, day selection and comparison. Quote and booking actions use the existing validated commands and APIs. The sidebar scope covers result composition and presentation. Persisted editing of individual itinerary stops and live Langfuse verification remain separate work.

[Homepage](screenshots/after/home-split-1440.jpg) · [Homepage sidebar](screenshots/after/sidebar-home-1440.jpg) · [Desktop Ella results](screenshots/after/sidebar-ella-1440.jpg) · [Mobile Ella results](screenshots/after/sidebar-ella-390.jpg)
