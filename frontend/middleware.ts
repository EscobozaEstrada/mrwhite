import { NextRequest, NextResponse } from "next/server";
import jwt from "jsonwebtoken";

const protectedRoutes = ["/talk"];
const authRoutes = ["/login", "/signup"];

export function middleware(req: NextRequest) {
    
    const {pathname} = req.nextUrl;
    const token = req.cookies.get("token")?.value

    // Check if user is trying to access an auth page while already logged in
    const isAuthRoute = authRoutes.some(route => pathname === route || pathname.startsWith(route));
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

    // Existing code for protected routes
    const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route));
    if(isProtectedRoute) {
        if(!token) {
            return NextResponse.redirect(new URL("/login", req.url));
        }
        
        try {
            jwt.verify(token, process.env.JWT_SECRET as string);
            return NextResponse.next();
        } catch (error) {
            return NextResponse.redirect(new URL("/login", req.url));
        }
    }

    return NextResponse.next();
}
