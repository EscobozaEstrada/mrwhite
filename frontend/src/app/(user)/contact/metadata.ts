import { generateMetadata } from '@/lib/metadata';

export const metadata = generateMetadata({
  title: 'Contact Us',
  description: 'Get in touch with the Mr. White team. We\'re here to answer your questions about dog care, training, and our services.',
  keywords: 'contact Mr. White, dog care help, pet assistance, dog training questions',
  path: '/contact',
});

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}; 