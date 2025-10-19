import { NextRequest, NextResponse } from "next/server";
import jwt from "jsonwebtoken";

// Define protected routes
const protectedRoutes = ["/talk", "/gallery", "/events", "/account", "/reminders"];
const authRoutes = ["/login", "/signup"];
// Define public routes that should always be accessible
const publicRoutes = ["/", "/contact", "/about", "/subscription"];

export function middleware(req: NextRequest) {
    const { pathname } = req.nextUrl;
    
    // Don't process redirects to login page to avoid loops
    if (pathname.startsWith("/login") && req.nextUrl.searchParams.has("message")) {
        return NextResponse.next();
    }

    // Always allow access to public routes (exact matches only for subscription)
    if (publicRoutes.some(route => {
        // For /subscription, only allow the exact route to be public
        if (route === "/subscription") {
            return pathname === route;
        }
        // For other public routes, allow both exact and nested paths
        return pathname === route || pathname.startsWith(`${route}/`);
    })) {
        return NextResponse.next();
    }
    
    const token = req.cookies.get("token")?.value;

    // Check if user is trying to access an auth page while already logged in
    const isAuthRoute = authRoutes.some(route => pathname === route || pathname.startsWith(`${route}/`));
    if (isAuthRoute && token) {
        try {
            jwt.verify(token, process.env.JWT_SECRET as string);
            // If token is valid, redirect to home
            return NextResponse.redirect(new URL("/", req.url));
        } catch (error) {
            // If token is invalid, allow access to auth pages
            return NextResponse.next();
        }
    }

    // Check for protected routes and nested subscription routes
    const isProtectedRoute = protectedRoutes.some((route) => 
        pathname === route || 
        pathname.startsWith(`${route}/`) ||
        pathname.startsWith(`${route}?`)
    ) || pathname.startsWith("/subscription/");

    if (isProtectedRoute) {
        if (!token) {
            // Redirect to login with redirect parameter only
            const loginUrl = new URL("/login", req.url);
            loginUrl.searchParams.set("redirect", pathname);
            return NextResponse.redirect(loginUrl);
        }
        
        try {
            jwt.verify(token, process.env.JWT_SECRET as string);
            return NextResponse.next();
        } catch (error) {
            // Redirect to login with redirect parameter only
            const loginUrl = new URL("/login", req.url);
            loginUrl.searchParams.set("redirect", pathname);
            return NextResponse.redirect(loginUrl);
        }
    }

    return NextResponse.next();
}

// Add matcher configuration to specify which paths the middleware should run on
export const config = {
    matcher: [
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
};
