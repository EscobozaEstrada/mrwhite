"use client"

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
	Bell,
	Calendar,
	Clock,
	Plus,
	Search,
	Filter,
	CheckCircle,
	AlertTriangle,
	XCircle,
	Edit,
	Trash2,
	AlertCircle,
	Activity,
	BarChart3,
	TrendingUp,
	CalendarDays,
	Brain,
	Zap,
	Globe,
	Timer,
	MapPin
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';
import { toast } from 'react-toastify';
import FrontendCountdown from '@/components/FrontendCountdown';
import TimezoneSelector from '@/components/TimezoneSelector';
import TimezoneDisplay from '@/components/TimezoneDisplay';
import RealTimeCountdown from '@/components/RealTimeCountdown';
import Image from 'next/image';

interface CountdownInfo {
	total_seconds: number;
	days: number;
	hours: number;
	minutes: number;
	formatted: string;
	urgency: 'low' | 'medium' | 'high' | 'critical' | 'unknown';
	color: string;
	is_overdue: boolean;
	due_local_time: string;
	due_local_date: string;
	due_local_time_only: string;
}

interface Reminder {
	id: number;
	title: string;
	description?: string;
	reminder_type: string;
	due_date?: string;
	due_time?: string;
	status: string;
	recurrence_type?: string;
	recurrence_interval?: number;
	created_at?: string;
	updated_at?: string;
	priority: string;
	advance_notice_days: number;
	send_push: boolean;
	is_active: boolean;
	countdown?: CountdownInfo;
	due_datetime: string;
	pet_name?: string;
	frequency?: string;
}

interface AITimeSuggestion {
	hour: number;
	minute: number;
	formatted_12h: string;
	formatted_24h: string;
	confidence: number;
	reason: string;
	user_pattern: Record<string, any>;
}

interface TimezoneSettings {
	timezone: string;
	location_city?: string;
	location_country?: string;
	time_format_24h: boolean;
	timezone_abbreviation: string;
	current_local_time: string;
}

const RemindersDashboard = () => {
	const { user } = useAuth();
	const [reminders, setReminders] = useState<Reminder[]>([]);
	const [loading, setLoading] = useState(true);
	const [activeTab, setActiveTab] = useState('all');
	const [searchQuery, setSearchQuery] = useState('');
	const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
	const [isTimezoneDialogOpen, setIsTimezoneDialogOpen] = useState(false);
	const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
	const [timezoneSettings, setTimezoneSettings] = useState<TimezoneSettings | null>(null);
	const [aiSuggestion, setAiSuggestion] = useState<AITimeSuggestion | null>(null);

	// Create reminder form state
	const [createForm, setCreateForm] = useState({
		title: '',
		description: '',
		reminder_type: 'vaccination',
		due_date: '',
		priority: 'medium',
		advance_notice_days: 3,
		send_push: true,
		is_active: true
	});

	// Edit reminder form state
	const [editForm, setEditForm] = useState({
		title: '',
		description: '',
		reminder_type: 'vaccination',
		due_date: '',
		priority: 'medium',
		advance_notice_days: 3,
		send_push: true,
		is_active: true
	});

	const reminderTypes = [
		{ value: 'vaccination', label: 'Vaccination', icon: '💉', color: 'bg-green-100 text-green-800' },
		{ value: 'vet_appointment', label: 'Vet Visit', icon: '🏥', color: 'bg-blue-100 text-blue-800' },
		{ value: 'medication', label: 'Medication', icon: '💊', color: 'bg-purple-100 text-purple-800' },
		{ value: 'grooming', label: 'Grooming', icon: '✂️', color: 'bg-pink-100 text-pink-800' },
		{ value: 'checkup', label: 'Checkup', icon: '🔍', color: 'bg-orange-100 text-orange-800' },
		{ value: 'custom', label: 'Custom', icon: '📝', color: 'bg-gray-100 text-gray-800' }
	];

	useEffect(() => {
		if (user) {
			fetchReminders();
			fetchTimezoneSettings();
		}
	}, [user]);

	const fetchReminders = async () => {
		try {
			setLoading(true);
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders`, {
				withCredentials: true,
				params: {
					limit: 100,
					offset: 0
				}
			});

			if (response.data.success && response.data.reminders) {
				// Transform the data to match the expected format
				const transformedReminders = response.data.reminders.map((reminder: any) => ({
					id: reminder.id,
					title: reminder.title,
					description: reminder.description,
					reminder_type: reminder.reminder_type,
					due_date: reminder.due_date,
					due_time: reminder.due_date ? new Date(reminder.due_date).toTimeString().slice(0, 5) : null,
					status: reminder.status,
					recurrence_type: reminder.recurrence_type || 'none',
					recurrence_interval: reminder.recurrence_interval || 1,
					created_at: reminder.created_at,
					updated_at: reminder.updated_at,
					priority: 'medium', // Default for health reminders
					advance_notice_days: reminder.advance_notice_days || 1,
					send_push: reminder.send_push,
					is_active: reminder.status === 'pending',
					due_datetime: reminder.due_date || null,
					pet_name: null,
					frequency: reminder.recurrence_type,
					countdown: reminder.countdown // Enhanced endpoint provides countdown data
				}));
				setReminders(transformedReminders);
			}
		} catch (error: any) {
			console.error('Error fetching reminders:', error);
			toast.error('Failed to load reminders');
		} finally {
			setLoading(false);
		}
	};

	const fetchTimezoneSettings = async () => {
		try {
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/user-settings`, {
				withCredentials: true
			});

			if (response.data.success) {
				setTimezoneSettings(response.data.settings);
			}
		} catch (error: any) {
			console.error('Error fetching timezone settings:', error);
		}
	};

	const fetchAISuggestion = async (reminderType: string) => {
		try {
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/ai-suggestions`, {
				withCredentials: true,
				params: { reminder_type: reminderType }
			});

			if (response.data.success) {
				setAiSuggestion(response.data.suggestion);
			}
		} catch (error: any) {
			console.error('Error fetching AI suggestion:', error);
		}
	};

	const createReminder = async () => {
		try {
			if (!createForm.title || !createForm.due_date) {
				toast.error('Please fill in required fields');
				return;
			}

			// Use enhanced reminder endpoint
			const enhancedReminderData = {
				title: createForm.title,
				description: createForm.description,
				reminder_type: createForm.reminder_type,
				due_date: createForm.due_date, // Send full datetime
				send_email: true,
				send_push: createForm.send_push,
				advance_notice_days: createForm.advance_notice_days
			};

			const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders`, enhancedReminderData, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder created successfully!');
				setIsCreateDialogOpen(false);
				setCreateForm({
					title: '',
					description: '',
					reminder_type: 'vaccination',
					due_date: '',
					priority: 'medium',
					advance_notice_days: 3,
					send_push: true,
					is_active: true
				});
				setAiSuggestion(null);
				fetchReminders();
			}
		} catch (error: any) {
			console.error('Error creating reminder:', error);
			toast.error(error.response?.data?.error || 'Failed to create reminder');
		}
	};

	const updateReminder = async (reminderId: number, updates: Partial<Reminder>) => {
		try {
			// Transform updates to enhanced reminder format
			const enhancedUpdates: any = {};
			if (updates.title) enhancedUpdates.title = updates.title;
			if (updates.description) enhancedUpdates.description = updates.description;
			if (updates.status) enhancedUpdates.status = updates.status;
			if (updates.reminder_type) enhancedUpdates.reminder_type = updates.reminder_type;
			if (updates.due_datetime) enhancedUpdates.due_date = updates.due_datetime;

			const response = await axios.put(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${reminderId}`, enhancedUpdates, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder updated successfully!');
				setEditingReminder(null);
				fetchReminders();
			}
		} catch (error: any) {
			console.error('Error updating reminder:', error);
			toast.error('Failed to update reminder');
		}
	};

	const deleteReminder = async (reminderId: number) => {
		try {
			const response = await axios.delete(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${reminderId}`, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder deleted!');
				fetchReminders();
			}
		} catch (error: any) {
			console.error('Error deleting reminder:', error);
			toast.error('Failed to delete reminder');
		}
	};

	const markComplete = async (reminderId: number) => {
		try {
			const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/complete/${reminderId}`, {
				completion_method: 'web_portal',
				notes: ''
			}, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder marked as completed!');
				fetchReminders();
			}
		} catch (error: any) {
			console.error('Error completing reminder:', error);
			toast.error('Failed to complete reminder');
		}
	};

	// Handle editing reminder
	const handleEditReminder = (reminder: Reminder) => {
		// Populate edit form with reminder data
		setEditForm({
			title: reminder.title,
			description: reminder.description || '',
			reminder_type: reminder.reminder_type,
			due_date: reminder.due_datetime ? new Date(reminder.due_datetime).toISOString().slice(0, 16) : '',
			priority: reminder.priority,
			advance_notice_days: reminder.advance_notice_days,
			send_push: reminder.send_push,
			is_active: reminder.is_active
		});
		setEditingReminder(reminder);
	};

	const saveEditReminder = async () => {
		if (!editingReminder) return;

		try {
			if (!editForm.title || !editForm.due_date) {
				toast.error('Please fill in required fields');
				return;
			}

			// Create update payload
			const updates = {
				title: editForm.title,
				description: editForm.description,
				reminder_type: editForm.reminder_type,
				due_date: editForm.due_date, // Send the full datetime
				advance_notice_days: editForm.advance_notice_days,
				send_push: editForm.send_push
			};

			const response = await axios.put(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${editingReminder.id}`, updates, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder updated successfully!');
				setEditingReminder(null);
				setEditForm({
					title: '',
					description: '',
					reminder_type: 'vaccination',
					due_date: '',
					priority: 'medium',
					advance_notice_days: 3,
					send_push: true,
					is_active: true
				});
				fetchReminders();
			}
		} catch (error: any) {
			console.error('Error updating reminder:', error);
			toast.error('Failed to update reminder');
		}
	};

	const applyAISuggestion = () => {
		if (aiSuggestion) {
			const today = createForm.due_date || new Date().toISOString().split('T')[0];
			const suggestedDateTime = `${today}T${aiSuggestion.formatted_24h}:00`;
			setCreateForm(prev => ({ ...prev, due_date: suggestedDateTime }));
			toast.success(`AI suggested ${aiSuggestion.formatted_12h} - ${aiSuggestion.reason}`);
		}
	};

	const getTypeInfo = (type: string) => {
		return reminderTypes.find(t => t.value === type) || reminderTypes[0];
	};

	const getFilteredReminders = () => {
		let filtered = reminders;

		// Filter by tab
		if (activeTab === 'pending') {
			filtered = filtered.filter(r => r.status === 'pending');
		} else if (activeTab === 'overdue') {
			// Only show pending reminders that are actually overdue
			filtered = filtered.filter(r => r.status === 'pending' && r.countdown?.is_overdue);
		} else if (activeTab === 'completed') {
			filtered = filtered.filter(r => r.status === 'completed');
		}

		// Filter by search query
		if (searchQuery) {
			filtered = filtered.filter(r =>
				r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
				r.description?.toLowerCase().includes(searchQuery.toLowerCase())
			);
		}

		return filtered;
	};

	const getUrgencyStats = () => {
		const stats = {
			total: reminders.length,
			overdue: reminders.filter(r => r.status === 'pending' && r.countdown?.is_overdue).length,
			critical: reminders.filter(r => r.status === 'pending' && r.countdown?.urgency === 'critical').length,
			high: reminders.filter(r => r.status === 'pending' && r.countdown?.urgency === 'high').length,
			pending: reminders.filter(r => r.status === 'pending').length,
			completed: reminders.filter(r => r.status === 'completed').length
		};
		return stats;
	};

	if (loading) {
		return (
			<div className="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50">
				<div className="relative w-16 h-8 mr-4 bg-gradient-to-t from-orange-400 via-yellow-400 to-yellow-200 rounded-t-full shadow-lg shadow-orange-300/50">
					<Image
						src="/assets/running-dog.gif"
						alt="Redirecting"
						fill
						priority
						className="object-contain"
					/>
				</div>
			</div>
		);
	}

	const stats = getUrgencyStats();

	return (
		<div className="min-h-screen bg-background p-4 sm:p-6">
			<div className="max-w-[1440px] mx-auto">
				{/* Header with Timezone Info */}
				<motion.div
					initial={{ opacity: 0, y: -20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="mb-6 sm:mb-8"
				>
					<div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
						<div>
							<h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-foreground mb-2">
								AI-Powered Health Reminders 🧠🔔
							</h1>
							<p className="text-sm sm:text-base md:text-lg text-muted-foreground">
								Intelligent timezone-aware reminders with real-time countdown
							</p>
						</div>

						{timezoneSettings && (
							<div className="flex items-start sm:items-center gap-3 sm:gap-4 w-full md:w-auto max-[1100px]:flex-col">
								<TimezoneDisplay
									userTimezone={timezoneSettings?.timezone}
									className="flex-shrink-0 w-full sm:w-auto"
									format="detailed"
									showIcon={true}
									showDate={true}
									auto24Hour={timezoneSettings?.time_format_24h}
								/>

								<Dialog open={isTimezoneDialogOpen} onOpenChange={setIsTimezoneDialogOpen}>
									<DialogTrigger asChild>
										<Button variant="outline" size="sm" className="w-full sm:w-auto mt-2 sm:mt-0">
											<Globe className="w-4 h-4 mr-2" />
											Timezone Settings
										</Button>
									</DialogTrigger>
									<DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
										<DialogHeader>
											<DialogTitle>Timezone Settings</DialogTitle>
											<DialogDescription>
												Manage your timezone preferences for accurate reminder timing
											</DialogDescription>
										</DialogHeader>
										<TimezoneSelector
											onTimezoneChange={() => fetchTimezoneSettings()}
											showAdvancedSettings={true}
										/>
									</DialogContent>
								</Dialog>
							</div>
						)}
					</div>
				</motion.div>

				{/* Enhanced Stats with Real-time Data */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.1 }}
					className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 mb-6 sm:mb-8"
				>
					<div className="bg-card rounded-lg p-4 sm:p-6 border">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-xs sm:text-sm font-medium text-muted-foreground">Total Reminders</p>
								<p className="text-xl sm:text-2xl font-bold text-foreground">{stats.total}</p>
							</div>
							<Bell className="h-6 w-6 sm:h-8 sm:w-8 text-blue-500" />
						</div>
						<p className="text-xs text-muted-foreground mt-2">
							AI-managed reminders
						</p>
					</div>

					<div className="bg-card rounded-lg p-4 sm:p-6 border">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-xs sm:text-sm font-medium text-muted-foreground">Overdue</p>
								<p className="text-xl sm:text-2xl font-bold text-red-600">{stats.overdue}</p>
							</div>
							<AlertTriangle className="h-6 w-6 sm:h-8 sm:w-8 text-red-500" />
						</div>
						<p className="text-xs text-muted-foreground mt-2">
							Need immediate attention
						</p>
					</div>

					<div className="bg-card rounded-lg p-4 sm:p-6 border">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-xs sm:text-sm font-medium text-muted-foreground">Critical</p>
								<p className="text-xl sm:text-2xl font-bold text-orange-600">{stats.critical}</p>
							</div>
							<Timer className="h-6 w-6 sm:h-8 sm:w-8 text-orange-500" />
						</div>
						<p className="text-xs text-muted-foreground mt-2">
							High priority items
						</p>
					</div>

					<div className="bg-card rounded-lg p-4 sm:p-6 border">
						<div className="flex items-center justify-between">
							<div>
								<p className="text-xs sm:text-sm font-medium text-muted-foreground">Completed</p>
								<p className="text-xl sm:text-2xl font-bold text-green-600">{stats.completed}</p>
							</div>
							<CheckCircle className="h-6 w-6 sm:h-8 sm:w-8 text-green-500" />
						</div>
						<p className="text-xs text-muted-foreground mt-2">
							Successfully done
						</p>
					</div>
				</motion.div>

				{/* Quick Actions with AI Features */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.2 }}
					className="bg-card rounded-lg p-4 sm:p-6 border mb-6 sm:mb-8"
				>
					<div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
						<div>
							<h2 className="text-lg sm:text-xl font-semibold mb-1 sm:mb-2">AI-Powered Actions</h2>
							<p className="text-xs sm:text-sm text-muted-foreground">Intelligent reminder management with timezone optimization</p>
						</div>
						<div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
							<Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
								<DialogTrigger asChild>
									<Button className="flex items-center gap-2 w-full sm:w-auto">
										<Brain className="h-4 w-4" />
										AI Smart Reminder
									</Button>
								</DialogTrigger>
								<DialogContent className="w-[95vw] max-w-[525px] max-h-[80vh] overflow-y-auto p-4 sm:p-6">
									<DialogHeader>
										<DialogTitle>Create AI-Optimized Reminder</DialogTitle>
										<DialogDescription>
											Our AI will suggest the optimal time based on your timezone and patterns
										</DialogDescription>
									</DialogHeader>
									<div className="grid gap-4 py-4">
										<div className="grid gap-2">
											<label className="text-sm font-medium">Reminder Type *</label>
											<Select
												value={createForm.reminder_type}
												onValueChange={(value) => {
													setCreateForm({ ...createForm, reminder_type: value });
													fetchAISuggestion(value);
												}}
											>
												<SelectTrigger>
													<SelectValue placeholder="Select reminder type" />
												</SelectTrigger>
												<SelectContent>
													{reminderTypes.map(type => (
														<SelectItem key={type.value} value={type.value}>
															<div className="flex items-center gap-2">
																<span>{type.icon}</span>
																<span>{type.label}</span>
															</div>
														</SelectItem>
													))}
												</SelectContent>
											</Select>
										</div>

										{aiSuggestion && (
											<motion.div
												initial={{ opacity: 0, height: 0 }}
												animate={{ opacity: 1, height: 'auto' }}
												className="p-3 sm:p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200"
											>
												<div className="flex items-center gap-2 mb-2">
													<Brain className="w-4 h-4 text-blue-600" />
													<span className="text-xs sm:text-sm font-medium text-blue-800 dark:text-blue-200">
														AI Time Suggestion
													</span>
													<Badge variant="outline" className="text-xs">
														{Math.round(aiSuggestion.confidence * 100)}% confident
													</Badge>
												</div>
												<p className="text-xs sm:text-sm text-blue-700 dark:text-blue-300 mb-2">
													Recommended time: <strong>{aiSuggestion.formatted_12h}</strong>
												</p>
												<p className="text-xs text-blue-600 dark:text-blue-400 mb-3">
													{aiSuggestion.reason}
												</p>
												<Button size="sm" variant="outline" onClick={applyAISuggestion}>
													<Zap className="w-3 h-3 mr-1" />
													Apply Suggestion
												</Button>
											</motion.div>
										)}

										<div className="grid gap-2">
											<label className="text-sm font-medium">Title *</label>
											<Input
												value={createForm.title}
												onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
												placeholder="e.g., Annual vaccination for Max"
											/>
										</div>

										<div className="grid gap-2">
											<label className="text-sm font-medium">Description</label>
											<Textarea
												value={createForm.description}
												onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
												placeholder="Additional details..."
												rows={3}
											/>
										</div>

										<div className="grid gap-2">
											<label className="text-sm font-medium">Due Date & Time *</label>
											<Input
												type="datetime-local"
												value={createForm.due_date}
												onChange={(e) => setCreateForm({ ...createForm, due_date: e.target.value })}
											/>
											{timezoneSettings && (
												<p className="text-xs text-muted-foreground">
													Time will be converted from your timezone: {timezoneSettings.timezone}
												</p>
											)}
										</div>

										<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
											<div className="grid gap-2">
												<label className="text-sm font-medium">Priority</label>
												<Select
													value={createForm.priority}
													onValueChange={(value) => setCreateForm({ ...createForm, priority: value })}
												>
													<SelectTrigger>
														<SelectValue />
													</SelectTrigger>
													<SelectContent>
														<SelectItem value="low">Low</SelectItem>
														<SelectItem value="medium">Medium</SelectItem>
														<SelectItem value="high">High</SelectItem>
														<SelectItem value="critical">Critical</SelectItem>
													</SelectContent>
												</Select>
											</div>

											<div className="grid gap-2">
												<label className="text-sm font-medium">Advance Notice (days)</label>
												<Input
													type="number"
													min="1"
													max="30"
													value={createForm.advance_notice_days}
													onChange={(e) => setCreateForm({ ...createForm, advance_notice_days: parseInt(e.target.value) || 3 })}
												/>
											</div>
										</div>
									</div>
									<DialogFooter className="flex-col sm:flex-row gap-2 mt-2">
										<Button type="submit" onClick={createReminder} className="w-full sm:w-auto">
											<Brain className="w-4 h-4 mr-2" />
											Create Smart Reminder
										</Button>
									</DialogFooter>
								</DialogContent>
							</Dialog>
						</div>
					</div>
				</motion.div>

				{/* Edit Reminder Dialog */}
				<Dialog open={!!editingReminder} onOpenChange={(open) => !open && setEditingReminder(null)}>
					<DialogContent className="w-[95vw] max-w-[525px] max-h-[80vh] overflow-y-auto p-4 sm:p-6">
						<DialogHeader>
							<DialogTitle>Edit Reminder</DialogTitle>
							<DialogDescription>
								Update your reminder details
							</DialogDescription>
						</DialogHeader>
						<div className="grid gap-4 py-4">
							<div className="grid gap-2">
								<label className="text-sm font-medium">Reminder Type *</label>
								<Select
									value={editForm.reminder_type}
									onValueChange={(value) => setEditForm({ ...editForm, reminder_type: value })}
								>
									<SelectTrigger>
										<SelectValue placeholder="Select reminder type" />
									</SelectTrigger>
									<SelectContent>
										{reminderTypes.map(type => (
											<SelectItem key={type.value} value={type.value}>
												<div className="flex items-center gap-2">
													<span>{type.icon}</span>
													<span>{type.label}</span>
												</div>
											</SelectItem>
										))}
									</SelectContent>
								</Select>
							</div>

							<div className="grid gap-2">
								<label className="text-sm font-medium">Title *</label>
								<Input
									value={editForm.title}
									onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
									placeholder="e.g., Annual vaccination for Max"
								/>
							</div>

							<div className="grid gap-2">
								<label className="text-sm font-medium">Description</label>
								<Textarea
									value={editForm.description}
									onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
									placeholder="Additional details..."
									rows={3}
								/>
							</div>

							<div className="grid gap-2">
								<label className="text-sm font-medium">Due Date & Time *</label>
								<Input
									type="datetime-local"
									value={editForm.due_date}
									onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
								/>
								{timezoneSettings && (
									<p className="text-xs text-muted-foreground">
										Time will be converted from your timezone: {timezoneSettings.timezone}
									</p>
								)}
							</div>

							<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div className="grid gap-2">
									<label className="text-sm font-medium">Priority</label>
									<Select
										value={editForm.priority}
										onValueChange={(value) => setEditForm({ ...editForm, priority: value })}
									>
										<SelectTrigger>
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value="low">Low</SelectItem>
											<SelectItem value="medium">Medium</SelectItem>
											<SelectItem value="high">High</SelectItem>
											<SelectItem value="critical">Critical</SelectItem>
										</SelectContent>
									</Select>
								</div>

								<div className="grid gap-2">
									<label className="text-sm font-medium">Advance Notice (days)</label>
									<Input
										type="number"
										min="1"
										max="30"
										value={editForm.advance_notice_days}
										onChange={(e) => setEditForm({ ...editForm, advance_notice_days: parseInt(e.target.value) || 3 })}
									/>
								</div>
							</div>
						</div>
						<DialogFooter className="flex-col sm:flex-row gap-2">
							<Button variant="outline" onClick={() => setEditingReminder(null)} className="w-full sm:w-auto">
								Cancel
							</Button>
							<Button type="submit" onClick={saveEditReminder} className="w-full sm:w-auto">
								<Edit className="w-4 h-4 mr-2" />
								Update Reminder
							</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>

				{/* Search and Filter */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.3 }}
					className="bg-card rounded-lg p-4 sm:p-6 border mb-6 sm:mb-8"
				>
					<div className="flex flex-col md:flex-row gap-4">
						<div className="flex-1">
							<div className="relative">
								<Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
								<Input
									placeholder="Search reminders..."
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									className="pl-10"
								/>
							</div>
						</div>
					</div>
				</motion.div>

				{/* Reminders Tabs with Real-time Counts */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5, delay: 0.4 }}
				>
					<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
						<TabsList className="grid w-full grid-cols-4 mb-2">
							<TabsTrigger value="all" className="text-xs sm:text-sm">
								All ({stats.total})
							</TabsTrigger>
							<TabsTrigger value="pending" className="text-xs sm:text-sm">
								Pending ({stats.pending})
							</TabsTrigger>
							<TabsTrigger value="overdue" className="text-xs sm:text-sm">
								Overdue ({stats.overdue})
							</TabsTrigger>
							<TabsTrigger value="completed" className="text-xs sm:text-sm">
								Completed ({stats.completed})
							</TabsTrigger>
						</TabsList>

						<TabsContent value={activeTab} className="mt-4 sm:mt-6">
							<div className="grid gap-3 sm:gap-4">
								<AnimatePresence>
									{getFilteredReminders().map((reminder) => {
										const typeInfo = getTypeInfo(reminder.reminder_type);

										return (
											<motion.div
												key={reminder.id}
												initial={{ opacity: 0, y: 20 }}
												animate={{ opacity: 1, y: 0 }}
												exit={{ opacity: 0, y: -20 }}
												transition={{ duration: 0.3 }}
											>
												<Card className={`${reminder.status !== 'completed' && reminder.countdown?.is_overdue ? 'border-red-200 bg-red-50/50 dark:bg-red-900/10' : ''}`}>
													<CardHeader className="p-4 sm:p-6">
														<div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
															<div className="flex items-start gap-3">
																<div className={`p-2 sm:p-3 rounded-full ${typeInfo.color}`}>
																	<span className="text-base sm:text-lg">{typeInfo.icon}</span>
																</div>
																<div className="flex-1">
																	<CardTitle className="text-base sm:text-lg mb-1">{reminder.title}</CardTitle>

																	{/* Show status based on reminder status */}
																	{reminder.status === 'completed' ? (
																		<div className="mb-2">
																			<Badge className="bg-green-100 text-green-800 border-green-200">
																				<CheckCircle className="w-3 h-3 mr-1" />
																				Completed
																			</Badge>
																		</div>
																	) : reminder.due_datetime ? (
																		<FrontendCountdown
																			dueDateTime={reminder.due_datetime}
																			userTimezone={timezoneSettings?.timezone}
																			format="detailed"
																			className="mb-2"
																			onOverdue={() => {
																				console.log(`Reminder ${reminder.id} is overdue!`);
																			}}
																			onCritical={() => {
																				console.log(`Reminder ${reminder.id} is critical!`);
																			}}
																		/>
																	) : null}

																	{reminder.description && (
																		<p className="text-xs sm:text-sm text-muted-foreground mt-2">
																			{reminder.description}
																		</p>
																	)}
																</div>
															</div>
															<div className="flex items-center gap-2 mt-2 sm:mt-0">
																<Badge variant="outline" className={`${typeInfo.color} text-xs`}>
																	{typeInfo.label}
																</Badge>
																<Badge variant="outline" className="text-xs">
																	{reminder.priority}
																</Badge>
															</div>
														</div>
													</CardHeader>
													<CardContent className="p-4 sm:p-6 pt-0">
														<div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
															<div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-muted-foreground">
																<div className="flex items-center gap-1">
																	<Calendar className="w-3 h-3 sm:w-4 sm:h-4" />
																	{reminder.due_date && new Date(reminder.due_date).toLocaleDateString()}
																</div>
																<div className="flex items-center gap-1">
																	<Clock className="w-3 h-3 sm:w-4 sm:h-4" />
																	{reminder.due_time ? (
																		timezoneSettings?.time_format_24h
																			? reminder.due_time
																			: new Date(`2000-01-01T${reminder.due_time}:00`).toLocaleTimeString([], {
																				hour: '2-digit',
																				minute: '2-digit',
																				hour12: true
																			})
																	) : (
																		reminder.due_datetime && new Date(reminder.due_datetime).toLocaleTimeString([], {
																			hour: '2-digit',
																			minute: '2-digit',
																			hour12: !timezoneSettings?.time_format_24h
																		})
																	)}
																</div>
															</div>
															<div className="flex flex-wrap items-center gap-2 mt-2 sm:mt-0">
																{reminder.status === 'pending' && (
																	<Button
																		size="sm"
																		variant="outline"
																		onClick={() => markComplete(reminder.id)}
																		className="text-xs h-8 px-2 py-1"
																	>
																		<CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
																		Complete
																	</Button>
																)}
																<Button
																	size="sm"
																	variant="outline"
																	onClick={() => handleEditReminder(reminder)}
																	className="text-xs h-8 px-2 py-1"
																>
																	<Edit className="w-3 h-3 sm:w-4 sm:h-4" />
																</Button>
																<Button
																	size="sm"
																	variant="outline"
																	onClick={() => deleteReminder(reminder.id)}
																	className="text-xs h-8 px-2 py-1"
																>
																	<Trash2 className="w-3 h-3 sm:w-4 sm:h-4" />
																</Button>
															</div>
														</div>
													</CardContent>
												</Card>
											</motion.div>
										);
									})}
								</AnimatePresence>

								{getFilteredReminders().length === 0 && (
									<div className="text-center py-8 sm:py-12">
										<Bell className="w-8 h-8 sm:w-12 sm:h-12 text-muted-foreground mx-auto mb-3 sm:mb-4" />
										<h3 className="text-base sm:text-lg font-medium text-muted-foreground mb-1 sm:mb-2">No reminders found</h3>
										<p className="text-xs sm:text-sm text-muted-foreground">
											{activeTab === 'all' ? 'Create your first AI-powered reminder!' : `No ${activeTab} reminders at the moment.`}
										</p>
									</div>
								)}
							</div>
						</TabsContent>
					</Tabs>
				</motion.div>
			</div>
		</div>
	);
};

export default RemindersDashboard; 