// This is a minimal service worker for Firebase Cloud Messaging
// It will be replaced with a proper implementation when Firebase is configured

// Firebase configuration (updated with actual values)
const firebaseConfig = {
    apiKey: "AIzaSyA2tLRqRfGC9lgFVZqn4MngLXuGpmWvWp4",
    authDomain: "mr-white-notifications.firebaseapp.com",
    projectId: "mr-white-notifications",
    storageBucket: "mr-white-notifications.firebasestorage.app",
    messagingSenderId: "345023183337",
    appId: "1:345023183337:web:dcdddabcf1dccd8079b378"
};

// Initialize Firebase in service worker
try {
    firebase.initializeApp(firebaseConfig);
    console.log('✅ Firebase initialized in service worker');
} catch (error) {
    console.error('❌ Failed to initialize Firebase in service worker:', error);
}

self.addEventListener('push', (event) => {
  console.log('Push notification received', event);
  
  // Default notification data
  const defaultData = {
    title: 'New Notification',
    body: 'You have a new notification',
    icon: '/logo.png',
    click_action: '/'
  };

  try {
    // Try to extract notification data from the push event
    const data = event.data?.json() || defaultData;
    
    const title = data.notification?.title || data.title || defaultData.title;
    const options = {
      body: data.notification?.body || data.body || defaultData.body,
      icon: data.notification?.icon || data.icon || defaultData.icon,
      badge: '/logo.png',
      tag: 'push-notification',
      data: {
        url: data.notification?.click_action || data.click_action || defaultData.click_action
      }
    };

    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (error) {
    console.error('Error showing notification:', error);
    
    // Fallback to default notification
    event.waitUntil(
      self.registration.showNotification(defaultData.title, {
        body: defaultData.body,
        icon: defaultData.icon,
        badge: '/logo.png',
        tag: 'push-notification-fallback',
        data: { url: defaultData.click_action }
      })
    );
  }
});

self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked', event);
  event.notification.close();

  const url = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // If a window client is already open, focus it
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      
      // Otherwise open a new window
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
}); 