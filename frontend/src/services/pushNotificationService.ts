/**
 * Push Notification Service
 * Handles device token registration and push notification setup
 */

import { getMessaging, getToken, onMessage } from 'firebase/messaging';
import { initializeApp } from 'firebase/app';

// Firebase configuration from environment variables
const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID
};

console.log('firebaseConfig =============>', firebaseConfig);

// Validate configuration
if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
    console.error('Firebase configuration is missing. Please check your environment variables.');
}

// Initialize Firebase - with error handling
let app: any = null;
let firebaseInitialized = false;

try {
    // Only initialize if we have valid config and browser support
    if (firebaseConfig.apiKey && firebaseConfig.projectId && typeof window !== 'undefined') {
        app = initializeApp(firebaseConfig);
        firebaseInitialized = true;
        console.log('✅ Firebase app initialized successfully');
    } else {
        console.warn('⚠️ Firebase not initialized - missing config or not in browser environment');
    }
} catch (error) {
    console.error('❌ Firebase initialization failed:', error);
    firebaseInitialized = false;
}

export class PushNotificationService {
    private static instance: PushNotificationService;
    private messaging: any = null;
    private currentToken: string | null = null; // Store current token
    private isRegistering: boolean = false; // Prevent multiple registration attempts
    private registrationRetries: number = 0;
    private maxRetries: number = 3;

    private constructor() {
        // Only initialize messaging if Firebase is available and browser supports it
        if (firebaseInitialized && app && this.isSupported()) {
            try {
                this.messaging = getMessaging(app);
                this.initializeMessaging();
                console.log('✅ Firebase Messaging initialized successfully');
            } catch (error) {
                console.error('❌ Firebase Messaging initialization failed:', error);
                this.messaging = null;
            }
        } else {
            console.warn('⚠️ Firebase Messaging not initialized - app not available or unsupported browser');
            this.messaging = null;
        }
    }

    static getInstance(): PushNotificationService {
        if (!PushNotificationService.instance) {
            PushNotificationService.instance = new PushNotificationService();
        }
        return PushNotificationService.instance;
    }

    private async initializeMessaging() {
        try {
            // Check if messaging is available
            if (!this.messaging) {
                console.warn('⚠️ Firebase Messaging not available, skipping initialization');
                return;
            }

            // Register service worker
            if ('serviceWorker' in navigator) {
                const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
                console.log('🔧 Service Worker registered:', registration);
            }

            // Handle foreground messages
            onMessage(this.messaging, (payload) => {
                console.log('📩 Message received while app is in foreground:', payload);

                // Show notification even when app is in foreground
                if (payload.notification) {
                    this.showNotification(payload.notification);
                }
            });

        } catch (error) {
            console.error('❌ Error initializing messaging:', error);
        }
    }

    private showNotification(notification: any) {
        // Create a notification when the app is in foreground
        if (Notification.permission === 'granted') {
            const options = {
                body: notification.body || '',
                icon: notification.icon || '/logo.png',
                badge: '/logo.png',
                tag: 'fcm-foreground-notification',
                requireInteraction: true
                // Actions are only supported for ServiceWorkerRegistration.showNotification()
                // Removed actions to fix runtime error
            };

            const notif = new Notification(notification.title || 'New Message', options);

            notif.onclick = () => {
                window.focus();
                notif.close();
                // Navigate to reminders page if it's a reminder notification
                if (notification.click_action) {
                    window.location.href = notification.click_action;
                }
            };

            // Auto-close after 10 seconds
            setTimeout(() => {
                notif.close();
            }, 10000);
        }
    }

    async requestPermission(): Promise<boolean> {
        try {
            if (!this.isSupported()) {
                console.warn('⚠️ Push notifications not supported in this browser');
                return false;
            }

            const permission = await Notification.requestPermission();
            console.log(`🔔 Permission request result: ${permission}`);
            return permission === 'granted';
        } catch (error) {
            console.error('❌ Error requesting notification permission:', error);
            return false;
        }
    }

    async getDeviceToken(): Promise<string | null> {
        try {
            // Check if messaging is available
            if (!this.messaging) {
                console.warn('⚠️ Firebase Messaging not available, cannot get device token');
                return null;
            }

            // Return cached token if available
            if (this.currentToken) {
                console.log('🔄 Using cached FCM token');
                return this.currentToken;
            }

            // Request permission first
            const hasPermission = await this.requestPermission();
            if (!hasPermission) {
                throw new Error('Notification permission not granted');
            }

            // Get FCM token
            const token = await getToken(this.messaging);
            console.log('🎫 New FCM token obtained:', token ? token.substring(0, 20) + '...' : 'null');

            // Store current token
            this.currentToken = token;

            return token;
        } catch (error) {
            console.error('❌ Error getting device token:', error);
            return null;
        }
    }

    async registerDeviceToken(userId: string): Promise<boolean> {
        try {
            // Prevent multiple registration attempts
            if (this.isRegistering) {
                console.log('🔄 Device token registration already in progress...');
                return false;
            }

            this.isRegistering = true;
            console.log(`🔔 Starting device token registration for user ${userId}...`);

            const token = await this.getDeviceToken();
            if (!token) {
                throw new Error('Failed to get device token');
            }

            // Get API base URL from environment
            const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

            // Prepare device info
            const deviceInfo = {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                screenResolution: `${screen.width}x${screen.height}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                registeredAt: new Date().toISOString()
            };

            // Send token to backend
            const response = await fetch(`${apiBaseUrl}/api/auth/device-token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include', // Include cookies
                body: JSON.stringify({
                    token: token,
                    platform: 'web',
                    device_info: deviceInfo
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.message || 'Unknown error'}`);
            }

            const data = await response.json();
            console.log('✅ Device token registered successfully:', data);

            this.registrationRetries = 0; // Reset retry counter on success
            return true;
        } catch (error) {
            console.error('❌ Error registering device token:', error);

            // Retry logic
            if (this.registrationRetries < this.maxRetries) {
                this.registrationRetries++;
                console.log(`🔄 Retrying device token registration (attempt ${this.registrationRetries}/${this.maxRetries})...`);

                // Wait before retry (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, this.registrationRetries) * 1000));

                return this.registerDeviceToken(userId);
            }

            return false;
        } finally {
            this.isRegistering = false;
        }
    }

    async unregisterDeviceToken(): Promise<boolean> {
        try {
            console.log('🗑️ Starting device token unregistration...');

            // Use stored token or try to get current token
            let token = this.currentToken;

            if (!token) {
                // Try to get current token (but don't request permission)
                if (Notification.permission === 'granted' && this.messaging) {
                    try {
                        token = await getToken(this.messaging);
                    } catch (error) {
                        console.warn('⚠️ Could not get token for unregistration:', error);
                    }
                }
            }

            if (!token) {
                console.log('ℹ️ No token available to unregister');
                return true; // Already unregistered
            }

            // Get API base URL from environment
            const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

            const response = await fetch(`${apiBaseUrl}/api/auth/device-token`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include', // Include cookies
                body: JSON.stringify({
                    token: token,
                    platform: 'web'
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.warn(`⚠️ Unregistration failed with status ${response.status}:`, errorData.message);

                // Don't throw error for 404 - token might already be removed
                if (response.status !== 404) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }

            console.log('✅ Device token unregistered successfully');

            // Clear stored token and reset retry counter
            this.currentToken = null;
            this.registrationRetries = 0;

            return true;
        } catch (error) {
            console.error('❌ Error unregistering device token:', error);

            // Clear stored token anyway to prevent stale state
            this.currentToken = null;

            return false;
        }
    }

    isSupported(): boolean {
        try {
            return typeof window !== 'undefined' && 
                   'serviceWorker' in navigator && 
                   'PushManager' in window && 
                   'Notification' in window &&
                   !!this.messaging;
        } catch (error) {
            console.error('❌ Error checking push notification support:', error);
            return false;
        }
    }

    getPermissionStatus(): NotificationPermission {
        return Notification.permission;
    }

    // 🎯 NEW: Method to check if device is registered
    async isDeviceRegistered(): Promise<boolean> {
        try {
            if (!this.currentToken) {
                return false;
            }

            // Could add an API call to verify token is still valid on server
            return Notification.permission === 'granted';
        } catch (error) {
            console.error('❌ Error checking device registration status:', error);
            return false;
        }
    }

    // 🎯 NEW: Method to get device info summary
    getDeviceInfo(): any {
        return {
            platform: navigator.platform,
            userAgent: navigator.userAgent,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            screenResolution: `${screen.width}x${screen.height}`,
            pushSupported: this.isSupported(),
            permission: this.getPermissionStatus(),
            hasToken: !!this.currentToken
        };
    }
}

export default PushNotificationService; 