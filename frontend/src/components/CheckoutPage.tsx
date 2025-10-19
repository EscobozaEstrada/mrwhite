'use client';

import React, { useState, useEffect } from "react";
import { useStripe, useElements, PaymentElement } from "@stripe/react-stripe-js";
import { useAuth } from "@/context/AuthContext";
import convertToSubcurrency from "@/lib/convertToSubcurrency";
import axios from "axios";
import { Loader2, CheckCircle } from "lucide-react";

interface CheckoutPageProps {
    amount: number;
    paymentType?: 'subscription' | 'credits';
    packageInfo?: {
        id: string;
        credits: number;
        amount: number;
    } | null;
}

const CheckoutPage = ({ amount, paymentType = 'subscription', packageInfo }: CheckoutPageProps) => {
    const stripe = useStripe();
    const elements = useElements();
    const { user } = useAuth();

    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [clientSecret, setClientSecret] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    useEffect(() => {
        const fetchClientSecret = async () => {
            try {
                setIsLoading(true);

                const requestData: any = {
                    amount: convertToSubcurrency(amount),
                    user_id: user?.id,
                };

                // Add package info for credit purchases
                if (paymentType === 'credits' && packageInfo) {
                    requestData.package_id = packageInfo.id;
                }

                const response = await axios.post(
                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/payment/create-payment-intent`,
                    requestData,
                    { withCredentials: true }
                );

                setClientSecret(response.data.clientSecret);
            } catch (error) {
                console.error("Error fetching client secret:", error);
                setErrorMessage("Could not initialize payment system. Please try again later.");
            } finally {
                setIsLoading(false);
            }
        }

        if (user) {
            fetchClientSecret();
        } else {
            setErrorMessage("Please log in to complete your purchase.");
        }
    }, [amount, paymentType, packageInfo, user]);

    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();

        if (!stripe || !elements || !clientSecret) {
            setErrorMessage("Stripe has not been properly initialized");
            return;
        }

        if (!user) {
            setErrorMessage("Please log in to complete your purchase.");
            return;
        }

        setIsLoading(true);

        try {
            // First submit the form elements
            const { error: submitError } = await elements.submit();

            if (submitError) {
                setErrorMessage(submitError.message || 'Payment form submission failed');
                setIsLoading(false);
                return;
            }

            // For credit purchases, use a different confirmation approach
            if (paymentType === 'credits') {
                // Use confirm payment without redirect for better control
                const { error: confirmError, paymentIntent } = await stripe.confirmPayment({
                    elements,
                    clientSecret: clientSecret,
                    redirect: 'if_required'
                });

                if (confirmError) {
                    setErrorMessage(confirmError.message || "Payment confirmation failed");
                    setIsLoading(false);
                    return;
                }

                // Wait a moment for Stripe to fully process
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Check payment status by retrieving the payment intent
                if (paymentIntent?.id) {
                    try {
                        // Try manual processing first as a backup to webhook
                        if (paymentIntent.status === 'succeeded') {
                            try {
                                const processResponse = await axios.post(
                                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/payment/verify-and-process-credit-purchase`,
                                    {
                                        payment_intent_id: paymentIntent.id,
                                        user_id: user.id
                                    },
                                    { withCredentials: true }
                                );

                                if (processResponse.data.success) {
                                    const redirectUrl = `/payment-success?amount=${amount}&type=${paymentType}&package=${packageInfo?.id}&credits=${packageInfo?.credits}&processed=true`;
                                    window.location.href = redirectUrl;
                                    return;
                                }
                            } catch (processError: any) {
                                // If manual processing fails, continue to webhook fallback
                            }
                        }

                        // If manual processing fails or payment isn't succeeded yet, redirect and let webhook handle it
                        const redirectUrl = `/payment-success?amount=${amount}&type=${paymentType}&package=${packageInfo?.id}&credits=${packageInfo?.credits}&payment_intent=${paymentIntent.id}&status=${paymentIntent.status}`;
                        window.location.href = redirectUrl;
                    } catch (error: any) {
                        console.error("Error processing credit purchase:", error);
                        setErrorMessage("Payment completed but credits may take a few moments to appear. Please refresh your account.");
                        setIsLoading(false);
                    }
                } else {
                    setErrorMessage("Payment processing failed - no payment intent returned");
                    setIsLoading(false);
                }
            } else {
                // For subscription payments, use the redirect approach
                const { error: confirmError } = await stripe.confirmPayment({
                    elements,
                    clientSecret: clientSecret,
                    confirmParams: {
                        return_url: `${process.env.NEXT_PUBLIC_FRONTEND_URL}/payment-success?amount=${amount}&type=${paymentType}`,
                    }
                });

                if (confirmError) {
                    setErrorMessage(confirmError.message || "Payment confirmation failed");
                    setIsLoading(false);
                    return;
                }
            }
        } catch (error) {
            console.error("Payment error:", error);
            setErrorMessage("An unexpected error occurred during payment processing");
            setIsLoading(false);
        }
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center py-8">
                <p className="text-red-400 mb-4">Please log in to complete your purchase.</p>
                <button
                    onClick={() => window.location.href = '/login'}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                    Log In
                </button>
            </div>
        );
    }

    if (isLoading && !clientSecret) {
        return (
            <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-white mb-4" />
                <p className="text-neutral-400">Initializing payment system...</p>
            </div>
        );
    }

    if (!clientSecret || !stripe || !elements) {
        return (
            <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-white" />
            </div>
        );
    }

    return (
        <div className="w-full">
            <form onSubmit={handleSubmit} className="w-full">
                <div className="w-full mb-6">
                    {clientSecret && (
                        <PaymentElement
                            className="w-full"
                            options={{
                                paymentMethodOrder: ['card'],
                                fields: {
                                    billingDetails: {
                                        name: 'auto',
                                        email: 'auto',
                                        phone: 'auto',
                                        address: {
                                            country: 'auto',
                                            line1: 'auto',
                                            line2: 'auto',
                                            city: 'auto',
                                            state: 'auto',
                                            postalCode: 'auto',
                                        }
                                    }
                                },
                                defaultValues: {
                                    billingDetails: {
                                        name: user?.email ? user.email.split('@')[0] : '',
                                        email: user?.email || '',
                                        phone: '',
                                        address: {
                                            country: 'US',
                                        }
                                    }
                                },
                                wallets: {
                                    applePay: 'never',
                                    googlePay: 'never'
                                }
                            }}
                        />
                    )}
                </div>

                {errorMessage && (
                    <div className="bg-red-900/30 border border-red-500 text-red-300 px-4 py-3 rounded-md mb-4">
                        {errorMessage}
                    </div>
                )}

                {message && (
                    <div className="bg-green-900/30 border border-green-500 text-green-300 px-4 py-3 rounded-md mb-4 flex items-center">
                        <CheckCircle className="mr-2 h-5 w-5" />
                        {message}
                    </div>
                )}

                <button
                    className="w-full py-4 px-6 bg-[var(--mrwhite-primary-color)] text-black font-bold text-lg rounded-md hover:bg-[var(--mrwhite-primary-color)]/80 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                    disabled={!stripe || isLoading}
                    type="submit"
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin mr-2" />
                            Processing...
                        </>
                    ) : (
                        `Pay $${amount}`
                    )}
                </button>

                {paymentType === 'credits' && (
                    <p className="text-center text-xs text-neutral-400 mt-3">
                        Credits will be added to your account immediately after payment
                    </p>
                )}
            </form>
        </div>
    );
}

export default CheckoutPage;