'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
    Coins,
    TrendingUp,
    Gift,
    ShoppingCart,
    Zap,
    Crown,
    DollarSign,
    Clock,
    Calendar,
    AlertTriangle
} from 'lucide-react';
import { motion } from 'framer-motion';

interface CreditStatus {
    credits_balance: number;
    available_credits: number;
    subscription_plan: string;
    plan_info: {
        name: string;
        daily_free_credits: number;
        monthly_credit_allowance: number;
        price: number;
        can_purchase_credits: boolean;
    };
    daily_free_credits_claimed: boolean;
    is_elite: boolean;
    can_purchase_credits: boolean;
    credits_used_today: number;
    credits_used_this_month: number;
    estimated_daily_cost: number;
    days_until_monthly_refill: number;
    monthly_allowance_used: number;
    credit_packages: Record<string, any>;
}

interface CreditTrackerProps {
    compact?: boolean;
    showPurchaseOptions?: boolean;
}

export const CreditTracker = ({
    compact = false,
    showPurchaseOptions = true
}: CreditTrackerProps) => {
    const { user, creditRefreshTrigger } = useAuth();
    const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [claiming, setClaiming] = useState(false);
    const [purchasing, setPurchasing] = useState(false);
    const lastFetchTime = useRef<number>(0);
    const FETCH_COOLDOWN = 1000; // Minimum 1 second between API calls

    const fetchCreditStatus = async () => {
        // Rate limiting: prevent excessive API calls
        const now = Date.now();
        if (now - lastFetchTime.current < FETCH_COOLDOWN) {
            return;
        }
        lastFetchTime.current = now;

        if (!user) {
            setLoading(false);
            return;
        }

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/status`, {
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    setCreditStatus(result.data);
                } else {
                    console.error('CreditTracker: Invalid API response structure:', result);
                    setCreditStatus(null);
                }
            } else {
                const errorText = await response.text();
                console.error('CreditTracker: Failed to fetch credit status:', response.status, errorText);
                setCreditStatus(null);
            }
        } catch (error) {
            console.error('CreditTracker: Error fetching credit status:', error);
            setCreditStatus(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) {
            fetchCreditStatus();
        }
    }, [user, creditRefreshTrigger]); // Listen for credit refresh triggers

    const handleClaimDailyCredits = async () => {
        try {
            setClaiming(true);
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/claim-daily`,
                {
                    method: 'POST',
                    credentials: 'include'
                }
            );

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    await fetchCreditStatus();

                    // Optional: Show success message
                    if (typeof window !== 'undefined') {
                        // Success feedback can be handled by UI components
                    }
                } else {
                    console.warn('Claim request succeeded but operation failed:', result.message);
                }
            } else {
                // Parse error response
                try {
                    const errorData = await response.json();
                    const errorMessage = errorData.message || `Failed to claim credits (Status: ${response.status})`;
                    console.warn('Unable to claim daily credits:', errorMessage);

                    // Optional: Show user-friendly error message
                    if (typeof window !== 'undefined') {
                        // Error feedback can be handled by UI components
                    }
                } catch (parseError) {
                    console.error('Failed to claim daily credits:', response.status, 'Unable to parse error response');
                }
            }
        } catch (error) {
            console.error('Error claiming daily credits:', error);

            // Optional: Show network error message
            if (typeof window !== 'undefined') {
                console.log('❌ Network error while claiming credits. Please try again.');
            }
        } finally {
            setClaiming(false);
        }
    };

    const handlePurchaseCredits = async (packageId: string) => {
        try {
            setPurchasing(true);
            // This would integrate with your existing Stripe payment flow
            // For now, just show what would happen
            const pkg = creditStatus?.credit_packages[packageId];
            if (pkg) {
                // Redirect to payment page with package info
                window.location.href = `/payment?package=${packageId}&amount=${pkg.price}&credits=${pkg.credits + pkg.bonus}`;
            }
        } catch (error) {
            console.error('Error purchasing credits:', error);
        } finally {
            setPurchasing(false);
        }
    };

    const formatCreditsAsUSD = (credits: number) => {
        return `$${(credits / 100).toFixed(2)}`;
    };

    const getBalanceColor = (credits: number) => {
        if (credits < 100) return 'text-red-400';
        if (credits < 500) return 'text-yellow-400';
        return 'text-green-400';
    };

    if (loading || !creditStatus) {
        return (
            <div className="animate-pulse bg-gray-800 rounded-sm p-4">
                <div className="h-4 bg-gray-700 rounded w-1/3 mb-2"></div>
                <div className="h-6 bg-gray-700 rounded w-2/3"></div>
            </div>
        );
    }

    if (compact) {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-black  rounded-sm p-3"
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Coins className={`w-5 h-5 ${getBalanceColor(creditStatus.available_credits)}`} />
                        <span className="text-sm font-medium">
                            {creditStatus.available_credits} credits
                        </span>
                        <span className="text-xs text-gray-400 mr-2">
                            ({formatCreditsAsUSD(creditStatus.available_credits)})
                        </span>
                    </div>

                    {creditStatus.is_elite ? (
                        <div className="flex items-center gap-1 text-xs text-[var(--mrwhite-primary-color)]">
                            <Crown className="w-3 h-3" />
                            Elite
                        </div>
                    ) : (
                        !creditStatus.daily_free_credits_claimed && (
                            <Button
                                size="sm"
                                onClick={handleClaimDailyCredits}
                                disabled={claiming}
                                className="bg-green-600 hover:bg-green-700 text-xs font-bold font-public-sans"
                            >
                                <Gift className="w-3 h-3 mr-1" />
                                Claim Free
                            </Button>
                        )
                    )}
                </div>

                {creditStatus.available_credits < 100 && (
                    <div className="mt-2 text-xs text-[var(--mrwhite-primary-color)] flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Low credits
                        {creditStatus.can_purchase_credits && (
                            <span> - purchase more to continue</span>
                        )}
                    </div>
                )}
            </motion.div>
        );
    }

    return (
        <Card className="p-6 bg-gradient-to-r from-white/10 to-black/30 border border-white/30">
            <div className="space-y-4">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Coins className={`w-5 h-5 ${getBalanceColor(creditStatus.available_credits)}`} />
                        Credit Balance
                    </h3>
                    <div className="flex items-center gap-2 text-sm">
                        {creditStatus.is_elite ? (
                            <div className="flex items-center gap-1 text-[var(--mrwhite-primary-color)]">
                                <Crown className="w-4 h-4" />
                                Elite Pack
                            </div>
                        ) : (
                            <div className="text-gray-400">Free Plan</div>
                        )}
                    </div>
                </div>

                {/* Balance Display */}
                <div className="text-center py-4">
                    <div className={`text-3xl font-bold ${getBalanceColor(creditStatus.available_credits)}`}>
                        {creditStatus.available_credits}
                    </div>
                    <div className="text-sm text-gray-400">
                        credits available ({formatCreditsAsUSD(creditStatus.available_credits)} value)
                    </div>
                </div>

                {/* Elite Users - Monthly Allowance Info */}
                {creditStatus.is_elite && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-blue-900/30 border border-blue-500/50 rounded-sm p-4"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-blue-400" />
                                <span className="font-medium text-blue-400">Monthly Allowance</span>
                            </div>
                            <span className="text-sm text-gray-300">
                                {creditStatus.days_until_monthly_refill} days until refill
                            </span>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span>Used this month:</span>
                                <span>{creditStatus.credits_used_this_month} credits</span>
                            </div>
                            <Progress
                                value={creditStatus.monthly_allowance_used}
                                className="h-2"
                            />
                            <div className="text-xs text-gray-400">
                                {creditStatus.monthly_allowance_used.toFixed(1)}% of monthly allowance used
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* Free Users - Daily Credits */}
                {!creditStatus.is_elite && !creditStatus.daily_free_credits_claimed && creditStatus.plan_info && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-green-900/30 border border-green-500/50 rounded-sm p-4"
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Gift className="w-4 h-4 text-green-400" />
                                    <span className="font-medium text-green-400">Daily Free Credits</span>
                                </div>
                                <p className="text-sm text-gray-300">
                                    Claim your {creditStatus.plan_info?.daily_free_credits || 0} free credits
                                    ({formatCreditsAsUSD(creditStatus.plan_info?.daily_free_credits || 0)} value)
                                </p>
                            </div>
                            <Button
                                onClick={handleClaimDailyCredits}
                                disabled={claiming}
                                className="bg-green-600 hover:bg-green-700"
                            >
                                {claiming ? 'Claiming...' : 'Claim Now'}
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* Usage Statistics */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white/10 border border-white/30 rounded-sm p-3">
                        <div className="text-sm  mb-1">Today's Usage</div>
                        <div className="font-medium">
                            {creditStatus.credits_used_today} credits
                        </div>
                        <div className="text-xs">
                            {formatCreditsAsUSD(creditStatus.credits_used_today)}
                        </div>
                    </div>

                    <div className="bg-white/10 border border-white/30 rounded-sm p-3">
                        <div className="text-sm mb-1">Monthly Usage</div>
                        <div className="font-medium">
                            {creditStatus.credits_used_this_month} credits
                        </div>
                        <div className="text-xs">
                            {formatCreditsAsUSD(creditStatus.credits_used_this_month)}
                        </div>
                    </div>
                </div>

                {/* Credit Purchase Options - Only for Elite Users */}
                {creditStatus.can_purchase_credits && showPurchaseOptions && creditStatus.credit_packages && (
                    <div className="space-y-3">
                        <h4 className="font-medium flex items-center gap-2">
                            <ShoppingCart className="w-4 h-4" />
                            Purchase Additional Credits
                        </h4>

                        <div className="grid grid-cols-1 gap-2">
                            {Object.entries(creditStatus.credit_packages).map(([key, pkg]: [string, any]) => {
                                const totalCredits = pkg.credits + pkg.bonus;
                                const savings = pkg.bonus > 0 ? Math.round((pkg.bonus / pkg.credits) * 100) : 0;

                                return (
                                    <div
                                        key={key}
                                        className="flex items-center justify-between p-3 bg-gray-800/50 border border-gray/30 rounded-sm hover:border-gray-600 transition-colors"
                                    >
                                        <div>
                                            <div className="font-medium">
                                                {totalCredits} credits
                                                {savings > 0 && (
                                                    <span className="ml-2 text-xs bg-green-600 text-white px-2 py-1 rounded">
                                                        +{savings}% bonus
                                                    </span>
                                                )}
                                            </div>
                                            <div className="text-sm text-gray-400">
                                                {formatCreditsAsUSD(totalCredits)} value
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-medium">${pkg.price}</div>
                                            <Button
                                                size="sm"
                                                className="mt-1"
                                                onClick={() => handlePurchaseCredits(key)}
                                                disabled={purchasing}
                                            >
                                                {purchasing ? 'Processing...' : 'Buy'}
                                            </Button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Upgrade Prompt for Free Users */}
                {!creditStatus.is_elite && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-gradient-to-r from-yellow-900/30 to-orange-900/30 border border-yellow-500/50 rounded-sm p-4"
                    >
                        <div className="flex items-center gap-2 text-[var(--mrwhite-primary-color)] mb-2">
                            <Crown className="w-4 h-4" />
                            <span className="font-medium">Upgrade to Elite Pack</span>
                        </div>
                        <p className="text-sm text-[var(--mrwhite-primary-color)] mb-3">
                            Get 3,000 credits monthly ($30 value) + access to all premium features
                            + ability to purchase additional credits when needed.
                        </p>
                        <Button
                            className="w-full bg-gradient-to-r whitespace-break-spaces from-[var(--mrwhite-primary-color)] to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-black font-medium"
                            onClick={() => window.location.href = '/subscription'}
                        >
                            Upgrade to Elite Pack - $28.95/month
                        </Button>
                    </motion.div>
                )}

                {/* Low Balance Warning */}
                {creditStatus.available_credits < 100 && creditStatus.is_elite && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-red-900/30 border border-red-500/50 rounded-sm p-4"
                    >
                        <div className="flex items-center gap-2 text-red-400">
                            <AlertTriangle className="w-4 h-4" />
                            <span className="font-medium">Low Credit Balance</span>
                        </div>
                        <p className="text-sm text-red-300 mt-1">
                            You're running low on credits. Purchase additional credits to continue
                            using all features until your next monthly refill in {creditStatus.days_until_monthly_refill} days.
                        </p>
                    </motion.div>
                )}
            </div>
        </Card>
    );
};

export default CreditTracker; 