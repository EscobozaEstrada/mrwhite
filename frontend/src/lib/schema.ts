/**
 * Helper functions to generate structured data for SEO
 */

export type WebsiteSchema = {
  name: string;
  url: string;
  description?: string;
  logo?: string;
  sameAs?: string[];
};

export type FAQItemSchema = {
  question: string;
  answer: string;
};

/**
 * Generate Website/Organization Schema
 */
export function generateWebsiteSchema(data: WebsiteSchema) {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';

  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: data.name,
    url: data.url || baseUrl,
    logo: data.logo ? (data.logo.startsWith('http') ? data.logo : `${baseUrl}${data.logo}`) : `${baseUrl}/assets/logo.png`,
    description: data.description || 'AI-powered dog care assistant and guide for all dog breeds',
    sameAs: data.sameAs || [],
  };
}

/**
 * Generate FAQ Schema
 */
export function generateFAQSchema(items: FAQItemSchema[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map(item => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  };
}

/**
 * Generate BreadcrumbList Schema
 */
export function generateBreadcrumbSchema(items: { name: string; url: string }[]) {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';

  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url.startsWith('http') ? item.url : `${baseUrl}${item.url}`,
    })),
  };
}

/**
 * Generate Product Schema
 */
export function generateProductSchema({
  name,
  description,
  image,
  price,
  currency = 'USD',
  availability = 'https://schema.org/InStock',
  url,
}: {
  name: string;
  description: string;
  image: string;
  price: number;
  currency?: string;
  availability?: string;
  url?: string;
}) {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';

  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name,
    description,
    image: image.startsWith('http') ? image : `${baseUrl}${image}`,
    offers: {
      '@type': 'Offer',
      price,
      priceCurrency: currency,
      availability,
      url: url || baseUrl,
    },
  };
} 