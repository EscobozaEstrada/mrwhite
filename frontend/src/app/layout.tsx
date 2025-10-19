import type { Metadata } from "next";
import { Geist, Geist_Mono, Work_Sans, Public_Sans } from "next/font/google";
import "./globals.css";
import Image from "next/image";
import Link from "next/link";
import { GiChatBubble } from "react-icons/gi";
import { Button } from "@/components/ui/button";
import { IoChatbubble } from "react-icons/io5";
import { TbLogin } from "react-icons/tb";
import Navbar from "@/components/Navbar";
import ImagePop from "@/components/ImagePop";
import Footer from "@/components/Footer";
import { AuthProvider } from "@/context/AuthContext";
import NextTopLoader from 'nextjs-toploader';

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
    url: process.env.NEXT_PUBLIC_FRONTEND_URL || "http://localhost:3005",
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
        {/* <Navbar /> */}
        <AuthProvider>
          {children}
        </AuthProvider>
        {/* <Footer /> */}
      </body>
    </html>
  );
}
