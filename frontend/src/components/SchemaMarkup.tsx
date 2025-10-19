"use client";

import Script from 'next/script';

interface SchemaMarkupProps {
  schema: Record<string, any>;
}

/**
 * Component to add structured data to pages
 */
export default function SchemaMarkup({ schema }: SchemaMarkupProps) {
  return (
    <Script
      id="schema-markup"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      strategy="afterInteractive"
    />
  );
}