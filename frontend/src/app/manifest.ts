import { MetadataRoute } from 'next';

// Required for static export
export const dynamic = 'force-static';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Mr. White - AI Dog Care Assistant',
    short_name: 'Mr. White',
    description: 'Your AI-powered companion for comprehensive dog care advice, training tips, and personalized guidance for all dog breeds',
    start_url: '/',
    display: 'standalone',
    background_color: '#000000',
    theme_color: '#D3B86A',
    icons: [
      {
        src: '/assets/logo.png',
        sizes: '47x47',
        type: 'image/png',
      },
    ],
  };
} 