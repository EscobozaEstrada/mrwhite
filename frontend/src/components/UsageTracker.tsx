'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Progress } from '@/components/ui/progress';
import { AlertTriangle, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';

interface UsageTrackerProps {
    feature: 'chat' | 'documents' | 'care_records';
    currentUsage: number;
    maxUsage: number;
    className?: string;
}

export const UsageTracker = ({
    feature,
    currentUsage,
    maxUsage,
    className = ""
}: UsageTrackerProps) => {
    const { user } = useAuth();
    const router = useRouter();

    // Premium users have unlimited usage
    if (user?.is_premium && user?.subscription_status === 'active') {
        return null;
    }

    const usagePercent = (currentUsage / maxUsage) * 100;
    const isNearLimit = usagePercent >= 80;
    const isAtLimit = currentUsage >= maxUsage;

    const getFeatureLabel = () => {
        switch (feature) {
            case 'chat':
                return 'AI Chat Messages';
            case 'documents':
                return 'Document Uploads';
            case 'care_records':
                return 'Care Records';
            default:
                return 'Usage';
        }
    };

    return (
        <div className={`bg-black border  rounded-lg p-4 ${className}`}>
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-300">
                    {getFeatureLabel()}
                </span>
                <span className="text-sm text-gray-400">
                    {currentUsage} / {maxUsage}
                </span>
            </div>

            <Progress
                value={usagePercent}
                className="mb-2"
                // @ts-ignore
                indicatorClassName={`${isAtLimit ? 'bg-red-500' :
                        isNearLimit ? 'bg-yellow-500' :
                            'bg-green-500'
                    }`}
            />

            {isNearLimit && (
                <div className="flex items-center gap-2 text-sm">
                    <AlertTriangle className={`w-4 h-4 ${isAtLimit ? 'text-red-500' : 'text-yellow-500'}`} />
                    <span className={isAtLimit ? 'text-red-400' : 'text-yellow-400'}>
                        {isAtLimit ? 'Limit reached' : 'Approaching limit'}
                    </span>
                </div>
            )}

            {isAtLimit && (
                <Button
                    onClick={() => router.push('/subscription')}
                    size="sm"
                    className="w-full mt-3 bg-gradient-to-r from-yellow-500 to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-black font-medium"
                >
                    <Zap className="w-4 h-4 mr-2" />
                    Upgrade for Unlimited Access
                </Button>
            )}
        </div>
    );
};

export default UsageTracker; 