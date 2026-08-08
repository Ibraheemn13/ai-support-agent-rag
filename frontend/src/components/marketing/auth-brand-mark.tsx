import { Wordmark } from "@/components/common/logo";

/**
 * Brand mark for the auth pages, shown only below the lg breakpoint where the
 * explanation panel is hidden and the form would otherwise have no context.
 */
export function AuthBrandMark() {
  return <Wordmark href="/" className="mb-8 lg:hidden" />;
}
