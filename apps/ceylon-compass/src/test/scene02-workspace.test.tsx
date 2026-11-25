import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
// @ts-expect-error JSX workspace module without .d.ts
import { MiraWorkspace } from "../../workspace/Workspace.jsx";

const state = vi.hoisted(() => ({items: [] as ReturnType<typeof turn>[], input: "", busy: false, ready: true, send: vi.fn()}));
vi.mock("../../workspace/useConversation", () => ({useConversation: () => state}));
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  state.busy = false;
  state.items = [];
});
const workspace = () => <MiraWorkspace navigate={() => {}} />;
function turn(trace: string, ...components: object[]) {
  return {prompt: trace, turn: {trace, text: trace, components}};
}
const picker = {type: "TravellerPicker", tour: "T01", date: "2027-01-10", adults: 2, ages: [1, 7]};
const quote = {type: "PriceBreakdown", quote: {id: "test-q", source: "T09", date: "2027-05-03",
  title: "Cultural Triangle Sri Lanka Package", adults: 2, ages: [], total: 2125, deposit: 532, balance: 1593}};

it("replaces a January family configuration with the May two-adult quote, including on restore", () => {
  state.items = [turn("family", picker)];
  const view = render(workspace());
  expect(screen.getByLabelText("Travel date")).toHaveValue(picker.date);
  expect(screen.getByLabelText(/Child ages/)).toHaveValue("7");
  state.items = [...state.items, turn("updated", quote)];
  view.rerender(workspace());
  const verify = () => {
    const panel = within(screen.getByRole("region", {name:"Verified quote"}));
    expect(panel.getByText("2027-05-03")).toBeVisible();
    expect(panel.getByText("2 adults")).toBeVisible();
    expect(panel.getByRole("button", {name:"Try mock booking"})).toBeEnabled();
  };
  verify();
  view.unmount();
  render(workspace());
  verify();
});

it("keeps checkout disabled when the traveller edits the picker after requesting rates", () => {
  state.items = [turn("picker", {...picker, tour: "T09", date: quote.quote.date, ages: []})];
  const view = render(workspace());
  fireEvent.click(screen.getByRole("button", {name:"Check rates"}));
  fireEvent.change(screen.getByLabelText("Travel date"), {target: {value:"2027-05-04"}});
  state.items = [...state.items, turn("earlier request", quote)];
  view.rerender(workspace());
  const stale = within(screen.getByRole("region", {name:"Outdated quote"}));
  expect(stale.getByRole("button", {name:"Try mock booking"})).toBeDisabled();
});

it("links route pins and day photos and opens a source-backed recommendation", () => {
  const days = [{source:"D03",name:"Kandy",passage:"Kandy stop"}, {source:"D05",name:"Ella",passage:"Ella stop"}];
  state.items = [turn("custom", {type:"JourneyPlan",days,selected:0}, {type:"InteractiveMap",days,selected:0},
    {type:"TourCard",id:"T09",source:"T09",title:quote.quote.title})];
  render(workspace());
  expect(screen.getByRole("img", {name:/Kandy Lake/})).toBeVisible();
  fireEvent.click(screen.getByRole("button", {name:"Ella"}));
  expect(screen.getByRole("img", {name:/Nine Arch Bridge in Ella/})).toBeVisible();
  expect(screen.getByRole("button", {name:"Ella"})).toHaveAttribute("aria-pressed","true");
  fireEvent.click(screen.getByRole("button", {name:"Explore itinerary"}));
  expect(screen.getByRole("button", {name:"Check rates"})).toBeVisible();
});
