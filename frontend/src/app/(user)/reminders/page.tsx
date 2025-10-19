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
	MapPin,
	ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import FrontendCountdown from '@/components/FrontendCountdown';
// COMMENTED OUT: Timezone settings not required - frontend auto-detects timezone
// import TimezoneSelector from '@/components/TimezoneSelector';
// import TimezoneDisplay from '@/components/TimezoneDisplay';
import RealTimeCountdown from '@/components/RealTimeCountdown';
import Image from 'next/image';
import { Dropdown, DropdownTrigger, DropdownContent, DropdownItem } from '@/components/ui/dropdown';
import { BsFillAlarmFill } from 'react-icons/bs';
import { FaCirclePlus } from 'react-icons/fa6';
import { FaBell, FaCalendarCheck, FaCheckSquare } from 'react-icons/fa';
import { GiBrain } from 'react-icons/gi';
import { RiProgress8Line } from 'react-icons/ri';
import { GoAlertFill } from 'react-icons/go';
import { BiSolidTimer } from 'react-icons/bi';

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

// COMMENTED OUT: Timezone settings interface not required
// interface TimezoneSettings {
// 	timezone: string;
// 	location_city?: string;
// 	location_country?: string;
// 	time_format_24h: boolean;
// 	timezone_abbreviation: string;
// 	current_local_time: string;
// }

const RemindersDashboard = () => {
	const { user } = useAuth();
	const [reminders, setReminders] = useState<Reminder[]>([]);
	const [loading, setLoading] = useState(true);
	const [initialLoading, setInitialLoading] = useState(true);
	const [isCreating, setIsCreating] = useState(false);
	const [isUpdating, setIsUpdating] = useState(false);
	const [isDeleting, setIsDeleting] = useState<number | null>(null);
	const [isCompleting, setIsCompleting] = useState<number | null>(null);
	const [activeTab, setActiveTab] = useState('all');
	const [searchQuery, setSearchQuery] = useState('');
	const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
	// COMMENTED OUT: Timezone dialog state not needed
	// const [isTimezoneDialogOpen, setIsTimezoneDialogOpen] = useState(false);
	const [editingReminder, setEditingReminder] = useState<Reminder | null>(null);
	// COMMENTED OUT: Timezone settings state not required - frontend auto-detects
	// const [timezoneSettings, setTimezoneSettings] = useState<TimezoneSettings | null>(null);
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

	// Add validation errors state
	const [validationErrors, setValidationErrors] = useState({
		title: "",
		due_date: "",
		reminder_type: ""
	});

	// Add edit form validation errors
	const [editValidationErrors, setEditValidationErrors] = useState({
		title: "",
		due_date: "",
		reminder_type: ""
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
			fetchReminders(true); // Show global loader on initial load
			// COMMENTED OUT: Timezone settings fetch not required
			// fetchTimezoneSettings();

			// Handle chat-created reminder highlighting
			handleChatCreatedReminder();
		}
	}, [user]);

	const handleChatCreatedReminder = () => {
		try {
			const urlParams = new URLSearchParams(window.location.search);
			const newReminderId = urlParams.get('new_reminder_id');
			const fromChat = urlParams.get('from_chat');

			if (newReminderId && fromChat === 'true') {
				// Show success message for chat-created reminder
				toast.success('🎉 Reminder created via chat! Your new reminder is highlighted below.');

				// Scroll to the new reminder after a short delay to ensure rendering
				setTimeout(() => {
					const reminderElement = document.querySelector(`[data-reminder-id="${newReminderId}"]`);
					if (reminderElement) {
						reminderElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
						// Add temporary highlight class
						reminderElement.classList.add('highlight-new-reminder');
						setTimeout(() => {
							reminderElement.classList.remove('highlight-new-reminder');
						}, 3000);
					}
				}, 1000);

				// Clean up URL parameters
				const newUrl = new URL(window.location.href);
				newUrl.searchParams.delete('new_reminder_id');
				newUrl.searchParams.delete('from_chat');
				window.history.replaceState({}, '', newUrl.toString());
			}
		} catch (error) {
			console.error('Error handling chat-created reminder:', error);
		}
	};

	const fetchReminders = async (showLoader = true) => {
		try {
			if (showLoader) {
				setInitialLoading(true);
				setLoading(true); // Keep the original loading state for backward compatibility
			}
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders`, {
				withCredentials: true,
				params: {
					limit: 100,
					offset: 0
				}
			});

			if (response.data.success && response.data.reminders) {
				// Transform the data to match the expected format
				const transformedReminders = response.data.reminders.map((reminder: any) => {
					// Log raw countdown data for debugging
					console.log(`Reminder ${reminder.id} raw countdown:`, reminder.countdown);

					return {
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
						priority: reminder.priority || 'medium', // Use server value or default to medium
						advance_notice_days: reminder.advance_notice_days || 1,
						send_push: reminder.send_push,
						is_active: reminder.status === 'pending',
						due_datetime: reminder.due_date || null,
						pet_name: null,
						frequency: reminder.recurrence_type,
						countdown: reminder.countdown ? {
							...reminder.countdown,
							// Ensure is_overdue is a proper boolean
							is_overdue: String(reminder.countdown.is_overdue).toLowerCase() === 'true',
							// Ensure urgency is a string
							urgency: String(reminder.countdown.urgency || 'unknown')
						} : null // Ensure countdown has proper structure
					};
				});

				// Debug logs
				console.log('Reminders data:', transformedReminders);
				console.log('Reminders with countdown:', transformedReminders.filter((r: Reminder) => r.countdown));
				console.log('Countdown data structure:', transformedReminders.map((r: Reminder) => ({
					id: r.id,
					title: r.title,
					status: r.status,
					countdown: r.countdown ? {
						is_overdue: r.countdown.is_overdue,
						urgency: r.countdown.urgency
					} : null
				})));
				console.log('Overdue reminders:', transformedReminders.filter((r: Reminder) => r.status === 'pending' && r.countdown?.is_overdue));
				console.log('Critical reminders:', transformedReminders.filter((r: Reminder) => r.status === 'pending' && r.countdown?.urgency === 'critical'));

				setReminders(transformedReminders);
			}
		} catch (error: any) {
			console.error('Error fetching reminders:', error);
			toast.error('Failed to load reminders');
		} finally {
			setInitialLoading(false);
			setLoading(false); // Keep the original loading state for backward compatibility
		}
	};

	// COMMENTED OUT: Timezone settings fetch function not required
	// const fetchTimezoneSettings = async () => {
	// 	try {
	// 		const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/user-settings`, {
	// 			withCredentials: true
	// 		});

	// 		if (response.data.success) {
	// 			setTimezoneSettings(response.data.settings);
	// 		}
	// 	} catch (error: any) {
	// 		console.error('Error fetching timezone settings:', error);
	// 	}
	// };

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

	const validateForm = () => {
		let isValid = true;
		const errors = {
			title: "",
			due_date: "",
			reminder_type: ""
		};

		if (!createForm.title.trim()) {
			errors.title = "Title is required";
			isValid = false;
		}

		if (!createForm.due_date) {
			errors.due_date = "Due date and time are required";
			isValid = false;
		}

		if (!createForm.reminder_type) {
			errors.reminder_type = "Reminder type is required";
			isValid = false;
		}

		setValidationErrors(errors);
		return isValid;
	};

	// Clear validation error when user types in a field
	const handleInputChange = (field: string, value: any) => {
		setCreateForm(prev => ({ ...prev, [field]: value }));
		if (validationErrors[field as keyof typeof validationErrors]) {
			setValidationErrors(prev => ({
				...prev,
				[field]: ""
			}));
		}
	};

	// Clear edit validation error when user types in a field
	const handleEditInputChange = (field: string, value: any) => {
		setEditForm(prev => ({ ...prev, [field]: value }));
		if (editValidationErrors[field as keyof typeof editValidationErrors]) {
			setEditValidationErrors(prev => ({
				...prev,
				[field]: ""
			}));
		}
	};

	// Validate edit form
	const validateEditForm = () => {
		let isValid = true;
		const errors = {
			title: "",
			due_date: "",
			reminder_type: ""
		};

		if (!editForm.title.trim()) {
			errors.title = "Title is required";
			isValid = false;
		}

		if (!editForm.due_date) {
			errors.due_date = "Due date and time are required";
			isValid = false;
		}

		if (!editForm.reminder_type) {
			errors.reminder_type = "Reminder type is required";
			isValid = false;
		}

		setEditValidationErrors(errors);
		return isValid;
	};

	// Handle reminder type selection and fetch AI suggestion
	const handleReminderTypeChange = (value: string) => {
		handleInputChange("reminder_type", value);
		fetchAISuggestion(value);
	};

	const createReminder = async () => {
		try {
			// Validate form first
			if (!validateForm()) {
				return;
			}

			setIsCreating(true);

			// Use enhanced reminder endpoint
			const enhancedReminderData = {
				title: createForm.title,
				description: createForm.description,
				reminder_type: createForm.reminder_type,
				due_date: createForm.due_date, // Send full datetime
				send_email: true,
				send_push: createForm.send_push,
				advance_notice_days: createForm.advance_notice_days,
				priority: createForm.priority // Add priority to the request
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
				fetchReminders(false); // Don't show global loader when refreshing
			}
		} catch (error: any) {
			console.error('Error creating reminder:', error);
			toast.error(error.response?.data?.error || 'Failed to create reminder');
		} finally {
			setIsCreating(false);
		}
	};

	const updateReminder = async (reminderId: number, updates: Partial<Reminder>) => {
		try {
			setIsUpdating(true);

			// Transform updates to enhanced reminder format
			const enhancedUpdates: any = {};
			if (updates.title) enhancedUpdates.title = updates.title;
			if (updates.description) enhancedUpdates.description = updates.description;
			if (updates.status) enhancedUpdates.status = updates.status;
			if (updates.reminder_type) enhancedUpdates.reminder_type = updates.reminder_type;
			if (updates.due_datetime) enhancedUpdates.due_date = updates.due_datetime;
			if (updates.priority) enhancedUpdates.priority = updates.priority; // Add priority to updates

			const response = await axios.put(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${reminderId}`, enhancedUpdates, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder updated successfully!');
				setEditingReminder(null);
				fetchReminders(false); // Don't show global loader when refreshing
			}
		} catch (error: any) {
			console.error('Error updating reminder:', error);
			toast.error('Failed to update reminder');
		} finally {
			setIsUpdating(false);
		}
	};

	const deleteReminder = async (reminderId: number) => {
		try {
			setIsDeleting(reminderId);

			const response = await axios.delete(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${reminderId}`, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder deleted!');
				fetchReminders(false); // Don't show global loader when refreshing
			}
		} catch (error: any) {
			console.error('Error deleting reminder:', error);
			toast.error('Failed to delete reminder');
		} finally {
			setIsDeleting(null);
		}
	};

	const markComplete = async (reminderId: number) => {
		try {
			setIsCompleting(reminderId);

			const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/complete/${reminderId}`, {
				completion_method: 'web_portal',
				notes: ''
			}, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder marked as completed!');
				fetchReminders(false); // Don't show global loader when refreshing
			}
		} catch (error: any) {
			console.error('Error completing reminder:', error);
			toast.error('Failed to complete reminder');
		} finally {
			setIsCompleting(null);
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
			// Validate form first
			if (!validateEditForm()) {
				return;
			}

			setIsUpdating(true);

			// Create update payload
			const updates = {
				title: editForm.title,
				description: editForm.description,
				reminder_type: editForm.reminder_type,
				due_date: editForm.due_date, // Send the full datetime
				advance_notice_days: editForm.advance_notice_days,
				send_push: editForm.send_push,
				priority: editForm.priority // Add priority to the update request
			};

			const response = await axios.put(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/${editingReminder.id}`, updates, {
				withCredentials: true
			});

			if (response.data.success) {
				toast.success('Reminder updated successfully!');
				setEditingReminder(null);
				fetchReminders(false); // Don't show global loader when refreshing
			}
		} catch (error: any) {
			console.error('Error updating reminder:', error);
			toast.error('Failed to update reminder');
		} finally {
			setIsUpdating(false);
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

	const getPriorityInfo = (priority: string) => {
		switch (priority) {
			case 'low':
				return {
					color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
					dotColor: 'bg-blue-500',
					label: 'Low Priority'
				};
			case 'medium':
				return {
					color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
					dotColor: 'bg-green-500',
					label: 'Medium Priority'
				};
			case 'high':
				return {
					color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
					dotColor: 'bg-orange-500',
					label: 'High Priority'
				};
			case 'critical':
				return {
					color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
					dotColor: 'bg-red-500 animate-pulse',
					label: 'Critical Priority'
				};
			default:
				return {
					color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
					dotColor: 'bg-green-500',
					label: 'Medium Priority'
				};
		}
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
		// First, get all pending reminders
		const pendingReminders = reminders.filter(r => r.status === 'pending');

		// Calculate overdue and priority-based counts
		let overdueCount = 0;
		let criticalCount = 0;
		let highCount = 0;

		pendingReminders.forEach(reminder => {
			// Check if reminder is overdue based on due_date (using consistent field name)
			const dueDateTime = reminder.due_date || reminder.due_datetime;
			if (dueDateTime) {
				const dueDate = new Date(dueDateTime);
				const now = new Date();
				const isOverdue = dueDate.getTime() < now.getTime();

				// Count overdue reminders
				if (isOverdue) {
					overdueCount++;
				}
			}

			// Count by actual priority field (not time-based calculation)
			if (reminder.priority === 'critical') {
				criticalCount++;
			} else if (reminder.priority === 'high') {
				highCount++;
			}
		});

		const stats = {
			total: reminders.length,
			overdue: overdueCount,
			critical: criticalCount,
			high: highCount,
			pending: pendingReminders.length,
			completed: reminders.filter(r => r.status === 'completed').length
		};

		return stats;
	};

	// Show loading indicator only on initial load
	if (initialLoading) {
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
		<>
			<style jsx>{`
				.highlight-new-reminder {
					animation: highlightPulse 3s ease-in-out;
					border: 2px solid #10b981 !important;
					box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2) !important;
				}
				
				@keyframes highlightPulse {
					0%, 100% { 
						box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2);
					}
					50% { 
						box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.4);
					}
				}
			`}</style>
			<div className="min-h-screen bg-background p-4 sm:p-6 font-work-sans">
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
									Health Reminders Management <FaBell className="w-10 h-10 text-yellow-500 inline-block" />
								</h1>
								<p className="text-sm sm:text-base md:text-lg text-muted-foreground">
									Intelligent reminders with real-time countdown
								</p>
							</div>

							{/* COMMENTED OUT: Timezone settings UI not required - frontend auto-detects timezone */}
							{/* Timezone display and settings UI removed - frontend components auto-detect browser timezone */}
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
								<RiProgress8Line className="h-6 w-6 sm:h-8 sm:w-8 text-blue-500" />
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
								<BiSolidTimer className="!h-10 !w-10 sm:h-8 sm:w-8 text-orange-500" />
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
								<GoAlertFill className="h-6 w-6 sm:h-8 sm:w-8 text-red-500" />
							</div>
							<p className="text-xs text-muted-foreground mt-2">
								Includes overdue and urgent items
							</p>
						</div>

						<div className="bg-card rounded-lg p-4 sm:p-6 border">
							<div className="flex items-center justify-between">
								<div>
									<p className="text-xs sm:text-sm font-medium text-muted-foreground">Completed</p>
									<p className="text-xl sm:text-2xl font-bold text-green-600">{stats.completed}</p>
								</div>
								<FaCalendarCheck className="h-6 w-6 sm:h-8 sm:w-8 text-green-500" />
							</div>
							<p className="text-xs text-muted-foreground mt-2">
								Successfully done
							</p>
						</div>
					</motion.div>

					{/* Quick Actions with AI Features */}
					{/* <motion.div
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.5, delay: 0.2 }}
						className="bg-card rounded-lg p-4 sm:p-6 border mb-6 sm:mb-8"
					>
						<div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
							<div>
								<h2 className="text-lg sm:text-xl font-semibold mb-1 sm:mb-2">AI-Powered Actions</h2>
								<p className="text-xs sm:text-sm text-muted-foreground">Intelligent reminder management with AI optimization</p>
							</div>

						</div>
					</motion.div> */}

					{/* Edit Reminder Dialog */}
					<Dialog open={!!editingReminder} onOpenChange={(open) => !open && setEditingReminder(null)}>
						<DialogContent className="w-[95vw] max-w-[525px] p-4 sm:p-6">
							<DialogHeader>
								<DialogTitle>Edit Reminder</DialogTitle>
								<DialogDescription>
									Update your reminder details
								</DialogDescription>
							</DialogHeader>
							<div className="grid gap-4 py-4  pr-2">
								<div className="grid gap-2">
									<label className="text-sm font-medium">Reminder Type *</label>
									<Dropdown>
										<DropdownTrigger asChild>
											<Button variant="outline" className={`w-full justify-between bg-white/10 border-input ${editValidationErrors.reminder_type ? 'border-red-500 ring-1 ring-red-500' : ''}`}>
												<div className="flex items-center gap-2">
													{editForm.reminder_type ? (
														<>
															<span>{getTypeInfo(editForm.reminder_type).icon}</span>
															<span className="text-sm">{getTypeInfo(editForm.reminder_type).label}</span>
														</>
													) : (
														<span className="text-sm text-muted-foreground">Select reminder type</span>
													)}
												</div>
												<ChevronDown className="h-4 w-4 opacity-50" />
											</Button>
										</DropdownTrigger>
										<DropdownContent className="bg-black border-neutral-800 text-white">
											{reminderTypes.map(type => (
												<DropdownItem
													key={type.value}
													onClick={() => handleEditInputChange("reminder_type", type.value)}
												>
													<div className="flex items-center gap-2">
														<span>{type.icon}</span>
														<span>{type.label}</span>
													</div>
												</DropdownItem>
											))}
										</DropdownContent>
									</Dropdown>
									{editValidationErrors.reminder_type && (
										<span className="text-red-500 text-sm mt-1">{editValidationErrors.reminder_type}</span>
									)}
								</div>

								<div className="grid gap-2">
									<label className="text-sm font-medium">Title *</label>
									<Input
										value={editForm.title}
										onChange={(e) => handleEditInputChange("title", e.target.value)}
										placeholder="e.g., Annual vaccination for Max"
										className={`${editValidationErrors.title ? 'border-red-500 ring-1 ring-red-500' : ''}`}
									/>
									{editValidationErrors.title && (
										<span className="text-red-500 text-sm mt-1">{editValidationErrors.title}</span>
									)}
								</div>

								<div className="grid gap-2">
									<label className="text-sm font-medium">Description</label>
									<Textarea
										value={editForm.description}
										onChange={(e) => handleEditInputChange("description", e.target.value)}
										placeholder="Additional details..."
										rows={3}
									/>
								</div>

								<div className="grid gap-2">
									<label className="text-sm font-medium">Due Date & Time *</label>
									<Input
										type="datetime-local"
										value={editForm.due_date}
										onChange={(e) => handleEditInputChange("due_date", e.target.value)}
										className={`${editValidationErrors.due_date ? 'border-red-500 ring-1 ring-red-500' : ''}`}
										style={{ backgroundColor: '#121212', color: 'white', borderColor: '#333' }}
									/>
									{editValidationErrors.due_date && (
										<span className="text-red-500 text-sm mt-1">{editValidationErrors.due_date}</span>
									)}
									{/* COMMENTED OUT: Timezone conversion note not needed */}
									{/* Timezone conversion note removed - times are handled automatically */}
								</div>

								<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
									<div className="grid gap-2">
										<label className="text-sm font-medium">Priority</label>
										<Dropdown>
											<DropdownTrigger asChild>
												<Button variant="outline" className="w-full justify-between bg-white/10 border-input">
													<div className="flex items-center gap-2">
														<span className={`w-3 h-3 rounded-full ${getPriorityInfo(editForm.priority).dotColor}`}></span>
														<span className="text-sm">{getPriorityInfo(editForm.priority).label}</span>
													</div>
													<ChevronDown className="h-4 w-4 opacity-50" />
												</Button>
											</DropdownTrigger>
											<DropdownContent className="bg-black border-neutral-800 text-white">
												<DropdownItem onClick={() => handleEditInputChange("priority", "low")}>
													<div className="flex items-center gap-2">
														<span className="w-3 h-3 rounded-full bg-blue-500"></span>
														<span>Low</span>
													</div>
												</DropdownItem>
												<DropdownItem onClick={() => handleEditInputChange("priority", "medium")}>
													<div className="flex items-center gap-2">
														<span className="w-3 h-3 rounded-full bg-green-500"></span>
														<span>Medium</span>
													</div>
												</DropdownItem>
												<DropdownItem onClick={() => handleEditInputChange("priority", "high")}>
													<div className="flex items-center gap-2">
														<span className="w-3 h-3 rounded-full bg-orange-500"></span>
														<span>High</span>
													</div>
												</DropdownItem>
												<DropdownItem onClick={() => handleEditInputChange("priority", "critical")}>
													<div className="flex items-center gap-2">
														<span className="w-3 h-3 rounded-full bg-red-500"></span>
														<span>Critical</span>
													</div>
												</DropdownItem>
											</DropdownContent>
										</Dropdown>
									</div>

									<div className="grid gap-2">
										<label className="text-sm font-medium">Advance Notice (days)</label>
										<Input
											type="number"
											min="1"
											max="30"
											value={editForm.advance_notice_days}
											onChange={(e) => handleEditInputChange("advance_notice_days", parseInt(e.target.value) || 3)}
										/>
									</div>
								</div>
							</div>
							<DialogFooter className="flex-col sm:flex-row gap-2">
								<Button variant="outline" onClick={() => setEditingReminder(null)} className="w-full sm:w-auto">
									Cancel
								</Button>
								<Button
									type="submit"
									onClick={saveEditReminder}
									className="w-full sm:w-auto"
									disabled={isUpdating}
								>
									{isUpdating ? (
										<>
											<svg className="animate-spin w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
												<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
												<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
											</svg>
											Updating...
										</>
									) : (
										<>
											<Edit className="w-4 h-4 mr-2" />
											Update Reminder
										</>
									)}
								</Button>
							</DialogFooter>
						</DialogContent>
					</Dialog>

					{/* Search and Filter */}
					<motion.div
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.5, delay: 0.3 }}
						className="bg-card rounded-lg flex justify-between p-4 sm:p-6 border mb-6 sm:mb-8"
					>
						<div className="flex flex-col md:flex-row gap-4 w-full">
							<div className="flex-1">
								<div className="relative">
									<Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
									<Input
										placeholder="Search reminders..."
										value={searchQuery}
										onChange={(e) => setSearchQuery(e.target.value)}
										className="pl-10 w-full sm:w-2/3 md:w-1/2 lg:w-1/3"
									/>
								</div>
							</div>
						</div>

						<div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
							<Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
								<DialogTrigger asChild>
									<Button className="flex font-bold text-lg font-public-sans items-center gap-2 w-full sm:w-auto">
										<BsFillAlarmFill className="h-4 w-4" />
										Set Reminder
									</Button>
								</DialogTrigger>
								<DialogContent className="w-[95vw] max-w-[525px] p-4 sm:p-6">
									<DialogHeader>
										<DialogTitle>Create AI-Optimized Reminder</DialogTitle>
										<DialogDescription>
											Our AI will suggest the optimal time based on your patterns
										</DialogDescription>
									</DialogHeader>
									<div className="grid gap-4 py-4 overflow-y-auto custom-scrollbar h-[400px] pr-4">
										<div className="grid gap-2">
											<label className="text-sm font-medium">Reminder Type *</label>
											<Dropdown>
												<DropdownTrigger asChild>
													<Button variant="outline" className={`w-full justify-between bg-white/10 border-input ${validationErrors.reminder_type ? 'border-red-500 ring-1 ring-red-500' : ''}`}>
														<div className="flex items-center gap-2">
															{createForm.reminder_type ? (
																<>
																	<span>{getTypeInfo(createForm.reminder_type).icon}</span>
																	<span className="text-sm">{getTypeInfo(createForm.reminder_type).label}</span>
																</>
															) : (
																<span className="text-sm text-muted-foreground">Select reminder type</span>
															)}
														</div>
														<ChevronDown className="h-4 w-4 opacity-50" />
													</Button>
												</DropdownTrigger>
												<DropdownContent className="bg-black border-neutral-800 text-white">
													{reminderTypes.map(type => (
														<DropdownItem
															key={type.value}
															onClick={() => handleReminderTypeChange(type.value)}
														>
															<div className="flex items-center gap-2">
																<span>{type.icon}</span>
																<span>{type.label}</span>
															</div>
														</DropdownItem>
													))}
												</DropdownContent>
											</Dropdown>
											{validationErrors.reminder_type && (
												<span className="text-red-500 text-sm mt-1">{validationErrors.reminder_type}</span>
											)}
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
												onChange={(e) => handleInputChange("title", e.target.value)}
												placeholder="e.g., Annual vaccination for Max"
												className={`${validationErrors.title ? 'border-red-500 ring-1 ring-red-500' : ''}`}
											/>
											{validationErrors.title && (
												<span className="text-red-500 text-sm mt-1">{validationErrors.title}</span>
											)}
										</div>

										<div className="grid gap-2">
											<label className="text-sm font-medium">Description</label>
											<Textarea
												value={createForm.description}
												onChange={(e) => handleInputChange("description", e.target.value)}
												placeholder="Additional details..."
												rows={3}
											/>
										</div>

										<div className="grid gap-2">
											<label className="text-sm font-medium">Due Date & Time *</label>
											<Input
												type="datetime-local"
												value={createForm.due_date}
												onChange={(e) => handleInputChange("due_date", e.target.value)}
												className={`${validationErrors.due_date ? 'border-red-500 ring-1 ring-red-500' : ''}`}
												style={{ backgroundColor: '#121212', color: 'white', borderColor: '#333' }}
											/>
											{validationErrors.due_date && (
												<span className="text-red-500 text-sm mt-1">{validationErrors.due_date}</span>
											)}
											{/* COMMENTED OUT: Timezone conversion note not needed */}
											{/* Timezone conversion note removed - times are handled automatically */}
										</div>

										<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
											<div className="grid gap-2">
												<label className="text-sm font-medium">Priority</label>
												<Dropdown>
													<DropdownTrigger asChild>
														<Button variant="outline" className="w-full justify-between bg-white/10 border-input">
															<div className="flex items-center gap-2">
																<span className={`w-3 h-3 rounded-full ${getPriorityInfo(createForm.priority).dotColor}`}></span>
																<span className="text-sm">{getPriorityInfo(createForm.priority).label}</span>
															</div>
															<ChevronDown className="h-4 w-4 opacity-50" />
														</Button>
													</DropdownTrigger>
													<DropdownContent className="bg-black border-neutral-800 text-white">
														<DropdownItem onClick={() => handleInputChange("priority", "low")}>
															<div className="flex items-center gap-2">
																<span className="w-3 h-3 rounded-full bg-blue-500"></span>
																<span>Low</span>
															</div>
														</DropdownItem>
														<DropdownItem onClick={() => handleInputChange("priority", "medium")}>
															<div className="flex items-center gap-2">
																<span className="w-3 h-3 rounded-full bg-green-500"></span>
																<span>Medium</span>
															</div>
														</DropdownItem>
														<DropdownItem onClick={() => handleInputChange("priority", "high")}>
															<div className="flex items-center gap-2">
																<span className="w-3 h-3 rounded-full bg-orange-500"></span>
																<span>High</span>
															</div>
														</DropdownItem>
														<DropdownItem onClick={() => handleInputChange("priority", "critical")}>
															<div className="flex items-center gap-2">
																<span className="w-3 h-3 rounded-full bg-red-500"></span>
																<span>Critical</span>
															</div>
														</DropdownItem>
													</DropdownContent>
												</Dropdown>
											</div>

											<div className="grid gap-2">
												<label className="text-sm font-medium">Advance Notice (days)</label>
												<Input
													type="number"
													min="1"
													max="30"
													value={createForm.advance_notice_days}
													onChange={(e) => handleInputChange("advance_notice_days", parseInt(e.target.value) || 3)}
												/>
											</div>
										</div>
									</div>
									<DialogFooter className="flex-col sm:flex-row gap-2 mt-2">
										<Button
											type="submit"
											onClick={createReminder}
											className="w-full sm:w-auto font-public-sans text-sm font-bold"
											disabled={isCreating}
										>
											{isCreating ? (
												<>
													<svg className="animate-spin w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
														<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
														<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
													</svg>
													Creating...
												</>
											) : (
												<>
													<Brain className="w-4 h-4 mr-2" />
													Create Reminder
												</>
											)}
										</Button>
									</DialogFooter>
								</DialogContent>
							</Dialog>
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
								<div className="grid gap-3 sm:gap-4 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
									<AnimatePresence>
										{getFilteredReminders().map((reminder) => {
											const typeInfo = getTypeInfo(reminder.reminder_type);
											const priorityInfo = getPriorityInfo(reminder.priority);

											return (
												<motion.div
													key={reminder.id}
													initial={{ opacity: 0, y: 20 }}
													animate={{ opacity: 1, y: 0 }}
													exit={{ opacity: 0, y: -20 }}
													transition={{ duration: 0.3 }}
												>
													<Card
														className={`${reminder.status !== 'completed' && reminder.countdown?.is_overdue ? 'border-red-200 bg-red-50/50 dark:bg-red-900/10' : ''} overflow-hidden`}
														data-reminder-id={reminder.id}
													>
														<CardHeader className="p-3 sm:p-6">
															<div className="flex flex-col gap-3">
																<div className="flex items-start gap-3">
																	<div className={`p-2 sm:p-3 rounded-full ${typeInfo.color} flex-shrink-0`}>
																		<span className="text-base sm:text-lg">{typeInfo.icon}</span>
																	</div>
																	<div className="flex-1 min-w-0">
																		<div className="flex items-center gap-2 justify-between">
																			<CardTitle className="text-base sm:text-lg mb-1 break-words">{reminder.title}</CardTitle>
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
																					// COMMENTED OUT: userTimezone prop not needed - component auto-detects
																					// userTimezone={timezoneSettings?.timezone}
																					format="detailed"
																					className="mb-2"
																					onOverdue={() => {
																						// Silent callback - no need to log
																					}}
																					onCritical={() => {
																						// Silent callback - no need to log
																					}}
																				/>
																			) : null}

																		</div>



																		{reminder.description && (
																			<p className="text-xs sm:text-sm text-muted-foreground mt-2 break-words line-clamp-3">
																				{reminder.description}
																			</p>
																		)}
																	</div>
																</div>

																<div className="flex flex-wrap gap-2 mt-1">
																	<Badge variant="outline" className={`${typeInfo.color} text-xs`}>
																		{typeInfo.label}
																	</Badge>
																	<Badge variant="outline" className={`text-xs ${priorityInfo.color}`}>
																		{priorityInfo.label}
																	</Badge>
																</div>
															</div>
														</CardHeader>
														<CardContent className="p-3 sm:p-6 border-t border-gray-100 dark:border-gray-800 bg-card/50">
															<div className="flex flex-col gap-3">
																<div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-muted-foreground">
																	<div className="flex items-center gap-1 bg-background/50 px-2 py-1 rounded-md">
																		<Calendar className="w-3 h-3 sm:w-4 sm:h-4 text-[var(--mrwhite-primary-color)]" />
																		{reminder.due_date && new Date(reminder.due_date).toLocaleDateString()}
																	</div>
																	<div className="flex items-center gap-1 bg-background/50 px-2 py-1 rounded-md">
																		<Clock className="w-3 h-3 sm:w-4 sm:h-4" />
																		{reminder.due_time ? (
																			// COMMENTED OUT: timezone format preference, using 12-hour format as default
																			// timezoneSettings?.time_format_24h
																			// 	? reminder.due_time
																			// 	: 
																			new Date(`2000-01-01T${reminder.due_time}:00`).toLocaleTimeString([], {
																				hour: '2-digit',
																				minute: '2-digit',
																				hour12: true
																			})
																		) : (
																			reminder.due_datetime && new Date(reminder.due_datetime).toLocaleTimeString([], {
																				hour: '2-digit',
																				minute: '2-digit',
																				hour12: true // Default to 12-hour format
																			})
																		)}
																	</div>
																</div>
																<div className="flex flex-wrap items-center gap-2 mt-2 justify-end">
																	{reminder.status === 'pending' && (
																		<Button
																			size="sm"

																			onClick={() => markComplete(reminder.id)}
																			className="font-bold h-8 px-2 py-1 font-public-sans"
																			disabled={isCompleting === reminder.id}
																		>
																			{isCompleting === reminder.id ? (
																				<>
																					<svg className="animate-spin w-3 h-3 sm:w-4 sm:h-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
																						<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
																						<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
																					</svg>
																					Completing...
																				</>
																			) : (
																				<>
																					<FaCheckSquare className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
																					Mark as Complete
																				</>
																			)}
																		</Button>
																	)}
																	{/* <Button
																	size="sm"
																	variant="outline"
																	onClick={() => handleEditReminder(reminder)}
																	className="text-xs h-8 px-2 py-1"
																	disabled={isUpdating}
																>
																	<Edit className="w-3 h-3 sm:w-4 sm:h-4" />
																</Button> */}
																	<Button
																		size="sm"
																		variant="outline"
																		onClick={() => deleteReminder(reminder.id)}
																		className="text-xs h-8 px-2 py-1"
																		disabled={isDeleting === reminder.id}
																	>
																		{isDeleting === reminder.id ? (
																			<svg className="animate-spin w-3 h-3 sm:w-4 sm:h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
																				<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
																				<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
																			</svg>
																		) : (
																			<Trash2 className="w-3 h-3 sm:w-4 sm:h-4" />
																		)}
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
										<div className="text-center py-8 sm:py-12 col-span-full bg-card/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 px-4">
											<Bell className="w-8 h-8 sm:w-12 sm:h-12 text-muted-foreground mx-auto mb-3 sm:mb-4" />
											<h3 className="text-base sm:text-lg font-medium text-muted-foreground mb-1 sm:mb-2">No reminders found</h3>
											<p className="text-xs sm:text-sm text-muted-foreground">
												{activeTab === 'all' ? 'Create your first AI-powered reminder!' : `No ${activeTab} reminders at the moment.`}
											</p>
											{activeTab === 'all' && (
												<Button
													className="mt-4"
													size="sm"
													onClick={() => setIsCreateDialogOpen(true)}
												>
													<FaCirclePlus className="w-4 h-4 mr-2" />
													Create Reminder
												</Button>
											)}
										</div>
									)}
								</div>
							</TabsContent>
						</Tabs>
					</motion.div>
				</div>
			</div>
		</>
	);
};

export default RemindersDashboard; 