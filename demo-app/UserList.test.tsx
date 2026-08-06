import { describe, it, expect } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { UserList } from "./UserList";

describe("UserList", () => {
  it("renders user names from items array", () => {
    const data = { items: [{ name: "Hazel" }, { name: "Alex" }] };
    const html = renderToStaticMarkup(createElement(UserList, { data }));
    expect(html).toContain("Hazel");
    expect(html).toContain("Alex");
  });

  it("renders empty list when items is undefined", () => {
    const data = {};
    const html = renderToStaticMarkup(createElement(UserList, { data }));
    expect(html).toBe("<ul></ul>");
  });

  it("renders empty list when items is empty", () => {
    const data = { items: [] };
    const html = renderToStaticMarkup(createElement(UserList, { data }));
    expect(html).toBe("<ul></ul>");
  });
});
