import { Metadata } from 'next';

type MetadataProps = {
  title?: string;
  description?: string;
  keywords?: string;
  path?: string;
  image?: string;
};

export function generateMetadata({
  title,
  description,
  keywords,
  path = '',
  image = '/assets/og-image.jpg',
}: MetadataProps): Metadata {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com';
  const baseTitle = process.env.NEXT_PUBLIC_APP_TITLE || 'Mr. White - AI Dog Care Assistant';
  const baseDescription = process.env.NEXT_PUBLIC_APP_DESCRIPTION ||
    'Your AI-powered companion for comprehensive dog care advice, training tips, and personalized guidance for all dog breeds';

  const pageTitle = title ? `${title} | ${baseTitle.split(' - ')[0]}` : baseTitle;
  const pageDescription = description || baseDescription;
  const pageKeywords = keywords || 'dog care, AI pet assistant, dog training, dog health, pet advice';
  const canonical = `${baseUrl}${path}`;

  return {
    title: pageTitle,
    description: pageDescription,
    keywords: pageKeywords,
    alternates: {
      canonical: canonical,
    },
    openGraph: {
      title: pageTitle,
      description: pageDescription,
      url: canonical,
      images: [
        {
          url: image.startsWith('http') ? image : `${baseUrl}${image}`,
          width: 1200,
          height: 630,
          alt: pageTitle,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: pageTitle,
      description: pageDescription,
      images: [image.startsWith('http') ? image : `${baseUrl}${image}`],
    },
  };
} 