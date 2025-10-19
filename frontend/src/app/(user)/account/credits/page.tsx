'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import {
    Coins,
    Crown,
    TrendingUp,
    Gift,
    ShoppingCart,
    Calendar,
    AlertTriangle,
    ArrowRight,
    Zap,
    Plus,
    Settings,
    ExternalLink
} from 'lucide-react';
import { motion } from 'framer-motion';
import { CreditTracker } from '@/components/CreditTracker';
import { Progress } from '@/components/ui/progress';

const CreditManagementPage = () => {
    const { user, creditRefreshTrigger, triggerCreditRefresh } = useAuth();
    const router = useRouter();
    const [creditStatus, setCreditStatus] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            fetchCreditStatus();
        } else {
            router.push('/login');
        }
    }, [user, router, creditRefreshTrigger]);

    const fetchCreditStatus = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5001';
            const url = `${apiUrl}/api/credit-system/status`;

            const response = await fetch(url, {
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    setCreditStatus(result.data);
                } else {
                    console.error('Invalid API response structure:', result);
                    setCreditStatus(null);
                }
            } else {
                const errorText = await response.text();
                console.error('Credits page: Error fetching credit status:', response.status, errorText);
                setCreditStatus(null);
            }
        } catch (error) {
            console.error('Credits page: Error fetching credit status:', error);
            setCreditStatus(null);
        } finally {
            setLoading(false);
        }
    };

    const formatCreditsAsUSD = (credits: number) => {
        return `$${(credits / 100).toFixed(2)}`;
    };

    const getBalanceColor = (credits: number) => {
        if (credits < 100) return 'text-red-400';
        if (credits < 500) return 'text-[var(--mrwhite-primary-color)]';
        return 'text-green-400';
    };

    if (loading || !creditStatus) {
        return (
            <div className="min-h-screen bg-background p-6">
                <div className="max-w-6xl mx-auto">
                    <div className="animate-pulse space-y-6">
                        <div className="h-8 bg-gray-700 rounded w-1/3"></div>
                        <div className="h-32 bg-gray-700 rounded"></div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <div className="h-48 bg-gray-700 rounded"></div>
                            <div className="h-48 bg-gray-700 rounded"></div>
                            <div className="h-48 bg-gray-700 rounded"></div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background px-12 max-[1024px]:px-4 max-[450px]:px-3 pb-20">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h1 className="text-4xl font-bold text-foreground mb-2 flex items-center gap-3">
                        <Coins className={`w-8 h-8 ${getBalanceColor(creditStatus.available_credits)}`} />
                        Credit Management
                    </h1>
                    <p className="text-muted-foreground">
                        Monitor your credit balance, usage, and purchase additional credits
                    </p>
                </motion.div>

                {/* Credit Balance Overview */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="mb-8"
                >
                    <Card className="p-6 bg-gradient-to-r from-white/10 to-black/30 border border-white/30">
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-2 mb-4">
                                {creditStatus.is_elite ? (
                                    <div className="flex items-center gap-2 text-[var(--mrwhite-primary-color)]">
                                        <Crown className="w-6 h-6" />
                                        <span className="text-lg font-semibold">Elite Pack Member</span>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-2 text-gray-400">
                                        <Gift className="w-6 h-6" />
                                        <span className="text-lg font-semibold">Free Plan Member</span>
                                    </div>
                                )}
                            </div>

                            <div className={`text-5xl font-bold mb-2 ${getBalanceColor(creditStatus.available_credits)}`}>
                                {creditStatus.available_credits}
                            </div>
                            <div className="text-lg text-gray-300 mb-4">
                                credits available ({formatCreditsAsUSD(creditStatus.available_credits)} value)
                            </div>

                            {!creditStatus.is_elite && !creditStatus.daily_free_credits_claimed && creditStatus.plan_info && (
                                <Button
                                    className="bg-green-600 hover:bg-green-700"
                                    onClick={() => window.location.reload()}
                                >
                                    <Gift className="w-4 h-4 mr-2" />
                                    Claim {creditStatus.plan_info?.daily_free_credits || 0} Free Credits Today
                                </Button>
                            )}
                        </div>
                    </Card>
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    {/* Usage Statistics */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <Card className="p-6">
                            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <TrendingUp className="w-5 h-5 text-blue-400" />
                                Usage Statistics
                            </h3>

                            <div className="space-y-4">
                                <div className="bg-gray-800/50 rounded-sm p-4">
                                    <div className="text-sm text-gray-400 mb-1">Today's Usage</div>
                                    <div className="text-2xl font-bold text-white">
                                        {creditStatus.credits_used_today}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        {formatCreditsAsUSD(creditStatus.credits_used_today)} spent
                                    </div>
                                </div>

                                <div className="bg-gray-800/50 rounded-sm p-4">
                                    <div className="text-sm text-gray-400 mb-1">This Month</div>
                                    <div className="text-2xl font-bold text-white">
                                        {creditStatus.credits_used_this_month}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        {formatCreditsAsUSD(creditStatus.credits_used_this_month)} spent
                                    </div>
                                </div>

                                {creditStatus.is_elite && (
                                    <div className="bg-blue-900/30 border border-blue-500/50 rounded-sm p-4">
                                        <div className="text-sm text-blue-400 mb-2">Monthly Allowance Used</div>
                                        <Progress
                                            value={creditStatus.monthly_allowance_used}
                                            className="h-2 mb-2"
                                        />
                                        <div className="text-xs text-gray-400">
                                            {creditStatus.monthly_allowance_used.toFixed(1)}% of 3,000 credits used
                                        </div>
                                    </div>
                                )}
                            </div>
                        </Card>
                    </motion.div>

                    {/* Quick Actions */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <Card className="p-6">
                            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Zap className="w-5 h-5 text-[var(--mrwhite-primary-color)]" />
                                Quick Actions
                            </h3>

                            <div className="space-y-3">
                                <Button
                                    onClick={() => router.push('/talk/conversation/new-chat')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <Coins className="w-4 h-4 mr-2" />
                                    Start Using Credits
                                    <ArrowRight className="w-4 h-4 ml-auto" />
                                </Button>

                                {creditStatus.is_elite && (
                                    <Button
                                        onClick={() => router.push('/care-archive')}
                                        className="w-full justify-start"
                                        variant="outline"
                                    >
                                        <Settings className="w-4 h-4 mr-2" />
                                        Care Archive
                                        <ArrowRight className="w-4 h-4 ml-auto" />
                                    </Button>
                                )}

                                <Button
                                    onClick={() => router.push('/subscription')}
                                    className="w-full justify-start"
                                    variant="outline"
                                >
                                    <Crown className="w-4 h-4 mr-2" />
                                    View Plans
                                    <ExternalLink className="w-4 h-4 ml-auto" />
                                </Button>

                                {creditStatus.is_elite && (
                                    <Button
                                        onClick={() => router.push('/subscription/manage')}
                                        className="w-full justify-start"
                                        variant="outline"
                                    >
                                        <Settings className="w-4 h-4 mr-2" />
                                        Manage Subscription
                                        <ExternalLink className="w-4 h-4 ml-auto" />
                                    </Button>
                                )}
                            </div>
                        </Card>
                    </motion.div>

                    {/* Account Info */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.4 }}
                    >
                        <Card className="p-6">
                            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Calendar className="w-5 h-5 text-green-400" />
                                Account Info
                            </h3>

                            <div className="space-y-3">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Plan:</span>
                                    <span className="font-medium">
                                        {creditStatus.is_elite ? 'Elite Pack' : 'Free Plan'}
                                    </span>
                                </div>

                                <div className="flex justify-between">
                                    <span className="text-gray-400">Total Credits Purchased:</span>
                                    <span className="font-medium">{creditStatus.total_credits_purchased || 0}</span>
                                </div>

                                {creditStatus.is_elite && (
                                    <div className="flex justify-between">
                                        <span className="text-gray-400">Next Refill:</span>
                                        <span className="font-medium text-blue-400">
                                            {creditStatus.days_until_monthly_refill} days
                                        </span>
                                    </div>
                                )}

                                {!creditStatus.is_elite && (
                                    <div className="bg-[var(--mrwhite-primary-color)]/30 border border-[var(--mrwhite-primary-color)]/50 rounded-sm p-3">
                                        <div className="text-xs text-[var(--mrwhite-primary-color)]">
                                            Upgrade to Elite to get 3,000 monthly credits + purchase additional credits
                                        </div>
                                    </div>
                                )}
                            </div>
                        </Card>
                    </motion.div>
                </div>

                {/* Credit Purchase Section - Only for Elite Users */}
                {creditStatus.can_purchase_credits && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="mb-8"
                    >
                        <Card className="p-6">
                            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <ShoppingCart className="w-5 h-5 text-purple-400" />
                                Purchase Additional Credits
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {Object.entries(creditStatus.credit_packages).map(([key, pkg]: [string, any]) => {
                                    const totalCredits = pkg.credits + pkg.bonus;
                                    const savings = pkg.bonus > 0 ? Math.round((pkg.bonus / pkg.credits) * 100) : 0;

                                    return (
                                        <div
                                            key={key}
                                            className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border border-purple-500/30 rounded-sm p-4 hover:border-purple-500/50 transition-colors"
                                        >
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-white mb-1">
                                                    {totalCredits}
                                                </div>
                                                <div className="text-sm text-gray-400 mb-2">
                                                    credits ({formatCreditsAsUSD(totalCredits)} value)
                                                </div>
                                                {savings > 0 && (
                                                    <div className="bg-green-600 text-white text-xs px-2 py-1 rounded mb-3">
                                                        +{savings}% bonus credits
                                                    </div>
                                                )}
                                                <div className="text-xl font-bold text-[var(--mrwhite-primary-color)] mb-4">
                                                    ${pkg.price}
                                                </div>
                                                <Button
                                                    className="w-full bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
                                                    onClick={() => {
                                                        window.location.href = `/payment?package=${key}&amount=${pkg.price}&credits=${totalCredits}`;
                                                    }}
                                                >
                                                    <Plus className="w-4 h-4 mr-2" />
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

                {/* Upgrade Prompt for Free Users */}
                {!creditStatus.is_elite && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.6 }}
                    >
                        <Card className="p-6 bg-gradient-to-r from-[var(--mrwhite-primary-color)]/30 to-orange-900/30 border border-[var(--mrwhite-primary-color)]/50">
                            <div className="text-center">
                                <Crown className="w-12 h-12 text-[var(--mrwhite-primary-color)] mx-auto mb-4" />
                                <h3 className="text-2xl font-bold text-[var(--mrwhite-primary-color)] mb-2">
                                    Upgrade to Elite Pack
                                </h3>
                                <p className="text-[var(--mrwhite-primary-color)] mb-6">
                                    Get 3,000 credits monthly ($30 value) + access to all premium features
                                    + ability to purchase additional credits when needed.
                                </p>
                                <Button
                                    size="lg"
                                    className="bg-gradient-to-r whitespace-break-spaces from-[var(--mrwhite-primary-color)] to-orange-500 hover:from-[var(--mrwhite-primary-color)] hover:to-orange-600 text-black font-bold px-8"
                                    onClick={() => router.push('/subscription')}
                                >
                                    <Crown className="w-5 h-5 mr-2" />
                                    Upgrade to Elite Pack - $28.95/month
                                </Button>
                            </div>
                        </Card>
                    </motion.div>
                )}

                {/* Low Balance Warning */}
                {creditStatus.available_credits < 100 && creditStatus.is_elite && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.7 }}
                        className="mt-6"
                    >
                        <Card className="p-6 bg-red-900/30 border border-red-500/50">
                            <div className="flex items-center gap-3">
                                <AlertTriangle className="w-6 h-6 text-red-400" />
                                <div>
                                    <h3 className="text-lg font-semibold text-red-400">Low Credit Balance</h3>
                                    <p className="text-red-300">
                                        You're running low on credits. Purchase additional credits to continue
                                        using all features until your next monthly refill in {creditStatus.days_until_monthly_refill} days.
                                    </p>
                                </div>
                            </div>
                        </Card>
                    </motion.div>
                )}

                {/* Full Credit Tracker Component */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 }}
                    className="mt-8"
                >
                    <CreditTracker compact={false} showPurchaseOptions={true} />
                </motion.div>
            </div>
        </div>
    );
};

export default CreditManagementPage; 