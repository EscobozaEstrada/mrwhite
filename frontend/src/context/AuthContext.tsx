'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react'
import axios from 'axios'
import { User } from '@/types/user'
import { PushNotificationService } from '@/services/pushNotificationService'

interface CreditStatus {
    credits_balance: number;
    available_credits: number;
    is_elite: boolean;
    daily_free_credits_claimed: boolean;
    can_purchase_credits: boolean;
    plan_info: {
        daily_free_credits: number;
        monthly_credit_allowance?: number;
    };
    total_credits_purchased?: number;
    credits_used_today?: number;
    credits_used_this_month?: number;
    days_until_monthly_refill?: number;
    monthly_allowance_used?: number;
    credit_packages?: Record<string, any>;
    cost_breakdown?: {
        chat_messages: number;
        document_processing: number;
        health_features: number;
        other: number;
    };
}

interface AuthContextType {
    user: User | null;
    setUser: (user: User | null) => void;
    loading: boolean;
    refreshSubscriptionStatus: (userData?: User, force?: boolean) => Promise<void>;
    refreshCreditStatus: (force?: boolean) => Promise<CreditStatus | null>;
    refreshUser: () => Promise<void>;
    creditRefreshTrigger: number;
    triggerCreditRefresh: () => void;
    forceCreditRefresh: () => Promise<void>;
    pushNotificationSupported: boolean;
    initializePushNotifications: () => Promise<boolean>;
    logout: () => Promise<void>;
    creditStatus: CreditStatus | null;
    token: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [creditRefreshTrigger, setCreditRefreshTrigger] = useState(0)
    const [pushNotificationSupported, setPushNotificationSupported] = useState(false)
    const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null)
    const lastTriggerTime = useRef<number>(0)
    const pushService = useRef<PushNotificationService | null>(null)
    const TRIGGER_COOLDOWN = 1000 // 1 second minimum between triggers
    const lastStatusFetchTime = useRef<number>(0)
    const STATUS_FETCH_COOLDOWN = 1000 // 1 second between status API calls
    const lastSubscriptionFetchTime = useRef<number>(0)
    const SUBSCRIPTION_FETCH_COOLDOWN = 5000 // 5 seconds between subscription status API calls

    const fetchUser = async () => {
        try {
            console.log("Fetching user data...");
            const { data } = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`, {
                withCredentials: true
            });
            console.log("User data fetched successfully:", JSON.stringify(data, null, 2));
            

            // If user exists, also fetch subscription status
            if (data) {
                // Set user data first to ensure all fields are available
                setUser(data);
                // Then fetch subscription status and credit status
                await refreshSubscriptionStatus(data);
                await refreshCreditStatus();
                // 🎯 ENHANCEMENT: Auto-register device token after successful authentication
                setTimeout(async () => {
                    console.log("🔔 Auto-registering device token after authentication...");
                    await initializePushNotifications();
                    await autoRegisterDeviceToken(data);
                }, 1000); // Delay to ensure UI is ready
            }
        } catch (error: any) {
            setUser(null);
        } finally {
            setLoading(false);
        }
    }

    const refreshUser = async () => {
        try {
            console.log("Refreshing user data...");
            const { data } = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`, {
                withCredentials: true
            });
            console.log("User data refreshed successfully:", JSON.stringify(data, null, 2));

            if (data) {
                // Set user data first to ensure all fields are updated
                setUser(data);
                // Then fetch subscription status and credit status
                await refreshSubscriptionStatus(data);
                await refreshCreditStatus();
                // 🎯 ENHANCEMENT: Also register device token during refresh if user is authenticated
                if (user && !user.id) { // Only if this is a new login session
                    setTimeout(async () => {
                        console.log("🔔 Auto-registering device token after user refresh...");
                        await autoRegisterDeviceToken();
                    }, 500);
                }
            }
        } catch (error: any) {
            console.error("Error refreshing user data:", error);
        }
    }

    const logout = async () => {
        try {
            // Call logout endpoint
            await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/logout`, {}, {
                withCredentials: true
            });
        } catch (error) {
            console.error("Error during logout:", error);
        } finally {
            // Clear user state regardless of API response
            setUser(null);
        }
    }

    const autoRegisterDeviceToken = async (userData?: User): Promise<boolean> => {
        try {
            // Use provided userData or current user state
            const currentUser = userData || user;

            // Only register if push notifications are supported and user is authenticated
            if (!pushNotificationSupported || !currentUser) {
                console.log("🔔 Skipping device token registration - not supported or not authenticated");
                return false;
            }

            // Initialize push service if not already done
            if (!pushService.current) {
                pushService.current = PushNotificationService.getInstance();
            }

            // Check current permission status
            const permissionStatus = pushService.current.getPermissionStatus();

            if (permissionStatus === 'granted') {
                // Permission already granted, register token
                console.log("🔔 Push permission granted, registering device token...");
                const success = await pushService.current.registerDeviceToken(currentUser.id.toString());
                if (success) {
                    console.log("✅ Device token registered successfully during login");
                    return true;
                } else {
                    console.warn("⚠️ Failed to register device token during login");
                }
            } else if (permissionStatus === 'default') {
                // Permission not requested yet - this will be handled by user interaction
                console.log("🔔 Push permission not yet requested - will be handled by user interaction");
            } else {
                // Permission denied
                console.log("🔔 Push permission denied - cannot register device token");
            }

            return false;
        } catch (error) {
            console.error('❌ Error during auto device token registration:', error);
            return false;
        }
    }

    const initializePushNotifications = async (): Promise<boolean> => {
        try {
            // Only run in browser environment
            if (typeof window === 'undefined') {
                return false;
            }

            // Initialize push service if not already done
            try {
                if (!pushService.current) {
                    pushService.current = PushNotificationService.getInstance();
                }
            } catch (error) {
                console.log('🔔 Push notification service initialization failed:', error);
                setPushNotificationSupported(false);
                return false;
            }

            // Check if push notifications are supported
            const supported = pushService.current?.isSupported() || false;
            setPushNotificationSupported(supported);

            if (!supported) {
                console.log('🔔 Push notifications not supported in this browser');
                return false;
            }

            // Check current permission status
            try {
                const permissionStatus = pushService.current.getPermissionStatus();
                console.log('Current notification permission:', permissionStatus);
                return permissionStatus === 'granted';
            } catch (error) {
                console.log('🔔 Unable to get notification permission status:', error);
                return false;
            }
        } catch (error) {
            console.error('Error initializing push notifications:', error);
            return false;
        }
    }

    const refreshSubscriptionStatus = async (userData?: User, force: boolean = false) => {
        try {
            const now = Date.now();
            if (!force && now - lastSubscriptionFetchTime.current < SUBSCRIPTION_FETCH_COOLDOWN) {
                console.log(`🔄 Subscription status fetch rate limited - Last fetch ${now - lastSubscriptionFetchTime.current}ms ago`);
                return;
            }
            
            lastSubscriptionFetchTime.current = now;
            
            const currentUser = userData || user;
            if (currentUser) {
                console.log('Fetching subscription status...');
                const subscriptionResponse = await axios.get(
                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/status`,
                    { withCredentials: true }
                );

                console.log('Subscription data received:', subscriptionResponse.data);
                
                const updatedUser: User = {
                    ...currentUser,
                    is_premium: subscriptionResponse.data.is_premium,
                    subscription_status: subscriptionResponse.data.subscription_status,
                    subscription_start_date: subscriptionResponse.data.subscription_start_date,
                    subscription_end_date: subscriptionResponse.data.subscription_end_date,
                    last_payment_date: subscriptionResponse.data.last_payment_date,
                    payment_failed: subscriptionResponse.data.payment_failed,
                    stripe_customer_id: subscriptionResponse.data.stripe_customer_id,
                    stripe_subscription_id: subscriptionResponse.data.stripe_subscription_id
                };

                console.log('Updated user subscription data:', {
                    status: updatedUser.subscription_status,
                    end_date: updatedUser.subscription_end_date
                });

                setUser(updatedUser);
                console.log('✅ Subscription status updated successfully');
            }
        } catch (error) {
            console.error('Error fetching subscription status:', error);
            // If subscription fetch fails, still set user data
            if (userData) {
                setUser(userData);
            }
        }
    }

    const triggerCreditRefresh = () => {
        const now = Date.now();

        if (now - lastTriggerTime.current < TRIGGER_COOLDOWN) {
            console.log(`🔄 Credit refresh rate limited - Last trigger ${now - lastTriggerTime.current}ms ago (min: ${TRIGGER_COOLDOWN}ms)`);
            return;
        }

        lastTriggerTime.current = now;
        const newTrigger = Date.now(); // Use timestamp instead of incrementing counter

        console.log(`🔄 Triggering credit refresh #${newTrigger}`);
        setCreditRefreshTrigger(newTrigger);
        
        // Immediately refresh credit status when triggered
        refreshCreditStatus();
    };

    const forceCreditRefresh = async () => {
        console.log('🔄 Force refreshing credit status (bypassing rate limit)');
        await refreshCreditStatus(true);
    };

    const refreshCreditStatus = async (force: boolean = false) => {
        try {
            const now = Date.now();
            if (!force && now - lastStatusFetchTime.current < STATUS_FETCH_COOLDOWN) {
                console.log(`🔄 Credit status fetch rate limited - Last fetch ${now - lastStatusFetchTime.current}ms ago`);
                return creditStatus;
            }
            
            lastStatusFetchTime.current = now;
            
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/status`, {
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    console.log('✅ Credit status refreshed from AuthContext');
                    setCreditStatus(result.data);
                    return result.data;
                }
            } else {
                console.error('❌ Failed to refresh credit status from AuthContext:', response.status);
            }
            return null;
        } catch (error) {
            console.error('❌ Error refreshing credit status from AuthContext:', error);
            return null;
        }
    };

    useEffect(() => {
        fetchUser()
    }, [])

    // Initialize push notification support check on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            try {
                const pushServiceInstance = PushNotificationService.getInstance();
                setPushNotificationSupported(pushServiceInstance.isSupported());
            } catch (error) {
                console.log('🔔 Push notification service not available:', error);
                setPushNotificationSupported(false);
            }
        }
    }, [])

    // Refresh credit status whenever creditRefreshTrigger changes
    useEffect(() => {
        if (user) {
            refreshCreditStatus();
        }
    }, [creditRefreshTrigger, user]);

    if (loading) {
        return null; // or a loading spinner
    }

    return (
        <AuthContext.Provider
            value={{
                user,
                setUser,
                loading,
                refreshSubscriptionStatus,
                refreshCreditStatus,
                refreshUser,
                creditRefreshTrigger,
                triggerCreditRefresh,
                forceCreditRefresh,
                pushNotificationSupported,
                initializePushNotifications,
                logout,
                creditStatus,
                token: null // Token would be stored in httpOnly cookie or handled separately
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}