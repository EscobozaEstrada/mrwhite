'use client';

import Link from 'next/link';
import { FiArrowLeft, FiCheckCircle, FiCreditCard } from 'react-icons/fi';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Coins } from 'lucide-react';

const PaymentSuccessPage = () => {
    const searchParams = useSearchParams();
    const { refreshSubscriptionStatus, user, triggerCreditRefresh, creditStatus } = useAuth();
    const [amount, setAmount] = useState<string>('0');
    const [paymentType, setPaymentType] = useState<'subscription' | 'credits'>('subscription');
    const [packageInfo, setPackageInfo] = useState<any>(null);
    const [isRefreshing, setIsRefreshing] = useState(true);
    const [refreshComplete, setRefreshComplete] = useState(false);
    const refreshTriggeredRef = useRef(false);
    const router = useRouter();

    useEffect(() => {
        // Safely access searchParams in useEffect
        const amountParam = searchParams.get('amount');
        const typeParam = searchParams.get('type');
        const packageParam = searchParams.get('package');
        const creditsParam = searchParams.get('credits');
        const processedParam = searchParams.get('processed');

        if (amountParam) {
            setAmount(amountParam);
        }

        if (typeParam === 'credits') {
            setPaymentType('credits');
            if (packageParam && creditsParam) {
                setPackageInfo({
                    id: packageParam,
                    credits: parseInt(creditsParam) || 0,
                    processed: processedParam === 'true'
                });
            }
        }

        // Only refresh once when the component mounts
        if (!refreshTriggeredRef.current && user) {
            refreshTriggeredRef.current = true;

            // Single refresh with a delay to allow webhook processing
            setTimeout(async () => {
                try {
                    console.log('Performing single payment verification refresh...');

                    // For subscription payments, refresh subscription status
                    if (paymentType === 'subscription') {
                        await refreshSubscriptionStatus();
                    }

                    // For credit purchases, process if needed and refresh credit status
                    if (paymentType === 'credits') {
                        const paymentIntentParam = searchParams.get('payment_intent');
                        if (paymentIntentParam && !processedParam) {
                            try {
                                console.log('Attempting manual credit processing...');
                                await fetch(
                                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/payment/verify-and-process-credit-purchase`,
                                    {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        credentials: 'include',
                                        body: JSON.stringify({
                                            payment_intent_id: paymentIntentParam,
                                            user_id: user?.id
                                        })
                                    }
                                );
                            } catch (error) {
                                console.error('Credit processing error:', error);
                            }
                        }

                        // Refresh credit status once
                        triggerCreditRefresh();
                    }

                } catch (error) {
                    console.error('Error during payment verification:', error);
                } finally {
                    setIsRefreshing(false);
                    setRefreshComplete(true);
                }
            }, 3000); // Single delay of 3 seconds
        }
    }, [searchParams, user, paymentType, refreshSubscriptionStatus, triggerCreditRefresh]);

    // Simplified verification for credit purchases
    useEffect(() => {
        if (paymentType === 'credits' && user && !refreshTriggeredRef.current && creditStatus) {
            refreshTriggeredRef.current = true;

            // Check if credits were already added
            const currentBalance = creditStatus.credits_balance;
            const totalPurchased = creditStatus.total_credits_purchased || 0;

            console.log(`Credit verification: Balance=${currentBalance}, Purchased=${totalPurchased}`);

            // If credits don't appear to be added yet, try one more refresh after a delay
            if (currentBalance < 3000 && totalPurchased === 0) {
                setTimeout(() => {
                    console.log('Final credit verification attempt');
                    triggerCreditRefresh();
                    setRefreshComplete(true);
                }, 5000);
            } else {
                console.log('✅ Credit purchase verified - credits were added successfully!');
                setRefreshComplete(true);
            }
        } else if (paymentType === 'subscription' && user) {
            // For subscription payments, just mark as complete
            setRefreshComplete(true);
        }
    }, [paymentType, user, creditStatus]);

    const getSuccessContent = () => {
        if (paymentType === 'credits' && packageInfo) {
            const isProcessed = packageInfo.processed;
            return {
                title: isProcessed ? 'Credits Added Successfully!' : 'Payment Processed!',
                description: isProcessed
                    ? `${packageInfo.credits} credits have been added to your account`
                    : `Your payment for ${packageInfo.credits} credits has been processed`,
                icon: <Coins className="w-10 h-10 text-green-500" />,
                primaryAction: {
                    text: isProcessed ? 'Start Using Credits' : 'View Account',
                    href: isProcessed ? '/talk/conversation/new-chat' : '/account/credits'
                },
                secondaryAction: {
                    text: 'View Credit Balance',
                    href: '/account/credits'
                }
            };
        } else {
            return {
                title: 'Welcome to Elite Pack!',
                description: 'Your subscription is now active with 3,000 monthly credits',
                icon: <FiCheckCircle className="w-10 h-10 text-green-500" />,
                primaryAction: {
                    text: 'Start Chatting',
                    href: '/talk/conversation/new-chat'
                },
                secondaryAction: {
                    text: 'Manage Subscription',
                    href: '/subscription/manage'
                }
            };
        }
    };

    const content = getSuccessContent();

    return (
        <div className="flex flex-col gap-y-24 bg-black min-h-screen">
            {/* Hero Section */}
            <section className="h-[200px] md:h-[250px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/talk-hero.png')] bg-cover bg-center">
                <div className="absolute inset-0 bg-black/40"></div>
                <div className="z-20 px-4 text-center">
                    <h1 className="text-[28px] md:text-[40px] font-work-sans font-semibold text-center">
                        Payment Successful
                    </h1>
                    <p className="text-[16px] md:text-[20px] font-public-sans font-light text-center">
                        Thank you for your purchase
                    </p>
                </div>
                <Link
                    href="/"
                    className="absolute top-8 left-8 flex items-center gap-2 text-white hover:text-gray-300 transition-colors"
                >
                    <FiArrowLeft className="w-5 h-5" />
                    <span>Go to Home</span>
                </Link>
            </section>

            {/* Success Section */}
            <section className="px-4 md:px-0 max-w-[800px] mx-auto w-full mb-20">
                <div className="bg-neutral-950 rounded-lg p-6 md:p-10 shadow-xl text-center">
                    <div className="flex flex-col items-center mb-8">
                        <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mb-6">
                            {content.icon}
                        </div>
                        <h2 className="text-2xl md:text-3xl font-semibold mb-2">
                            {content.title}
                        </h2>
                        <p className="text-neutral-400 mb-6">
                            {content.description}
                        </p>

                        <div className="bg-neutral-900 p-6 rounded-lg mb-6 w-full max-w-md">
                            <div className="flex items-center justify-center gap-2 mb-2">
                                <FiCreditCard className="w-5 h-5 text-neutral-400" />
                                <p className="text-neutral-400">Amount Paid</p>
                            </div>
                            <p className="text-3xl md:text-4xl font-bold">${amount}</p>

                            {paymentType === 'credits' && packageInfo && (
                                <div className="mt-4 pt-4 border-t border-neutral-800">
                                    <div className="flex items-center justify-center gap-2 text-blue-400">
                                        <Coins className="w-4 h-4" />
                                        <span className="text-sm">{packageInfo.credits} Credits Added</span>
                                    </div>
                                </div>
                            )}

                            {paymentType === 'subscription' && (
                                <div className="mt-4 pt-4 border-t border-neutral-800">
                                    <div className="flex items-center justify-center gap-2 text-green-400">
                                        <Coins className="w-4 h-4" />
                                        <span className="text-sm">3,000 Monthly Credits Included</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {isRefreshing && (
                            <div className="mb-4 text-neutral-400 text-sm">
                                Updating your account...
                            </div>
                        )}

                        <div className="flex flex-col gap-4 w-full max-w-md">
                            <Link
                                href={content.primaryAction.href}
                                className="w-full py-4 px-6 bg-white text-black font-bold text-lg rounded-md hover:bg-white/90 transition-all duration-200 text-center"
                            >
                                {content.primaryAction.text}
                            </Link>
                            <Link
                                href={content.secondaryAction.href}
                                className="w-full py-4 px-6 bg-transparent border border-white text-white font-bold text-lg rounded-md hover:bg-white/10 transition-all duration-200 text-center"
                            >
                                {content.secondaryAction.text}
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default PaymentSuccessPage;