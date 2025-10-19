'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Coins, Crown, Plus, Gift, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface CreditStatus {
    credits_balance: number;
    available_credits: number;
    is_elite: boolean;
    daily_free_credits_claimed: boolean;
    can_purchase_credits: boolean;
    plan_info: {
        daily_free_credits: number;
    };
}

interface CreditDisplayProps {
    variant?: 'navbar' | 'mobile';
}

export const CreditDisplay = ({ variant = 'navbar' }: CreditDisplayProps) => {
    const { user, creditRefreshTrigger } = useAuth();
    const router = useRouter();
    const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
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
                    console.error('CreditDisplay: Invalid API response structure:', result);
                    setCreditStatus(null);
                }
            } else {
                const errorText = await response.text();
                console.error('CreditDisplay: Failed to fetch credit status:', response.status, errorText);
                setCreditStatus(null);
            }
        } catch (error) {
            console.error('CreditDisplay: Error fetching credit status:', error);
            setCreditStatus(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user) {
            fetchCreditStatus();
        } else {
            setLoading(false);
        }
    }, [user, creditRefreshTrigger]); // Listen for credit refresh triggers

    const getBalanceColor = (credits: number) => {
        if (credits < 100) return 'text-red-400';
        if (credits < 500) return 'text-yellow-400';
        return 'text-green-400';
    };

    const handleClaimCredits = async () => {
        try {
            // More robust API URL detection
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL ||
                (typeof window !== 'undefined' && window.location.origin === 'http://localhost:3000'
                    ? 'http://localhost:5001'
                    : 'http://localhost:5001');
            const response = await fetch(
                `${apiUrl}/api/credit-system/claim-daily`,
                {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                }
            );

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    await fetchCreditStatus();

                    // Optional: Show success toast/notification
                    if (typeof window !== 'undefined') {
                        // You could add a toast notification here
                        console.log('✅ Credits claimed successfully!');
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
                        // You could add a toast notification here
                        console.log('ℹ️', errorMessage);
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
        }
    };

    // Show loading state
    if (loading) {
        return (
            <div className="flex items-center gap-2">
                <div className="animate-pulse">
                    <div className="h-8 w-20 bg-gray-700 rounded"></div>
                </div>
            </div>
        );
    }

    // Show error state
    if (error) {
        return (
            <div className="flex items-center gap-2">
                <Button
                    variant="ghost"
                    onClick={fetchCreditStatus}
                    className="px-3 py-1 h-auto text-xs text-red-400 border border-red-700"
                    title={error}
                >
                    <Coins className="w-4 h-4" />
                    Error
                </Button>
            </div>
        );
    }

    // Hide if no user or no credit status
    if (!user || !creditStatus) {
        return null;
    }

    if (variant === 'mobile') {
        return (
            <div className="bg-gray-800/50 rounded-lg p-3 mb-4">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Coins className={`w-4 h-4 ${getBalanceColor(creditStatus.available_credits)}`} />
                        <span className="text-sm font-medium">
                            {creditStatus.available_credits} credits
                        </span>
                        {creditStatus.is_elite && (
                            <Crown className="w-3 h-3 text-yellow-400" />
                        )}
                    </div>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => router.push('/account/credits')}
                        className="text-xs"
                    >
                        Manage
                    </Button>
                </div>

                <div className="flex gap-2">
                    {!creditStatus.is_elite && !creditStatus.daily_free_credits_claimed && creditStatus.plan_info && (
                        <Button
                            size="sm"
                            onClick={handleClaimCredits}
                            className="bg-green-600 hover:bg-green-700 text-xs flex-1"
                        >
                            <Gift className="w-3 h-3 mr-1" />
                            Claim {creditStatus.plan_info?.daily_free_credits || 0}
                        </Button>
                    )}

                    {creditStatus.can_purchase_credits && (
                        <Button
                            size="sm"
                            onClick={() => router.push('/account/credits')}
                            className="bg-blue-600 hover:bg-blue-700 text-xs flex-1"
                        >
                            <Plus className="w-3 h-3 mr-1" />
                            Buy More
                        </Button>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2">
            {/* Credit Balance Display */}
            <Button
                variant="ghost"
                onClick={() => router.push('/account/credits')}
                className="px-3 py-1 h-auto flex items-center gap-2 hover:bg-gray-800 transition-colors border border-gray-700"
            >
                <Coins className={`w-4 h-4 ${getBalanceColor(creditStatus.available_credits)}`} />
                <span className="text-sm font-medium">
                    {creditStatus.available_credits}
                </span>
                {creditStatus.is_elite && (
                    <Crown className="w-3 h-3 text-yellow-400" />
                )}
            </Button>

            {/* Quick Action Button */}
            {!creditStatus.is_elite && !creditStatus.daily_free_credits_claimed ? (
                <Button
                    size="sm"
                    onClick={handleClaimCredits}
                    className="bg-green-600 hover:bg-green-700 px-2 py-1 h-auto text-xs"
                    title="Claim free daily credits"
                >
                    <Gift className="w-3 h-3" />
                </Button>
            ) : creditStatus.can_purchase_credits && creditStatus.available_credits < 500 ? (
                <Button
                    size="sm"
                    onClick={() => router.push('/account/credits')}
                    className="bg-blue-600 hover:bg-blue-700 px-2 py-1 h-auto text-xs"
                    title="Buy more credits"
                >
                    <Plus className="w-3 h-3" />
                </Button>
            ) : null}
        </div>
    );
};

export default CreditDisplay; 