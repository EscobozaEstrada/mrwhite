'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react'
import axios from 'axios'
import { User } from '@/types/user'
import { PushNotificationService } from '@/services/pushNotificationService'

interface AuthContextType {
    user: User | null;
    setUser: (user: User | null) => void;
    loading: boolean;
    refreshSubscriptionStatus: () => Promise<void>;
    refreshCreditStatus: () => Promise<void>;
    refreshUser: () => Promise<void>;
    creditRefreshTrigger: number;
    triggerCreditRefresh: () => void;
    pushNotificationSupported: boolean;
    initializePushNotifications: () => Promise<boolean>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [creditRefreshTrigger, setCreditRefreshTrigger] = useState(0)
    const [pushNotificationSupported, setPushNotificationSupported] = useState(false)
    const lastTriggerTime = useRef<number>(0)
    const pushService = useRef<PushNotificationService | null>(null)
    const TRIGGER_COOLDOWN = 2000 // Increased to 2 seconds minimum between triggers

    const fetchUser = async () => {
        try {
            console.log("Fetching user data...");
            const { data } = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`, {
                withCredentials: true
            });
            console.log("User data fetched successfully:", data);

            // If user exists, also fetch subscription status
            if (data) {
                await refreshSubscriptionStatus(data);
                // 🎯 ENHANCEMENT: Auto-register device token after successful authentication
                setTimeout(async () => {
                    console.log("🔔 Auto-registering device token after authentication...");
                    await initializePushNotifications();
                    await autoRegisterDeviceToken(data);
                }, 1000); // Delay to ensure UI is ready
            } else {
                setUser(data);
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
            console.log("User data refreshed successfully:", data);

            if (data) {
                await refreshSubscriptionStatus(data);
                // 🎯 ENHANCEMENT: Also register device token during refresh if user is authenticated
                if (user && !user.id) { // Only if this is a new login session
                    setTimeout(async () => {
                        console.log("🔔 Auto-registering device token after user refresh...");
                        await autoRegisterDeviceToken();
                    }, 500);
                }
            } else {
                setUser(data);
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
            if (!pushService.current) {
                pushService.current = PushNotificationService.getInstance();
            }

            // Check if push notifications are supported
            const supported = pushService.current.isSupported();
            setPushNotificationSupported(supported);

            if (!supported) {
                console.log('Push notifications not supported in this browser');
                return false;
            }

            // Check current permission status
            const permissionStatus = pushService.current.getPermissionStatus();
            console.log('Current notification permission:', permissionStatus);

            return permissionStatus === 'granted';
        } catch (error) {
            console.error('Error initializing push notifications:', error);
            return false;
        }
    }

    const refreshSubscriptionStatus = async (userData?: User) => {
        try {
            const currentUser = userData || user;
            if (currentUser) {
                const subscriptionResponse = await axios.get(
                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/subscription/status`,
                    { withCredentials: true }
                );

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

                setUser(updatedUser);
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
        const cooldownPeriod = 2000; // Increased to 2 seconds minimum between triggers

        if (now - lastTriggerTime.current < cooldownPeriod) {
            console.log(`🔄 Credit refresh rate limited - Last trigger ${now - lastTriggerTime.current}ms ago (min: ${cooldownPeriod}ms)`);
            return;
        }

        lastTriggerTime.current = now;
        const newTrigger = Date.now(); // Use timestamp instead of incrementing counter

        console.log(`🔄 Triggering credit refresh #${newTrigger}`);
        setCreditRefreshTrigger(newTrigger);
    };

    const refreshCreditStatus = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/status`, {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                console.log('✅ Credit status refreshed from AuthContext');
                // This is mainly for global state if needed
                // Individual components will handle their own refresh
            } else {
                console.error('❌ Failed to refresh credit status from AuthContext:', response.status);
            }
        } catch (error) {
            console.error('❌ Error refreshing credit status from AuthContext:', error);
        }
    };

    useEffect(() => {
        fetchUser()
    }, [])

    // Initialize push notification support check on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const pushServiceInstance = PushNotificationService.getInstance();
            setPushNotificationSupported(pushServiceInstance.isSupported());
        }
    }, [])

    if (loading) {
        return null; // or a loading spinner
    }

    return (
        <AuthContext.Provider value={{
            user,
            setUser,
            loading,
            refreshSubscriptionStatus,
            refreshCreditStatus,
            refreshUser,
            creditRefreshTrigger,
            triggerCreditRefresh,
            pushNotificationSupported,
            initializePushNotifications,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}