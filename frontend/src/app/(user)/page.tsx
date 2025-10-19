"use client"
import { Button } from "@/components/ui/button";
import { BsBagHeartFill, BsPatchCheckFill } from "react-icons/bs";
import { PiBoneFill } from "react-icons/pi";
import { DogCard } from "@/components/DogCard";
import FadeInSection from "@/components/FadeInSection";
import { TbCirclePercentageFilled, TbClockHour3, TbLogin, TbTableFilled } from "react-icons/tb";
import ShakingIcon from "@/components/ShakingIcon";
import StepsAnimated from "@/components/StepsAnimated";
import { IoChatbubble } from "react-icons/io5";
import ImagePop from "@/components/ImagePop";
import CompanyNameSection from "@/components/CompanyNameSection";
import SubscriptionCard from "@/components/SubscriptionCard";
import Rotating3DCard from "@/components/Rotating3DCard";
import { useRouter } from "next/navigation";
import FAQAccordion from "@/components/FAQAccordion";
import { useAuth } from "@/context/AuthContext";
import SEO from "@/components/SEO";
import { generateFAQSchema } from "@/lib/schema";
import TestimonialSlider from "@/components/TestimonialSlider";
import { testimonials } from "@/data/testimonials";
import Image from "next/image";
import { AiOutlinePaperClip } from "react-icons/ai";
import { GiCrossedBones, GiHabitatDome } from "react-icons/gi";
import { RiUserCommunityLine } from "react-icons/ri";
import { HiOutlineSupport } from "react-icons/hi";
import { BiSolidBookBookmark } from "react-icons/bi";
import { FaUser, FaVectorSquare } from "react-icons/fa";
import { MdOutlineFamilyRestroom } from "react-icons/md";
import { motion } from "motion/react";
import { useState, useEffect } from 'react';
import { UsageTracker } from '@/components/UsageTracker';
import { PremiumGate } from '@/components/PremiumGate';
import { CreditDisplay } from '@/components/CreditDisplay';
import { Card } from '@/components/ui/card';
import { Crown, Coins, TrendingUp, Calendar, ArrowRight, MessageSquare } from 'lucide-react';
import { LuCrown } from "react-icons/lu";

export default function Home() {
  const router = useRouter();
  const { user, setUser, creditRefreshTrigger, creditStatus } = useAuth();
  const [usageStats, setUsageStats] = useState<any>(null);

  // Fetch usage stats for free users
  useEffect(() => {
    if (user && !user.is_premium) {
      fetchUsageStats();
    }
  }, [user]);

  const fetchUsageStats = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/usage/status`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUsageStats(data.usage);
      }
    } catch (error) {
      console.error('Error fetching usage stats:', error);
    }
  };

  const getBalanceColor = (credits: number) => {
    if (credits < 100) return 'text-red-400';
    if (credits < 500) return 'text-[var(--mrwhite-primary-color)]';
    return 'text-green-400';
  };

  const formatCreditsAsUSD = (credits: number) => {
    return `$${(credits / 100).toFixed(2)}`;
  };

  const faqs = [
    {
      id: "item-1",
      question: "Who is Mr. White?",
      answer: "Mr. White is a master of the dog world who, after a life of love and service, ascended to join a lineage of dog guardians throughout history. Now, as a digital guide inspired by Anahata Graceland and powered by AI, Mr. White shares wisdom to deepen the bond between dogs and their people. Ask him about breeds, care, history, or dog-human connections, and he'll provide thoughtful answers to support your journey. Mr. White can also serve as an ageless skillful assistant to all your dogs needs with alerts, store records etc. should you become an Elite Pack member."
    },
    {
      id: "item-2",
      question: "Can I use Mr. White for free?",
      answer: "Yes! Follow Mr. White on X at @MrWhiteAIBuddy for daily free tips, breed facts, training insights, and dog wisdom. Start your journey with this trusted friend, and when you're ready for more in-depth support, consider joining the pack."
    },
    {
      id: "item-3",
      question: "What benefits come with the Elite Pack Membership?",
      answer: (
        <>
          For $19.95/month or save 20% for yearly subscription, pack members unlock the full power of the Legacy of Love Dog Hub, plus:
          <ul className="list-disc list-inside">
            <li>3,000 monthly credits ($30.00 value) for all features</li>
            <li>Secure storage and easy access to your dog's complete records</li>
            <li>Personalized medication and appointment alerts</li>
            <li>Advanced AI chat with health analysis capabilities</li>
            <li>Document upload and AI-powered analysis</li>
            <li>Care Archive with intelligent search</li>
            <li>Voice message processing</li>
            <li>Recommendations for trusted local vets, groomers, and dog-friendly travel</li>
            <li>A BlockchainDNA NFT that secures your dog's legacy and your bond</li>
            <li>Exclusive product discounts and priority support</li>
            <li>Access to a private community of dog lovers</li>
            <li>Ability to purchase additional credits when needed</li>
          </ul>
        </>
      )
    },
    {
      id: "item-4",
      question: "What is the BlockchainDNA NFT, and how does it secure my dog's bond with me?",
      answer: "The BlockchainDNA NFT is a sacred digital certificate that verifies your dog's records on the blockchain, linking them permanently to you. This unbreakable bond honors your shared life beyond ownership, offering peace of mind that your dog's legacy and your story are secure for generations. It is fully transferable."
    },
    {
      id: "item-5",
      question: "How does Mr. White build community for me and my dog?",
      answer: "Mr. White creates a private community where dog families connect, share stories, organize meetups, and explore topics that deepen bonds. It's a vibrant pack where friendships flourish and collective wisdom grows, enriching your journey with your dog."
    },
    {
      id: "item-6",
      question: "How does Mr. White support veterinarians and pet service professionals?",
      answer: "Veterinarians, groomers, trainers, and other professionals benefit from discounted pack memberships. They gain access to family records, a collaborative network for sharing insights, and connections with dog families to enhance their care and services."
    },
    {
      id: "item-7",
      question: "Is there a reduced rate for veterinarians and pet service professionals?",
      answer: "Yes! Professionals can join for $9/month or $90/year, supporting their communities while gaining access to valuable tools and networks tailored for their work with dogs."
    },
    {
      id: "item-8",
      question: "How does Mr. White support top dog product companies and other organizations?",
      answer: "Mr. White provides a platform for product companies, event organizers, educators, nonprofits, dog park leaders, and wellness practitioners to connect with dog families, showcase quality offerings, share knowledge, and foster community through events and educational activities."
    },
    {
      id: "item-9",
      question: "Can I talk to Mr. White about anything in life?",
      answer: "Yes! Mr. White is your mentor not just for dog care but for life's journey. Share your dreams, challenges, and joys, and receive wise counsel to help create a harmonious life for you and your companion."
    },
    {
      id: "item-10",
      question: "How does Mr. White help me save money?",
      answer: "Mr. White helps avoid unnecessary vet visits by recalling your dog's health history, reminds you about medications and care schedules, and offers 5% off trusted product recommendations—all designed to save you money while ensuring the best care."
    },
    {
      id: "item-11",
      question: "What kinds of products does Mr. White recommend?",
      answer: "Recommendations focus on quality, safety, and true dog approval, including toys, treats, training tools, and organic remedies backed by Anahata Graceland's 50+ years of expertise. The community's feedback further refines these trusted choices"
    },
    {
      id: "item-12",
      question: "Are my pet's records safe with Mr. White?",
      answer: "Absolutely. Your pet's records are securely stored and accessible only to you, your most important documents protected by your BlockchainDNA NFT and other personal stories, photos, videos and other items are stored on our website, honoring your privacy and safeguarding your data."
    },
    {
      id: "item-13",
      question: "How does Mr. White support dog-human relationships?",
      answer: "By prioritizing intelligence, true nourishment, enriching activities, and revealing the canine spirit's nature, Mr. White helps deepen the joyful bond between you and your dog."
    },
    {
      id: "item-14",
      question: "What if I need help with a specific dog issue?",
      answer: "Ask Mr. White about anything—from breed suitability to behavior or health concerns. He'll recall your dog's history and provide tailored advice. For medical issues, always consult a licensed veterinarian."
    },
    {
      id: "item-15",
      question: "How do I join Mr. White's Elite pack?",
      answer: "Sign up on this website for $19.95/month or 20% off/year and begin your journey to joyful, harmonious companion care. You'll get 3,000 monthly credits ($30 value) plus access to all premium features. Share your pet's details and unlock a world of support."
    }
  ];

  // Generate FAQ schema for structured data
  const faqSchema = generateFAQSchema(
    faqs.map(faq => ({
      question: faq.question,
      answer: typeof faq.answer === 'string' ? faq.answer : 'Please visit our website for the detailed answer.',
    }))
  );

  return (
    <div className="overflow-x-hidden">
      <SEO schema={faqSchema} />

      {/* Usage Tracker for Free Users */}
      {usageStats && !user?.is_premium && (
        <div className="max-w-7xl mx-auto px-4 py-2">
          <UsageTracker
            feature="chat"
            currentUsage={usageStats.used?.chat_messages_today || 0}
            maxUsage={10}
            className="mb-4"
          />
        </div>
      )}


      {/* SECTION 1  */}
      <div className="bg-background">
        <section className="max-w-[1440px] mx-auto min-h-[calc(100vh-95px)] py-16 px-12 flex flex-col md:flex-row justify-center md:justify-between items-center gap-10 max-[1024px]:px-4 max-[450px]:px-3">

          <div className="w-full md:w-1/2 max-[1000px] max-[768px]:aspect-auto aspect-[652/596] h-full flex flex-col justify-between max-[768px]:justify-center">
            <div className="w-full flex flex-col gap-[40px] max-[1280px]:gap-[24px]">
              <div className="w-full flex flex-col gap-[32px] max-[885px]:gap-[10px] max-[1300px]:gap-[18px] max-[768px]:gap-[32px]">
                <h1 className="text-[44px]/12 font-semibold font-work-sans max-[1200px]:text-[32px] tracking-tighter max-[885px]:text-[32px] max-[768px]:text-[44px]/12">
                  Secrets of Paws and Humans, revealed they are.
                </h1>
                <p className="w-full min-[1440px]:w-[413px] font-medium text-[24px]/6 max-[1300px]:text-[18px] tracking-tighter max-[885px]:text-[14px] max-[450px]:text-[24px] max-[768px]:text-[24px]/6">
                  All the information for dogs and humans, packed into one hub.
                </p>
              </div>
              <div className="flex gap-12 max-[1251px]:gap-4 max-[885px]:flex-col">

                {/* <div className="">
                  <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                  <p className="inline-block max-[450px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">All-in-One Solution</p>
                </div>
                <div className="">
                  <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                  <p className="inline-block max-[450px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">Knowledge to strengthen your bond</p>
                </div>
                <div className="">
                  <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                  <p className="inline-block max-[450px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">For every dog & their human</p>
                </div>
                <div className="">
                  <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                  <p className="inline-block max-[450px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">100% human support</p>
                </div> */}

                <div className="flex flex-col gap-4">
                  <h3>
                    <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                    <p className="inline-block max-[768px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">All-in-One Solution</p>
                  </h3>

                  <h3>
                    <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                    <p className="inline-block max-[768px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">Knowledge to strengthen your bond</p>
                  </h3> 
                </div>

                <div className="flex flex-col gap-4">
                  <h3>
                    <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                    <p className="inline-block max-[768px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">For every dog & their human</p>
                  </h3>

                  <h3>
                    <BsPatchCheckFill aria-hidden="true" className="inline-block mr-2 max-[1200px]:w-[14px] max-[1200px]:h-[14px]" />
                    <p className="inline-block max-[768px]:text-[16px] max-[1200px]:text-[14px] max-[1074px]:text-[12px]">100% human support</p>
                  </h3>
                </div>

              </div>
              <div className="w-full relative max-[450px]:mb-10">
                <Button onClick={() => router.push('/subscription')} className="max-[900px]:w-full w-[279px] h-[47px] text-[20px]">
                  <ShakingIcon icon={<PiBoneFill className="!w-6 !h-6" aria-hidden="true" />} />
                  View Subscriptions
                </Button>
              </div>
            </div>
            <div className="w-full">
              <TestimonialSlider testimonials={testimonials} autoplaySpeed={6000} />
            </div>
          </div>

          <ImagePop
            src="/assets/home-hero.webp"
            alt="Dog and owner bonding together, showing the Mr. White experience"
            fill
            className="object-cover"
            containerClassName="w-full md:w-1/2 aspect-[652/596] relative"
            priority={true}
          />
        </section>
      </div>

      {/* SECTION 2 */}

      <div className=" bg-white/5">
        <section className="max-w-[1440px] mx-auto py-16 flex flex-col md:flex-row justify-center md:justify-between gap-10  px-12 max-[1024px]:px-4 max-[450px]:px-3">
          <div className="w-full flex flex-col items-center gap-[40px]">
            <FadeInSection className="w-full flex items-center justify-center">
              <h2 className="text-[24px] md:text-[32px] font-semibold">Preserve, Learn, and Honor Your Dog's Journey</h2>
            </FadeInSection>
            <div className="w-full grid grid-cols-3 max-[1024px]:grid-cols-1 max-[1350px]:grid-cols-2 max-[1350px]:justify-items-center gap-[24px]">
              <DogCard
                imageSrc="/assets/home-card-1.webp"
                imageAlt="home-card-1"
                title="Ancient Wisdom for Modern Dog Care"
                description={[`Mr. White holds eons of dog knowledge, from ancient canine history to modern care insights, ready for pack members to explore.`,
                  `Use this wisdom to understand your companion's needs, enhance training, keep track of vaccination times, and deepen your bond—whether you're solving a behavior challenge, choosing the best activities, or simply learning more about your dog's unique spirit.`]}
                delay={0}
              />
              <DogCard
                imageSrc="/assets/home-card-2.webp"
                imageAlt="home-card-2"
                title="All-in-One Secure Storage Solution"
                description={[`Mr. White offers a customizable storage solution for you and your dog, keeping everything you need in one secure place. Upload vet records, certifications, health history, training milestones, or cherished photos and stories—Mr. White remembers it all.`,
                  `Access this information anytime, anywhere, whether you need a vet record for an appointment, an alert for the appt, a certification for travel, or a special memory to share.`]}
                delay={0.1}
              />
              <DogCard
                imageSrc="/assets/home-card-3.webp"
                imageAlt="home-card-3"
                title="Building Interspecies Family Bonds"
                description={[`Mr. White and I, Anahata Graceland, a breeder with over 50 years of knowledge, offer pack members a rare perspective: dogs and humans belong to each other as family, not as owners.`,
                  `Together, we guide you in building an interspecies culture that honors the true intelligence and spirit of your bond, doing right by each other with love and respect.`]}
                delay={0.2}
              />
            </div>
            <Button onClick={() => {
              // Store the intended destination for after login
              localStorage.setItem('redirectAfterLogin', '/my-hub');
              router.push('/my-hub');
            }} className="w-full sm:w-[200px] md:w-[253px] h-[47px] text-[20px]">
              <ShakingIcon icon={<PiBoneFill className="!w-6 !h-6" />} />
              Read More
            </Button>
          </div>
        </section>
      </div>

      {/* SECTION 3 */}

      <div className="bg-white/5">
        <section className="max-w-[1440px] mx-auto flex justify-center items-center p-10 w-full px-12 max-[1024px]:px-4 max-[450px]:px-3">
          <div className="flex max-[1000px]:flex-col h-full justify-center items-center gap-x-10 w-full bg-black p-8 max-[1000px]:p-4">
            {/* <Rotating3DCard /> */}

            <div className="flex flex-col gap-y-4 w-1/3 max-[1000px]:w-full relative">

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                // animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="w-full h-[280px] relative"
                whileInView={{ scale: 1, opacity: 1 }}
              >
                <Image
                  src="/assets/dog-nft-card.webp"
                  alt="nft-card"
                  fill
                  className="object-contain"
                />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                // animate={{ opacity: 1, scale: 1 }}
                whileInView={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.2, delay: 0.8 }}
                className="w-1/2 h-[160px] absolute -top-6 max-[1000px]:-top-2 right-0 max-[450px]:right-6 max-[550px]:right-10 max-[700px]:right-16 max-[780px]:right-20 max-[960px]:right-28 max-[1000px]:right-38"
              >
                <Image
                  src="/assets/dog-nft-comment.webp"
                  alt="your dog's picture here"
                  fill
                  className="object-contain"
                />
              </motion.div>

            </div>


            <div className='flex flex-col gap-y-4 max-[1000px]:text-justify w-2/3 max-[1000px]:w-full'>
              <div>
                <h1 className='text-[24px] font-work-sans font-semibold'>Legacy of Love Dog Hub</h1>
                <h1 className='text-[24px] font-work-sans font-semibold'>A New Era in Caring for Your Best Friend</h1>
                <h1 className='text-[24px] font-work-sans font-light italic'>"Where your dog's health, story, and happiness come together."</h1>
              </div>
              <p className='text-[16px] font-public-sans font-light'>Unlock the Elite Pack and step into (Your Dog's Name) Legacy of Love Living Dog Hub, your AI-powered sanctuary for celebrating and caring for your cherished companion. This one-of-a-kind living hub securely stores vital records, sets timely medication alerts, tracks vaccinations, and beautifully organizes stories and photos from your shared journey. It's truly designed to keep every memory you cherish while helping life move smoothly and safely. Plus, you can effortlessly print a custom book of any section you choose, with Mr. White guiding you every step of the way. Inspired by The Way of the Dog by Anahata Graceland, this innovative personal assistant captures every milestone and joy you've shared—offering a connection and memory archive unmatched anywhere else.</p>
            </div>
          </div>
        </section>
      </div>

      {/* SECTION 4 */}
      <section className="max-w-[1440px] mx-auto min-h-screen py-16 px-12 max-[1024px]:px-4 max-[450px]:px-3">
        <FadeInSection className="w-full mb-12">
          <h2 className="text-[24px] md:text-[32px] font-semibold">The Benefits of Mr. White In Your Life</h2>
        </FadeInSection>

        <div className="h-[740px] max-[900px]:h-auto w-full bg-white/10 rounded-sm flex flex-col p-8 mb-10 max-[550px]:p-6">

          <div className="text-[24px] max-[550px]:text-[18px] font-semibold font-work-sans border-b border-black pb-6 flex items-center gap-x-4">
            <Image src="/assets/dog-icon-free.webp" alt="dog-icon-free" width={100} height={100} className="w-10 h-10 max-[550px]:w-8 max-[550px]:h-8" />
            <h1>1. For Companion Crew Pack Members (Free)</h1>
          </div>

          <div className="flex h-full max-[900px]:flex-col">

            <div className="hidden max-[900px]:block max-[750px]:h-[260px] relative h-[350px] w-[1/2 max-[900px]:w-full max-[900px]:h-auto] max-[550px]:h-[200px] max-[450px]:h-[150px]">

              <Image
                src="/assets/dog-cat-fight.webp"
                alt="dog-cat-fight"
                fill
                priority
              />
            </div>

            <div className="w-1/2 max-[900px]:w-full h-full">
              <div className="h-1/4 w-full border-b border-black pt-8 pb-8 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <TbClockHour3 className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Save Time and Money
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Mr. White helps you avoid costly vet visits with complete health histories and timely care recommendations. Pack members enjoy savings on trusted products and services, making quality care more affordable. </p>
              </div>
              <div className="h-1/4 w-full border-b border-black pt-8 pb-8 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <AiOutlinePaperClip className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Build a Deeper Bond
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">With wisdom, guidance, and a community behind you, Mr. White supports you in creating a joyful, harmonious life with your beloved companion. </p>
              </div>
              <div className="h-1/4 w-full border-b border-black pt-8 pb-8 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <GiCrossedBones className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Daily Wisdom and Guidance
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Access free, expert advice from Mr. White—tips on training, health, play, and bonding that help enrich your relationship with your dog every day. Available through your personal portal and X & other social media. </p>
              </div>
              <div className="h-1/4 w-full pt-8 pb-8 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4 max-[900px]:border-b max-[900px]:border-black">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <RiUserCommunityLine className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Community Connection
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Join a supportive community of dog lovers to share stories, advice, meetups, and celebrations, creating friendships and shared joy. </p>
              </div>
            </div>

            <div className="w-1/2 max-[900px]:w-full">

              <div className="h-2/4 pt-8 pl-10 max-[900px]:hidden">
                <div className="relative h-full">

                  <Image
                    src="/assets/dog-cat-fight.webp"
                    alt="dog-cat-fight"
                    fill
                    priority
                  />
                </div>
              </div>

              <div className="h-1/4 w-full border-b border-black pt-8 pb-8 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4 pl-10 max-[900px]:pl-0">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <GiHabitatDome className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Trusted Product Recommendations
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Benefit from vetted product suggestions, focusing on quality and safety, curated from over 50 years of breeder experience. </p>
              </div>

              <div className="h-1/4 w-full pt-8 pb-8 pl-10 max-[1300px]:pt-6 max-[1300px]:pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4 max-[900px]:pl-0">
                <h2 className="text-[16px] font-bold font-public-sans">
                  <HiOutlineSupport className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                  Practical Support for Professionals
                </h2>
                <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Veterinarians, trainers, and groomers can join at a reduced rate, gaining access to a network for sharing insights and connecting with dog families. </p>
              </div>

            </div>

          </div>

        </div>

        <div className="w-full bg-white/10 rounded-sm flex flex-col p-8 max-[550px]:p-6 max-[450px]:p-4">

          <div className="text-[24px] max-[550px]:text-[18px] font-semibold font-work-sans border-b border-black pb-6 flex items-center gap-x-4">
            <Image src="/assets/dog-icon-elite.webp" alt="dog-icon-free" width={100} height={100} className="w-10 h-10 max-[550px]:w-8 max-[550px]:h-8" />
            <h1>2. For Elite Pack Members (Premium) + everything from the Companion Crew Pack Members</h1>
          </div>

          <div className="flex max-[900px]:flex-col border-b border-black gap-10 max-[900px]:gap-6 pt-6 pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
            <div className="w-1/2 max-[900px]:w-full max-[900px]:border-b max-[900px]:border-black  max-[900px]:pb-4">
              <h1 className="text-[16px] font-bold font-public-sans">
                <TbTableFilled className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Exclusive Access to the Legacy of Love Dog Hub
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Unlock the full power of Mr. White's AI-driven personal portal that securely stores your dog's complete health records, training milestones, photos, stories, and more—available anytime, anywhere. This hub simplifies care management and preserves your dog's legacy. </p>
            </div>
            <div className="w-1/2 max-[900px]:w-full">
              <h1 className="text-[16px] font-bold font-public-sans">
                <BiSolidBookBookmark className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Create a Beautiful Keepsake Book
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">As an Elite Pack member, you have the unique ability to transform your dog's story into a beautifully personalized book. Whether it's to celebrate milestones like a first birthday, commemorate a special journey, or simply preserve your favorite memories, you can easily select any section of your Legacy of Love Dog Hub to print as a keepsake. This tangible tribute allows you to hold, share, and treasure the rich life you and your companion have built together—making memories truly timeless. </p>
            </div>
          </div>

          <div className="flex max-[900px]:flex-col border-b gap-10 max-[900px]:gap-6 border-black pt-6 pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
            <div className="w-1/2 max-[900px]:w-full max-[900px]:border-b max-[900px]:border-black  max-[900px]:pb-4">
              <h1 className="text-[16px] font-bold font-public-sans">
                <FaUser className="w-4 h-4 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Personalized Care Alerts and Reminders
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Never miss a medication dose, vet visit, or important appointment with tailored, timely alerts designed specifically for your dog's needs. </p>
            </div>
            <div className="w-1/2 max-[900px]:w-full">
              <h1 className="text-[16px] font-bold font-public-sans">
                <FaVectorSquare className="w-4 h-4 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                BlockchainDNA NFT for Legacy Security
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Receive a unique digital certificate verifying your dog's records on the blockchain, securing your unbreakable bond and protecting your dog's legacy for generations. </p>
            </div>
          </div>

          <div className="flex max-[900px]:flex-col border-b gap-10 max-[900px]:gap-6 border-black justify-between pt-6 pb-6 max-[1200px]:pt-4 max-[1200px]:pb-4">
            <div className="w-1/2 max-[900px]:w-full max-[900px]:border-b max-[900px]:border-black  max-[900px]:pb-4">
              <h1 className="text-[16px] font-bold font-public-sans">
                <BsBagHeartFill className="w-4 h-4 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Access to Trusted Local Services and Dog-Friendly Travel
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Discover recommended vets, groomers, and travel destinations with real community reviews, making care and adventures easier to plan. </p>
            </div>
            <div className="w-1/2 max-[900px]:w-full">
              <h1 className="text-[16px] font-bold font-public-sans">
                <TbCirclePercentageFilled className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Exclusive Product Discounts
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Enjoy lifelong 5% discounts on premium, carefully reviewed products that enhance your dog's health and happiness. </p>
            </div>
          </div>

          <div className="flex max-[900px]:flex-col gap-10 max-[900px]:gap-6 pt-6 pb-8 max-[1200px]:pt-4 max-[1200px]:pb-4">
            <div className="w-1/2 max-[900px]:w-full max-[900px]:border-b max-[900px]:border-black   max-[900px]:pb-4">
              <h1 className="text-[16px] font-bold font-public-sans">
                <MdOutlineFamilyRestroom className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                A Vibrant, Private Community
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Join an exclusive circle of committed dog lovers for deeper connection, support, and shared growth. </p>
            </div>
            <div className="w-1/2 max-[900px]:w-full">
              <h1 className="text-[16px] font-bold font-public-sans">
                <HiOutlineSupport className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)] mb-2" />
                Advanced Support for Professionals
              </h1>
              <p className="text-[16px] max-[550px]:text-justify font-light font-public-sans">Pet care professionals receive expanded tools and community features to enhance their services and build strong relationships with dog families. </p>
            </div>
          </div>

        </div>

        <Button
          onClick={() => {
            localStorage.setItem('redirectAfterLogin', '/subscription');
            router.push('/subscription');
          }}
          className={`w-full mt-16 sm:w-fit md:w-[293px] mx-auto h-[47px] text-[20px] mb-1 flex items-center justify-center gap-2`}
        >
          <ShakingIcon icon={<LuCrown className="!w-6 !h-6" />} />
          View Subscription
        </Button>

      </section>

      {/* SECTION 5 */}
      <div className="bg-gradient-to-t from-white/5 to-black">
        <section className="max-w-[1440px] mx-auto min-h-screen py-16 px-12 flex flex-col md:flex-row justify-center md:justify-between items-center gap-10 max-[1024px]:px-4 max-[450px]:px-3">
          <ImagePop
            src="/assets/home-section-3.webp"
            alt="home-section-dog"
            fill
            className="object-cover"
            containerClassName="w-full md:w-1/2 relative"
            style={{ aspectRatio: '652 / 602' }}
            overlay={true}
          />

          <div className="w-full md:w-1/2 flex flex-col gap-[40px]">
            <FadeInSection className="w-full flex flex-col gap-[2px]">
              <h2 className="font-semibold text-[32px] font-work-sans tracking-tighter">
                Get Started with Mr. White in 3 Easy Steps
              </h2>
              <p className="text-[20px] font-light font-public-sans">
                A short guide on how to get started with Mr White.
              </p>
            </FadeInSection>

            <StepsAnimated direction="flex-col" background="bg-gradient-to-r from-white/10 from-10% to-black to-90%" />
            <div>
              <Button
                onClick={() => {
                  localStorage.setItem('redirectAfterLogin', '/subscription');
                  router.push('/login');
                }}
                disabled={!!user} // disables the button if `user` is truthy
                className={`w-full md:w-[293px] h-[47px] text-[20px] mb-1 flex items-center justify-center gap-2 ${user ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
              >
                <ShakingIcon icon={<TbLogin className="!w-6 !h-6" />} />
                Sign Up & Login
              </Button>
              {user ? <p className="text-sm text-muted-foreground text-center md:text-left"> You're already logged in. </p> : ""}
            </div>
          </div>
        </section>
      </div>

      {/* SECTION 6 */}
      <section className="max-w-[1440px] mx-auto min-h-screen py-16 px-12 flex flex-col justify-center md:justify-between items-center gap-10 max-[1024px]:px-4 max-[450px]:px-3">

        <section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/subscription-hero.png')] bg-cover bg-center">
          <div className="absolute inset-0 bg-black/40"></div>
          <FadeInSection className="h-[70px] w-[1344px]flex flex-col gap-[12px] items-center z-20">
            <h2 className="text-[32px] max-[1200px]:text-center font-semibold font-work-sans tracking-tighter">Connect with Mr. White Your Way: Free or Premium</h2>
            <p className="text-[20px] text-center font-medium font-public-sans">How does Mr. White benefit your life?</p>
          </FadeInSection>
        </section>

        <div className="flex max-[1200px]:flex-col max-[1200px]:items-center gap-[40px]">
          <SubscriptionCard
            title="Mr. White's Companion Crew - FREE Plan"
            subtitle="Enjoy a FREE account with Benefits of Mr. White"
            description="Mr. White guides dogs and their humans toward a fulfilling life with free daily tips on X and other socials @MrWhiteAIBuddy and his website at Mr.WhiteAIBuddy.com. Discover toys, rituals, and training to deepen your bond, plus proven products for health and care, backed by Anahata Graceland's 50+ years of expertise."
            price="Free!"
            priceSubtext="*Lifetime free subscription"
            amount={0}
            features={[
              {
                title: "Access Your Personal Portal Anytime",
                image: "/assets/subscription-1.webp",
                description: "Step into your personal portal with Mr. White, where tailored guidance, and wisdom for you and your companion are available 24/7. It also includes an ongoing history of your priceless queries about your dog."
              },
              {
                title: "Unlock Expert Canine Knowledge",
                image: "/assets/subscription-2.webp",
                description: "Gain insight into your dog's history, needs, and bond with humans through Mr.White's vast data and real-world experience. Get tailored input on questions you raise such as: training and activity recommendations to strengthen your connection. Benefit from fun events, networks, and practices that honor dogs as souls, fostering happier lives together."
              },
              {
                title: "Top Product Recommendations with Care",
                image: "/assets/subscription-3.webp",
                description: "Mr. White reviews products with Anahata Graceland's 50+ years of expertise—those used in her kennel earn a star, as do all we recommend. We focus on quality, longevity, safety, and dog approval, gathering marketplace feedback to ensure the best. With little pet industry regulation, we deliver trusted choices."
              },
              {
                title: "A Unique Dog Lover's Community",
                image: "/assets/subscription-4.webp",
                description: "Mr. White Gathers his pack members to share the unending knowledge and great ideas person to person. Meet new friends, create meet-ups and enjoy accessing a resource that will last a lifetime."
              },
              {
                title: "A Thriving Network for Dog Welfare Professionals ",
                image: "/assets/subscription-5.webp",
                description: "Mr. White supports veterinarians, groomers, trainers, product companies, event organizers, educators, nonprofits, dog park leaders, and wellness practitioners with reduced-rate pack membership. Access dog family records, exchange insights in a fun network, and connect with families to grow your craft and deliver quality care. "
              }
            ]}
          />

          <SubscriptionCard
            title="Mr. White AI Buddy - LEGACY OF LOVE LIVING HUB"
            subtitle="Everything in the FREE Account Plus these Invaluable Services"
            description="Unlock an all-encompassing, AI-powered subscription designed to honor your companion's unique journey and simplify every aspect of their care. This seamless, thoughtfully crafted living hub combines advanced technology with decades of expertise to preserve memories, streamline health management, and nurture the extraordinary bond you share—making life safer, easier, and infinitely more meaningful for both of you."
            price="$19.95/Month - Save 20% on yearly plan"
            priceSubtext="Includes dedicated human support!"
            amount={19.95}
            features={[
              {
                title: "Comprehensive Memory & Care Archive",
                image: "/assets/subscription-6.webp",
                description: "Securely store vital records, vaccination history, medication alerts, vet visits, milestones, photos, and stories—all organized beautifully in one place and accessible 24/7. Preserve every cherished moment while keeping your dog's care on track."
              },
              {
                title: "Personalized Health & Savings Tracker",
                image: "/assets/subscription-7.webp",
                description: "Avoid duplicate vet costs with your pups full health history at your fingertips. Receive expert care tips and timely reminders tailored to support extending your dog's life and wellbeing."
              },
              {
                title: "BlockchainDNA NFT Legacy",
                image: "/assets/subscription-8.webp",
                description: "Protect your family bond with a unique BlockchainDNA NFT that verifies your dog's records on the blockchain, ensuring an unbreakable, verifiable legacy passed down through generations, fully transferrable."
              },
              {
                title: "Interspecies Culture & Bonding Guidance",
                image: "/assets/subscription-9.webp",
                description: "With over 50 years of experience, Anahata Graceland and Mr. White offer unique insights and guidance to help you nurture a deep, respectful relationship that honors your dog and helps you build a bond as equals each with your own roles in one family."
              },
              {
                title: "Trusted Local Services & Dog-Friendly Travel",
                image: "/assets/subscription-10.webp",
                description: "Easily find and review vets, groomers, and discover dog-friendly hotels, restaurants, and destinations—making every outing a joyful adventure."
              },

              {
                title: "Turn Memories into a Treasured Book",
                image: "/assets/subscription-13.webp",
                description: "One of the most special features of your Living Legacy of Love Dog Hub subscription is the ability to create a beautifully personalized book. Whether you want to commemorate your dog's first birthday, a memorable milestone, or simply preserve your favorite photos and stories, you can easily select any section of the Living Hub to print as a keepsake. This tangible collection of memories is perfect for sharing with family and friends or cherishing for years to come—a lasting tribute to the unique journey you share with your companion."
              },
              {
                title: "Private Dog Family Community",
                image: "/assets/subscription-11.webp",
                description: "Connect with fellow dog lovers in an exclusive space to share stories, plan meetups, and strengthen your bonds within a warm, vibrant community."
              },
              {
                title: "Exclusive Discounts & Early Access",
                image: "/assets/subscription-12.webp",
                description: "Enjoy lifetime 5% discounts on qualified recommended products and get first access to new offerings from trusted partners."
              },
              {
                title: "Fetch Subscription – Hassle-Free Essentials Tracking",
                image: "/assets/subscription-14.webp",
                description: "Never worry about running out—get personalized alerts on food, medications, supplements, and more, right on your phone, supported by Mr. White."
              }
            ]}
            isPremium={true}
          />
        </div>

      </section>

      {/* SECTION 7 */}
      <section className="max-w-[1440px] mx-auto min-h-screen py-16 px-12 flex flex-col justify-center md:justify-between items-center gap-10 max-[1024px]:px-4 max-[450px]:px-3">

        <div className="w-full h-fit flex flex-col md:flex-row justify-center md:justify-between gap-10">

          <div className="w-full md:w-1/2  flex flex-col gap-[24px]">
            <div className="w-full h-[108px] flex flex-col justify-between">
              <h2 className="text-[32px]/8 max-[1200px]:text-[24px] font-semibold font-work-sans tracking-tighter">Discover Mr. White: Your Questions
                Answered</h2>
              <p className="text-[20px] font-medium font-public-sans">
                Frequently Asked Questions
              </p>
            </div>

            <div className="max-[900px]:w-full w-[425px] gap-2 bg-white/10 rounded-sm flex flex-col justify-between p-6">
              <p className="text-[20px] font-semibold font-work-sans text-[var(--mrwhite-primary-color)]">Still have questions?</p>
              <p className="text-[16px] font-light font-public-sans">Can&apos;t find your question? Contact us directly!</p>
              <Button onClick={() => router.push('/contact')} className="w-[168px] h-[39px] text-[20px] font-medium font-work-sans">
                <ShakingIcon icon={<IoChatbubble className="!w-6 !h-6" />} />
                Contact Us
              </Button>
            </div>

            <div className="h-[766px]  relative">
              <ImagePop
                src="/assets/home-last.webp"
                alt="mrwhite-nft"
                fill
                className="object-cover"
                containerClassName="w-full h-full"
                style={{
                  maskImage: 'radial-gradient(ellipse at center, black 60%, transparent 100%)',
                  WebkitMaskImage: 'radial-gradient(ellipse at center, black 60%, transparent 100%)'
                }}
              />
            </div>
          </div>

          <div className="w-full md:w-1/2 h-fit px-6 py-6 bg-white/10 rounded-sm">
            <FAQAccordion faqs={faqs} />
          </div>

        </div>

      </section>

      {/* SECTION 6 */}
      <CompanyNameSection
        companies={[
          { src: "/assets/home-company-1.webp", alt: "home-section-6-1" },
          { src: "/assets/home-company-2.webp", alt: "home-section-6-2" },
          { src: "/assets/home-company-3.webp", alt: "home-section-6-3" },
          { src: "/assets/home-company-4.webp", alt: "home-section-6-4" }
        ]}
      />

    </div >
  );
}


