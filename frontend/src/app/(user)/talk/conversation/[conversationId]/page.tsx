'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
	FiSend,
	FiBookmark,
	FiClock,
	FiX,
	FiPaperclip,
	FiMoreVertical,
	FiTrash2,
	FiEdit,
	FiSearch,
	FiTrash,
} from 'react-icons/fi';
import { Button } from '@/components/ui/button';
import { PiBookmarkBold, PiGlobeHemisphereWestBold, PiInfo, PiBookmarkFill } from 'react-icons/pi';
import { RiVoiceprintFill } from "react-icons/ri";
import { FaPlus } from "react-icons/fa6";
import { InputBox } from '@/components/InputBox';
import Message from '@/components/Message';
import MessageLoader from '@/components/MessageLoader';
import axios from 'axios';
import UploadModal from '@/components/UploadModal';
import SelectedFiles from '@/components/SelectedFiles';
import Sidebar from '@/components/Sidebar';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { IoImageOutline } from 'react-icons/io5';
// Import our new components and utilities
import HeroSection from '@/components/HeroSection';
import ChatHeader from '@/components/ChatHeader';
import ChatControls from '@/components/ChatControls';
import {
	fetchConversationHistory,
	fetchBookmarks as fetchBookmarksApi,
	toggleConversationBookmark as toggleBookmarkApi,
	createNewConversation as createNewConversationApi,
	loadConversationMessages as loadConversationMessagesApi
} from '@/utils/api';
import {
	copyToClipboard,
	speakText,
	handleMessageReaction,
	bookmarkMessage,
	retryAiMessage
} from '@/utils/messageUtils';
import { Heart } from 'lucide-react';
import { EnhancedChatResponse } from '@/types/care-archive';
import ConfirmDialog from '@/components/ConfirmDialog';
import BookGeneratorSidebar from '@/components/BookGeneratorSidebar';
import { UsageTracker } from '@/components/UsageTracker';
import { PremiumGate } from '@/components/PremiumGate';
import { CreditTracker } from '@/components/CreditTracker';
import { ArrowLeft, Menu } from 'lucide-react';
import Image from 'next/image';
import { BsBookmarkFill, BsFillBookmarkCheckFill, BsFillBookmarkXFill } from 'react-icons/bs';

interface Message {
	id: string;
	content: string;
	type: 'user' | 'ai';
	timestamp: Date;
	liked?: boolean;
	disliked?: boolean;
	attachments?: Array<{
		type: 'image' | 'file';
		url: string;
		name: string;
	}>;
}

interface Bookmark extends Message {
	bookmarkedAt: Date;
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
	type: 'file' | 'image';
	previewUrl?: string;
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
	const [currentBgIndex, setCurrentBgIndex] = useState(0);
	const [isHealthMode, setIsHealthMode] = useState(false);
	const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
	const [conversation, setConversation] = useState<Conversation | null>(null);
	const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
	const [isBookGeneratorOpen, setIsBookGeneratorOpen] = useState(false);
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
		if (conversationId && conversationId !== 'new-chat') {
			setCurrentConversationId(conversationId);
		} else {
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
		try {
			// Check if the user is authenticated
			if (!user) {
				router.push('/login');
				return null;
			}

			// Use our utility function
			const newId = await createNewConversationApi();
			return newId;
		} catch (error: any) {
			console.error('Error creating new conversation:', error);

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

	// Background image carousel effect
	useEffect(() => {
		const bgImages = [
			'/assets/talk-hero.webp',
			'/assets/talk-hero-1.webp',
			'/assets/talk-hero-2.webp',
			'/assets/talk-hero-3.webp'
		];

		const interval = setInterval(() => {
			setCurrentBgIndex(prevIndex => (prevIndex + 1) % bgImages.length);
		}, 5001); // Change image every 5 seconds

		return () => clearInterval(interval);
	}, []);

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

		// Get or create conversation ID
		let workingConversationId = currentConversationId || conversationId;
		let isNewConversation = false;
		if (workingConversationId === 'new-chat' || !workingConversationId) {
			const newId = await createNewConversation();
			if (!newId) return; // Failed to create conversation
			workingConversationId = newId;
			setCurrentConversationId(newId); // Update state immediately
			isNewConversation = true;
		}

		const attachments = selectedFiles.map(file => ({
			type: file.type,
			url: file.previewUrl || URL.createObjectURL(file.file),
			name: file.file.name
		}));

		const userMessage: Message = {
			id: Date.now().toString(),
			type: 'user',
			content: inputValue.trim(),
			timestamp: new Date(),
			attachments: attachments.length > 0 ? attachments : undefined
		};

		// Save the input before clearing it
		const currentInput = inputValue.trim();

		// Update UI immediately
		setMessages(prev => [...prev, userMessage]);
		setInputValue('');
		setSelectedFiles([]);
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
				// Use health service for enhanced context-aware responses
				const healthResponse = await axios.post<EnhancedChatResponse>(
					`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/enhanced-chat`,
					{
						message: messageForAI,
						conversation_id: workingConversationId !== 'new-chat' ? parseInt(workingConversationId) : undefined,
						thread_id: workingConversationId
					},
					{
						withCredentials: true
					}
				);

				if (healthResponse.data.success) {
					const aiResponse: Message = {
						id: healthResponse.data.context_info?.conversation_id?.toString() || Date.now().toString(),
						type: 'ai',
						content: healthResponse.data.response,
						timestamp: new Date()
					};

					setMessages(prev => [...prev, aiResponse]);
					response = healthResponse;

					// Update conversation ID from response if we got a new one
					if (healthResponse.data.context_info?.conversation_id && !currentConversationId) {
						const newConvId = healthResponse.data.context_info.conversation_id.toString();
						setCurrentConversationId(newConvId);
						workingConversationId = newConvId;
					}

					// Trigger credit refresh since credits were consumed
					triggerCreditRefresh();
				} else {
					throw new Error('Health service failed to process request');
				}
			} else {
				// Use regular chat service
				const formData = new FormData();
				formData.append('message', messageForAI);
				formData.append('context', attachments.length > 0 ? 'file_upload' : 'chat');
				formData.append('conversationId', workingConversationId);
				selectedFiles.forEach(file => formData.append('attachments', file.file));

				response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/chat`, formData, {
					withCredentials: true
				});

				const aiResponse: Message = {
					id: response.data.aiMessageId.toString(),
					type: 'ai',
					content: response.data.response,
					timestamp: new Date()
				};

				// Update the user message ID with the one from the database
				setMessages(prev => prev.map(msg =>
					msg.id === userMessage.id
						? { ...msg, id: response.data.userMessageId.toString() }
						: msg
				));

				setMessages(prev => [...prev, aiResponse]);

				// Trigger credit refresh since credits were consumed
				triggerCreditRefresh();
			}

			setIsTyping(false);

			// Scroll to bottom again to show the new message
			setTimeout(() => {
				scrollToBottom();
			}, 0);

			if (isNewConversation) {

				window.history.replaceState(
					{},
					'',
					`/talk/conversation/${workingConversationId}`
				);
			}

			// Refresh usage stats after sending
			await fetchUsageStats()
		} catch (error) {
			console.error('Error fetching AI response:', error);
			setIsTyping(false);

			// Show error message based on error type
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else if (axios.isAxiosError(error) && error.response?.status === 402) {
				// Credit-related error (Payment Required)
				const errorData = error.response.data;
				let creditErrorMessage = "Insufficient credits to continue.";

				if (errorData && errorData.message) {
					creditErrorMessage = errorData.message;
				}

				// Add credit error message to chat with upgrade/purchase options
				const aiErrorMessage: Message = {
					id: Date.now().toString(),
					type: 'ai',
					content: creditErrorMessage,
					timestamp: new Date()
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
					id: Date.now().toString(),
					type: 'ai',
					content: upgradeMessage,
					timestamp: new Date()
				};

				setMessages(prev => [...prev, aiErrorMessage]);
			} else {
				// Add generic error message to chat based on mode
				let errorMessage = "Error sending message. Please try again.";
				if (isHealthMode) {
					errorMessage = "Sorry, I couldn't access your health records right now. Please try again or contact support if the issue persists.";
				}

				const aiErrorMessage: Message = {
					id: Date.now().toString(),
					type: 'ai',
					content: errorMessage,
					timestamp: new Date()
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
				alert('Failed to load bookmarks. Please try again.');
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
					? { ...msg, liked: isLike, disliked: !isLike && msg.disliked }
					: msg
			));

			// Use our utility function
			await handleMessageReaction(messageId, isLike);
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
				bookmarkedAt: new Date()
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
		} catch (error) {
			console.error('Error retrying message:', error);

			// Revert to original message on error
			setMessages(prev => prev.map(msg =>
				msg.id === messageId
					? aiMessage
					: msg
			));
			setIsTyping(false);

			// Show error message
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			}
		}
	};

	const handleFileUpload = (files: File[]) => {
		const newFiles: SelectedFile[] = files.map(file => ({
			file,
			type: file.type.startsWith('image/') ? 'image' : 'file',
			previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
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

	const openUploadModal = (type: 'file' | 'image' | 'book-generator') => {
		if (type === 'book-generator') {
			setIsBookGeneratorOpen(true);
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
					// Fetch bookmarks
					const bookmarksResponse = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/bookmarked-conversations`, {
						withCredentials: true
					});

					if (bookmarksResponse.data && Array.isArray(bookmarksResponse.data)) {
						const formattedBookmarks = bookmarksResponse.data.map(conversation => {
							return {
								id: conversation.id.toString(),
								content: conversation.title || `Conversation ${conversation.id}`,
								type: 'ai' as 'user' | 'ai',
								timestamp: new Date(conversation.updated_at),
								bookmarkedAt: new Date(conversation.updated_at)
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
			if (conversationId === selectedConversationId.toString() && messages.length > 0) {
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
						const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}`, {
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

			// Call the API to toggle bookmark status
			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Update the local state with the response
			setIsBookmarked(response.data.is_bookmarked);

			// Refresh bookmarks in the sidebar
			fetchBookmarks();
		} catch (error: any) {
			console.error('Error in bookmark operation:', error);
			if (error.response && error.response.status === 401) {
				router.push('/login');
			} else {
				alert('Failed to update bookmark. Please try again.');
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
			await axios.delete(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}`, {
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
				alert('Failed to delete conversation. Please try again.');
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
			await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Update the UI if this is the current conversation
			if (params.conversationId === conversationId.toString()) {
				// Check bookmark status of current conversation
				const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}`, {
					withCredentials: true
				});
				setIsBookmarked(response.data.is_bookmarked || false);
			}

			// Refresh bookmarks if the panel is open
			if (showBookmarks) {
				fetchBookmarks();
			}
		} catch (error) {
			console.error('Error bookmarking conversation:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
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

			// Call the API to update the conversation title
			await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${conversationId}`,
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

			// If this is the current conversation, update the document title too
			if (params.conversationId === String(conversationId)) {
				document.title = newTitle;
			}

			// Refresh the history panel to show the updated title
			if (showHistory) {
				toggleHistory();
			}
		} catch (error) {
			console.error('Error renaming conversation:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				alert('Failed to rename conversation. Please try again.');
			}
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
			// Make API call to update bookmark status in the database
			await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/conversations/${bookmark.id}/bookmark`,
				{},
				{
					withCredentials: true
				}
			);

			// Update current conversation bookmark state if applicable
			if (params.conversationId === bookmark.id) {
				setIsBookmarked(false);
			}

			// Refresh bookmarks to get the latest data
			fetchBookmarks();
		} catch (error) {
			console.error('Error removing bookmark:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				alert('Failed to remove bookmark. Please try again.');
			}
		}
	};

	// Function to perform the actual history clearing
	const performClearHistory = async () => {
		try {
			// Clear the history state immediately for responsive UI
			setHistory([]);
			setFilteredHistory([]);

			// If we're currently viewing a conversation, redirect to a new chat
			if (conversationId !== 'new-chat') {
				setMessages([]);
				router.push('/talk/conversation/new-chat');
			}

			// Call the API to clear all conversations
			await axios.delete(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/${user?.id}/conversations`, {
				withCredentials: true
			});

			// Close the confirmation dialog
			setConfirmDialogOpen(false);
		} catch (error) {
			console.error('Error clearing history:', error);

			if (axios.isAxiosError(error) && error.response?.status === 401) {
				router.push('/login');
			} else {
				// alert('Failed to clear conversation history. Please try again.');
				console.log('Failed to clear conversation history. Please try again.');
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

	return (
		<div className="flex flex-col min-h-screen bg-black">
			{/* Sliding Credit Tracker */}
			<div
				className={`fixed right-0 top-1/2 -translate-y-1/2 transform transition-transform duration-300 z-50 ${isCreditTrackerVisible ? 'translate-x-0' : 'translate-x-[calc(100%-8px)]'
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
						<PiBookmarkFill className="w-5 h-5  max-[900px]:w-3 max-[900px]:h-3 text-black" />
					</div>

					<CreditTracker compact={true} showPurchaseOptions={false} />
					{usageStats && !user?.is_premium && (
						<UsageTracker
							feature="chat"
							currentUsage={usageStats.usage?.chat_messages_today || 0}
							maxUsage={10}
							className="mt-4 w-full"
						/>
					)}
				</div>
			</div>

			{/* Hero Section */}
			<HeroSection
				title="Talk with Mr. White"
				subtitle="Ask Mr. White a question and answers shall be given."
				images={heroImages}
			/>

			{/* SECTION 2 */}
			<section className="min-h-[200px] px-2 md:px-0 max-w-[800px]:px-24 mb-20 flex flex-col justify-between items-center mt-20">

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
							<h1 className="text-white text-[32px] max-[640px]:text-[24px] max-[400px]:text-[20px] max-[320px]:text-[18px] font-public-sans font-bold mb-4">
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
							messages.map((message) => (
								<Message
									key={message.id}
									id={message.id}
									content={message.content}
									type={message.type}
									liked={message.liked}
									disliked={message.disliked}
									timestamp={new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
									attachments={message.attachments}
									onCopy={copyToClipboard}
									onLike={handleLike}
									onSpeak={speakText}
									onRetry={handleRetry}
									onDownload={(url, filename) => {
										// Implement download logic here
										console.log('Downloading:', url, filename);
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
				<div className="space-y-4">
					{bookmarks.map((bookmark, index) => (
						<div
							key={index}
							className="p-4 bg-neutral-800 rounded-lg space-y-2 cursor-pointer hover:bg-neutral-700"
							onClick={() => {
								loadConversationMessages(bookmark.id);
								setShowBookmarks(false);
							}}
						>
							<div className="flex items-center justify-between">
								<span className="text-sm text-neutral-400">
									{new Date(bookmark.timestamp).toLocaleString()}
								</span>
								<button
									onClick={(e) => {
										e.stopPropagation(); // Prevent triggering the parent div's onClick
										handleRemoveBookmark(bookmark, index);
									}}
									className="text-neutral-400 hover:text-white"
								>
									<FiX />
								</button>
							</div>
							<p className="text-sm">{bookmark.content}</p>
						</div>
					))}
					{bookmarks.length === 0 && (
						<p className="text-center text-neutral-400">No bookmarks yet</p>
					)}
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
					<div className="space-y-6 overflow-y-auto flex-1">
						{filteredHistory.map((day, index) => (
							<div key={index} className="space-y-3">
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
												<input
													type="text"
													value={newTitle}
													onChange={(e) => setNewTitle(e.target.value)}
													onKeyDown={(e) => {
														32
														if (e.key === 'Enter') {
															handleRenameConversation(conversation.id);
														} else if (e.key === 'Escape') {
															setIsRenaming(null);
															setNewTitle('');
														}
													}}
													className="bg-neutral-700 text-white px-2 py-1 rounded w-full text-sm rename-input"
													autoFocus
													onClick={(e) => e.stopPropagation()}
												/>
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

			{/* Book Generator Sidebar */}
			<BookGeneratorSidebar
				isOpen={isBookGeneratorOpen}
				onClose={() => setIsBookGeneratorOpen(false)}
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