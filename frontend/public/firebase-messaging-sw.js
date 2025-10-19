// Import Firebase scripts for service worker
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Firebase configuration (same as frontend)
const firebaseConfig = {
    apiKey: "AIzaSyBxJq3q3q3q3q3q3q3q3q3q3q3q3q3q3q", // This will be replaced by actual config
    authDomain: "mr-white-notifications.firebaseapp.com",
    projectId: "mr-white-notifications",
    storageBucket: "mr-white-notifications.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123456789:web:abcdefghijklmnop"
};

// Initialize Firebase in service worker
firebase.initializeApp(firebaseConfig);

// Get messaging instance
const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
    console.log('📩 Background message received:', payload);

    const notificationTitle = payload.notification?.title || 'New Message';
    const notificationOptions = {
        body: payload.notification?.body || '',
        icon: payload.notification?.icon || '/logo.png',
        badge: '/logo.png',
        tag: 'mr-white-notification',
        requireInteraction: true,
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/logo.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/logo.png'
            }
        ],
        data: {
            ...payload.data,
            click_action: payload.notification?.click_action || '/reminders'
        }
    };

    // Show notification
    return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    console.log('🖱️ Notification clicked:', event);

    event.notification.close();

    const action = event.action;
    const clickAction = event.notification.data?.click_action || '/reminders';

    if (action === 'dismiss') {
        // Just close the notification
        return;
    }

    // Default action (view) or click on notification body
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // Check if app is already open
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    // Focus existing window and navigate
                    client.focus();
                    client.postMessage({
                        type: 'NOTIFICATION_CLICK',
                        action: action,
                        url: clickAction,
                        data: event.notification.data
                    });
                    return;
                }
            }

            // Open new window if app is not open
            if (clients.openWindow) {
                const fullUrl = `${self.location.origin}${clickAction}`;
                return clients.openWindow(fullUrl);
            }
        })
    );
});

// Handle push event
self.addEventListener('push', (event) => {
    console.log('📨 Push event received:', event);

    if (!event.data) {
        console.warn('⚠️ Push event has no data');
        return;
    }

    try {
        const data = event.data.json();
        console.log('📊 Push data:', data);

        const options = {
            body: data.notification?.body || data.body || '',
            icon: data.notification?.icon || '/logo.png',
            badge: '/logo.png',
            tag: 'mr-white-push',
            requireInteraction: true,
            data: data.data || {}
        };

        event.waitUntil(
            self.registration.showNotification(
                data.notification?.title || data.title || 'New Message',
                options
            )
        );
    } catch (error) {
        console.error('❌ Error handling push event:', error);
    }
});

// Service worker installation
self.addEventListener('install', (event) => {
    console.log('🔧 Firebase messaging service worker installed');
    self.skipWaiting(); // Activate immediately
});

// Service worker activation
self.addEventListener('activate', (event) => {
    console.log('✅ Firebase messaging service worker activated');
    event.waitUntil(clients.claim()); // Take control of all clients
});

// Handle messages from main thread
self.addEventListener('message', (event) => {
    console.log('📬 Service worker received message:', event.data);

    if (event.data && event.data.type === 'CHECK_SW_STATUS') {
        // Respond with service worker status
        event.ports[0].postMessage({
            type: 'SW_STATUS',
            status: 'active',
            timestamp: new Date().toISOString()
        });
    }
}); 