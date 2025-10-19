'use client';

import { useEffect, useRef } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import Image from "next/image";
import DiscordIcon from "@/components/DiscordIcon";
import toast from "@/components/ui/sound-toast";

// Define public pages that don't require authentication
const publicPages = ['/', '/contact', '/about', '/subscription'];

const UserLayout = ({ children }: { children: React.ReactNode }) => {
    const { user, loading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();
    const toastShownRef = useRef(false);
    
    // Check if current path is a public page
    const isPublicPage = publicPages.some(page => {
        // For /subscription, only allow the exact route to be public
        if (page === '/subscription') {
            return pathname === page;
        }
        // For other public routes, allow both exact and nested paths
        return pathname === page || pathname.startsWith(`${page}/`);
    });

    useEffect(() => {
        // Only redirect if not a public page and user is not authenticated
        if (!loading && !user && !isPublicPage && !toastShownRef.current) {
            toastShownRef.current = true; // Mark toast as shown
            router.push(`/login?redirect=${pathname}`);
        }
    }, [user, loading, router, pathname, isPublicPage]);

    // Show loading state while checking authentication
    if (loading) {
        return null;
    }
    
    // Allow access to public pages without authentication
    if (!user && !isPublicPage) {
        return null; // Don't render protected content for unauthenticated users
    }

    const isChatPage = pathname === '/chat';
    
    return (
        <div className={`overflow-x-hidden bg-black ${isChatPage ? 'overflow-hidden h-screen' : ''}`}>
            <Navbar />
            <div className={isChatPage ? '' : 'pt-[70px] sm:pt-[80px] md:pt-[95px]'}>
                {children}
                {!isChatPage && <DiscordIcon />}
            </div>
            {!isChatPage && <Footer />}
        </div>
    )
}

export default UserLayout;