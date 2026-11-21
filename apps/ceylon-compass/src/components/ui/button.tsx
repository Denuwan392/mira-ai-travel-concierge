import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium cursor-pointer select-none transition-[background-color,color,border-color,transform,box-shadow] duration-150 ease-out active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-saffron disabled:pointer-events-none disabled:opacity-45 disabled:cursor-not-allowed [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-ink text-on-dark hover:bg-charcoal-soft",
        saffron: "bg-saffron text-ink hover:bg-saffron-bright shadow-soft",
        ink: "bg-ink text-on-dark hover:bg-charcoal-soft",
        paper: "bg-card text-ink hover:bg-paper-deep",
        destructive: "bg-destructive text-destructive-foreground hover:bg-maroon",
        outline: "border border-input bg-transparent text-ink hover:border-ink hover:bg-card",
        "outline-light":
          "border border-on-dark/40 bg-transparent text-on-dark hover:border-on-dark hover:bg-on-dark/10",
        secondary: "bg-secondary text-secondary-foreground hover:bg-border",
        ghost: "text-ink hover:bg-paper-deep",
        "ghost-light": "text-on-dark hover:bg-on-dark/10",
        link: "text-ink underline-offset-4 hover:underline rounded-md",
        chip: "border border-border bg-card text-ink hover:border-ink data-[active=true]:border-ink data-[active=true]:bg-ink data-[active=true]:text-on-dark",
        "chip-dark":
          "border border-line-dark bg-transparent text-on-dark hover:border-on-dark/60 data-[active=true]:border-saffron data-[active=true]:bg-saffron data-[active=true]:text-ink",
      },
      size: {
        default: "min-h-11 px-5 py-2.5",
        sm: "min-h-11 px-4 text-[13px]",
        lg: "min-h-12 px-7 text-[15px]",
        xl: "min-h-14 px-8 text-base",
        icon: "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
