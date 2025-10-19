'use client';

import { ReactNode } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { Crown, Lock, Star, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

interface PremiumGateProps {
    children: ReactNode;
    feature: string;
    showUpgrade?: boolean;
    fallback?: ReactNode;
    className?: string;
}

export const PremiumGate = ({
    children,
    feature,
    showUpgrade = true,
    fallback,
    className = ""
}: PremiumGateProps) => {
    const { user } = useAuth();
    const router = useRouter();

    const hasAccess = user?.is_premium && user?.subscription_status === 'active';

    if (hasAccess) {
        return <>{children}</>;
    }

    if (fallback) {
        return <>{fallback}</>;
    }

    if (!showUpgrade) {
        return null;
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-lg p-6 text-center ${className}`}
        >
            <div className="flex justify-center mb-4">
                <div className="relative">
                    <Crown className="w-12 h-12 text-[var(--mrwhite-primary-color)]" />
                    <Lock className="w-6 h-6 text-gray-400 absolute -bottom-1 -right-1" />
                </div>
            </div>

            <h3 className="text-xl font-semibold text-white mb-2 flex items-center justify-center gap-2">
                <Star className="w-5 h-5 text-[var(--mrwhite-primary-color)]" />
                Premium Feature
                <Star className="w-5 h-5 text-[var(--mrwhite-primary-color)]" />
            </h3>

            <p className="text-gray-300 mb-4">
                <strong>{feature}</strong> is available for Elite Pack members.
            </p>

            <div className="bg-gray-800 rounded-lg p-4 mb-4">
                <p className="text-sm text-gray-400 mb-2">
                    Unlock this feature and many more with the Elite Pack:
                </p>
                <ul className="text-sm text-gray-300 text-left space-y-1">
                    <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                        Comprehensive Memory & Care Archive
                    </li>
                    <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                        Personalized Health Tracking
                    </li>
                    <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                        Enhanced AI Chat with Context
                    </li>
                    <li className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                        And much more...
                    </li>
                </ul>
            </div>

            <Button
                onClick={() => router.push('/subscription')}
                className="w-full bg-gradient-to-r from-[var(--mrwhite-primary-color)] to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-black font-semibold"
            >
                <Crown className="w-4 h-4 mr-2" />
                Upgrade to Elite Pack
            </Button>
        </motion.div>
    );
};

export default PremiumGate; 