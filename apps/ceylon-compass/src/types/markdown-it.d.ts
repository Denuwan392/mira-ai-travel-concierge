declare module "markdown-it" {
  namespace MarkdownIt {
    interface Token {
      type: string;
      tag: string;
      attrs: [string, string][] | null;
      map: [number, number] | null;
      nesting: number;
      level: number;
      children: Token[] | null;
      content: string;
      markup: string;
      info: string;
      meta: unknown;
      block: boolean;
      hidden: boolean;
    }

    interface Options {
      html?: boolean;
      xhtmlOut?: boolean;
      breaks?: boolean;
      langPrefix?: string;
      linkify?: boolean;
      typographer?: boolean;
      quotes?: string | string[];
      highlight?: (str: string, lang: string) => string;
    }
  }

  interface MarkdownItInstance {
    parse(src: string, env: unknown): MarkdownIt.Token[];
    render(src: string, env?: unknown): string;
  }

  interface MarkdownItConstructor {
    new (options?: MarkdownIt.Options): MarkdownItInstance;
    (options?: MarkdownIt.Options): MarkdownItInstance;
  }

  const MarkdownIt: MarkdownItConstructor;
  export default MarkdownIt;
}
