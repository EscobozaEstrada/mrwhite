import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const UserLayout = ({ children }: { children: React.ReactNode }) => {
    return (
        <div className="overflow-x-hidden">
            <Navbar />
            <div className="pt-[70px] sm:pt-[80px] md:pt-[95px]">
                {children}
            </div>
            <Footer />
        </div>
    )
}

export default UserLayout;