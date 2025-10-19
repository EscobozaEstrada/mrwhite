'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import {
    Crown,
    Calendar,
    CreditCard,
    AlertTriangle,
    CheckCircle,
    Settings,
    Download,
    X,
    ExternalLink,
    Coins,
    Plus,
    TrendingUp,
    Zap,
    ShoppingCart
} from 'lucide-react';
import { motion } from 'framer-motion';
import { CreditDisplay } from '@/components/CreditDisplay';
import { Progress } from '@/components/ui/progress';
import axios from 'axios';
import { toast } from 'react-toastify';

const SubscriptionManagePage = () => {
    const { user, refreshSubscriptionStatus } = useAuth();
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [cancelLoading, setCancelLoading] = useState(false);
    const [creditStatus, setCreditStatus] = useState<any>(null);
    const [creditLoading, setCreditLoading] = useState(true);

    // Redirect if not premium user
    useEffect(() => {
        if (user && !user.is_premium) {
            router.push('/subscription');
        }
    }, [user, router]);

    useEffect(() => {
        if (user) {
            fetchCreditStatus();
        }
    }, [user]);

    const fetchCreditStatus = async () => {
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/status`,
                { credentials: 'include' }
            );

            if (response.ok) {
                const data = await response.json();
                setCreditStatus(data.data);
            }
        } catch (error) {
            console.error('Error fetching credit status:', error);
        } finally {
            setCreditLoading(false);
        }
    };

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
        if (!confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your billing period.')) {
            return;
        }

        try {
            setCancelLoading(true);
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/cancel`,
                {},
                { withCredentials: true }
            );

            if (response.status === 200) {
                toast.success('Subscription canceled successfully');
                await refreshSubscriptionStatus();
            }
        } catch (error) {
            console.error('Error canceling subscription:', error);
            toast.error('Failed to cancel subscription');
        } finally {
            setCancelLoading(false);
        }
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
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

                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Plan:</span>
                                    <span className="font-medium">Elite Pack</span>
                                </div>

                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Status:</span>
                                    <span className={`font-medium capitalize ${getStatusColor(user.subscription_status)}`}>
                                        {user.subscription_status || 'Unknown'}
                                    </span>
                                </div>

                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Started:</span>
                                    <span className="font-medium">{formatDate(user.subscription_start_date)}</span>
                                </div>

                                {user.subscription_status === 'canceled' && user.subscription_end_date && (
                                    <div className="flex justify-between">
                                        <span className="text-muted-foreground">Expires:</span>
                                        <span className="font-medium text-yellow-500">
                                            {formatDate(user.subscription_end_date)}
                                        </span>
                                    </div>
                                )}

                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Last Payment:</span>
                                    <span className="font-medium">{formatDate(user.last_payment_date)}</span>
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
                            </div>
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

                                    {creditStatus.monthly_allowance_used !== undefined && (
                                        <div className="mt-4">
                                            <div className="flex justify-between text-sm mb-2">
                                                <span>Monthly allowance used:</span>
                                                <span>{creditStatus.monthly_allowance_used.toFixed(1)}%</span>
                                            </div>
                                            <Progress value={creditStatus.monthly_allowance_used} className="h-2" />
                                        </div>
                                    )}

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

                                <Button
                                    onClick={() => router.push('/care-archive')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <Download className="w-4 h-4 mr-2" />
                                    Access Care Archive
                                </Button>

                                {user.subscription_status === 'active' && (
                                    <Button
                                        onClick={handleCancelSubscription}
                                        disabled={cancelLoading}
                                        className="w-full justify-start"
                                        variant="destructive"
                                    >
                                        <X className="w-4 h-4 mr-2" />
                                        {cancelLoading ? 'Canceling...' : 'Cancel Subscription'}
                                    </Button>
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
                                {Object.entries(creditStatus.credit_packages || {}).map(([key, pkg]: [string, any]) => {
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
        </div>
    );
};

export default SubscriptionManagePage; 