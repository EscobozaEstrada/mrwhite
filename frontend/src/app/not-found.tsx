'use client'
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Metadata } from 'next';
import ImagePop from '@/components/ImagePop';
import SpaceScene from '@/components/SpaceScene';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';



export default function NotFound() {
  const handleGoBack = () => {
    window.history.back();
  };
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16 relative overflow-hidden">
      <SpaceScene />
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        onClick={handleGoBack}
        className="absolute top-4 left-4 text-gray-400 hover:text-white flex items-center gap-2 z-20"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </motion.button>
      
      <div className="w-[100px] h-[100px] relative mb-8 z-10">
        <ImagePop
          src="/assets/logo1.png"
          alt="Mr. White Logo"
          fill
          containerClassName="w-full h-full"
        />
      </div>
      
      <h1 className="text-4xl md:text-5xl font-bold mb-4 text-center z-10 text-white">404 - Page Not Found</h1>
      
      <p className="text-xl md:text-2xl mb-8 text-center max-w-[600px] text-gray-300 z-10">
        Oops! The page you are looking for seems to have wandered off into deep space. Let's get you back on track.
      </p>
      
      <div className="flex flex-col sm:flex-row gap-4 z-10">
        <Button asChild size="lg" className="bg-[var(--mrwhite-primary-color)] text-black font-public-sans font-bold text-lg hover:bg-[var(--mrwhite-primary-color)]/80">
          <Link href="/">
            Return to Homepage
          </Link>
        </Button>
        
        <Button asChild variant="outline" size="lg" className="border-purple-600 text-white hover:bg-purple-900/20 text-lg font-bold">
          <Link href="/contact">
            Contact Support
          </Link>
        </Button>
      </div>
    </div>
  );
} 