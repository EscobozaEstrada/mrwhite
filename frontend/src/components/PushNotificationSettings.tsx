'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { PushNotificationService } from '@/services/pushNotificationService';
import { Switch } from '@/components/ui/switch';
import { Bell, BellOff, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

// Define types for device tokens
interface DeviceToken {
    token: string;
    active: boolean;
    created_at?: string;
    updated_at?: string;
}

interface DeviceTokens {
    [platform: string]: DeviceToken;
}

// Extend User type to include device_tokens
interface ExtendedUser {
    id: string | number;
    device_tokens?: DeviceTokens;
    [key: string]: any;
}

export default function PushNotificationSettings() {
    const { user, refreshUser } = useAuth();
    const [isEnabled, setIsEnabled] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSupported, setIsSupported] = useState(false);
    const [permissionStatus, setPermissionStatus] = useState<NotificationPermission>('default');

    // Helper function to check if user has active device tokens
    const hasActiveDeviceTokens = (user: ExtendedUser | null): boolean => {
        if (!user?.device_tokens || typeof user.device_tokens !== 'object') {
            return false;
        }

        const tokens = user.device_tokens;
        // Check if any platform has an active token
        return Object.keys(tokens).some(platform => {
            const tokenData = tokens[platform];
            return tokenData &&
                typeof tokenData === 'object' &&
                tokenData.token &&
                tokenData.active !== false;
        });
    };

    useEffect(() => {
        const pushService = PushNotificationService.getInstance();

        // Check if push notifications are supported
        setIsSupported(pushService.isSupported());

        // Check current permission status
        const currentPermission = pushService.getPermissionStatus();
        setPermissionStatus(currentPermission);

        // Check if user has already enabled notifications
        const hasTokens = hasActiveDeviceTokens(user as ExtendedUser);
        setIsEnabled(hasTokens);

        console.log('🔔 Push notification state check:', {
            user_id: user?.id,
            device_tokens: (user as ExtendedUser)?.device_tokens,
            has_tokens: hasTokens,
            permission: currentPermission,
            is_enabled: hasTokens
        });
    }, [user]);

    const handleToggleNotifications = async () => {
        if (!user) return;

        setIsLoading(true);
        setError(null);

        try {
            const pushService = PushNotificationService.getInstance();

            if (!isEnabled) {
                // Enable notifications
                console.log('🔔 Attempting to enable push notifications...');
                const success = await pushService.registerDeviceToken(user.id.toString());

                if (success) {
                    console.log('✅ Device token registered successfully');
                    setIsEnabled(true);
                    setPermissionStatus('granted');

                    // Refresh user data multiple times to ensure backend has processed
                    console.log('🔄 Refreshing user data...');
                    await refreshUser();

                    // Multiple refresh attempts with delays
                    setTimeout(async () => {
                        console.log('🔄 Second refresh attempt...');
                        await refreshUser();
                    }, 1000);

                    setTimeout(async () => {
                        console.log('🔄 Third refresh attempt...');
                        await refreshUser();
                    }, 2000);
                } else {
                    setError('Failed to enable push notifications. Please try again.');
                }
            } else {
                // Disable notifications
                console.log('🔕 Attempting to disable push notifications...');
                const success = await pushService.unregisterDeviceToken();

                if (success) {
                    console.log('✅ Device token unregistered successfully');
                    setIsEnabled(false);

                    // Refresh user data multiple times to ensure backend has processed
                    console.log('🔄 Refreshing user data...');
                    await refreshUser();

                    // Multiple refresh attempts with delays
                    setTimeout(async () => {
                        console.log('🔄 Second refresh attempt...');
                        await refreshUser();
                    }, 1000);

                    setTimeout(async () => {
                        console.log('🔄 Third refresh attempt...');
                        await refreshUser();
                    }, 2000);
                } else {
                    setError('Failed to disable push notifications. Please try again.');
                }
            }
        } catch (err) {
            console.error('Error toggling notifications:', err);
            setError('An error occurred while updating notification settings.');
        } finally {
            setIsLoading(false);
        }
    };

    if (!isSupported) {
        return (
            <div className="bg-neutral-900 border border-neutral-800 rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4 text-white">Push Notifications</h2>
                <div className="p-4 bg-yellow-900/20 border border-yellow-800/30 rounded-lg">
                    <p className="text-yellow-500">
                        Push notifications are not supported in this browser.
                    </p>
                </div>
            </div>
        );
    }

    const getDeviceCount = () => {
        const deviceTokens = (user as ExtendedUser)?.device_tokens;
        if (!deviceTokens) return 0;

        // Count active device tokens
        return Object.keys(deviceTokens).filter(platform => {
            const tokenData = deviceTokens[platform];
            return tokenData &&
                typeof tokenData === 'object' &&
                tokenData.token &&
                tokenData.active !== false;
        }).length;
    };

    const getPermissionStatusText = () => {
        switch (permissionStatus) {
            case 'granted':
                return 'Granted';
            case 'denied':
                return 'Denied';
            default:
                return 'Not requested';
        }
    };

    const getPermissionStatusColor = () => {
        switch (permissionStatus) {
            case 'granted':
                return 'text-green-500';
            case 'denied':
                return 'text-red-500';
            default:
                return 'text-neutral-400';
        }
    };

    return (
        <div className="bg-neutral-900 border border-neutral-800 rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 text-white">Push Notifications</h2>

            <div className="space-y-4">
                {/* Current Status */}
                <div className="flex items-center justify-between p-4 bg-neutral-800/50 rounded-lg">
                    <div>
                        <h3 className="font-medium text-white">Notification Status</h3>
                        <p className="text-sm text-neutral-400">
                            {isEnabled ? 'Enabled' : 'Disabled'}
                        </p>
                    </div>
                    <div className="text-right">
                        <p className={`text-sm font-medium ${getPermissionStatusColor()}`}>
                            {getPermissionStatusText()}
                        </p>
                        <p className="text-xs text-neutral-400">
                            Registered Devices: {getDeviceCount()}
                        </p>
                    </div>
                </div>

                {/* Error Display */}
                {error && (
                    <div className="p-4 bg-red-900/20 border border-red-800/30 rounded-lg">
                        <p className="text-red-500 text-sm">{error}</p>
                    </div>
                )}

                {/* Permission Denied Warning */}
                {permissionStatus === 'denied' && (
                    <div className="p-4 bg-yellow-900/20 border border-yellow-800/30 rounded-lg">
                        <p className="text-yellow-500 text-sm">
                            You have denied notification permissions. Please enable them in your browser settings to receive push notifications.
                        </p>
                    </div>
                )}

                {/* Toggle Switch */}
                <div className="flex items-center justify-between p-4 bg-neutral-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                        {isEnabled ? (
                            <Bell className="h-5 w-5 text-[#D3B86A]" />
                        ) : (
                            <BellOff className="h-5 w-5 text-neutral-400" />
                        )}
                        <div>
                            <h3 className="font-medium text-white">Push Notifications</h3>
                            <p className="text-sm text-neutral-400">
                                {isEnabled ? 'Notifications are enabled' : 'Notifications are disabled'}
                            </p>
                        </div>
                    </div>
                    <div className="relative">
                        {isLoading && (
                            <div className="absolute inset-0 flex items-center justify-center z-10">
                                <div className="absolute inset-0 bg-neutral-900 rounded-full opacity-60"></div>
                                <svg className="animate-spin h-3 w-3 text-white z-20" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            </div>
                        )}
                        <Switch 
                            checked={isEnabled}
                            onCheckedChange={handleToggleNotifications}
                            disabled={isLoading || permissionStatus === 'denied'}
                            className={cn(
                                (permissionStatus === 'denied') && "opacity-50 cursor-not-allowed",
                                isLoading && "pointer-events-none"
                            )}
                        />
                    </div>
                </div>

                {/* Information */}
                <div className="p-4 bg-neutral-800/50 border border-neutral-700 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                        <Info className="h-4 w-4 text-[#D3B86A]" />
                        <h4 className="font-medium text-[#D3B86A]">About Push Notifications</h4>
                    </div>
                    <ul className="text-sm text-neutral-300 space-y-1">
                        <li>• Receive reminders even when the app is closed</li>
                        <li>• Get notified about important health events</li>
                        <li>• Works across all your devices where you're logged in</li>
                        <li>• You can enable/disable anytime from this page</li>
                    </ul>
                </div>
            </div>
        </div>
    );
} 