'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import { Crown, Calendar, CreditCard, AlertTriangle, CheckCircle } from 'lucide-react';

const SubscriptionManagePage = () => {
    const { user, refreshSubscriptionStatus } = useAuth();
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleBillingPortal = async () => {
        try {
            setLoading(true);
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/billing-portal`,
                {
                    method: 'POST',
                    credentials: 'include'
                }
            );

            if (response.ok) {
                const data = await response.json();
                window.open(data.url, '_blank');
            }
        } catch (error) {
            console.error('Error opening billing portal:', error);
        } finally {
            setLoading(false);
        }
    };

    if (!user?.is_premium) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Crown className="w-16 h-16 text-[var(--mrwhite-primary-color)] mx-auto mb-4" />
                    <h1 className="text-2xl font-bold mb-2">Premium Access Required</h1>
                    <Button onClick={() => router.push('/subscription')}>
                        Upgrade to Elite Pack
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-6">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-4xl font-bold mb-8 flex items-center gap-3">
                    <Crown className="w-8 h-8 text-[var(--mrwhite-primary-color)]" />
                    Subscription Management
                </h1>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Card className="p-6">
                        <h2 className="text-xl font-semibold mb-4">Subscription Status</h2>
                        <div className="space-y-3">
                            <div className="flex justify-between">
                                <span>Plan:</span>
                                <span className="font-medium">Elite Pack</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Status:</span>
                                <span className={`font-medium ${user.subscription_status === 'active' ? 'text-green-500' : 'text-yellow-500'
                                    }`}>
                                    {user.subscription_status || 'Active'}
                                </span>
                            </div>
                        </div>
                    </Card>

                    <Card className="p-6">
                        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                        <div className="space-y-3">
                            <Button
                                onClick={handleBillingPortal}
                                disabled={loading}
                                className="w-full"
                                variant="outline"
                            >
                                <CreditCard className="w-4 h-4 mr-2" />
                                {loading ? 'Opening...' : 'Manage Billing'}
                            </Button>
                        </div>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default SubscriptionManagePage; 