import { MetadataRoute } from 'next';

// Required for static export
export const dynamic = 'force-static';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';

  // Define your main routes
  const routes = [
    '',
    '/about',
    '/subscription',
    '/questbook',
    '/product',
    '/hub',
    '/payment',
    '/contact',
    '/login',
  ].map(route => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: route === '' ? 1 : 0.8,
  }));

  return routes;
} 