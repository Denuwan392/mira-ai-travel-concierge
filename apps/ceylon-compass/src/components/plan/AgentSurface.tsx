"use client";

import { Fragment, createContext, useContext, useMemo, type ReactNode } from "react";
import { z } from "zod/v4";
import { z as sdkSchema } from "zod3";
import {
  A2uiSurface,
  createBinderlessComponentImplementation,
  type ReactCatalogComponent,
} from "@a2ui/react/v0_9";
import { Catalog, MessageProcessor, childList } from "@a2ui/web_core/v0_9";
import type { Turn, Component } from "@/lib/live/catalog";

import { catalogId, kinds, slot, type SurfaceMessages } from "@/lib/live/surface";
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
    const children = z.array(z.string()).parse(context.componentModel.properties["children"]);
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
        const item = view?.items[slot.parse(context.componentModel.properties).index];
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
