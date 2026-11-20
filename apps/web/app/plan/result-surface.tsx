"use client";

import {
  Fragment,
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { z } from "zod";
import { z as sdkSchema } from "zod3";
import {
  A2uiSurface,
  createBinderlessComponentImplementation,
  type ReactCatalogComponent,
} from "@a2ui/react/v0_9";
import { Catalog, MessageProcessor, childList } from "@a2ui/web_core/v0_9";
import type { Turn, Component } from "../../lib/catalog";

const catalogId = "urn:ceylon-compass:mira:1";
const kinds = [
  "TourCard",
  "TravellerPicker",
  "ItineraryDay",
  "PolicySnippet",
  "DestinationHighlight",
  "PriceBreakdown",
  "BookingForm",
  "EnquiryNotice",
] as const;
const slot = z.object({ index: z.number().int().min(0).max(11) });
const node = z.union([
  z.strictObject({
    id: z.literal("root"),
    component: z.literal("JourneyColumn"),
    children: z.array(z.string()).max(13),
  }),
  z.strictObject({
    id: z.literal("results"),
    component: z.literal("JourneyResults"),
  }),
  z.strictObject({ id: z.string(), component: z.enum(kinds), ...slot.shape }),
]);
const target = z.literal("journey");
export const SurfaceMessages = z.tuple([
  z.strictObject({
    version: z.literal("v0.9"),
    createSurface: z.strictObject({
      surfaceId: target,
      catalogId: z.literal(catalogId),
    }),
  }),
  z.strictObject({
    version: z.literal("v0.9"),
    updateComponents: z.strictObject({
      surfaceId: target,
      components: z.array(node).min(1).max(14),
    }),
  }),
]);
export type SurfaceMessages = z.infer<typeof SurfaceMessages>;
export function readSurface(raw: unknown, turn: Turn) {
  const ops = SurfaceMessages.parse(raw);
  const [root, ...items] = ops[1].updateComponents.components;
  if (
    root.component !== "JourneyColumn" ||
    root.children.length !== items.length ||
    new Set(items.map((item) => item.id)).size !== items.length ||
    items.some(
      (item, i) =>
        root.children[i] !== item.id ||
        item.id === "root" ||
        item.component === "JourneyColumn" ||
        ("index" in item &&
          (item.id !== "item-" + item.index || turn.components[item.index]?.type !== item.component)),
    )
  )
    throw Error("Invalid journey surface.");
  return ops;
}
const View = createContext<{
  items: Component[];
  render: (value: Component) => ReactNode;
  guide: ReactNode;
} | null>(null);
const column = createBinderlessComponentImplementation(
  {
    name: "JourneyColumn",
    schema: sdkSchema.object({ children: childList() }),
  },
  ({ context, buildChild }) => {
    const children = z
      .array(z.string())
      .parse(context.componentModel.properties.children);
    return (
      <div className="advisor-components">
        {children.map((id) => (
          <Fragment key={id}>{buildChild(id)}</Fragment>
        ))}
      </div>
    );
  },
);
const results = createBinderlessComponentImplementation(
  { name: "JourneyResults", schema: sdkSchema.object({}) },
  () => useContext(View)?.guide,
);
const catalog = new Catalog<ReactCatalogComponent>(catalogId, "v0.9", [
  column,
  results,
  ...kinds.map((name) =>
    createBinderlessComponentImplementation(
      { name, schema: sdkSchema.object({ index: sdkSchema.number().int() }) },
      ({ context }) => {
        const view = useContext(View);
        const item =
          view?.items[slot.parse(context.componentModel.properties).index];
        return view && item?.type === name ? view.render(item) : null;
      },
    ),
  ),
]);
export function ResultSurface({
  messages,
  turn,
  render,
  guide,
}: {
  messages: SurfaceMessages;
  turn: Turn;
  render: (value: Component) => ReactNode;
  guide: ReactNode;
}) {
  const model = useMemo(() => {
    const processor = new MessageProcessor<ReactCatalogComponent>([catalog]);
    processor.processMessages(messages);
    return processor.model.surfacesMap.get("journey");
  }, [messages]);
  return (
    model && (
      <View.Provider value={{ items: turn.components, render, guide }}>
        <div data-a2ui-version="v0.9">
          <A2uiSurface surface={model} />
        </div>
      </View.Provider>
    )
  );
}
