'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { User, Bell, Shield, CreditCard, Settings, Trash2, AlertTriangle } from 'lucide-react';
import PushNotificationSettings from '@/components/PushNotificationSettings';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'react-toastify';
import axios from 'axios';

const AccountSettingsPage = () => {
    const { user, setUser, logout } = useAuth();
    const router = useRouter();
    const [loading, setLoading] = useState(true);
    const [creditStatus, setCreditStatus] = useState<any>(null);
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        if (!user) {
            router.push('/login');
        } else {
            setLoading(false);
            fetchCreditStatus();
        }
    }, [user, router]);

    const fetchCreditStatus = async () => {
        if (!user) return;
        
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/credit-system/status`, {
                credentials: 'include'
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    setCreditStatus(result.data);
                }
            }
        } catch (error) {
            console.error('Error fetching credit status:', error);
        }
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirmation !== 'DELETE') {
            toast.error('Please type DELETE to confirm account deletion');
            return;
        }

        setIsDeleting(true);
        try {
            // Use fetch instead of axios for consistency with other API calls
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/account`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            const data = await response.json();

            if (data.success) {
                toast.success('Your account has been deleted successfully');
                await logout();
                router.push('/');
            } else {
                toast.error(data.message || 'Failed to delete account');
            }
        } catch (error: any) {
            console.error('Error deleting account:', error);
            toast.error('Failed to delete account');
        } finally {
            setIsDeleting(false);
            setIsDeleteDialogOpen(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background p-6">
                <div className="max-w-4xl mx-auto">
                    <div className="animate-pulse space-y-6">
                        <div className="h-8 bg-gray-700 rounded w-1/3"></div>
                        <div className="grid gap-6">
                            <div className="h-64 bg-gray-700 rounded"></div>
                            <div className="h-64 bg-gray-700 rounded"></div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-6">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h1 className="text-4xl font-bold text-foreground mb-2 flex items-center gap-3">
                        <Settings className="w-8 h-8 text-[var(--mrwhite-primary-color)]" />
                        Account Settings
                    </h1>
                    <p className="text-muted-foreground">
                        Manage your account preferences and notification settings
                    </p>
                </motion.div>

                <div className="grid gap-6">
                    {/* Profile Information */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <User className="w-5 h-5" />
                                    Profile Information
                                </CardTitle>
                                <CardDescription>
                                    Your account details and subscription status
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-sm font-medium text-muted-foreground">Username</label>
                                        <div className="mt-1 p-3 bg-muted rounded-md">{user?.name}</div>
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-muted-foreground">Email</label>
                                        <div className="mt-1 p-3 bg-muted rounded-md">{user?.email}</div>
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-muted-foreground">Plan</label>
                                        <div className="mt-1 p-3 bg-muted rounded-md flex items-center gap-2">
                                            {user?.is_premium ? (
                                                <>
                                                    <CreditCard className="w-4 h-4 text-[var(--mrwhite-primary-color)]" />
                                                    Elite Pack
                                                </>
                                            ) : (
                                                <>
                                                    <Shield className="w-4 h-4 text-gray-400" />
                                                    Free Plan
                                                </>
                                            )}
                                        </div>
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium text-muted-foreground">Credits Balance</label>
                                        <div className="mt-1 p-3 bg-muted rounded-md">{creditStatus?.available_credits || 0} credits</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Push Notification Settings */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                    >
                        <PushNotificationSettings />
                    </motion.div>

                    {/* Additional Settings */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Settings className="w-5 h-5" />
                                    Preferences
                                </CardTitle>
                                <CardDescription>
                                    Customize your experience with Mr. White
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="text-sm text-muted-foreground">
                                    Additional preference settings will be available here in future updates.
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>

                    {/* Delete Account Section */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                    >
                        <Card className="border-red-800/20 bg-red-900/5">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-red-500">
                                    <Trash2 className="w-5 h-5" />
                                    Delete Account
                                </CardTitle>
                                <CardDescription>
                                    Permanently delete your account and all associated data
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="text-sm text-muted-foreground">
                                    <p className="mb-4">
                                        Warning: This action cannot be undone. All your data, including conversations, reminders, and settings will be permanently deleted.
                                    </p>
                                    <Button 
                                        variant="destructive" 
                                        className="flex items-center gap-2"
                                        onClick={() => setIsDeleteDialogOpen(true)}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Delete My Account
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                </div>
            </div>

            {/* Delete Account Confirmation Dialog */}
            <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2 text-red-500">
                            <AlertTriangle className="w-5 h-5" />
                            Delete Account Confirmation
                        </DialogTitle>
                        <DialogDescription>
                            This action cannot be undone. Please type DELETE to confirm.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="bg-yellow-900/20 border border-yellow-800/30 p-4 rounded-md text-sm">
                            <p className="flex items-start gap-2">
                                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                                <span>
                                    All your data will be permanently deleted, including your profile, conversations, reminders, and settings. 
                                    Any active subscriptions will need to be canceled separately.
                                </span>
                            </p>
                        </div>
                        <div className="grid gap-2">
                            <label htmlFor="confirmation" className="text-sm font-medium">
                                Type DELETE to confirm:
                            </label>
                            <input
                                id="confirmation"
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                value={deleteConfirmation}
                                onChange={(e) => setDeleteConfirmation(e.target.value)}
                                placeholder="Type DELETE here"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button 
                            variant="destructive" 
                            onClick={handleDeleteAccount}
                            disabled={isDeleting}
                            className="flex items-center gap-2"
                        >
                            {isDeleting ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    Deleting...
                                </>
                            ) : (
                                <>
                                    <Trash2 className="w-4 h-4" />
                                    Delete Account
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default AccountSettingsPage; 