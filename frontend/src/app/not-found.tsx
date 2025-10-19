import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Metadata } from 'next';
import ImagePop from '@/components/ImagePop';

export const metadata: Metadata = {
  title: 'Page Not Found | Mr. White',
  description: 'The page you are looking for does not exist. Return to Mr. White homepage.',
  robots: {
    index: false,
    follow: true,
  },
};

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16 bg-black">
      <div className="w-[100px] h-[100px] relative mb-8">
        <ImagePop
          src="/assets/logo1.png"
          alt="Mr. White Logo"
          fill
          containerClassName="w-full h-full"
        />
      </div>
      
      <h1 className="text-4xl md:text-5xl font-bold mb-4 text-center">404 - Page Not Found</h1>
      
      <p className="text-xl md:text-2xl mb-8 text-center max-w-[600px] text-gray-300">
        Oops! The page you are looking for seems to have wandered off. Let's get you back on track.
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4">
        <Button asChild size="lg">
          <Link href="/">
            Return to Homepage
          </Link>
        </Button>
        
        <Button asChild variant="outline" size="lg">
          <Link href="/contact">
            Contact Support
          </Link>
        </Button>
      </div>
    </div>
  );
} 