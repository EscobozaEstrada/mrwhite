'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { User, Bell, Shield, CreditCard, Settings, Trash2, AlertTriangle, Image as ImageIcon, Upload, X, Volume2, VolumeX } from 'lucide-react';
import PushNotificationSettings from '@/components/PushNotificationSettings';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import toast from '@/components/ui/sound-toast';
import axios from 'axios';
import Image from 'next/image';
import { FaPlus } from 'react-icons/fa';
import { CiCirclePlus } from "react-icons/ci";
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { getSoundPreferences, saveSoundPreferences, playNotificationSound } from '@/utils/soundUtils';
import { FaTrashCan } from 'react-icons/fa6';

const AccountSettingsPage = () => {
	const { user, setUser, logout, creditStatus, refreshUser } = useAuth();
	const router = useRouter();
	const [loading, setLoading] = useState(true);
	const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
	const [deleteConfirmation, setDeleteConfirmation] = useState('');
	const [isDeleting, setIsDeleting] = useState(false);
	const [uploading, setUploading] = useState(false);
	const [removing, setRemoving] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const deleteDialogRef = useRef<HTMLDivElement>(null);
	const [soundPreferences, setSoundPreferences] = useState({
		enabled: true,
		volume: 0.5,
	});

	useEffect(() => {
		if (!user) {
			router.push('/login');
		} else {
			setLoading(false);
		}
	}, [user, router]);

	// Close delete confirmation when clicking outside
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (deleteDialogRef.current && !deleteDialogRef.current.contains(event.target as Node)) {
				setShowDeleteConfirm(false);
			}
		}

		document.addEventListener("mousedown", handleClickOutside);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, []);

	// Load sound preferences
	useEffect(() => {
		if (typeof window !== 'undefined') {
			const prefs = getSoundPreferences();
			setSoundPreferences(prefs);
		}
	}, []);

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

	// Handle dog image upload
	const handleDogImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		if (!e.target.files || e.target.files.length === 0) return;

		const file = e.target.files[0];

		// Validate file type
		if (!file.type.startsWith('image/')) {
			toast.error('Please select an image file');
			return;
		}

		// Validate file size (max 5MB)
		if (file.size > 5 * 1024 * 1024) {
			toast.error('Image size should be less than 5MB');
			return;
		}

		try {
			setUploading(true);

			const formData = new FormData();
			formData.append('image', file);

			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/upload-dog-image`,
				formData,
				{
					headers: {
						'Content-Type': 'multipart/form-data',
					},
					withCredentials: true,
				}
			);

			if (response.data.success) {
				// After successful upload, refresh user data to get updated dog_image
				await refreshUser();
				toast.success('Dog image uploaded successfully');
			} else {
				toast.error(response.data.message || 'Failed to upload image');
			}
		} catch (error) {
			console.error('Error uploading dog image:', error);
			toast.error('Failed to upload image. Please try again.');
		} finally {
			setUploading(false);
		}
	};

	// Remove dog image
	const handleRemoveDogImage = async () => {
		try {
			setShowDeleteConfirm(false);
			setRemoving(true);

			const response = await axios.delete(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/remove-dog-image`,
				{
					withCredentials: true,
				}
			);

			if (response.data.success) {
				// After successful deletion, refresh user data
				await refreshUser();
				toast.success('Dog image removed successfully');
				
				// Reset the file input value to allow re-uploading the same file
				if (fileInputRef.current) {
					fileInputRef.current.value = '';
				}
			} else {
				toast.error(response.data.message || 'Failed to remove image');
			}
		} catch (error) {
			console.error('Error removing dog image:', error);
			toast.error('Failed to remove image. Please try again.');
		} finally {
			setRemoving(false);
		}
	};

	// Handle sound preference changes
	const handleSoundToggle = (enabled: boolean) => {
		const updatedPrefs = { ...soundPreferences, enabled };
		setSoundPreferences(updatedPrefs);
		saveSoundPreferences(updatedPrefs);
		
		// Play test sound when enabling
		if (enabled) {
			playNotificationSound('success');
		}
	};

	const handleVolumeChange = (value: number[]) => {
		const volume = value[0] / 100;
		const updatedPrefs = { ...soundPreferences, volume };
		setSoundPreferences(updatedPrefs);
		saveSoundPreferences(updatedPrefs);
		
		// Play test sound when changing volume
		playNotificationSound('success');
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
			{/* Hidden file input for dog image upload */}
			<input
				type="file"
				ref={fileInputRef}
				className="hidden"
				accept="image/*"
				onChange={handleDogImageUpload}
			/>

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
								{/* Dog Profile Image Section */}
								<div className="flex flex-col items-start mb-6 p-4 rounded-md">
									<h3 className="text-lg font-medium mb-3">Dog Profile Image</h3>

									<div className="relative mb-4">
										{user?.dog_image ? (
											<div className="relative w-32 h-32">
												<div className="w-full h-full rounded-full overflow-hidden border-4 border-[var(--mrwhite-primary-color)]">
													<Image
														src={user.dog_image}
														alt="Dog Profile"
														fill
														className="object-cover rounded-full"
													/>
												</div>
												<div
													className="absolute"
													style={{
														top: '-8px',
														right: '-8px',
														// zIndex: 999
													}}
												>
													<button
														onClick={() => setShowDeleteConfirm(true)}
														disabled={removing}
														className="bg-red-500 hover:bg-red-600 rounded-full p-1.5 text-white transition-colors shadow-md"
														title="Remove image"
													>
														<X size={18} />
													</button>
												</div>

												{/* Small confirmation popover */}
												{showDeleteConfirm && (
													<div
														ref={deleteDialogRef}
														className="absolute top-0 left-full w-45 bg-neutral-800 border border-neutral-700 rounded-md p-2 shadow-lg z-10 flex flex-col gap-2 items-center"
													>
														<p className="text-sm text-gray-300 mb-2">
															Remove this dog image?
														</p>
														<div className="flex justify-end gap-2">
															<button
																onClick={() => setShowDeleteConfirm(false)}
																className="text-sm bg-black hover:bg-neutral-700 px-2 py-1 rounded"
															>
																Cancel
															</button>
															<button
																onClick={handleRemoveDogImage}
																disabled={removing}
																className="text-sm bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-white"
															>
																{removing ? 'Removing...' : 'Remove'}
															</button>
														</div>
													</div>
												)}
											</div>
										) : (
											<div className="w-32 h-32 rounded-full bg-neutral-800 flex items-center justify-center border-4 border-neutral-700">
												<ImageIcon className="w-12 h-12 text-neutral-500" />
											</div>
										)}
									</div>

									<Button
										onClick={() => fileInputRef.current?.click()}
										disabled={uploading}
										className="flex items-center gap-2"
									>
										{uploading ? (
											<>
												<div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
												Uploading...
											</>
										) : (
											<>
												<Upload className="w-4 h-4" />
												{user?.dog_image ? 'Change Dog Image' : 'Upload Dog Image'}
											</>
										)}
									</Button>
									<p className="text-xs text-muted-foreground mt-2">
										Upload a photo of your dog to personalize your profile.
									</p>
								</div>

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
										<div className="mt-1 p-2 bg-muted rounded-md flex justify-between items-center">
											{creditStatus?.available_credits || 0} credits
											<CiCirclePlus 
												className="w-8 h-8 text-[var(--mrwhite-primary-color)] hover:fill-amber-400 cursor-pointer" 
												onClick={() => router.push('/account/credits')} 
												title="Buy more credits"
											/>
										</div>
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
							<CardContent className="space-y-6">
								{/* Sound Settings */}
								<div className="space-y-4">
									<h3 className="text-lg font-medium">Notification Sounds</h3>
									
									{/* Main Sound Toggle */}
									<div className="flex items-center justify-between">
										<div className="space-y-0.5">
											<Label className="text-base">
												{soundPreferences.enabled ? (
													<Volume2 className="h-4 w-4 inline mr-2" />
												) : (
													<VolumeX className="h-4 w-4 inline mr-2" />
												)}
												Toast Notification Sounds
											</Label>
											<p className="text-sm text-muted-foreground">
												Play sounds for success and error notifications
											</p>
										</div>
										<Switch
											checked={soundPreferences.enabled}
											onCheckedChange={handleSoundToggle}
										/>
									</div>
									
									{/* Volume Slider */}
									{soundPreferences.enabled && (
										<div className="space-y-2">
											<Label className="text-sm">Volume</Label>
											<div className="pt-2">
												<Slider
													defaultValue={[soundPreferences.volume * 100]}
													max={100}
													step={5}
													onValueChange={handleVolumeChange}
												/>
											</div>
										</div>
									)}
								</div>

								<div className="text-sm text-muted-foreground mt-4">
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
									<button
										className="flex items-center gap-2 cursor-pointer bg-red-500 hover:bg-red-600 p-2 rounded-md text-white"
										onClick={() => setIsDeleteDialogOpen(true)}
									>
										<Trash2 className="w-4 h-4" />
										Delete My Account
									</button>
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
								className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
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
							// variant="destructive"
							onClick={handleDeleteAccount}
							disabled={isDeleting}
							className={`flex items-center gap-2 ${deleteConfirmation === 'DELETE' ? 'bg-red-500 text-white hover:bg-red-600' : 'bg-red-400 hover:bg-red-500'}`}
						>
							{isDeleting ? (
								<>
									<div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
									Deleting...
								</>
							) : (
								<>
									<FaTrashCan className="w-4 h-4" />
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