'use client';

import { useAuth } from "@/context/AuthContext";
import Image from "next/image";

const DiscordIcon = () => {
    const { user } = useAuth();

    // Only show the Discord icon if the user is logged in
    if (!user) return null;

    return (
        <a 
            href={user?.is_premium ? "https://discord.gg/premium-community" : "https://discord.gg/free-community"} 
            target="_blank" 
            rel="noopener noreferrer"
            className="fixed bottom-6 right-6 z-30 transition-transform hover:scale-110 md:z-40"
        >
            <div className="relative w-12 h-12 max-[900px]:w-10 max-[900px]:h-10 overflow-hidden shadow-lg">
                <Image
                    src="/assets/discord-icon.webp" 
                    alt="Join our Discord" 
                    fill 
                    sizes="48px"
                    className="object-cover"
                />
            </div>
        </a>
    );
};

export default DiscordIcon;