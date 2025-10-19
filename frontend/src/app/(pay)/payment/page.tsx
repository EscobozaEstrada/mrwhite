'use client';

import CheckoutPage from "@/components/CheckoutPage";
import convertToSubcurrency from "@/lib/convertToSubcurrency";
import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { FiCreditCard, FiShield, FiStar } from 'react-icons/fi';
import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const stripePromise = (() => {
    const key = process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY;
    if (!key) {
        console.error('NEXT_PUBLIC_STRIPE_PUBLIC_KEY is not defined');
        return null;
    }
    console.log('Stripe key loaded:', key.substring(0, 20) + '...');
    return loadStripe(key);
})();

const PaymentPage = () => {
    const searchParams = useSearchParams();
    const router = useRouter();
    const amountParam = searchParams.get('amount');
    const packageParam = searchParams.get('package');
    const creditsParam = searchParams.get('credits');

    const [paymentType, setPaymentType] = useState<'subscription' | 'credits'>('subscription');
    const [packageInfo, setPackageInfo] = useState<any>(null);

    // Safely parse the amount parameter with validation
    const amount = (() => {
        if (!amountParam) return 28.95; // Default amount

        const parsed = parseFloat(amountParam);

        // Validate the amount is a positive number
        if (isNaN(parsed) || parsed <= 0) {
            return 28.95; // Default to 28.95 if invalid
        }

        return parsed;
    })();

    // Determine payment type and package info
    useEffect(() => {
        if (packageParam && creditsParam) {
            setPaymentType('credits');
            setPackageInfo({
                id: packageParam,
                credits: parseInt(creditsParam) || 0,
                amount: amount
            });
        } else {
            setPaymentType('subscription');
        }
    }, [packageParam, creditsParam, amount]);

    // Redirect to subscription page if amount is invalid or zero
    useEffect(() => {
        if (amountParam === '0' || amount <= 0) {
            router.replace('/subscription');
        }
    }, [amountParam, amount, router]);

    const getOrderSummary = () => {
        if (paymentType === 'credits' && packageInfo) {
            return {
                title: 'Credit Package',
                description: `${packageInfo.credits} credits`,
                amount: amount
            };
        } else {
            return {
                title: 'Elite Subscription',
                description: 'Monthly subscription with 3,000 credits',
                amount: amount
            };
        }
    };

    const orderSummary = getOrderSummary();

    return (
        <div className="flex flex-col gap-y-12 bg-black min-h-screen">
            {/* Hero Section */}
            <section className="h-[200px] md:h-[250px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/talk-hero.png')] bg-cover bg-center">
                <div className="absolute inset-0 bg-black/40"></div>
                <div className="z-20 px-4 text-center">
                    <h1 className="text-[28px] md:text-[40px] font-work-sans font-semibold text-center">
                        {paymentType === 'credits' ? 'Purchase Credits' : 'Complete Your Payment'}
                    </h1>
                    <p className="text-[16px] md:text-[20px] font-public-sans font-light text-center">
                        Secure checkout powered by Stripe
                    </p>
                </div>
            </section>

            {/* Payment Section */}
            <section className="px-4 md:px-0 max-w-[1000px] mx-auto w-full mb-20">
                <div className="bg-neutral-950 rounded-lg shadow-xl flex flex-col md:flex-row">
                    {/* Left Side - Order Summary */}
                    <div className="md:w-1/3 p-6 md:p-8 border-r border-neutral-800">
                        <h2 className="text-xl font-semibold mb-6">Order Summary</h2>

                        <div className="space-y-4">
                            <div className="flex justify-between">
                                <span className="text-neutral-400">{orderSummary.title}</span>
                                <span>${orderSummary.amount.toFixed(2)}</span>
                            </div>

                            <div className="text-sm text-neutral-500">
                                {orderSummary.description}
                            </div>

                            {paymentType === 'credits' && packageInfo && (
                                <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
                                    <div className="flex items-center gap-2 text-blue-400 text-sm mb-2">
                                        <FiStar className="w-4 h-4" />
                                        <span>Bonus Credits Included</span>
                                    </div>
                                    <div className="text-xs text-blue-300">
                                        Total value: ${(packageInfo.credits / 100).toFixed(2)}
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-between">
                                <span className="text-neutral-400">Subtotal</span>
                                <span>${orderSummary.amount.toFixed(2)}</span>
                            </div>

                            <div className="border-t border-neutral-800 pt-4 mt-4">
                                <div className="flex justify-between font-semibold">
                                    <span>Total due today</span>
                                    <span>${orderSummary.amount.toFixed(2)}</span>
                                </div>
                                <p className="text-xs text-neutral-400 mt-2">
                                    {paymentType === 'credits'
                                        ? 'One-time payment for credits. Credits never expire.'
                                        : "You'll be charged the amount and at the frequency listed above until you cancel."
                                    }
                                </p>
                            </div>
                        </div>

                        <div className="mt-8 pt-6 border-t border-neutral-800">
                            <div className="flex items-center gap-2 text-neutral-400 text-sm mb-4">
                                <FiShield className="w-4 h-4" />
                                <span>Secure payment</span>
                            </div>
                            <div className="flex items-center gap-2 text-neutral-400 text-sm">
                                <FiCreditCard className="w-4 h-4" />
                                <span>Powered by Stripe</span>
                            </div>
                        </div>
                    </div>

                    {/* Right Side - Payment Form */}
                    <div className="md:w-2/3 p-6 md:p-8">
                        <h2 className="text-xl font-semibold mb-6">Payment Details</h2>
                        <div className="bg-neutral-900 p-6 rounded-lg">
                            <Elements
                                stripe={stripePromise}
                                options={{
                                    mode: "payment",
                                    amount: convertToSubcurrency(amount),
                                    currency: "usd",
                                    paymentMethodTypes: ['card'],
                                    appearance: {
                                        theme: 'night',
                                        variables: {
                                            colorPrimary: '#ffffff',
                                            colorBackground: '#171717',
                                            colorText: '#ffffff',
                                            colorDanger: '#ef4444',
                                            fontFamily: 'Public Sans, ui-sans-serif, system-ui',
                                            borderRadius: '4px',
                                            spacingUnit: '4px',
                                        },
                                    }
                                }}
                            >
                                <CheckoutPage
                                    amount={amount}
                                    paymentType={paymentType}
                                    packageInfo={packageInfo}
                                />
                            </Elements>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    )
}

export default PaymentPage;