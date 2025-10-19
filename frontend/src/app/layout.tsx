import type { Metadata } from "next";
import { Geist, Geist_Mono, Work_Sans, Public_Sans } from "next/font/google";
import "./globals.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { AuthProvider } from "@/context/AuthContext";
import NextTopLoader from 'nextjs-toploader';
import { Toaster } from 'react-hot-toast';
import Script from 'next/script';
import { TimezoneDetector } from '@/components/TimezoneDetector';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const workSans = Work_Sans({
  variable: "--font-work-sans",
  subsets: ["latin"],
  display: "swap",
})

const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
  display: "swap",
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_APP_TITLE || "Mr. White - AI Dog Care Assistant",
  description: process.env.NEXT_PUBLIC_APP_DESCRIPTION || "Your AI-powered companion for comprehensive dog care advice, training tips, and personalized guidance for all dog breeds",
  keywords: "dog care, AI pet assistant, dog training, dog health, pet advice, Mr. White, dog breeds, puppy care, dog nutrition, pet health",
  authors: [{ name: "Mr. White Team" }],
  creator: "Mr. White",
  publisher: "Mr. White",
  formatDetection: {
    email: false,
    telephone: false,
    address: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_FRONTEND_URL || "https://mrwhiteaidogbuddy.com/"),
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-video-preview': -1,
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: process.env.NEXT_PUBLIC_FRONTEND_URL,
    title: process.env.NEXT_PUBLIC_APP_TITLE || "Mr. White - AI Dog Care Assistant",
    description: process.env.NEXT_PUBLIC_APP_DESCRIPTION || "Your AI-powered companion for comprehensive dog care advice, training tips, and personalized guidance for all dog breeds",
    siteName: "Mr. White",
    images: [
      {
        url: "/assets/logo.png",
        width: 1200,
        height: 630,
        alt: "Mr. White - AI Dog Care Assistant",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: process.env.NEXT_PUBLIC_APP_TITLE || "Mr. White - AI Dog Care Assistant",
    description: process.env.NEXT_PUBLIC_APP_DESCRIPTION || "Your AI-powered companion for comprehensive dog care advice, training tips, and personalized guidance for all dog breeds",
    images: ["/assets/logo.png"],
    creator: "@mrwhiteai",
  },
  verification: {
    google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        {/* Head content is managed by Next.js */}
      </head>
      <body
        suppressHydrationWarning
        className={`${geistSans.variable} ${geistMono.variable} ${workSans.variable} ${publicSans.variable} antialiased`}
      >
        <NextTopLoader
          color="#D3B86A"
          showSpinner={false}
          height={3}
          shadow="0 0 10px #2563eb,0 0 5px #2563eb"
        />
        <Toaster
          position="bottom-center"
          toastOptions={{
            duration: 3000,
            style: {
              background: '#333',
              color: '#fff',
              border: '1px solid #D3B86A',
            },
          }}
        />
        {/* <Navbar /> */}
        <AuthProvider>
          <TimezoneDetector />
          {children}
        </AuthProvider>
        {/* <Footer /> */}
        
        {/* Initialize sound preloading */}
        <Script id="preload-sounds">
          {`
            if (typeof window !== 'undefined') {
              try {
                // Preload sound files
                const sounds = ['/sounds/success.mp3', '/sounds/error.mp3'];
                sounds.forEach(src => {
                  const audio = new Audio();
                  audio.preload = 'auto';
                  audio.src = src;
                });
              } catch (e) {
                console.error('Error preloading sounds:', e);
              }
            }
          `}
        </Script>
      </body>
    </html>
  );
}
