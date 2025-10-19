'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import {
    CheckCircle,
    AlertTriangle,
    X,
    CreditCard,
    ExternalLink,
    Zap,
    Coins,
    TrendingUp,
    Plus,
    ShoppingCart,
    Crown,
    Calendar,
    Settings,
    Download,
} from 'lucide-react';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { Progress } from '@/components/ui/progress';
import CreditDisplay from '@/components/CreditDisplay';
import CancelSubscriptionDialog from './_components/CancelSubscriptionDialog';
import ReactivateSubscriptionDialog from './_components/ReactivateSubscriptionDialog';

const SubscriptionManagePage = () => {
    const { user, refreshSubscriptionStatus, creditStatus } = useAuth();
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [cancelLoading, setCancelLoading] = useState(false);
    const [creditLoading, setCreditLoading] = useState(false);
    const [showCancelDialog, setShowCancelDialog] = useState(false);
    const [showReactivateDialog, setShowReactivateDialog] = useState(false);
    const [showCancelSuccess, setShowCancelSuccess] = useState(false);
    const [showReactivateSuccess, setShowReactivateSuccess] = useState(false);

    // Redirect if not premium user and handle subscription status changes
    useEffect(() => {
        if (user && !user.is_premium) {
            router.push('/subscription');
        }
        
        // Set credit loading state based on creditStatus
        if (creditStatus) {
            setCreditLoading(false);
        }

        // Log subscription details for debugging
        if (user && user.subscription_status === 'canceled') {
            console.log('Subscription end date:', user.subscription_end_date);
            
            // If subscription was just canceled, show success message
            if (!showCancelSuccess) {
                setShowCancelSuccess(true);
            }
        }
    }, [user, router, creditStatus, showCancelSuccess]);

    // Refresh subscription status periodically
    useEffect(() => {
        // Initial refresh
        const refreshStatus = async () => {
            if (user) {
                await refreshSubscriptionStatus(undefined, true);
            }
        };
        
        // Set up periodic refresh
        const intervalId = setInterval(refreshStatus, 10000); // Every 10 seconds
        
        // Clean up
        return () => clearInterval(intervalId);
    }, [user, refreshSubscriptionStatus]);

    // Reset success message after 5 seconds
    useEffect(() => {
        if (showCancelSuccess) {
            const timer = setTimeout(() => {
                setShowCancelSuccess(false);
            }, 5000);
            
            return () => clearTimeout(timer);
        }
    }, [showCancelSuccess]);

    useEffect(() => {
        if (showReactivateSuccess) {
            const timer = setTimeout(() => {
                setShowReactivateSuccess(false);
            }, 5000);
            
            return () => clearTimeout(timer);
        }
    }, [showReactivateSuccess]);

    const handleBillingPortal = async () => {
        try {
            setLoading(true);
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/billing-portal`,
                {},
                { withCredentials: true }
            );

            if (response.data.url) {
                window.open(response.data.url, '_blank');
            }
        } catch (error) {
            console.error('Error opening billing portal:', error);
            toast.error('Failed to open billing portal');
        } finally {
            setLoading(false);
        }
    };

    const handleCancelSubscription = async () => {
        try {
            setCancelLoading(true);
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/cancel`,
                {},
                { withCredentials: true }
            );

            if (response.status === 200) {
                toast.success('Subscription canceled successfully');
                console.log('Cancellation response:', response.data);
                
                // Force refresh subscription status to bypass cooldown
                await refreshSubscriptionStatus(undefined, true);
                setShowCancelDialog(false);
                
                // Force a second refresh after a short delay to ensure we get the updated status from Stripe
                setTimeout(async () => {
                    await refreshSubscriptionStatus(undefined, true);
                }, 1000);
            }
        } catch (error) {
            console.error('Error canceling subscription:', error);
            toast.error('Failed to cancel subscription');
        } finally {
            setCancelLoading(false);
        }
    };

    const handleReactivateSubscription = async () => {
        try {
            setCancelLoading(true);
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/reactivate`,
                {},
                { withCredentials: true }
            );

            if (response.status === 200) {
                toast.success('Subscription reactivated successfully');
                console.log('Reactivation response:', response.data);
                
                // Force refresh subscription status to bypass cooldown
                await refreshSubscriptionStatus(undefined, true);
                setShowReactivateDialog(false);
                
                // Force a second refresh after a short delay to ensure we get the updated status from Stripe
                setTimeout(async () => {
                    await refreshSubscriptionStatus(undefined, true);
                    setShowReactivateSuccess(true);
                }, 1000);
            }
        } catch (error) {
            console.error('Error reactivating subscription:', error);
            toast.error('Failed to reactivate subscription');
        } finally {
            setCancelLoading(false);
        }
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) return 'N/A';
        
        try {
            // Try to parse the date string
            const date = new Date(dateString);
            
            // Check if date is valid
            if (isNaN(date.getTime())) {
                console.error('Invalid date string:', dateString);
                return 'N/A';
            }
            
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (error) {
            console.error('Error formatting date:', error, dateString);
            return 'N/A';
        }
    };

    const formatCreditsAsUSD = (credits: number) => {
        return `$${(credits / 100).toFixed(2)}`;
    };

    const getStatusColor = (status?: string) => {
        switch (status) {
            case 'active':
                return 'text-green-500';
            case 'canceled':
                return 'text-yellow-500';
            case 'past_due':
                return 'text-red-500';
            default:
                return 'text-gray-500';
        }
    };

    const getStatusIcon = (status?: string) => {
        switch (status) {
            case 'active':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'canceled':
                return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
            case 'past_due':
                return <X className="w-5 h-5 text-red-500" />;
            default:
                return <AlertTriangle className="w-5 h-5 text-gray-500" />;
        }
    };

    const getBalanceColor = (credits: number) => {
        if (credits < 100) return 'text-red-400';
        if (credits < 500) return 'text-yellow-400';
        return 'text-green-400';
    };

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background px-12 max-[1024px]:px-4 max-[450px]:px-3">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h1 className="text-4xl font-bold text-foreground mb-2 flex items-center gap-3">
                        <Crown className="w-8 h-8 text-yellow-500" />
                        Elite Pack Management
                    </h1>
                    <p className="text-muted-foreground">
                        Manage your Mr. White Elite Pack subscription, billing, and credits
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    {/* Subscription Status Card */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                        <Card className="p-6">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                {getStatusIcon(user.subscription_status)}
                                Subscription Status
                            </h2>

                            <div className="mb-6">
                                <div className="flex items-center gap-2 mb-2">
                                    <div className="text-sm text-muted-foreground">Status:</div>
                                    <div className={`text-sm font-medium ${getStatusColor(user.subscription_status)}`}>
                                        {user.subscription_status === 'active' && 'Active'}
                                        {user.subscription_status === 'canceled' && 'Canceled - Access until period end'}
                                        {user.subscription_status === 'past_due' && 'Past Due'}
                                        {!user.subscription_status && 'Inactive'}
                                    </div>
                                </div>

                                {user.subscription_status === 'canceled' && (
                                    <div className="flex items-center gap-2 mb-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-md">
                                        <Calendar className="w-4 h-4 text-yellow-500" />
                                        <div className="text-sm">
                                            {user.subscription_end_date ? (
                                                <>Your subscription will end on <span className="font-medium">{formatDate(user.subscription_end_date)}</span></>
                                            ) : (
                                                <>Your subscription will end at the end of your current billing period</>
                                            )}
                                        </div>
                                    </div>
                                )}

                                <div className="flex items-center gap-2 mb-2">
                                    <div className="text-sm text-muted-foreground">Start Date:</div>
                                    <div className="text-sm">{formatDate(user.subscription_start_date)}</div>
                                </div>
                                
                                {user.subscription_status !== 'canceled' && (
                                    <div className="flex items-center gap-2">
                                        <div className="text-sm text-muted-foreground">Next Billing:</div>
                                        <div className="text-sm">{formatDate(user.subscription_end_date)}</div>
                                    </div>
                                )}
                            </div>

                            {user.payment_failed && (
                                <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3">
                                    <div className="flex items-center gap-2 text-red-400">
                                        <AlertTriangle className="w-4 h-4" />
                                        <span className="text-sm font-medium">Payment Failed</span>
                                    </div>
                                    <p className="text-sm text-red-300 mt-1">
                                        Please update your payment method to continue your subscription.
                                    </p>
                                </div>
                            )}
                        </Card>
                    </motion.div>

                    {/* Credit Status Card */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <Card className="p-6">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Coins className={creditStatus ? getBalanceColor(creditStatus.available_credits) : "text-gray-400"} />
                                Credit Status
                            </h2>

                            {creditLoading || !creditStatus ? (
                                <div className="animate-pulse space-y-3">
                                    <div className="h-4 bg-gray-700 rounded w-3/4"></div>
                                    <div className="h-4 bg-gray-700 rounded w-1/2"></div>
                                    <div className="h-4 bg-gray-700 rounded w-2/3"></div>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Available Credits:</span>
                                        <span className={`font-medium ${getBalanceColor(creditStatus.available_credits)}`}>
                                            {creditStatus.available_credits}
                                        </span>
                                    </div>

                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Credits Value:</span>
                                        <span className="font-medium">
                                            {formatCreditsAsUSD(creditStatus.available_credits)}
                                        </span>
                                    </div>

                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Used This Month:</span>
                                        <span className="font-medium">
                                            {creditStatus.credits_used_this_month}
                                        </span>
                                    </div>

                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Next Refill:</span>
                                        <span className="font-medium text-blue-400">
                                            {creditStatus.days_until_monthly_refill} days
                                        </span>
                                    </div>

                                    {creditStatus.available_credits < 100 && (
                                        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-3 mt-3">
                                            <div className="flex items-center gap-2 text-red-400">
                                                <AlertTriangle className="w-4 h-4" />
                                                <span className="text-sm font-medium">Low Credit Balance</span>
                                            </div>
                                            <p className="text-sm text-red-300 mt-1">
                                                Consider purchasing additional credits below.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </Card>
                    </motion.div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    {/* Subscription Actions Card */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <Card className="p-6">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Settings className="w-5 h-5" />
                                Subscription Actions
                            </h2>

                            {showCancelSuccess && user.subscription_status === 'canceled' && (
                                <div className="bg-green-900/20 border border-green-500/50 rounded-lg p-3 mb-4 animate-fade-in">
                                    <div className="flex items-center gap-2 text-green-400">
                                        <CheckCircle className="w-4 h-4" />
                                        <span className="text-sm font-medium">Subscription Canceled Successfully</span>
                                    </div>
                                    <p className="text-sm text-green-300 mt-1">
                                        Your subscription will remain active until {formatDate(user.subscription_end_date)}.
                                    </p>
                                </div>
                            )}

                            {showReactivateSuccess && user.subscription_status === 'active' && (
                                <div className="bg-green-900/20 border border-green-500/50 rounded-lg p-3 mb-4 animate-fade-in">
                                    <div className="flex items-center gap-2 text-green-400">
                                        <CheckCircle className="w-4 h-4" />
                                        <span className="text-sm font-medium">Subscription Reactivated Successfully</span>
                                    </div>
                                    <p className="text-sm text-green-300 mt-1">
                                        Your subscription is now active and will continue to renew automatically.
                                    </p>
                                </div>
                            )}

                            <div className="space-y-3">
                                <Button
                                    onClick={handleBillingPortal}
                                    disabled={loading}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <CreditCard className="w-4 h-4 mr-2" />
                                    {loading ? 'Opening...' : 'Manage Billing & Payment'}
                                    <ExternalLink className="w-4 h-4 ml-auto" />
                                </Button>

                                <Button
                                    onClick={() => router.push('/subscription')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <Crown className="w-4 h-4 mr-2" />
                                    View All Plans
                                </Button>



                                {user.subscription_status === 'active' && (
                                    <Button
                                        onClick={() => setShowCancelDialog(true)}
                                        disabled={cancelLoading}
                                        className="w-full justify-start"
                                        variant="destructive"
                                    >
                                        <X className="w-4 h-4 mr-2" />
                                        {cancelLoading ? 'Canceling...' : 'Cancel Subscription'}
                                    </Button>
                                )}

                                {user.subscription_status === 'canceled' && (
                                    <>
                                        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mb-3">
                                            <div className="flex items-center gap-2 text-yellow-400">
                                                <AlertTriangle className="w-4 h-4" />
                                                <span className="text-sm font-medium">Subscription Canceled</span>
                                            </div>
                                            <p className="text-sm text-yellow-300/80 mt-1">
                                                Your subscription has been canceled and will end on {formatDate(user.subscription_end_date)}.
                                                You can reactivate your subscription before this date to continue your benefits.
                                            </p>
                                        </div>
                                        
                                        <Button
                                            onClick={() => setShowReactivateDialog(true)}
                                            disabled={cancelLoading}
                                            className="w-full justify-start"
                                            variant="outline"
                                        >
                                            <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                                            Reactivate Subscription
                                        </Button>
                                    </>
                                )}
                            </div>
                        </Card>
                    </motion.div>

                    {/* Credit Actions Card */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 }}
                    >
                        <Card className="p-6">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Zap className="w-5 h-5 text-yellow-400" />
                                Credit Actions
                            </h2>

                            <div className="space-y-3">
                                <Button
                                    onClick={() => router.push('/account/credits')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <Coins className="w-4 h-4 mr-2" />
                                    Full Credit Management
                                    <ExternalLink className="w-4 h-4 ml-auto" />
                                </Button>

                                <Button
                                    onClick={() => router.push('/talk/conversation/new-chat')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <TrendingUp className="w-4 h-4 mr-2" />
                                    Start Using Credits
                                </Button>

                                {creditStatus?.can_purchase_credits && (
                                    <Button
                                        onClick={() => router.push('/account/credits')}
                                        className="w-full justify-start bg-blue-600 hover:bg-blue-700"
                                    >
                                        <Plus className="w-4 h-4 mr-2" />
                                        Purchase More Credits
                                    </Button>
                                )}
                            </div>
                        </Card>
                    </motion.div>
                </div>

                {/* Credit Purchase Packages - Only show if user can purchase credits */}
                {creditStatus?.can_purchase_credits && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="mb-8"
                    >
                        <Card className="p-6">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <ShoppingCart className="w-5 h-5 text-purple-400" />
                                Quick Credit Purchases
                            </h2>
                            <p className="text-muted-foreground mb-6">
                                Need more credits? Purchase additional credits instantly to continue using all Elite features.
                            </p>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {Object.entries((creditStatus as any).credit_packages || {}).map(([key, pkg]: [string, any]) => {
                                    const totalCredits = pkg.credits + pkg.bonus;
                                    const savings = pkg.bonus > 0 ? Math.round((pkg.bonus / pkg.credits) * 100) : 0;

                                    return (
                                        <div
                                            key={key}
                                            className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border border-purple-500/30 rounded-lg p-4 hover:border-purple-500/50 transition-colors"
                                        >
                                            <div className="text-center">
                                                <div className="text-xl font-bold text-white mb-1">
                                                    {totalCredits}
                                                </div>
                                                <div className="text-sm text-gray-400 mb-2">
                                                    credits
                                                </div>
                                                <div className="text-xs text-gray-500 mb-2">
                                                    {formatCreditsAsUSD(totalCredits)} value
                                                </div>
                                                {savings > 0 && (
                                                    <div className="bg-green-600 text-white text-xs px-2 py-1 rounded mb-3">
                                                        +{savings}% bonus
                                                    </div>
                                                )}
                                                <div className="text-lg font-bold text-yellow-400 mb-3">
                                                    ${pkg.price}
                                                </div>
                                                <Button
                                                    size="sm"
                                                    className="w-full bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
                                                    onClick={() => {
                                                        window.location.href = `/payment?package=${key}&amount=${pkg.price}&credits=${totalCredits}`;
                                                    }}
                                                >
                                                    <Plus className="w-3 h-3 mr-1" />
                                                    Buy Now
                                                </Button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </Card>
                    </motion.div>
                )}

                {/* Features Overview */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="mt-8"
                >
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold mb-4">Your Elite Pack Benefits</h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {[
                                '3,000 Monthly Credits ($30 value)',
                                'Unlimited AI Chat Messages',
                                'Comprehensive Care Archive',
                                'Document Upload & Processing',
                                'Health Tracking & Analytics',
                                'Voice Message Processing',
                                'Advanced AI Features',
                                'Credit Purchase Options',
                                'Priority Customer Support'
                            ].map((feature, index) => (
                                <div key={index} className="flex items-center gap-2 text-sm">
                                    <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                                    <span>{feature}</span>
                                </div>
                            ))}
                        </div>
                    </Card>
                </motion.div>

                {/* Credit Display Component */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7 }}
                    className="mt-8"
                >
                    <h2 className="text-xl font-semibold mb-4">Detailed Credit Information</h2>
                    <CreditDisplay variant="mobile" />
                </motion.div>

                
            </div>
            
            {/* Cancel Subscription Dialog */}
            <CancelSubscriptionDialog 
                open={showCancelDialog}
                onOpenChange={setShowCancelDialog}
                onConfirm={handleCancelSubscription}
                loading={cancelLoading}
            />

            {/* Reactivate Subscription Dialog */}
            <ReactivateSubscriptionDialog
                open={showReactivateDialog}
                onOpenChange={setShowReactivateDialog}
                onConfirm={handleReactivateSubscription}
                loading={cancelLoading}
            />
        </div>
    );
};

export default SubscriptionManagePage; 