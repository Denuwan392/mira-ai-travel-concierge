import React, { useMemo } from "react";
import MarkdownIt from "markdown-it";

export interface MarkdownContentProps {
  content: string;
  stripLeadingH1?: boolean;
  parentTitle?: string;
  className?: string;
}

interface ASTNode {
  tag: string;
  attrs: Record<string, string>;
  children: (ASTNode | string)[];
}

const md = new MarkdownIt({
  html: false, // Strictly disable HTML tags to prevent XSS
  xhtmlOut: false,
  breaks: true, // Respect line breaks
  linkify: true, // Auto-detect URLs
  typographer: false,
});

function isSafeUrl(url: string): boolean {
  if (!url) return false;
  const trimmed = url.trim().toLowerCase();
  return (
    trimmed.startsWith("https://") ||
    trimmed.startsWith("http://") ||
    trimmed.startsWith("mailto:") ||
    trimmed.startsWith("#") ||
    (trimmed.startsWith("/") && !trimmed.startsWith("//"))
  );
}

function parseInlines(children: MarkdownIt.Token[] | null): (ASTNode | string)[] {
  if (!children || children.length === 0) return [];
  const result: (ASTNode | string)[] = [];
  const stack: { tag: string | null; attrs: Record<string, string>; children: (ASTNode | string)[] }[] = [
    { tag: null, attrs: {}, children: result },
  ];

  for (const token of children) {
    if (token.type === "text") {
      stack[stack.length - 1]!.children.push(token.content);
    } else if (token.type === "code_inline") {
      stack[stack.length - 1]!.children.push({
        tag: "code",
        attrs: {},
        children: [token.content],
      });
    } else if (token.type === "softbreak" || token.type === "hardbreak") {
      stack[stack.length - 1]!.children.push({
        tag: "br",
        attrs: {},
        children: [],
      });
    } else if (token.type.endsWith("_open")) {
      const tag = token.tag;
      const attrs = Object.fromEntries(token.attrs || []);
      const node: ASTNode = { tag, attrs, children: [] };
      stack[stack.length - 1]!.children.push(node);
      stack.push(node);
    } else if (token.type.endsWith("_close")) {
      if (stack.length > 1) {
        stack.pop();
      }
    }
  }

  return result;
}

function parseTokensToAST(
  tokens: MarkdownIt.Token[],
  options: { stripLeadingH1?: boolean | undefined; parentTitle?: string | undefined } = {},
): ASTNode[] {
  const { stripLeadingH1 = false, parentTitle = "" } = options;
  const result: ASTNode[] = [];
  const stack: { tag: string | null; attrs: Record<string, string>; children: (ASTNode | string)[] }[] = [
    { tag: null, attrs: {}, children: result },
  ];

  let skipUntilIndex = -1;

  // Problem 7: Check if the very first block is an H1 that duplicates the card title or should be stripped
  if (tokens.length >= 3 && tokens[0]?.type === "heading_open" && tokens[0]?.tag === "h1") {
    const inlineToken = tokens[1];
    const h1Text = inlineToken?.content?.trim() || "";
    const matchesParent =
      parentTitle && h1Text.toLowerCase() === parentTitle.trim().toLowerCase();

    if (stripLeadingH1 || matchesParent) {
      skipUntilIndex = 2; // skip heading_open (0), inline (1), heading_close (2)
    }
  }

  for (let i = 0; i < tokens.length; i++) {
    if (i <= skipUntilIndex) continue;
    const token = tokens[i]!;

    if (token.type === "inline") {
      const inlines = parseInlines(token.children);
      stack[stack.length - 1]!.children.push(...inlines);
    } else if (token.type.endsWith("_open")) {
      const tag = token.tag;
      const attrs = Object.fromEntries(token.attrs || []);
      const node: ASTNode = { tag, attrs, children: [] };
      stack[stack.length - 1]!.children.push(node);
      stack.push(node);
    } else if (token.type.endsWith("_close")) {
      if (stack.length > 1) {
        stack.pop();
      }
    }
  }

  return result;
}

function renderASTNode(node: ASTNode | string, key: string | number): React.ReactNode {
  if (typeof node === "string") {
    return node;
  }

  const { tag, attrs, children } = node;
  const renderedChildren = children.map((child, idx) =>
    renderASTNode(child, `${key}-${idx}`),
  );

  // Link safety enforcement
  if (tag === "a") {
    const href = attrs["href"] || "";
    if (!isSafeUrl(href)) {
      return (
        <span key={key} className="unsafe-link-text">
          {renderedChildren}
        </span>
      );
    }
    return (
      <a
        key={key}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="markdown-link"
      >
        {renderedChildren}
      </a>
    );
  }

  if (tag === "br") {
    return <br key={key} />;
  }

  // Self-closing void tags
  if (tag === "hr") {
    return <hr key={key} />;
  }

  // Valid standard HTML tags only
  const validTags = new Set([
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "strong",
    "em",
    "span",
  ]);

  const ComponentTag = (validTags.has(tag) ? tag : "div") as keyof React.JSX.IntrinsicElements;

  return React.createElement(ComponentTag, { key }, renderedChildren);
}

export function MarkdownContent({
  content,
  stripLeadingH1 = false,
  parentTitle,
  className = "markdown-content",
}: MarkdownContentProps) {
  const ast = useMemo(() => {
    if (!content || !content.trim()) return [];
    try {
      const tokens = md.parse(content, {});
      return parseTokensToAST(tokens, { stripLeadingH1, parentTitle });
    } catch {
      return [];
    }
  }, [content, stripLeadingH1, parentTitle]);

  if (!content || !content.trim()) {
    return null;
  }

  if (ast.length === 0) {
    return <div className={className}>{content}</div>;
  }

  return (
    <div className={className}>
      {ast.map((node, index) => renderASTNode(node, index))}
    </div>
  );
}
