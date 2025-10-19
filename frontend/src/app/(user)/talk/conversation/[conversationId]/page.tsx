'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
	FiX,
	FiMoreVertical,
	FiTrash2,
	FiEdit,
	FiSearch,
	FiSave,
} from 'react-icons/fi';
import { PiBookmarkFill } from 'react-icons/pi';
import { AiOutlineLoading } from "react-icons/ai";
import Message from '@/components/Message';
import MessageLoader from '@/components/MessageLoader';
import axios from 'axios';
import UploadModal from '@/components/UploadModal';
import Sidebar from '@/components/Sidebar';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
// Import our new components and utilities
import HeroSection from '@/components/HeroSection';
import ChatHeader from '@/components/ChatHeader';
import ChatControls from '@/components/ChatControls';
import {
	fetchConversationHistory,
	fetchBookmarks as fetchBookmarksApi,
	toggleConversationBookmark as toggleBookmarkApi,
	createNewConversation as createNewConversationApi,
	loadConversationMessages as loadConversationMessagesApi,
	sendChatMessage,
	sendHealthMessage,
	FASTAPI_BASE_URL
} from '@/utils/api';
import {
	copyToClipboard,
	speakText,
	handleMessageReaction,
	bookmarkMessage,
	retryAiMessage
} from '@/utils/messageUtils';
import { Heart } from 'lucide-react';
import ConfirmDialog from '@/components/ConfirmDialog';
import BookCreationModal from '@/components/BookCreationModal';
import EnhancedBookCreationModal from '@/components/EnhancedBookCreationModal';
import { UsageTracker } from '@/components/UsageTracker';
import { PremiumGate } from '@/components/PremiumGate';
import { CreditTracker } from '@/components/CreditTracker';
import { BsBookmarkFill, BsFillBookmarkCheckFill } from 'react-icons/bs';
import toast from '@/components/ui/sound-toast';

interface Message {
	id: string;
	content: string;
	type: 'user' | 'ai';
	timestamp: string;
	liked?: boolean;
	disliked?: boolean;
	attachments?: Array<{
		type: 'image' | 'file' | 'audio';
		url: string;
		name: string;
	}>;
}

interface Bookmark extends Message {
	bookmarkedAt: string;
}

interface ConversationItem {
	id: number;
	title: string;
}

interface HistoryDay {
	date: string;
	conversations: ConversationItem[];
}

interface SidePanelProps {
	type: 'history' | 'bookmarks';
	isOpen: boolean;
	onClose: () => void;
}

interface SelectedFile {
	file: File;
	type: 'file' | 'image' | 'audio';
	previewUrl?: string;
	description?: string;
	s3Url?: string;
}

interface Conversation {
	id: string;
	title: string;
	updated_at?: string;
}

const TalkPage = () => {
	const [messages, setMessages] = useState<Message[]>([]);
	const [inputValue, setInputValue] = useState('');
	const [isTyping, setIsTyping] = useState(false);
	const [showHistory, setShowHistory] = useState(false);
	
	// Counter to ensure unique IDs even in rapid succession
	const messageIdCounter = useRef(0);
	
	// Function to generate unique message IDs
	const generateUniqueId = useCallback(() => {
		messageIdCounter.current += 1;
		return `${Date.now()}-${messageIdCounter.current}`;
	}, []);
	
	const [showBookmarks, setShowBookmarks] = useState(false);
	const [uploadType, setUploadType] = useState<'file' | 'image'>('file');
	const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
	const [history, setHistory] = useState<HistoryDay[]>([]);
	const [uploadModalOpen, setUploadModalOpen] = useState(false);
	const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
	const [isBookmarked, setIsBookmarked] = useState(false);
	const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);
	const [isRenaming, setIsRenaming] = useState<string | null>(null);
	const [newTitle, setNewTitle] = useState<string>('');
	const [searchQuery, setSearchQuery] = useState<string>('');
	const [filteredHistory, setFilteredHistory] = useState<HistoryDay[]>([]);
	const [isSaving, setIsSaving] = useState<string | null>(null);
	const [isHealthMode, setIsHealthMode] = useState(false);
	const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
	const [conversation, setConversation] = useState<Conversation | null>(null);
	const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
	const [isBookCreationModalOpen, setIsBookCreationModalOpen] = useState(false);
	const [isEnhancedBookModalOpen, setIsEnhancedBookModalOpen] = useState(false);
	const [usageStats, setUsageStats] = useState<any>(null);
	const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);
	const [isCreditTrackerVisible, setIsCreditTrackerVisible] = useState(false);

	const params = useParams();
	const conversationId = params.conversationId as string;
	const router = useRouter();
	const { user, triggerCreditRefresh } = useAuth();

	const messagesContainerRef = useRef<HTMLDivElement>(null);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);

	// Initialize conversation ID state
	useEffect(() => {
		console.log('🔄 URL changed - conversationId:', conversationId);
		console.log('🔍 CONVERSATION STATE DEBUG:', {
			conversationId,
			currentConversationId,
			timestamp: new Date().toISOString()
		});
		if (conversationId && conversationId !== 'new-chat') {
			console.log('📝 Setting currentConversationId to:', conversationId);
			setCurrentConversationId(conversationId);
		} else {
			console.log('🆕 Resetting currentConversationId to null (new-chat mode)');
			setCurrentConversationId(null);
		}
	}, [conversationId]);

	// Modify the showHistory state setter to always fetch fresh data when opening
	const toggleHistory = async () => {
		if (!showHistory) {
			await fetchHistory();
		} else {
			// Just close the panel
			setShowHistory(false);
		}
	};

	// Create a new conversation if needed
	const createNewConversation = async () => {
		console.log('🚨 CRITICAL: createNewConversation() called!', {
			timestamp: new Date().toISOString(),
			stackTrace: new Error().stack,
			currentUrl: window.location.pathname,
			conversationId: conversationId,
			currentConversationId: currentConversationId,
			user: user?.id
		});
		
		try {
			// Check if the user is authenticated
			if (!user) {
				console.log('❌ User not authenticated, redirecting to login');
				router.push('/login');
				return null;
			}

			console.log('🔄 About to call createNewConversationApi...');
			// Use our utility function
			const newId = await createNewConversationApi();
			console.log('✅ New conversation created:', newId);
			return newId;
		} catch (error: any) {
			console.error('❌ Error creating new conversation:', error);

			if (error.response && error.response.status === 401) {
				router.push('/login');
			}

			return null;
		}
	};

	const scrollToBottom = () => {
		if (messagesContainerRef.current) {
			messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
		}
	};

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	// Redirect to login if user is not authenticated
	useEffect(() => {
		if (!user) {
			router.push('/login');
		}
	}, [user, router]);

	// CRITICAL DEBUG: Track all URL changes and navigation
	useEffect(() => {
		const handlePopState = (event: PopStateEvent) => {
			console.log('🔄 BROWSER NAVIGATION DETECTED:', {
				timestamp: new Date().toISOString(),
				newUrl: window.location.pathname,
				conversationId: conversationId,
				currentConversationId: currentConversationId,
				event: event
			});
		};

		window.addEventListener('popstate', handlePopState);
		
		// Log current URL state
		console.log('🌐 URL STATE MONITOR ACTIVE:', {
			currentUrl: window.location.pathname,
			conversationId: conversationId,
			currentConversationId: currentConversationId
		});

		return () => {
			window.removeEventListener('popstate', handlePopState);
		};
	}, [conversationId, currentConversationId]);

	// Add this effect for auto-sliding on page load
	useEffect(() => {
		// Show the credit tracker immediately when page loads
		setIsCreditTrackerVisible(true);

		// Hide it after 3 seconds
		const timer = setTimeout(() => {
			setIsCreditTrackerVisible(false);
		}, 3000);

		// Cleanup timer on component unmount
		return () => clearTimeout(timer);
	}, []); // Empty dependency array means this runs once on mount

	const handleSendMessage = async () => {
		if (!inputValue.trim() && selectedFiles.length === 0) return;

		// Check if user is at message limit
		if (usageStats && !user?.is_premium) {
			const dailyRemaining = usageStats.remaining?.chat_messages_today || 0
			const monthlyRemaining = usageStats.remaining?.chat_messages_this_month || 0

			if (dailyRemaining <= 0 || monthlyRemaining <= 0) {
				setShowUpgradePrompt(true)
				return
			}
		}

		// Check if user is authenticated
		if (!user) {
			router.push('/login');
			return;
		}

		
		
		let workingConversationId = conversationId === 'new-chat' ? 'new-chat' : (currentConversationId || conversationId);
		let isNewConversation = false;
		console.log('🔍 Conversation setup - currentConversationId:', currentConversationId, 'URL conversationId:', conversationId, 'workingConversationId:', workingConversationId);
		console.log('🚨 CRITICAL DEBUG - Message send triggered:', {
			timestamp: new Date().toISOString(),
			urlConversationId: conversationId,
			currentConversationId: currentConversationId,
			workingConversationId: workingConversationId,
			isNewChatMode: conversationId === 'new-chat',
			willCreateNewConversation: workingConversationId === 'new-chat'
		});
		
		
		// Do NOT create new conversations for existing conversation IDs
		if (workingConversationId === 'new-chat') {
			console.log('🆕 Creating new conversation (new-chat mode)...');
			const newId = await createNewConversation();
			if (!newId) {
				console.log('⚠️ Upfront conversation creation failed, backend will create it during message processing');
			} else {
				workingConversationId = newId;
				setCurrentConversationId(newId); // Update state immediately
				isNewConversation = true;
				console.log('✅ Upfront conversation created:', newId, 'isNewConversation:', isNewConversation);
			}
		} else {
			// For existing conversations, ensure state is synchronized
			if (conversationId && conversationId !== 'new-chat' && conversationId !== currentConversationId) {
				console.log('📌 Synchronizing existing conversation:', conversationId);
				setCurrentConversationId(conversationId);
				workingConversationId = conversationId;
			}
		}

		const attachments = selectedFiles.map(file => {
			// For audio files with S3 URLs, use that URL directly
			if (file.type === 'audio' && file.s3Url) {
				return {
					type: file.type,
					url: file.s3Url,
					name: file.file.name
				};
			}

			// For other files, use the previewUrl or create a blob URL
			return {
				type: file.type,
				url: file.previewUrl || URL.createObjectURL(file.file),
				name: file.file.name
			};
		});

		const userMessage: Message = {
			id: generateUniqueId(),
			type: 'user',
			content: inputValue.trim(),
			timestamp: new Date().toISOString(),
			attachments: attachments.length > 0 ? attachments : undefined
		};

		// Save the input before clearing it
		const currentInput = inputValue.trim();

		// Update UI immediately
		setMessages(prev => [...prev, userMessage]);
		setInputValue('');
		setSelectedFiles([]);

		// Show typing indicator
		setIsTyping(true);

		// Scroll to bottom to show the loader
		setTimeout(() => {
			scrollToBottom();
		}, 0);

		try {
			// Prepare the message for the AI
			let messageForAI = currentInput;

			// If there are attachments, include file information in the message
			if (attachments.length > 0) {
				const fileTypes = attachments.map(file => file.type).join(', ');
				const fileNames = attachments.map(file => file.name).join(', ');
				// messageForAI = `[User has uploaded ${attachments.length} ${attachments.length > 1 ? 'files' : 'file'}: ${fileNames} (Types: ${fileTypes})] ${messageForAI}`;
			}

			let response: any;

			if (isHealthMode) {
				// Track health mode usage for analytics
				// Use FastAPI talk service with health context
				const files = selectedFiles.map(file => file.file);
				
				// DEBUG: Log conversation ID before sending to backend (health)
				const conversationIdToSend = workingConversationId !== 'new-chat' ? parseInt(workingConversationId) : undefined;
				console.log('🔍 SENDING TO BACKEND (HEALTH):', {
					messageForAI: messageForAI.substring(0, 50) + '...',
					workingConversationId,
					conversationIdToSend,
					currentConversationId,
					urlConversationId: conversationId
				});

				response = await sendHealthMessage(
					messageForAI,
					conversationIdToSend,
					{}, // health context can be added here if needed
					files.length > 0 ? files : undefined
				);

				// Handle FastAPI response (same as normal mode)
				if (response.data && response.data.success) {
					// FastAPI returns content field for the AI response
					const responseContent = response.data.content || response.data.response;

					if (responseContent) {
						const aiResponse: Message = {
							id: response.data.message_id?.toString() || generateUniqueId(),
							type: 'ai',
							content: responseContent,
							timestamp: new Date().toISOString()
						};

						setMessages(prev => [...prev, aiResponse]);

						// FIX: Always sync with backend conversation ID for consistency
						if (response.data.conversation_id) {
							const backendConversationId = response.data.conversation_id.toString();
							console.log('📥 Backend provided conversation_id (health):', backendConversationId, 'Current URL param:', conversationId, 'Working ID:', workingConversationId);
							
							// Always update state to match backend
							setCurrentConversationId(backendConversationId);
							
							// Only trigger URL update if we're transitioning from new-chat
							if (conversationId === 'new-chat' && backendConversationId !== conversationId) {
								isNewConversation = true;
								workingConversationId = backendConversationId;
								console.log('🔄 Set isNewConversation=true to trigger URL update from new-chat to:', backendConversationId);
							}
						}

						// Handle special reminder actions if present
						if (response.data.ai_agent_action === 'reminder_created') {
							console.log('✅ Reminder created:', response.data.reminder_info);
						} else if (response.data.ai_agent_action === 'reminder_failed') {
							console.log('❌ Reminder creation failed:', response.data.error);
						}
					}
				}

				// Trigger credit refresh since credits were consumed
				triggerCreditRefresh();
			} else {
				// Use FastAPI regular chat service
				const files = selectedFiles.map(file => file.file);

				// DEBUG: Log conversation ID before sending to backend
				const conversationIdToSend = workingConversationId !== 'new-chat' ? parseInt(workingConversationId) : undefined;
				console.log('🔍 SENDING TO BACKEND:', {
					messageForAI: messageForAI.substring(0, 50) + '...',
					workingConversationId,
					conversationIdToSend,
					currentConversationId,
					urlConversationId: conversationId
				});

				response = await sendChatMessage(
					messageForAI,
					conversationIdToSend,
					files.length > 0 ? files : undefined
				);

				// Handle FastAPI response
				if (response.data && response.data.success) {
					// FastAPI returns content field for the AI response
					const responseContent = response.data.content || response.data.response;

					if (responseContent) {
						const aiResponse: Message = {
							id: response.data.message_id?.toString() || generateUniqueId(),
							type: 'ai',
							content: responseContent,
							timestamp: new Date().toISOString()
						};

						setMessages(prev => [...prev, aiResponse]);

						//  FIX: Always sync with backend conversation ID for consistency
						if (response.data.conversation_id) {
							const backendConversationId = response.data.conversation_id.toString();
							console.log('📥 Backend provided conversation_id:', backendConversationId, 'Current URL param:', conversationId, 'Working ID:', workingConversationId);
							
							// Always update state to match backend
							setCurrentConversationId(backendConversationId);
							
							// Only trigger URL update if we're transitioning from new-chat
							if (conversationId === 'new-chat' && backendConversationId !== conversationId) {
								isNewConversation = true;
								workingConversationId = backendConversationId;
								console.log('🔄 Set isNewConversation=true to trigger URL update from new-chat to:', backendConversationId);
							}
						}

						// Handle special reminder actions if present
						if (response.data.ai_agent_action === 'reminder_created') {
							console.log('✅ Reminder created:', response.data.reminder_info);
						} else if (response.data.ai_agent_action === 'reminder_failed') {
							console.log('❌ Reminder creation failed:', response.data.error);
						}
					}
				}

				// Trigger credit refresh since credits were consumed
				triggerCreditRefresh();
			}

			setIsTyping(false);

			if (isNewConversation) {
				console.log('🔥 URL Update: Transitioning from new-chat to conversation', workingConversationId);
				
				// CRITICAL FIX: Use Next.js router instead of window.history to properly update route parameters
				router.replace(`/talk/conversation/${workingConversationId}`);
				
				console.log('✅ URL Update: Successfully updated to', `/talk/conversation/${workingConversationId}`);
			} else {
				console.log('⚠️ URL Update: Skipped (isNewConversation is false)');
			}

			// Refresh usage stats after sending
			await fetchUsageStats()
		} catch (error) {
			setIsTyping(false);

			// Show error message based on error type
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else if (axios.isAxiosError(error) && error.response?.status === 402) {
				// Credit-related error (Payment Required) - Don't log as console error since this is expected behavior
				const errorData = error.response.data;
				let creditErrorMessage = "Insufficient credits to continue.";

				if (errorData && errorData.message) {
					creditErrorMessage = errorData.message;
				}

				// Add credit error message to chat with upgrade/purchase options
				const aiErrorMessage: Message = {
					id: generateUniqueId(),
					type: 'ai',
					content: creditErrorMessage,
					timestamp: new Date().toISOString()
				};

				setMessages(prev => [...prev, aiErrorMessage]);

				// Trigger credit refresh to update displays
				triggerCreditRefresh();
			} else if (axios.isAxiosError(error) && error.response?.status === 403) {
				// Elite subscription required error
				const errorData = error.response.data;
				let upgradeMessage = "This feature requires an Elite subscription. Upgrade to access all premium features and get 3,000 monthly credits.";

				if (errorData && errorData.message) {
					upgradeMessage = errorData.message;
				}

				const aiErrorMessage: Message = {
					id: generateUniqueId(),
					type: 'ai',
					content: upgradeMessage,
					timestamp: new Date().toISOString()
				};

				setMessages(prev => [...prev, aiErrorMessage]);
			} else {
				// Log unexpected errors to console for debugging
				console.error('Error fetching AI response:', error);
				
				// Add generic error message to chat based on mode
				let errorMessage = "Error sending message. Please try again.";
				if (isHealthMode) {
					errorMessage = "Sorry, I couldn't access your health records right now. Please try again or contact support if the issue persists.";
				}

				const aiErrorMessage: Message = {
					id: generateUniqueId(),
					type: 'ai',
					content: errorMessage,
					timestamp: new Date().toISOString()
				};

				setMessages(prev => [...prev, aiErrorMessage]);
			}
		}
	};

	const fetchHistory = async () => {
		try {
			// Check if the user is authenticated
			if (!user) {
				console.error('User not authenticated');
				router.push('/login');
				return false;
			}

			const userId = user.id;

			// Make sure the userId is valid
			if (!userId) {
				console.error('No user ID provided');
				return;
			}

			// Use our new utility function
			const formattedHistory = await fetchConversationHistory(userId.toString());

			// Update the history state
			setHistory(formattedHistory);
			// Also update filteredHistory
			setFilteredHistory(formattedHistory);
			// Show the history sidebar
			setShowHistory(true);
		} catch (error: any) {
			console.error('Error fetching conversation history:', error);

			if (error.response?.status === 401) {
				router.push('/login');
			}
		}
	}

	const fetchBookmarks = async () => {
		try {
			// Check if the user is authenticated
			if (!user) {
				console.error('User not authenticated');
				router.push('/login');
				return;
			}

			// Use our new utility function
			const formattedBookmarks = await fetchBookmarksApi();

			// Update the bookmarks state
			setBookmarks(formattedBookmarks);
			// Show the bookmarks sidebar
			setShowBookmarks(true);
		} catch (error: any) {
			console.error('Error fetching bookmarks:', error);

			if (error.response?.status === 401) {
				router.push('/login');
			} else {
				toast.error('Failed to load bookmarks. Please try again.');
			}
		}
	};

	useEffect(() => {
		// Messages updated
	}, [messages]);

	const handleLike = async (messageId: string, isLike: boolean) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Update UI immediately for better user experience
			setMessages(messages.map(msg =>
				msg.id === messageId
					? { 
						...msg, 
						liked: isLike ? true : false, 
						disliked: isLike ? false : true 
					}
					: msg
			));

			// Use our utility function and get updated message data
			const updatedMessage = await handleMessageReaction(messageId, isLike);

			// Update the message with the server response data to ensure consistency
			if (updatedMessage && updatedMessage.reaction) {
				setMessages(messages.map(msg =>
					msg.id === messageId
						? {
							...msg,
							liked: updatedMessage.reaction.liked,
							disliked: updatedMessage.reaction.disliked
						}
						: msg
				));
			}
		} catch (error: any) {
			console.error('Error saving reaction:', error);

			// Revert UI change if there was an error
			if (error.response && error.response.status === 401) {
				router.push('/login');
			} else {
				// Refresh messages from the server to get the correct state
				if (conversationId && conversationId !== 'new') {
					loadConversationMessages(conversationId);
				}
			}
		}
	};

	const handleBookmark = async (message: Message) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Use our utility function
			await bookmarkMessage(message.id);

			// Add to local bookmarks
			const bookmark: Bookmark = {
				...message,
				bookmarkedAt: new Date().toISOString()
			};
			setBookmarks(prev => [...prev, bookmark]);

			// Refresh bookmarks
			fetchBookmarks();
		} catch (error: any) {
			console.error('Error bookmarking message:', error);
			if (error.response && error.response.status === 401) {
				router.push('/login');
			}
		}
	};

	const handleRetry = async (messageId: string) => {
		// Find the AI message to retry
		const aiMessage = messages.find(m => m.id === messageId && m.type === 'ai');
		if (!aiMessage) return;

		// Find the user message that came before this AI message
		const userMessageIndex = messages.findIndex(m => m.id === messageId) - 1;
		if (userMessageIndex < 0) return;

		const userMessage = messages[userMessageIndex];
		if (!userMessage || userMessage.type !== 'user') return;

		// Set the message to loading state
		setIsTyping(true);
		setMessages(prev => prev.map(msg =>
			msg.id === messageId
				? { ...msg, content: '' }
				: msg
		));

		try {
			// Use our utility function
			const newResponse = await retryAiMessage(
				messageId,
				userMessage.content,
				conversationId,
				userMessage.attachments
			);

			// Update the AI message with the new response
			setMessages(prev => prev.map(msg =>
				msg.id === messageId
					? {
						...msg,
						content: newResponse,
						liked: false,
						disliked: false
					}
					: msg
			));
			setIsTyping(false);
			
			// Trigger credit refresh since credits were consumed for retry
			triggerCreditRefresh();
		} catch (error) {
			console.error('Error retrying message:', error);

			// Revert to original message on error
			setMessages(prev => prev.map(msg =>
				msg.id === messageId
					? aiMessage
					: msg
			));
			setIsTyping(false);

			// Handle different error types
			if (axios.isAxiosError(error)) {
				if (error.response?.status === 401) {
					router.push('/login');
				} else if (error.response?.status === 402) {
					// Credit-related error - credits might have been checked but not deducted
					// Refresh credits to show current state
					triggerCreditRefresh();
				} else if (error.response?.status !== 402 && error.response?.status !== 401) {
					// For other errors that might have occurred after credit deduction,
					// refresh credits to ensure UI is in sync
					triggerCreditRefresh();
				}
			}
		}
	};

	// Define allowed file types
	const IMAGE_TYPES = [
		'image/jpeg', 
		'image/jpg', 
		'image/png', 
		'image/gif', 
		'image/webp',
		'image/svg+xml'
	];
	
	const TEXT_BASED_TYPES = [
		'text/plain',
		'application/pdf',
		'application/msword',
		'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		'application/rtf',
		'text/markdown',
		'text/csv',
		'application/json',
		'application/xml',
		'text/xml',
		'text/html'
	];
	
	// Maximum number of files allowed
	const MAX_FILES = 5;
	
	const handleFileUpload = (files: File[], imageDescriptions?: Record<string, string>) => {
		// Check if adding these files would exceed the maximum
		if (selectedFiles.length >= MAX_FILES) {
			toast.error(`You can only upload a maximum of ${MAX_FILES} files at once.`);
			return;
		}
		
		// Filter to only allow image and text-based files
		const validFiles = files.filter(file => 
			IMAGE_TYPES.includes(file.type) || TEXT_BASED_TYPES.includes(file.type)
		);
		
		// Show error if some files were filtered out due to type
		if (validFiles.length < files.length) {
			toast.error('Some files were not added. Only image and text-based files are allowed.');
		}
		
		// Enforce the maximum file limit
		const availableSlots = MAX_FILES - selectedFiles.length;
		const filesToAdd = validFiles.slice(0, availableSlots);
		
		// Show warning if some files were cut off due to the limit
		if (filesToAdd.length < validFiles.length) {
			toast.error(`Only ${availableSlots} more files could be added due to the ${MAX_FILES} file limit.`);
		}
		
		const newFiles: SelectedFile[] = filesToAdd.map(file => ({
			file,
			type: IMAGE_TYPES.includes(file.type) ? 'image' : 'file',
			previewUrl: IMAGE_TYPES.includes(file.type) ? URL.createObjectURL(file) : undefined,
			description: IMAGE_TYPES.includes(file.type) && imageDescriptions && imageDescriptions[file.name]
				? imageDescriptions[file.name]
				: undefined
		}));
		setSelectedFiles(prev => [...prev, ...newFiles]);
	};

	const removeSelectedFile = (index: number) => {
		setSelectedFiles(prev => {
			const newFiles = [...prev];
			// Revoke the URL if it's an image
			if (newFiles[index].previewUrl) {
				URL.revokeObjectURL(newFiles[index].previewUrl!);
			}
			newFiles.splice(index, 1);
			return newFiles;
		});
	};

	const openUploadModal = (type: 'file' | 'image' | 'book-generator' | 'enhanced-book-generator') => {
		if (type === 'book-generator') {
			setIsBookCreationModalOpen(true);
			return;
		}

		if (type === 'enhanced-book-generator') {
			setIsEnhancedBookModalOpen(true);
			return;
		}

		setUploadType(type as 'file' | 'image');
		setUploadModalOpen(true);
	};

	const userId = user?.id;

	// Fetch bookmarks and history when the component loads and user is authenticated
	useEffect(() => {
		const userId = user?.id;

		if (user && userId) {
			// Fetch initial data silently (without showing alerts)
			const fetchInitialData = async () => {
				try {
					// Fetch bookmarks using FastAPI utility
					const bookmarksData = await fetchBookmarksApi();

					if (bookmarksData && Array.isArray(bookmarksData)) {
						const formattedBookmarks = bookmarksData.map(conversation => {
							return {
								id: conversation.id.toString(),
								content: conversation.title || `Conversation ${conversation.id}`,
								type: 'ai' as 'user' | 'ai',
								timestamp: conversation.updated_at,
								bookmarkedAt: conversation.updated_at
							};
						});

						setBookmarks(formattedBookmarks);
					}

					// Fetch history
					const historyResponse = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/${userId}/conversations`, {
						withCredentials: true
					});

					if (historyResponse.data && Array.isArray(historyResponse.data)) {
						// Group conversations by date
						const groupedByDate = historyResponse.data.reduce((acc, conversation) => {
							// Convert the date string to a date object
							const date = new Date(conversation.created_at);
							// Format the date for grouping (YYYY-MM-DD)
							const dateStr = date.toISOString().split('T')[0];

							// Check if we already have this date in our accumulator
							if (!acc[dateStr]) {
								acc[dateStr] = [];
							}

							// Add the conversation to the accumulator with its ID
							acc[dateStr].push({
								id: conversation.id,
								title: conversation.title || `Conversation ${conversation.id}`
							});

							return acc;
						}, {});

						// Convert the grouped data to the format expected by our history state
						const formattedHistory = Object.keys(groupedByDate).map(date => {
							// Format the date for display
							const displayDate = new Date(date).toLocaleDateString('en-US', {
								weekday: 'long',
								month: 'short',
								day: 'numeric'
							});

							return {
								date: displayDate,
								conversations: groupedByDate[date]
							};
						});

						setHistory(formattedHistory);
						// Also update filteredHistory
						setFilteredHistory(formattedHistory);
					}
				} catch (error) {
					// Just log errors, don't show alerts
					console.error('Error fetching initial data:', error);
				}
			};

			fetchInitialData();
		}
	}, [user, userId]);

	// Function to load messages for a selected conversation
	const loadConversationMessages = useCallback(async (selectedConversationId: string | number) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				console.error('User not authenticated');
				router.push('/login');
				return false;
			}

			const userId = user.id;

			// Make sure the userId is valid
			if (!userId) {
				console.error('No user ID provided');
				return false;
			}

			// If we're already viewing this conversation and have messages, don't reload
			if (conversationId && conversationId === selectedConversationId.toString() && messages.length > 0) {
				return true;
			}

			// Set loading state while fetching messages
			setIsTyping(true);

			// Use our utility function
			const { messages: formattedMessages, isBookmarked: bookmarkStatus } =
				await loadConversationMessagesApi(selectedConversationId);

			// Update the messages state
			setMessages(formattedMessages);

			// Update bookmark status
			setIsBookmarked(bookmarkStatus);

			// Update URL if it's not already correct
			if (params.conversationId !== selectedConversationId.toString()) {
				router.push(`/talk/conversation/${selectedConversationId}`);
			}

			// Clear loading state
			setIsTyping(false);

			// Scroll to the bottom after messages are loaded
			setTimeout(() => {
				scrollToBottom();
			}, 0);

			return true;
		} catch (error: any) {
			console.error('Error loading conversation messages:', error);
			setIsTyping(false);

			if (error.response && error.response.status === 401) {
				router.push('/login');
			}

			return false;
		}
	}, [user, conversationId, messages.length, router, params.conversationId]);

	// Load the current conversation's messages when the component mounts
	useEffect(() => {
		// Only load if we have a valid conversationId (not 'new')
		if (user && conversationId && conversationId !== 'new-chat') {
			loadConversationMessages(conversationId);

			// Check if conversation is bookmarked
			if (conversationId !== 'new-chat') {
				const checkBookmarkStatus = async () => {
					try {
						const response = await axios.get(`${FASTAPI_BASE_URL}/api/conversations/${conversationId}`, {
							withCredentials: true
						});
						setIsBookmarked(response.data.is_bookmarked || false);
					} catch (error) {
						console.error('Error checking bookmark status:', error);
					}
				};

				checkBookmarkStatus();
			}
		}
	}, [user, conversationId]);

	// Clear messages when switching to a new chat
	useEffect(() => {
		if (conversationId === 'new-chat') {
			setMessages([]);
			setSelectedFiles([]);
			setIsTyping(false);
			setIsBookmarked(false);
			setInputValue('');
			document.title = 'New Chat';
		}
	}, [conversationId]);

	// Add a separate useEffect to listen for URL changes specifically
	useEffect(() => {
		// This will run when the component mounts or when conversationId changes
		if (conversationId && conversationId !== 'new-chat') {
			// If URL changes to a specific conversation, load its messages
			// But only if we don't have messages yet (initial load)
			if (messages.length === 0) {
				loadConversationMessages(conversationId);
			}
		}
	}, [conversationId, messages.length, loadConversationMessages]);

	const toggleConversationBookmark = async () => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Check if we have a valid conversationId
			if (!conversationId || conversationId === 'new-chat') {
				return;
			}

			// Immediately update UI for better responsiveness
			const newBookmarkStatus = !isBookmarked;
			setIsBookmarked(newBookmarkStatus);

			// Update bookmarks array immediately for UI consistency
			if (newBookmarkStatus) {
				// Find conversation title from history
				const allConversations = history.flatMap(day => day.conversations);
				const conversation = allConversations.find(conv => conv.id.toString() === conversationId);

				// Add to bookmarks
				const newBookmark: Bookmark = {
					id: conversationId,
					content: conversation?.title || `Conversation ${conversationId}`,
					type: 'ai',
					timestamp: new Date().toISOString(),
					bookmarkedAt: new Date().toISOString()
				};
				setBookmarks(prev => [...prev, newBookmark]);
			} else {
				// Remove from bookmarks
				setBookmarks(prev => prev.filter(bookmark => bookmark.id !== conversationId));
			}

			// Call the API to toggle bookmark status
			const response = await axios.post(
				`${FASTAPI_BASE_URL}/api/conversations/${conversationId}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Update the local state with the response (in case server response differs)
			setIsBookmarked(response.data.is_bookmarked);

			// Show toast notification
			if (response.data.is_bookmarked) {
				toast.success('Conversation bookmarked');
			} else {
				toast.success('Bookmark removed');
			}

			// Fetch updated bookmarks from server to ensure data consistency
			fetchBookmarks();
		} catch (error: any) {
			console.error('Error in bookmark operation:', error);
			if (error.response && error.response.status === 401) {
				router.push('/login');
			} else {
				toast.error('Failed to update bookmark');
				// Revert UI changes on error
				setIsBookmarked(!isBookmarked);
				fetchBookmarks();
			}
		}
	};

	// Function to handle conversation deletion
	const handleDeleteConversation = async (conversationId: number) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Call the API to delete the conversation
			await axios.delete(`${FASTAPI_BASE_URL}/api/conversations/${conversationId}`, {
				withCredentials: true
			});

			// Remove the conversation from history
			setHistory(prevHistory => {
				return prevHistory.map(day => {
					return {
						...day,
						conversations: day.conversations.filter(conv => conv.id !== conversationId)
					};
				}).filter(day => day.conversations.length > 0);
			});

			// If we're currently viewing this conversation, redirect to a new chat
			if (params.conversationId === conversationId.toString()) {
				router.push('/talk/conversation/new-chat');
			}
		} catch (error) {
			console.error('Error deleting conversation:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else if (axios.isAxiosError(error) && error.response?.status !== 404) {
				// Show error message only if it's not a 404 (already deleted)
				toast.error('Failed to delete conversation. Please try again.');
			}
		}
	};

	// Function to handle conversation bookmark toggle
	const handleBookmarkConversationFromHistory = async (conversationId: number) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Call the API to toggle bookmark status
			const response = await axios.post(
				`${FASTAPI_BASE_URL}/api/conversations/${conversationId}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Show appropriate toast notification based on bookmark status
			if (response.data.is_bookmarked) {
				toast.success('Conversation bookmarked');

				// Immediately add to bookmarks array for UI update
				const newBookmark: Bookmark = {
					id: conversationId.toString(),
					content: history.flatMap(day => day.conversations).find(conv => conv.id === conversationId)?.title || `Conversation ${conversationId}`,
					type: 'ai',
					timestamp: new Date().toISOString(),
					bookmarkedAt: new Date().toISOString()
				};
				setBookmarks(prev => [...prev, newBookmark]);
			} else {
				toast.success('Bookmark removed');

				// Immediately remove from bookmarks array for UI update
				setBookmarks(prev => prev.filter(bookmark => bookmark.id !== conversationId.toString()));
			}

			// Update the UI if this is the current conversation
			if (params.conversationId === conversationId.toString()) {
				setIsBookmarked(response.data.is_bookmarked || false);
			}

			// Also fetch bookmarks from server to ensure data consistency
			fetchBookmarks();
		} catch (error) {
			console.error('Error bookmarking conversation:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				toast.error('Failed to update bookmark');
			}
		}
	};

	// Function to handle conversation rename
	const handleRenameConversation = async (conversationId: number) => {
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return;
			}

			// Set saving state to show loading indicator
			setIsSaving(String(conversationId));

			// Call the API to update the conversation title
			await axios.put(
				`${FASTAPI_BASE_URL}/api/conversations/${conversationId}`,
				{
					title: newTitle
				},
				{
					withCredentials: true
				}
			);

			// Update the conversation title in both history and filteredHistory
			const updateConversationTitle = (prevState: HistoryDay[]) => {
				return prevState.map(day => {
					return {
						...day,
						conversations: day.conversations.map(conv => {
							if (conv.id === conversationId) {
								return {
									...conv,
									title: newTitle
								};
							}
							return conv;
						})
					};
				});
			};

			setHistory(prevHistory => updateConversationTitle(prevHistory));
			setFilteredHistory(prevFiltered => updateConversationTitle(prevFiltered));

			// Reset renaming state
			setIsRenaming(null);
			setNewTitle('');

			// Show toast notification
			toast.success('Conversation renamed');

			// If this is the current conversation, update the document title too
			if (params.conversationId === String(conversationId)) {
				document.title = newTitle;
			}

			// No need to refresh the history panel as we've already updated the state
			// This prevents the sidebar from closing
		} catch (error) {
			console.error('Error renaming conversation:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				toast.error('Failed to rename conversation');
			}
		} finally {
			// Clear saving state regardless of success or failure
			setIsSaving(null);
		}
	};

	// Close dropdown when clicking outside
	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (dropdownOpen !== null && !(event.target as Element).closest('.dropdown-menu')) {
				setDropdownOpen(null);
			}

			// Close rename input when clicking outside
			if (isRenaming !== null && !(event.target as Element).closest('.rename-input')) {
				setIsRenaming(null);
				setNewTitle('');
			}
		};

		document.addEventListener('mousedown', handleClickOutside);
		return () => {
			document.removeEventListener('mousedown', handleClickOutside);
		};
	}, [dropdownOpen, isRenaming]);

	// Filter history based on search query
	useEffect(() => {
		if (!searchQuery.trim()) {
			setFilteredHistory(history);
			return;
		}

		const query = searchQuery.toLowerCase();
		const filtered = history.map(day => {
			const filteredConversations = day.conversations.filter(conversation =>
				conversation.title.toLowerCase().includes(query)
			);

			return {
				...day,
				conversations: filteredConversations
			};
		}).filter(day => day.conversations.length > 0);

		setFilteredHistory(filtered);
	}, [searchQuery, history]);

	// Handle clear history
	const handleClearHistory = async () => {
		if (!user) {
			router.push('/login');
			return;
		}

		// Open confirmation dialog instead of using window.confirm
		setConfirmDialogOpen(true);
	};

	// Function to handle removing a bookmark from the sidebar
	const handleRemoveBookmark = async (bookmark: Bookmark, index: number) => {
		try {
			// Immediately update UI for better responsiveness
			// Remove from bookmarks array
			setBookmarks(prev => prev.filter((_, i) => i !== index));

			// Update current conversation bookmark state if applicable
			if (params.conversationId === bookmark.id) {
				setIsBookmarked(false);
			}

			// Make API call to update bookmark status in the database
			await axios.post(
				`${FASTAPI_BASE_URL}/api/conversations/${bookmark.id}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Show toast notification
			toast.success('Bookmark removed');

			// Fetch updated bookmarks from server to ensure data consistency
			fetchBookmarks();
		} catch (error) {
			console.error('Error removing bookmark:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				toast.error('Failed to remove bookmark');
				// Revert UI changes on error by refreshing bookmarks
				fetchBookmarks();
			}
		}
	};

	// Function to perform the actual history clearing
	const performClearHistory = async () => {
		try {
			// Show loading toast
			toast.loading('Clearing conversation history...');

			// Call the API to clear all conversations first
			await axios.delete(`${FASTAPI_BASE_URL}/api/user/${user?.id}/conversations`, {
				withCredentials: true
			});

			// If API call succeeds, then update the UI
			// Clear the history state
			setHistory([]);
			setFilteredHistory([]);

			// If we're currently viewing a conversation, redirect to a new chat
			if (conversationId !== 'new-chat') {
				setMessages([]);
				router.push('/talk/conversation/new-chat');
			}

			// Close the confirmation dialog
			setConfirmDialogOpen(false);

			// Show success toast
			toast.success('Conversation history cleared successfully!');
		} catch (error) {
			console.error('Error clearing history:', error);

			// Show error toast
			toast.error('Failed to clear conversation history. Please try again.');

			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			}
		}
	};

	// Function to clear chat messages and reset state
	const clearChat = useCallback(() => {
		setMessages([]);
		setSelectedFiles([]);
		setIsTyping(false);
		setIsBookmarked(false);
		setInputValue('');
		document.title = 'New Chat';
	}, []);

	// Define the hero images
	const heroImages = [
		'/assets/talk-hero.webp',
		'/assets/talk-hero-1.webp',
		'/assets/talk-hero-2.webp',
		'/assets/talk-hero-3.webp'
	];

	// Toggle health mode function
	const toggleHealthMode = () => {
		const newHealthMode = !isHealthMode;
		setIsHealthMode(newHealthMode);

		// Show toast notification
		if (newHealthMode) {
			// Show success message for health mode activation
			console.log('Health Mode Activated: Enhanced AI will now access your pet\'s care history');
		} else {
			// Show info message for health mode deactivation
			console.log('Health Mode Deactivated: Switched back to general chat');
		}
	};

	// Fetch usage stats
	const fetchUsageStats = async () => {
		try {
			const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/usage/status`, {
				credentials: 'include'
			})
			if (response.ok) {
				const data = await response.json()
				setUsageStats(data.data)
			}
		} catch (error) {
			console.error('Error fetching usage stats:', error)
		}
	}

	useEffect(() => {
		if (user) {
			fetchUsageStats()
		}
	}, [user])

	// Handle voice message
	const handleVoiceMessage = (file: File, transcription: string) => {
		// Check if file has an S3 URL (from our enhanced File type)
		const fileWithS3 = file as File & { s3Url?: string };

		// Create a selected file object
		const voiceFile: SelectedFile = {
			file,
			type: 'audio',
			description: transcription,
			previewUrl: fileWithS3.s3Url || URL.createObjectURL(file)
		};

		// Add to selected files
		setSelectedFiles(prev => [...prev, voiceFile]);

		// Don't auto-fill the input field with transcription
	};

	return (
		<div className="flex flex-col min-h-screen bg-black">
			{/* Sliding Credit Tracker */}
			<div
				className={`fixed right-0 top-1/2 -translate-y-1/2 transform transition-transform duration-300 cursor-pointer z-50 ${isCreditTrackerVisible ? 'translate-x-0' : 'translate-x-[calc(100%-8px)]'
					}`}
				onMouseEnter={() => setIsCreditTrackerVisible(true)}
				onMouseLeave={() => setIsCreditTrackerVisible(false)}
			>
				<div className="bg-neutral-800 rounded-l-lg shadow-lg p-4 flex flex-col items-center">
					{/* Bookmark icon that's visible when panel is open */}
					<div className={`absolute left-4 top-4 transition-opacity duration-300 ${isCreditTrackerVisible ? 'opacity-100' : 'opacity-0'}`}>
						<PiBookmarkFill className="w-5 h-5 text-[var(--mrwhite-primary-color)]" />
					</div>

					{/* Bookmark icon that's visible when panel is closed */}
					<div className={`absolute left-0 top-1/4 -translate-y-1/2 -translate-x-[calc(100%-1px)] bg-[var(--mrwhite-primary-color)] p-1 rounded-l-md transition-opacity duration-300 ${isCreditTrackerVisible ? 'opacity-0' : 'opacity-100'}`}>
						<PiBookmarkFill className="w-5 h-5 max-[900px]:w-3 max-[900px]:h-3 text-black" />
					</div>

					<CreditTracker compact={true} showPurchaseOptions={false} />
					{/* {usageStats && !user?.is_premium && (
						<UsageTracker
							feature="chat"
							currentUsage={usageStats.usage?.chat_messages_today || 0}
							maxUsage={10}
							className="mt-4 w-full"
						/>
					)} */}
				</div>
			</div>

			{/* Hero Section */}
			<HeroSection
				title="Talk with Mr. White"
				subtitle="Ask Mr. White a question and answers shall be given."
				images={heroImages}
			/>

			{/* SECTION 2 */}
			<section className="min-h-screen px-2 md:px-0 max-w-[800px]:px-24 mb-20 flex flex-col justify-center items-center mt-20">

				{/* Header */}
				<ChatHeader
					fetchBookmarks={fetchBookmarks}
					toggleHistory={toggleHistory}
					user={user}
					clearChat={clearChat}
				/>

				<div className={`${messages.length > 0 ? 'min-h-[300px] md:min-h-[450px]' : ''} w-full max-w-7xl bg-neutral-950 flex flex-col justify-between gap-4 md:gap-8 p-4 md:p-8`}>

					{/* Chat Container */}
					{messages.length === 0 && (
						<div className="text-center">
							<h1 className="text-white text-[32px] max-[640px]:text-[24px] max-[400px]:text-[20px] max-[320px]:text-[18px] font-public-sans font-bold mb-4 select-none">
								How can Mr. White help you?
							</h1>
							{isHealthMode && (
								<div className="flex items-center justify-center gap-2 text-red-400 text-lg">
									<Heart className="w-5 h-5 fill-current" />
									<span>Health Mode Active - Ask about your pet's care history</span>
								</div>
							)}
						</div>
					)}

					<div ref={messagesContainerRef} className={`rounded-sm h-[400px] md:h-[292px] space-y-4 overflow-hidden pb-4 pr-4 flex-col gap-y-4 overflow-y-auto custom-scrollbar ${messages.length > 0 || isTyping ? 'flex' : 'hidden'}`}>
						{
							messages.map((message, index) => (
								<Message
									key={`message-${message.id}-${index}-${message.timestamp}`}
									id={message.id}
									content={message.content}
									type={message.type}
									liked={message.liked}
									disliked={message.disliked}
									timestamp={(() => {
										// If the timestamp contains the hardcoded value, use current time instead
										if (message.timestamp && message.timestamp.includes('09:49:28.146600')) {
											return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
										}
										// Handle UTC timestamps properly - ensure consistent display
										if (message.timestamp) {
											// Parse the timestamp as UTC and convert to local time for display
											const utcDate = new Date(message.timestamp);
											// Ensure we're working with a valid date
											if (!isNaN(utcDate.getTime())) {
												return utcDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
											}
										}
										return '';
									})()}
									attachments={message.attachments}
									onCopy={copyToClipboard}
									onLike={handleLike}
									onSpeak={speakText}
									onRetry={handleRetry}
									onDownload={(url, filename, attachmentId) => {
										const downloadFile = async (fileUrl: string, fileName: string, attId?: number) => {
											try {
												// Validate inputs
												if (!fileUrl) {
													console.error('Download failed: URL is undefined or empty');
													toast.error('Download failed: Invalid file URL');
													return;
												}
												
												// Fix URL handling - use backend proxy for S3 URLs to avoid CORS
												let absoluteUrl;
												if (fileUrl.startsWith('https://') && fileUrl.includes('s3.amazonaws.com') && attId) {
													// S3 presigned URL - use backend proxy to avoid CORS issues
													absoluteUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/download/${attId}`;
												} else if (fileUrl.startsWith('http')) {
													// Other HTTP URLs (legacy)
													absoluteUrl = fileUrl;
												} else if (fileUrl.startsWith('blob:')) {
													// Already a blob URL
													absoluteUrl = fileUrl;
												} else if (fileUrl.startsWith('file://')) {
													// Placeholder URL - file not actually stored, show error
													toast.error('File not available for download. This file was uploaded before permanent storage was implemented.');
													return;
												} else {
													// Fallback to relative URL
													absoluteUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}${fileUrl}`;
												}

												// Fetch the file as a blob
												const response = await fetch(absoluteUrl);
												const blob = await response.blob();

												// Create a blob URL and use it for download
												const blobUrl = window.URL.createObjectURL(blob);
												const anchor = document.createElement('a');
												anchor.href = blobUrl;
												anchor.download = fileName || 'download';
												anchor.style.display = 'none';
												document.body.appendChild(anchor);
												anchor.click();

												// Clean up
												setTimeout(() => {
													document.body.removeChild(anchor);
													window.URL.revokeObjectURL(blobUrl);
												}, 100);
											} catch (error) {
												console.error('Error downloading file:', error);
												toast.error('Failed to download file');
											}
										};

										// Execute the download function
										downloadFile(url, filename, attachmentId);
									}}
								/>
							))
						}

						{isTyping && <MessageLoader healthMode={isHealthMode} />}
					</div>

					{/* Chat Controls */}
					<ChatControls
						inputValue={inputValue}
						setInputValue={setInputValue}
						handleSendMessage={handleSendMessage}
						selectedFiles={selectedFiles}
						removeSelectedFile={removeSelectedFile}
						openUploadModal={openUploadModal}
						toggleConversationBookmark={toggleConversationBookmark}
						isBookmarked={isBookmarked}
						isHealthMode={isHealthMode}
						toggleHealthMode={toggleHealthMode}
						placeholder={isHealthMode ? "Ask about your pet's health records, vaccinations, medications..." : "Write your message here ..."}
						onVoiceMessageAdd={handleVoiceMessage}
					/>

				</div>
			</section>

			{/* Sidebars */}
			<Sidebar
				isOpen={showBookmarks}
				onClose={() => setShowBookmarks(false)}
				title="Bookmarks"
				isBookGenerated={false}
			>
				<div className="flex flex-col h-full">
					{/* Bookmarks List */}
					<div className="overflow-y-auto custom-scrollbar flex-1">
						<div className="">
							{bookmarks.map((bookmark, index) => (
								<div
									key={bookmark.id}
									className="p-3 cursor-pointer hover:bg-neutral-800 flex justify-between items-center border-b-2 border-neutral-800"
									onClick={() => {
										loadConversationMessages(bookmark.id);
										setShowBookmarks(false);
									}}
								>
									<p className="text-sm font-public-sans truncate flex-1">
										{bookmark.content}
									</p>
									<div className="relative">
										<button
											onClick={(e) => {
												e.stopPropagation(); // Prevent triggering the parent div's onClick
												handleRemoveBookmark(bookmark, index);
											}}
											className="text-neutral-400 hover:text-white p-1"
										>
											<FiX />
										</button>
									</div>
								</div>
							))}
						</div>
						{bookmarks.length === 0 && (
							<p className="text-center text-neutral-400 mt-4">No bookmarks yet</p>
						)}
					</div>
				</div>
			</Sidebar>
			{/* History Sidebar - Keep this as is since it's quite complex */}
			<Sidebar
				isOpen={showHistory}
				onClose={() => setShowHistory(false)}
				title="History"
				isBookGenerated={false}
				onClearHistory={handleClearHistory}
			>
				<div className="flex flex-col h-full">
					{/* Search */}
					<div className="flex items-center mb-4">
						<div className="relative flex-1">
							<FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400" />
							<input
								type="text"
								placeholder="Search History"
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="w-full bg-neutral-800 rounded-full py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 border-2 border-neutral-700 focus:ring-white/20"
							/>
						</div>
					</div>

					{/* History List */}
					<div className="space-y-6 overflow-y-auto custom-scrollbar flex-1">
						{filteredHistory.map((day, index) => (
							<div key={day.date} className="space-y-3">
								<h3 className="text-lg font-semibold text-neutral-400">
									{day.date}
								</h3>
								<div className="">
									{day.conversations.map((conversation) => (
										<div
											key={conversation.id}
											className="p-3 cursor-pointer hover:bg-neutral-800 flex justify-between items-center border-b-2 border-neutral-800"
										>
											{isRenaming === String(conversation.id) ? (
												<div className="flex items-center w-3/4 rename-input">
													<input
														type="text"
														value={newTitle}
														onChange={(e) => setNewTitle(e.target.value)}
														onKeyDown={(e) => {
															if (e.key === 'Enter') {
																handleRenameConversation(conversation.id);
															} else if (e.key === 'Escape') {
																setIsRenaming(null);
																setNewTitle('');
															}
														}}
														className="bg-neutral-700 text-white px-2 py-1 rounded flex-grow text-sm"
														autoFocus
														onClick={(e) => e.stopPropagation()}
													/>
													<button
														onClick={(e) => {
															e.stopPropagation();
															handleRenameConversation(conversation.id);
														}}
														className="ml-1 p-1 bg-blue-600 hover:bg-blue-700 rounded text-white"
														title="Save"
														disabled={isSaving === String(conversation.id)}
													>
														{isSaving === String(conversation.id) ? (
															<AiOutlineLoading className="w-4 h-4 animate-spin" />
														) : (
															<FiSave className="w-4 h-4" />
														)}
													</button>
												</div>
											) : (
												<p
													className="text-sm font-public-sans truncate flex-1"
													onClick={() => {
														loadConversationMessages(conversation.id);
														setShowHistory(false);
													}}
												>
													{conversation.title}
												</p>
											)}

											<div className="relative dropdown-menu">
												<button
													onClick={(e) => {
														e.stopPropagation();
														setDropdownOpen(dropdownOpen === String(conversation.id) ? null : String(conversation.id));
													}}
													className="text-neutral-400 hover:text-white p-1"
												>
													<FiMoreVertical />
												</button>

												{dropdownOpen === String(conversation.id) && (
													<div className="absolute right-0 mt-1 bg-neutral-800 rounded-md shadow-lg z-10 w-48 py-1 dropdown-menu">
														<button
															onClick={(e) => {
																e.stopPropagation();
																setDropdownOpen(null);
																setIsRenaming(String(conversation.id));
																setNewTitle(conversation.title);
															}}
															className="flex items-center gap-2 px-4 py-2 text-sm text-white hover:bg-neutral-700 w-full text-left"
														>
															<FiEdit className="text-blue-400" />
															Rename
														</button>
														<button
															onClick={(e) => {
																e.stopPropagation();
																setDropdownOpen(null);
																handleBookmarkConversationFromHistory(conversation.id);
															}}
															className="flex items-center gap-2 px-4 py-2 text-sm text-white hover:bg-neutral-700 w-full text-left"
														>
															{bookmarks.some(bookmark => bookmark.id === conversation.id.toString()) ? (
																<BsFillBookmarkCheckFill className="text-green-600" />
															) : (
																<BsBookmarkFill className="text-[var(--mrwhite-primary-color)]" />
															)}
															Bookmark
														</button>
														<button
															onClick={(e) => {
																e.stopPropagation();
																setDropdownOpen(null);
																handleDeleteConversation(conversation.id);
															}}
															className="flex items-center gap-2 px-4 py-2 text-sm text-white hover:bg-neutral-700 w-full text-left"
														>
															<FiTrash2 className="text-red-400" />
															Delete
														</button>
													</div>
												)}
											</div>
										</div>
									))}
								</div>
							</div>
						))}
						{filteredHistory.length === 0 && (
							<p className="text-center text-neutral-400">
								{history.length === 0 ? "No conversation history" : "No matching conversations found"}
							</p>
						)}
					</div>
				</div>
			</Sidebar>

			{/* Upload Dialog */}
			<UploadModal
				isOpen={uploadModalOpen}
				onClose={() => setUploadModalOpen(false)}
				onUpload={handleFileUpload}
				type={uploadType}
			/>

			{/* Confirmation Dialog for Clear History */}
			<ConfirmDialog
				isOpen={confirmDialogOpen}
				onClose={() => setConfirmDialogOpen(false)}
				onConfirm={performClearHistory}
				title="Clear Conversation History"
				message="Are you sure you want to clear all conversation history? This action cannot be undone."
				confirmText="Clear All"
				cancelText="Cancel"
				type="danger"
			/>

			{/* Book Creation Modal */}
			<BookCreationModal
				isOpen={isBookCreationModalOpen}
				onClose={() => setIsBookCreationModalOpen(false)}
				conversationId={conversationId}
			/>

			{/* Enhanced Book Creation Modal */}
			<EnhancedBookCreationModal
				isOpen={isEnhancedBookModalOpen}
				onClose={() => setIsEnhancedBookModalOpen(false)}
				conversationId={conversationId}
			/>

			{/* Premium Gate for Upgrade Prompt */}
			{showUpgradePrompt && (
				<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
					<div className="max-w-md">
						<PremiumGate
							feature="Unlimited AI Chat Messages"
							className="bg-gray-900 border border-gray-700"
						>
							<div />
						</PremiumGate>
						<button
							onClick={() => setShowUpgradePrompt(false)}
							className="mt-4 w-full text-center text-gray-400 hover:text-white"
						>
							Continue with limited messages
						</button>
					</div>
				</div>
			)}

		</div>
	)
}

export default TalkPage;