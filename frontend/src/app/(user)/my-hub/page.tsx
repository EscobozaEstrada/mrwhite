"use client"

import FadeInSection from "@/components/FadeInSection";
import ImagePop from "@/components/ImagePop";
import { Button } from "@/components/ui/button";
import { HiMiniBellAlert } from "react-icons/hi2";
import { TbArrowRight, TbCaptureFilled, TbDiscountFilled } from "react-icons/tb";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LuHeartHandshake } from "react-icons/lu";
import { FaBrain, FaCalendarAlt, FaCameraRetro, FaCloud, FaFeatherAlt, FaHeart, FaImages, FaMapMarkedAlt, FaPaw, FaPuzzlePiece, FaTshirt } from "react-icons/fa";
import { FaBookOpen, FaChartSimple, FaFolderClosed, FaLightbulb, FaMicrophone } from "react-icons/fa6";
import { RiCakeFill, RiCheckboxMultipleBlankFill, RiFlowerFill, RiMedicineBottleFill } from "react-icons/ri";
import { IoSettings, IoSparkles } from "react-icons/io5";
import { PiAlarmFill, PiUsersThreeFill } from "react-icons/pi";
import { GrUpdate } from "react-icons/gr";
import { MdOutlineInsights, MdOutlineUpdate } from "react-icons/md";
import { GiHeartWings } from "react-icons/gi";
import { VscDebugBreakpointLog } from "react-icons/vsc";
import { useAuth } from "@/context/AuthContext";

const HubPage = () => {
    const router = useRouter();
    const { user, setUser } = useAuth();
    
    return (
        <div className="flex flex-col gap-y-24 overflow-x-hidden">

            {/* SECTION 1  */}
            <section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/hub-hero.webp')] bg-cover bg-center">
                <div className="absolute inset-0 bg-black/40"></div>
                <div className="z-20">
                    <h1 className="max-[1200px]:text-[32px] text-[40px] font-work-sans font-semibold text-center">Legacy of Love Living Hub</h1>
                    <p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">The exclusive heart of the Elite Pack experience. </p>
                </div>
            </section>

            {/* SECTION 2 */}
            <section className="max-w-[1440px] mx-auto max-[1200px]:px-4 px-10">

                <div className="flex max-[850px]:flex-col flex-row items-center max-[850px]:px-0 rounded-sm overflow-hidden">

                    <div className="max-[850px]:w-full w-1/2 max-[850px]:h-fit h-[469px] space-y-6 flex flex-col justify-center">
                        <FadeInSection>
                            <h2 className="text-[32px]/8 max-[850px]:text-[24px] font-work-sans font-semibold gap-2 tracking-tighter">
                                <span className="inline-block mr-2 w-[10px] h-[30px] max-[850px]:w-[5px] max-[850px]:h-[15px] bg-[var(--mrwhite-primary-color)]"></span>
                                <span>Welcome to (Your Dog’s Name) Legacy of Love Dog Hub</span>
                            </h2>
                        </FadeInSection>
                        <p className="text-light text-justify font-public-sans text-[16px] ">
                            Exclusively available to Elite Pack members, the Legacy of Love Living Hub is nothing like your’ve seen before! Imagine a dynamic, AI-powered sanctuary where every cherished memory and vital detail about your companion’s life is held with care, easily accessible anytime, anywhere. This isn’t just a digital journal — Mr. White is your personal assistant, your memory keeper, even an aid to custom publishing your dogs life in book form and your partner in ensuring your dog enjoys a long, healthy, joyful life.
                        </p>
                        <p className="text-light text-justify font-public-sans text-[16px] ">With the Legacy of Love Living Hub, you’ll discover a new level of ease and confidence in managing your pup’s health, milestones, and adventures — all wrapped in a space designed to grow with you and your dog. Feel proud knowing that support and awareness are available 24/7, helping you make informed decisions and celebrate every step of your journey together. </p>
                    </div>

                    {/* <div className="max-[850px]:w-full w-1/2 max-[850px]:h-[320px] h-[469px] relative"> */}
                    {/* <Image
                            src="/assets/hub-macbook.webp"
                            alt="hub-macbook"
                            fill
                            sizes="(max-width: 768px) 100vw, 50vw"
                            className="object-contain"
                        /> */}
                    <ImagePop
                        src="/assets/hub-macbook.webp"
                        alt="hub-macbook"
                        fill
                        className="!object-contain"
                        containerClassName="max-[850px]:w-full w-1/2 max-[850px]:h-[320px] h-[469px] relative"
                        style={{ aspectRatio: '' }}
                        overlay={true}
                    />
                    {/* </div> */}

                </div>

            </section>

            {/* SECTION 3 */}
            <section className="max-w-[1440px] mx-auto max-[1200px]:px-4 px-10">

                <div className="flex max-[850px]:flex-col  flex-col  max-[850px]:px-0 rounded-sm overflow-hidden">

                    <FadeInSection>
                        <h2 className="text-[32px]/8 max-[850px]:text-[24px] font-work-sans font-semibold gap-2 tracking-tighter mb-6">
                            <span className="inline-block mr-2 w-[10px] h-[30px] max-[850px]:w-[5px] max-[850px]:h-[15px] bg-[var(--mrwhite-primary-color)]"></span>
                            <span>What Is the Legacy of Love Dog Hub?</span>
                        </h2>
                    </FadeInSection>

                    <div className="flex flex-col gap-10">
                        <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                            <div className="w-1/2 max-[850px]:w-full">
                                <p className="font-bold flex items-center gap-2">
                                    <LuHeartHandshake className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    A Living, Evolving Companion Care Space
                                </p>
                                <p className="font-light text-justify font-public-sans ">The Legacy of Love Dog Hub is much more than a simple journal or folder of documents. It’s a vibrant, ever-growing space that captures your relationship with you dog and the full story of your dog’s life. From health records and vet visits to daily activities and special moments, everything is thoughtfully organized in one place.
                                </p>
                            </div>

                            <div className="w-1/2 max-[850px]:w-full">
                                <p className="font-bold text-[16px] flex items-center gap-2">
                                    <FaCameraRetro className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Create Custom Keepsakes Anytime</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Turn your dog’s story into a beautiful, personalized book. Select any section of the Dog Hub to print as a keepsake. Celebrate birthdays, milestone anniversaries, or simply preserve your favorite memories to have digitally or as a lovely book for your living room, or any room you would like to showcase and enjoy it.</p>
                            </div>
                        </div>

                        <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                            <div className="w-1/2 max-[850px]:w-full">
                                <p className="font-bold flex items-center gap-2">
                                    <FaPaw className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Your personal AI guide
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">
                                    Mr. White isn’t just a digital assistant, he’s your knowledgeable partner in care. As you add stories, records, or questions, Mr. White learns and adapts, providing helpful reminders, alerts, tailored advice, suggested rituals, fun adventures and insights that make daily care simpler and more effective.
                                </p>
                            </div>

                            <div className="w-1/2 max-[850px]:w-full">
                                <p className="font-bold text-[16px] flex items-center gap-2">
                                    <FaCloud className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Always Accessible, Always Yours
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Your Legacy of Love Your Legacy of Love Living Hub is accessible anytime and anywhere via your personal portal. Whether at home, traveling, or at the vet, your dog’s complete history and care details are just a click away—24/7.</p>
                            </div>
                        </div>

                        <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                            <div className="w-full max-[850px]:w-full">
                                <p className="font-bold flex items-center gap-2">
                                    <GiHeartWings className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Grow Even Deeper with The Way of the Dog
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">
                                    The Legacy of Love Dog Hub is powerful on its own, but even more meaningful when paired with The Way of the Dog: A Guide to Intuitive Bonding and Creating an Interspecies Culture with Your Dog, the book by Anahata Graceland herself, also the founder and bestie of Mr. White. Anahata and Mr White help guide you in creating experiences from a foundational philosophy for deepening your bond with your dog. Get ready for your next best hobby!
                                </p>
                                <Button variant="ghost" onClick={() => router.push('/the-way')} className="text-public-sans text-light font-extralight text-[16px] italic self-start !text-[var(--mrwhite-primary-color)] !p-0 mb-6">
                                    Discover The Way of the Dog
                                    <TbArrowRight className="w-4 h-4" />
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* --------------------------------------------------------------------------------------- */}
                    <section className="h-[560px] max-[850px]:h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/hub-hotel-1.webp')] bg-cover bg-center rounded-sm"></section>
                    {/* --------------------------------------------------------------------------------------- */}

                    <div className="flex flex-col gap-10 mt-10">
                        <div>
                            <FadeInSection>
                                <h2 className="text-[32px]/8 max-[850px]:text-[24px] font-work-sans font-semibold gap-2 tracking-tighter mb-6">
                                    <span className="inline-block mr-2 w-[10px] h-[30px] max-[850px]:w-[5px] max-[850px]:h-[15px] bg-[var(--mrwhite-primary-color)]"></span>
                                    <span>Mr. White Legacy of Love AI Journal Structure</span>
                                </h2>
                            </FadeInSection>
                            <div>
                                <p className="mb-4 text-[16px]">All the sections below are already tucked inside your Mr. White AI Journal, designed to spark memories, track moments, and make caring for your pup feel like a breeze. But hey, if you’re the creative type and want to build your own layout or story flow, go for it! Think of these areas as files and all of your additions to your hub will go into one of these files below. </p>
                                <p className="mb-4 text-[16px]">You can also create a new file just the way you want it.</p>
                                <p className="text-[16px]">Mr. White is flexible and happy to follow your lead, he’s here to help you make your dog’s story as unique and wonderful as your journey together. And super easy to access!</p>
                            </div>
                        </div>

                        {/* <div className="flex flex-col gap-10">
                            <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                                <div className="w-1/2 max-[850px]:w-full">
                                    <p className="font-bold flex items-center gap-2">
                                        <LuHeartHandshake className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                        A Living, Evolving Companion Care Space
                                    </p>
                                    <p className="font-light text-justify font-public-sans ">The Legacy of Love Dog Hub is much more than a simple journal or folder of documents. It’s a vibrant, ever-growing space that captures your relationship with you dog and the full story of your dog’s life. From health records and vet visits to daily activities and special moments, everything is thoughtfully organized in one place.
                                    </p>
                                </div>

                                <div className="w-1/2 max-[850px]:w-full">
                                    <p className="font-bold text-[16px] flex items-center gap-2">
                                        <FaCameraRetro className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                        Create Custom Keepsakes Anytime</p>
                                    <p className="font-light text-justify font-public-sans text-[16px]">Turn your dog’s story into a beautiful, personalized book. Select any section of the Dog Hub to print as a keepsake. Celebrate birthdays, milestone anniversaries, or simply preserve your favorite memories to have digitally or as a lovely book for your living room, or any room you would like to showcase and enjoy it.</p>
                                </div>
                            </div>

                            <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                                <div className="w-1/2 max-[850px]:w-full">
                                    <p className="font-bold flex items-center gap-2">
                                        <FaPaw className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                        Your personal AI guide
                                    </p>
                                    <p className="font-light text-justify font-public-sans text-[16px]">
                                        Mr. White isn’t just a digital assistant, he’s your knowledgeable partner in care. As you add stories, records, or questions, Mr. White learns and adapts, providing helpful reminders, alerts, tailored advice, suggested rituals, fun adventures and insights that make daily care simpler and more effective.
                                    </p>
                                </div>

                                <div className="w-1/2 max-[850px]:w-full">
                                    <p className="font-bold text-[16px] flex items-center gap-2">
                                        <FaCloud className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                        Always Accessible, Always Yours
                                    </p>
                                    <p className="font-light text-justify font-public-sans text-[16px]">Your Legacy of Love Your Legacy of Love Living Hub is accessible anytime and anywhere via your personal portal. Whether at home, traveling, or at the vet, your dog’s complete history and care details are just a click away—24/7.</p>
                                </div>
                            </div>

                            <div className="max-[850px]:w-full max-[850px]:flex-col flex gap-10 max-[850px]:h-fit">

                                <div className="w-full max-[850px]:w-full">
                                    <p className="font-bold flex items-center gap-2">
                                        <GiHeartWings className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                        Grow Even Deeper with The Way of the Dog
                                    </p>
                                    <p className="font-light text-justify font-public-sans text-[16px]">
                                        The Legacy of Love Dog Hub is powerful on its own, but even more meaningful when paired with The Way of the Dog: A Guide to Intuitive Bonding and Creating an Interspecies Culture with Your Dog, the book by Anahata Graceland herself, also the founder and bestie of Mr. White. Anahata and Mr White help guide you in creating experiences from a foundational philosophy for deepening your bond with your dog. Get ready for your next best hobby!
                                    </p>
                                    <Button variant="ghost" onClick={() => router.push('/way-of-the-dog')} className="text-public-sans text-light font-extralight text-[16px] italic self-start !text-[var(--mrwhite-primary-color)] !p-0 mb-6">
                                        Discover The Way of the Dog
                                        <TbArrowRight className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        </div> */}

                        <div className="flex max-[1000px]:flex-col gap-10">

                            <ImagePop
                                src="/assets/hub-eat.webp"
                                alt="hub-eat"
                                fill
                                className="object-cover"
                                containerClassName="w-1/2 max-[1000px]:w-[500px] max-[600px]:w-[400px] max-[600px]:h-[800px] max-[430px]:w-full max-[600px]:h-[400px] max-[1000px]:mx-auto max-[1000px]:h-[800px] max-[1000px]:object-contain"
                                style={{ aspectRatio: '' }}
                                overlay={true}
                            />

                            <div className="w-2/3 max-[1000px]:w-full flex">
                                <div className="text-public-sans text-light flex flex-col gap-6">
                                    <div>
                                        <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                            <FaMicrophone className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                            Voice Options for You and Mr White
                                        </p>
                                        <p className="font-light font-public-sans text-[16px]">You can talk to Mr. White or write, whichever feels more natural! Just say what you need, and he’ll respond with his own fun voice, or quietly take notes if you’re in writing mode. Whether you’re logging memories hands-free on a walk or typing out a longer reflection, Mr. White is always listening with care (and a dash of charm).</p>
                                    </div>

                                    <div>
                                        <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                            <FaFolderClosed className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                            Mr. White’s AI Organization
                                        </p>
                                        <p className="font-light font-public-sans text-[16px]">Mr. White continuously updates your hubs based on inputs, keeping everything current and easy to navigate.</p>
                                    </div>

                                    <div>
                                        <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                            <FaBookOpen className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                            Your Choice in Building Your Companion’s Story
                                        </p>
                                        <p className="font-light font-public-sans text-[16px]">Mr. White continuously updates your hubs based on inputs, keeping everything current and easy to navigate.</p>
                                        <p className="font-light font-public-sans text-[16px]">Full Control to Customize Choose what to include. Add stories, photos, and milestones.</p>
                                        <p className="font-light font-public-sans text-[16px]">Mr. White Learns from You— Your inputs shape the experience, Mr. White adapts accordingly.</p>
                                    </div>

                                    <div>
                                        <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                            <IoSparkles className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                            Creative Ways to Use It
                                        </p>
                                        <ul className="list-disc pl-4" >
                                            <li>Photo Galleries</li>
                                            <li>Playdate Memories</li>
                                            <li>Health & Behavior Journals</li>
                                            <li>Training Progress</li>
                                            <li>Special Occasions</li>
                                            <li>Daily Moments</li>
                                            <li>Seasonal Reflections</li>
                                            <li>Legacy Planning</li>
                                        </ul>
                                    </div>

                                    <div>
                                        <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                            <FaLightbulb className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                            Tips for Using Mr. White Legacy of Living Hub
                                        </p>
                                        <ul className="list-disc pl-4" >
                                            <li>Use daily or weekly</li>
                                            <li>Upload photos anytime</li>
                                            <li>Keep it fun and rich as you plan adventures and play with exercises from The Way of the Dog experience</li>
                                            <li>Get vet records when necessary in real time 24/7</li>
                                            <li>Share stories easily</li>
                                            <li>Let AI simplify care</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                        </div>

                        

                    </div>


                </div>

            </section >

            <section className="max-w-[1440px] mx-auto max-[1200px]:px-4 px-10">

                <div className="flex max-[850px]:flex-col  flex-col  max-[850px]:px-0 rounded-sm overflow-hidden">
                    <FadeInSection>
                        <h2 className="text-[32px]/8 max-[850px]:text-[24px] font-work-sans font-semibold gap-2 tracking-tighter mb-6">
                            <span className="inline-block mr-2 w-[10px] h-[30px] max-[850px]:w-[5px] max-[850px]:h-[15px] bg-[var(--mrwhite-primary-color)]"></span>
                            <span>Key Areas Organized by Mr. White</span>
                        </h2>
                    </FadeInSection>
                </div>

                <div className="flex gap-10 max-[1300px]:gap-6 max-[850px]:flex-col ">

                    <div className="w-2/3 flex flex-col gap-8 max-[1150px]:gap-4 max-[850px]:w-full">

                        <div className="">
                            <p className="font-bold flex items-center gap-2">
                                <FaCalendarAlt className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                Companion Profile Hub
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px] tracking-tighter max-[850px]:tracking-normal">
                                This is the heart of your dog’s personal information. Here, Mr. White keeps important details like your dog’s birthdate, breed, and veterinarian or groomer contacts neatly organized. Having this information easily accessible helps you stay on top of routine care and emergencies alike. Whether you need to quickly share health info with a new caretaker or schedule a grooming appointment, everything you need is right here.
                            </p>
                        </div>

                        <div className="">
                            <p className="font-bold flex items-center gap-2">
                                <FaChartSimple className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                Daily and Weekly Living Log Hub
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px] tracking-tighter max-[850px]:tracking-normal">Track your dog’s everyday life with ease. This hub lets you log activities, moods, behaviors, and photos to capture the full picture of their wellbeing and happiness. Whether it’s a playful afternoon, a change in appetite, or a special moment during a walk, you can record it all. Over time, these logs create valuable insights that help you understand patterns, celebrate joys, and address any concerns early.</p>
                        </div>

                        <div className="">
                            <p className="font-bold flex items-center gap-2">
                                <FaMapMarkedAlt className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                Favorites and Travel Treasures Hub
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px] tracking-tighter max-[850px]:tracking-normal">Keep a curated list of your dog’s favorite toys, friends, and travel spots. This hub helps you remember which toys spark joy, where to get them at the best rate, who their best playmates are, and the places where they feel most at home on the road. It’s perfect for planning trips, playdates, or simply ensuring your dog’s world stays full of the things and beings they love. </p>
                        </div>

                        <div className="">
                            <p className="font-bold flex items-center gap-2">
                                <RiMedicineBottleFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                Medicine and Appointment Alerts Hub
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px] tracking-tighter max-[850px]:tracking-normal">Never miss an important medication dose, vet visit, or playdate again. This hub manages all reminders for medicines, treatments, vaccinations, and appointments, customized to your dog’s unique schedule. Mr. White’s timely alerts make it simple to keep care on track without stress. </p>
                        </div>
                    </div>

                    <ImagePop
                        src="/assets/hub-single.webp"
                        alt="hub-single"
                        fill
                        className="object-cover"
                        containerClassName="w-1/2 max-[450px]:w-full max-[650px]:w-[400px] max-[650px]:h-[600px] max-[850px]:h-[400px] max-[600px]:h-[400px] max-[1000px]:mx-auto max-[1000px]:object-contain"
                        style={{ aspectRatio: '' }}
                        overlay={true}
                    />

                </div>

                <div className="flex gap-10 mt-8 flex-col">
                    <div className="flex gap-10 max-[850px]:flex-col-reverse">
                        <ImagePop
                            src="/assets/hub-multi.webp"
                            alt="hub-multi"
                            fill
                            className="object-cover "
                            containerClassName="w-1/2 h-[450px] max-[1300px]:h-[350px]  max-[850px]:h-[400px] max-[600px]:h-[400px] max-[1000px]:mx-auto max-[1000px]:object-contain max-[850px]:w-full"
                            style={{ aspectRatio: '' }}
                            overlay={true}
                        />

                        <div className="w-1/2 max-[850px]:w-full flex flex-col gap-6">

                            <div className="">
                                <p className="font-bold flex items-center gap-2">
                                    <FaFeatherAlt className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Inspirational Insights Hub
                                </p>
                                <p className="font-light mb-2 text-justify font-public-sans text-[16px] tracking-tighter">
                                    Beyond practical care, this space offers thoughtful reflections, wisdom, and gentle guidance from Mr. White. Drawing on decades of experience and AI-driven understanding, it provides encouragement and ideas to deepen your bond and nurture your dog’s spirit every day.
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px] tracking-tighter">
                                    Please feel free to check out The Way of the Dog as it offers a powerful
                                    companion experience filled with an entire book along with exercises,
                                    rituals and insights designed to strengthen your intuitive connection and
                                    create a more meaningful life together. The Legacy of Living Dog Hub, your
                                    journal and total Mr White masterful assistant, paired with The Way of the
                                    Dog, becomes a daily invitation to grow heartfully, side by side
                                </p>
                                <Button variant="ghost" onClick={() => router.push('/the-way')} className="text-public-sans text-light font-extralight text-[16px] italic self-start !text-[var(--mrwhite-primary-color)] !p-0">
                                    Learn more about The Way of the Dog
                                    <TbArrowRight className="w-4 h-4" />
                                </Button>
                            </div>

                            <div className="max-[1300px]:hidden">
                                <p className="font-bold flex items-center gap-2">
                                    <RiFlowerFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    End of Life Planning Hub
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Planning ahead with compassion, this hub supports you in preparing for your dog’s final journey. It helps organize wishes, memorial ideas, and Page 4 of 12 practical steps with care and sensitivity, offering peace of mind and honoring the love you share.</p>
                                <p>And The Way of the Dog offers soulful guidance for walking this sacred path. With reflections, journaling prompts, and end-of-life wisdom and plans woven throughout the book, it gently helps you hold grief, memory, and love with grace. Together, this hub and The Way of the Dog create a tender and courageous way to celebrate the life you've shared—and the bond that never ends.</p>
                                <Button variant="ghost" onClick={() => router.push('/the-way')} className="text-public-sans text-light font-extralight text-[16px] italic self-start !text-[var(--mrwhite-primary-color)] !p-0">
                                    Explore The Way of the Dog
                                    <TbArrowRight className="w-4 h-4" />
                                </Button>
                            </div>

                            <div className="max-[1300px]:hidden">
                                <p className="font-bold flex items-center gap-2">
                                    <FaBrain className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Mr. White’s AI-driven organization and updates
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Behind the scenes, Mr. White’s intelligent system continuously organizes and updates all these hubs based on your input and ongoing data. This means your Legacy of Love Living Hub is always current, easy to navigate, and personalized—ready to support you and your dog every step of the way.</p>
                            </div>
                        </div>
                    </div>

                    <div className="hidden max-[1300px]:flex gap-10 max-[850px]:flex-col">
                        <div className="w-1/2 max-[850px]:w-full">
                            <p className="font-bold flex items-center gap-2">
                                <RiFlowerFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                End of Life Planning Hub
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px]">Planning ahead with compassion, this hub supports you in preparing for your dog’s final journey. It helps organize wishes, memorial ideas, and Page 4 of 12 practical steps with care and sensitivity, offering peace of mind and honoring the love you share.</p>
                            <p>And The Way of the Dog offers soulful guidance for walking this sacred path. With reflections, journaling prompts, and end-of-life wisdom and plans woven throughout the book, it gently helps you hold grief, memory, and love with grace. Together, this hub and The Way of the Dog create a tender and courageous way to celebrate the life you've shared—and the bond that never ends.</p>
                            <Button variant="ghost" onClick={() => router.push('/the-way')} className="text-public-sans text-light font-extralight text-[16px] italic self-start !text-[var(--mrwhite-primary-color)] !p-0">
                                Explore The Way of the Dog
                                <TbArrowRight className="w-4 h-4" />
                            </Button>
                        </div>

                        <div className="w-1/2 max-[850px]:w-full">
                            <p className="font-bold flex items-center gap-2">
                                <FaBrain className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                Mr. White’s AI-driven organization and updates
                            </p>
                            <p className="font-light text-justify font-public-sans text-[16px]">Behind the scenes, Mr. White’s intelligent system continuously organizes and updates all these hubs based on your input and ongoing data. This means your Legacy of Love Living Hub is always current, easy to navigate, and personalized—ready to support you and your dog every step of the way.</p>
                        </div>
                    </div>

                </div>

            </section>

            {/* SECTION 3 */}
            <section className="max-w-[1440px] mx-auto min-h-screen max-[1200px]:px-4 px-10 flex flex-col gap-y-20">

                <div className="flex max-xl:flex-col gap-10">


                    <div className="w-full flex">
                        <div className="text-public-sans text-light flex flex-col gap-6">
                            <FadeInSection>
                                <h1 className="text-[32px] font-work-sans font-semibold gap-2">
                                    <span className="inline-block mr-2 w-[10px] h-[30px] bg-[var(--mrwhite-primary-color)]"></span>
                                    A Day with Mr. White’s Living Hub
                                </h1>
                            </FadeInSection>

                            <div>
                                <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                    <PiAlarmFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Morning Reminder: Never Miss an Appointment
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Imagine starting your day with a quick glance at your personal Legacy of Love Living Hub. Today, you have a vet appointment scheduled for your dog, Bella. Mr. White has already reminded you this morning—ensuring you won’t miss the important checkup. </p>
                            </div>

                            <div>
                                <p className="font-bold text-[16px] mb-1 flex items-center gap-2">
                                    <MdOutlineUpdate className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Updating Health Records Made Simple
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">After the visit, you easily upload the vet’s notes and update Bella’s health records in the Companion Profile Hub. Mr. White automatically organizes the new information, flagging upcoming vaccinations and suggesting any needed follow-ups based on the vet’s advice. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <TbCaptureFilled className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Capturing Travel Memories </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Later, during a weekend getaway, you snap a photo of Bella at her favorite dog park. You upload it to the Favorites and Travel Treasures Hub, adding a note about the fun she had chasing butterflies. Mr. White gently suggests tagging the location and friends she met there, helping you build a vivid travel log filled with joyful memories. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <HiMiniBellAlert className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Timely Medication Alerts </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">That evening, you receive a timely medicine alert from Mr. White’s Medicine and Appointment Alerts Hub reminding you to give Bella her allergy medication. No more second-guessing or missed doses—the care stays on track effortlessly. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <MdOutlineInsights className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    AI-Powered Insights Throughout Your Day
                                </p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Throughout the day, Mr. White’s AI keeps learning from your entries and habits, offering personalized insights and gentle nudges to deepen your understanding of Bella’s health and happiness. By the end of the day, your Legacy of Love Living Hub feels like a true extension of your care—a smart, caring partner working alongside you every step of the way. </p>
                            </div>

                        </div>
                    </div>



                </div>

                <div className="flex max-xl:flex-col justify-center gap-10">

                    <ImagePop
                        src="/assets/hub-love.webp"
                        alt="hub-love"
                        fill
                        className="object-cover"
                        containerClassName="w-1/2  max-[600px]:h-[400px] max-[1000px]:mx-auto max-[1000px]:h-[800px] max-[1000px]:object-contain"
                        style={{ aspectRatio: '' }}
                        overlay={true}
                    />
                    {/* </div> */}
                    {/* </div> */}
                    <div className="max-[1280px]:w-full w-2/3 flex">
                        <div className="text-public-sans text-light flex flex-col gap-6">
                            <FadeInSection>
                                <h1 className="text-[32px] font-work-sans font-semibold gap-2">
                                    <span className="inline-block mr-2 w-[10px] h-[30px] bg-[var(--mrwhite-primary-color)]"></span>
                                    Additional Helpful Features
                                </h1>
                            </FadeInSection>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <PiUsersThreeFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Connect and Share with a Supportive Community</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Beyond personal care, the Legacy of Love Living Hub invites you to join a vibrant community of dog lovers. Share stories, exchange tips, organize meetups, and celebrate your companions together. This space offers connection and support, turning your journey into a shared experience filled with friendship and understanding. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <TbDiscountFilled className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Exclusive Product Discounts and Perks</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">As an Elite Pack member, you enjoy special discounts on trusted products carefully curated by Mr. White and Anahata Graceland. These savings help you access the best in health, nutrition, and comfort for your dog, ensuring quality care without compromise. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <RiCakeFill className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Celebrate Life’s Milestones and Birthdays</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Plan unforgettable birthday celebrations and important milestones right from your Living Hub. Whether it’s a fun party idea, a personalized message, or a memorable photo album, Mr. White helps you make each occasion special. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <FaImages className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Create Virtual Montages and Keepsakes</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Turn your favorite photos and stories into beautiful virtual montages that capture your dog’s personality and journey. Share them with family or keep them as treasured digital memories. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <FaHeart className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Thoughtful Eulogy Drafting Assistance</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">When the time comes, Mr. White gently supports you with tools to craft a heartfelt eulogy or memorial tribute. This feature helps honor your dog’s legacy with compassion and dignity, offering comfort during difficult moments. </p>
                            </div>

                            <div>
                                <p className="font-bold mb-1 flex items-center gap-2">
                                    <FaTshirt className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                    Exciting Future Features: Fetch Fridays Apparel and More</p>
                                <p className="font-light text-justify font-public-sans text-[16px]">Stay tuned for upcoming additions like exclusive apparel from Fetch Fridays and other community-inspired products that celebrate the special bond between you and your dog. The Living Hub continues to grow, bringing you fresh ways to cherish and express your love. </p>
                            </div>


                        </div>
                    </div>
                </div>

                <div className="flex max-xl:flex-col gap-10">


                    <div className="w-full flex">
                        <div className="text-public-sans text-light flex flex-col gap-6">
                            <FadeInSection>
                                <h1 className="text-[32px] font-work-sans font-semibold gap-2">
                                    <span className="inline-block mr-2 w-[10px] h-[30px] bg-[var(--mrwhite-primary-color)]"></span>
                                    How to Get Started
                                </h1>
                            </FadeInSection>

                            <p className="font-light text-justify font-public-sans text-[16px]">Ready to elevate the way you care for your companion? Urenlock the full power of the (Your Dog’s Name) Legacy of Love Living Hub by joining the Elite Pack today. </p>

                            <p className="font-light text-justify font-public-sans text-[16px]">With your Elite Pack membership, you’ll gain 24/7 access to your personal portal, exclusive AI-powered tools, and all the features that make caring for your dog easier, richer, and more connected.</p>
                            
                            <p className="font-bold text-[16px]">
                                Unlock Your Legacy Today! {!user && <Link href="/signup" className="text-public-sans italic inline-block text-light text-[16px] !text-[var(--mrwhite-primary-color)]">Sign Up Now</Link>}</p>

                            <p className="font-light text-justify font-public-sans text-[16px]">Not quite ready to commit? Explore a live preview or demo of the Living Hub to see how it works and how it can transform your daily care routine. </p>

                            <p className="font-light text-justify font-public-sans text-[16px]">Take the first step toward a deeper, more organized, and joyful companion care experience—because every moment with your dog deserves to be cherished and supported.</p>

                        </div>
                    </div>

                </div>

            </section>

            <section className="max-w-[1440px] mx-auto max-[1200px]:px-4 px-10 flex flex-col gap-y-8 mb-20">

                <FadeInSection>
                    <h1 className="text-[32px] font-work-sans font-semibold gap-2">
                        <span className="inline-block mr-2 w-[10px] h-[30px] bg-[var(--mrwhite-primary-color)]"></span>
                        What Our Community Says
                    </h1>
                </FadeInSection>

                <div>
                    <p className="text-[16px] font-public-sans font-light italic">"The Legacy of Love Living Hub has completely changed how I care for Luna. Having everything organized and Mr. White’s gentle reminders means less stress and more quality time together. It truly feels like a trusted friend walking alongside us."
                        <br />
                        — Sarah M., proud dog mom</p>
                </div>

                <div>
                    <p className="text-[16px] font-public-sans font-light italic">"I love how I can add photos and stories about Max’s adventures. Creating a keepsake book for his birthday was so easy and meaningful."
                        <br />
                        — Emily R., happy dog owner</p>
                </div>

                <div>
                    <p className="text-[16px] font-public-sans font-light italic">"Joining the Elite Pack gave me peace of mind. Mr. White’s insights and alerts have helped me catch small health issues early. It’s like having a vet assistant on call!"
                        <br />
                        — James K., caring pet parent</p>
                </div>

                <div>
                    <p className="text-[16px] font-public-sans font-light italic">"The community is wonderful—sharing tips and stories with other dog lovers makes this journey so much richer. The Legacy of Love Living Hub feels like family."
                        <br />
                        — Lisa T., lifelong dog enthusiast</p>
                </div>

            </section>

        </div>
    )
}

export default HubPage;