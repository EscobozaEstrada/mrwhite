'use client';

import { Button } from '@/components/ui/button';
import { PiBoneFill } from 'react-icons/pi';
import { motion } from 'framer-motion';
import ShakingIcon from './ShakingIcon';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { CheckCircle, Crown, Star, Check, Coins, Zap, Info } from 'lucide-react';
import { FaCircleInfo } from "react-icons/fa6";
import toast from '@/components/ui/sound-toast';

interface SubscriptionCardProps {
    title: string;
    subtitle: string;
    description: string;
    price: string;
    priceSubtext: string;
    features: Array<{
        title: string;
        description: string;
        image: string;
    }>;
    isPremium?: boolean;
    amount?: number;
}

const SubscriptionCard = ({
    title,
    subtitle,
    description,
    price,
    priceSubtext,
    features,
    isPremium = false,
    amount = 19.95,
}: SubscriptionCardProps) => {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const { user, refreshSubscriptionStatus } = useAuth();

    // Check if user already has premium subscription
    const hasActivePremium = user?.is_premium && user?.subscription_status === 'active';

    const getButtonText = () => {
        if (isLoading) return 'Processing...';

        // Check if user is not logged in
        if (!user) {
            return isPremium ? 'Sign Up to Subscribe' : 'Sign Up to Get Started';
        }

        // For free plan
        if (!isPremium) {
            return 'Get Started Free';
        }

        // For premium plan
        if (user?.is_premium) {
            switch (user.subscription_status) {
                case 'active':
                    return 'Current Plan ✓';
                case 'canceled':
                    return 'Reactivate Plan';
                case 'past_due':
                    return 'Resume Plan';
                default:
                    return 'Upgrade to Elite';
            }
        }

        return 'Fetch Subscription';
    };

    const handleSubscription = async () => {
        // Check if user is authenticated first
        if (!user) {
            // Store the intended destination for redirect after login
            localStorage.setItem('redirectAfterLogin', '/subscription');
            router.push('/signup');
            return;
        }

        // Prevent multiple subscriptions
        if (user?.is_premium && user?.subscription_status === 'active') {
            toast.success('You already have an active Elite subscription!', {
                icon: <PiBoneFill className="!w-6 !h-6" />,
                duration: 3000,
                position: 'bottom-center',
                style: {
                    background: '#333',
                    color: '#fff',
                    border: '1px solid #D3B86A',
                }
            });
            return;
        }

        // Handle free subscription
        if (amount === 0) {
            router.push('/');
            return;
        }

        // Handle new subscription purchase (user is already authenticated here)
        try {
            setIsLoading(true);
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL
                ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/payment/create-checkout-session`
                : `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/payment/create-checkout-session`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    success_url: `${window.location.origin}/payment-success?amount=${amount}&type=subscription`,
                    cancel_url: `${window.location.origin}/subscription`,
                    user_id: user?.id,
                    email: user?.email
                }),
                credentials: 'include',
                mode: 'cors'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data && data.url) {
                window.location.href = data.url;
            } else {
                console.error('Invalid response from server:', data);
                setIsLoading(false);
            }
        } catch (error) {
            console.error('Error creating checkout session:', error);
            setIsLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3 }}
            whileHover={{
                boxShadow: `0 0 0 2px var(--mrwhite-primary-color)`
            }}
            className="w-1/2 max-[1200px]:w-[652px] max-[600px]:w-full h-fit flex flex-col gap-[24px] px-6 py-8 bg-white/10 rounded-sm relative"
        >
            {isPremium && <div className='bg-[var(--mrwhite-primary-color)] h-[30px] w-[112px] font-work-sans text-[12px] font-semibold absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 transform rounded-full flex items-center justify-center text-black'>Most Wanted</div>}
            <div className="flex flex-col gap-[12px]">
                <motion.h2
                    initial={{ x: -20, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.1, duration: 0.2 }}
                    className="text-[28px]/8 font-semibold font-work-sans tracking-tighter"
                >
                    {title}
                </motion.h2>

                {
                    isPremium && (
                        <div className="italic text-[28px] font-work-sans font-light">
                            (Your Dog's Name) Legacy of Love Living Hub
                        </div>
                    )
                }

                <div className="flex flex-col gap-[12px]"></div>
                <motion.p
                    initial={{ x: -20, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.15, duration: 0.2 }}
                    className={`text-[16px] font-semibold font-work-sans ${isPremium ? 'bg-[var(--mrwhite-primary-color)] text-black px-2 py-2 w-fit rounded-sm tracking-tighter' : ''
                        }`}
                >
                    {subtitle}
                </motion.p>
                <motion.p
                    initial={{ x: -20, opacity: 0 }}
                    whileInView={{ x: 0, opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.2, duration: 0.2 }}
                    className="text-[16px] text-justify font-light font-public-sans tracking-tight text-white/80"
                >
                    {description}
                </motion.p>
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.25, duration: 0.2 }}
            >
                <h2 className="text-[32px] font-medium font-work-sans text-[var(--mrwhite-primary-color)] tracking-tighter">
                    {price}
                </h2>
                <p className={`text-[14px] font-light font-public-sans text-white/80 ${isPremium ? 'italic text-[16px]' : ''}`}>
                    {priceSubtext}
                </p>
            </motion.div>

            <div className="border-1 border-[var(--mrwhite-primary-color)]" />

            <div className="flex flex-col gap-[24px]">
                {features.map((feature, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3 + index * 0.05, duration: 0.2 }}
                        className="w-full flex flex-col justify-center gap-[12px] border-b-2 border-b-black/80"
                    >
                        <h3 className="text-[16px] font-semibold font-work-sans tracking-tighter gap-[5px]">
                            <div className="relative w-4 h-4 inline-block mr-2">
                                <Image src={feature.image} alt="bone" fill sizes="250px" priority className="object-contain" />
                            </div>
                            {feature.title}
                        </h3>
                        <p className="text-[16px] text-justify mb-6 font-light font-public-sans tracking-tight text-white/80">
                            {feature.description}
                        </p>
                    </motion.div>
                ))}
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4, duration: 0.2 }}
            >
                <Button
                    onClick={handleSubscription}
                    className="w-full self-center h-[45px] text-[20px] relative"
                    disabled={isLoading || (isPremium && hasActivePremium)}
                >
                    <div className="flex items-center justify-center gap-2">
                        {isLoading ? <div className="relative w-12 h-6">
                            <Image
                                src="/assets/running-dog.gif"
                                alt="Loading"
                                fill
                                priority
                                className="object-cover"
                            />
                        </div> : <ShakingIcon icon={<PiBoneFill className="!w-6 !h-6" />} />}
                        <span>{isLoading ? 'Processing...' : getButtonText()}</span>

                        <div className="group relative inline-block">
                            <FaCircleInfo className="w-5 h-5 cursor-help opacity-70 hover:opacity-100 text-black" />
                            <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-black text-white text-xs rounded-md absolute z-10 px-3 py-2 -right-4 bottom-full mb-2 w-fit text-center">
                                {isPremium
                                    ? "Credit-based usage - pay only for what you use!"
                                    : "Limited to 10 free credits daily"}
                                <div className="absolute bottom-[-5px] right-[18px] w-2 h-2 bg-black transform rotate-45"></div>
                            </div>
                        </div>
                    </div>
                </Button>
            </motion.div>

            {/* Additional Info */}
            {isPremium && hasActivePremium && (
                <div className="mt-3 text-center text-xs text-gray-400">
                    <div>Subscription active since {user.subscription_start_date ? new Date(user.subscription_start_date).toLocaleDateString() : 'N/A'}</div>
                    <a href="/subscription/manage" className="text-[var(--mrwhite-primary-color)] hover:underline">
                        Manage subscription
                    </a>
                </div>
            )}
        </motion.div>
    );
};

export default SubscriptionCard;