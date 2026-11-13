import type { ButtonHTMLAttributes } from "react";
import { actionVariantClassName } from "../constants";

type ButtonVariant = "positive" | "danger" | "tab";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  active?: boolean;
  variant?: ButtonVariant;
};

export function Button({
  active = false,
  className = "",
  variant = "positive",
  ...props
}: ButtonProps) {
  const variantClassName = variant === "tab"
    ? `px-3 py-2 text-ui font-semibold transition-colors max-sm:px-2 max-sm:text-caption ${
        active
          ? "bg-surface-brand text-brand-strong"
          : "bg-clear text-ink-subtle hover:bg-surface-muted hover:text-brand-strong"
      }`
    : `px-4 py-2 text-small font-semibold text-brand-strong transition hover:brightness-95 ${actionVariantClassName[variant]}`;

  return (
    <button
      {...props}
      className={`cursor-pointer rounded-md border-0 focus-visible:outline-3 focus-visible:outline-focus focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${variantClassName} ${className}`}
    />
  );
}
