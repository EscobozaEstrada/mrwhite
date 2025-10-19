"use client";

import { usePathname } from 'next/navigation';
import SchemaMarkup from './SchemaMarkup';
import { generateWebsiteSchema } from '@/lib/schema';
import Script from 'next/script';

interface SEOProps {
  schema?: Record<string, any>;
  noindex?: boolean;
  nofollow?: boolean;
}

/**
 * SEO component for adding page-specific SEO enhancements
 */
export default function SEO({ schema, noindex = false, nofollow = false }: SEOProps) {
  const pathname = usePathname();
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';
  const canonicalUrl = `${baseUrl}${pathname}`;

  // Default schema is the website/organization schema
  const defaultSchema = generateWebsiteSchema({
    name: 'Mr. White',
    url: baseUrl,
    description: 'AI-powered dog care assistant and guide for all dog breeds',
    logo: '/assets/logo.png',
    sameAs: [
      'https://twitter.com/MrWhiteAIBuddy',
      'https://www.instagram.com/mrwhiteai',
      'https://www.facebook.com/mrwhiteai'
    ],
  });

  return (
    <>
      {/* Canonical URL */}
      <link rel="canonical" href={canonicalUrl} />

      {/* Robots meta tag */}
      {(noindex || nofollow) && (
        <meta
          name="robots"
          content={`${noindex ? 'noindex' : 'index'}, ${nofollow ? 'nofollow' : 'follow'}`}
        />
      )}

      {/* Structured data */}
      <SchemaMarkup schema={schema || defaultSchema} />

      {/* Google Tag Manager */}
      {process.env.NEXT_PUBLIC_GTM_ID && (
        <Script
          id="gtm-script"
          strategy="afterInteractive"
          dangerouslySetInnerHTML={{
            __html: `
              (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
              new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
              j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
              'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
              })(window,document,'script','dataLayer','${process.env.NEXT_PUBLIC_GTM_ID}');
            `,
          }}
        />
      )}
    </>
  );
} 