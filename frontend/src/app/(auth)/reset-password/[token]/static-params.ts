// This is required for static export with dynamic routes
// Since password reset tokens are unpredictable, we return empty array
// The actual routing happens client-side via Next.js router
export function generateStaticParams() {
  return [];
}

export const dynamicParams = true;
