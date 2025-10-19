import { Metadata } from 'next';
import GoogleDocsStylePDFReader from '@/components/GoogleDocsStylePDFReader';

export const metadata: Metadata = {
    title: 'The Way of the Dog | Mr. White',
    description: 'Read "The Way of the Dog" with Google Docs-style commenting, text selection, and collaborative note-taking features.',
    keywords: 'dog training, Anahata, book, reading, Google Docs, commenting, text selection, collaborative notes, PDF reader',
    openGraph: {
        title: 'The Way of the Dog - A guide to intuitive bonding',
        description: 'Experience advanced PDF reading with Google Docs-style commenting and text selection features.',
        type: 'website',
        images: [
            {
                url: '/assets/way-of-dog-hero.webp',
                width: 1200,
                height: 630,
                alt: 'The Way of the Dog Anahata Book Cover',
            },
        ],
    },
    twitter: {
        card: 'summary_large_image',
        title: 'The Way of the Dog Anahata - A guide to intuitive bonding',
        description: 'Advanced PDF reading with Google Docs-style commenting and text selection.',
        images: ['/assets/way-of-dog-hero.webp'],
    },
    viewport: 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no',
};

export default function BookPage() {
    return (
        <div className="min-h-screen w-full max-w-full overflow-hidden">
            <GoogleDocsStylePDFReader />
        </div>
    );
}