import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import Image from "next/image";
import DiscordIcon from "@/components/DiscordIcon";

const UserLayout = ({ children }: { children: React.ReactNode }) => {
    return (
        <div className="overflow-x-hidden bg-black">
            <Navbar />
            <div className="pt-[70px] sm:pt-[80px] md:pt-[95px]">
                {children}
                <DiscordIcon />
            </div>
            <Footer />
        </div>
    )
}

export default UserLayout;