"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Upload, Grid, List, Download, Trash2, Eye, Filter, Image as ImageIcon, Calendar, FileText, MoveVertical, Pencil, Save, X, Maximize2, Folder, FolderPlus, Plus, LayoutGrid, MoreVertical, Edit, Trash, PlusCircle, Check, HelpCircle, Info } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs as UITabs, TabsContent as UITabsContent, TabsList as UITabsList, TabsTrigger as UITabsTrigger } from "@/components/ui/tabs";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NativeMenu } from '@/components/ui/native-menu';
import axios from 'axios';
import {toast} from '@/components/ui/sound-toast';
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// Import DnD Kit components
import {
	DndContext,
	closestCenter,
	KeyboardSensor,
	PointerSensor,
	useSensor,
	useSensors,
	DragEndEvent,
	DragStartEvent,
	DragOverlay,
	DragOverEvent,
} from '@dnd-kit/core';
import {
	arrayMove,
	SortableContext,
	sortableKeyboardCoordinates,
	rectSortingStrategy,
	useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { IoMdMove } from 'react-icons/io';
import { useRouter } from 'next/navigation';

interface ImageMetadata {
	file_size: number;
	width: number;
	height: number;
	format: string;
	content_type: string;
}

interface GalleryImage {
	id: number;
	url: string;
	title: string;
	description: string;
	uploaded_at: string;
	file_size: number;
	width: number;
	height: number;
	metadata?: ImageMetadata;
	original_filename?: string;
	display_order?: number;
}

interface GalleryStats {
	total_images: number;
	total_size_mb: number;
	recent_uploads: number;
	storage_limit_mb: number;
	storage_used_percent: number;
}

interface FolderData {
	id: number;
	name: string;
	description: string;
	display_order: number;
	created_at: string;
	updated_at: string;
	image_count: number;
	thumbnail_url?: string; // Add thumbnail_url property
}

// Create a styled markdown component to reuse
const StyledMarkdown = ({ children }: { children: string }) => (
	<ReactMarkdown
		remarkPlugins={[remarkGfm]}
		components={{
			p: ({ node, ...props }) => <p className="my-1" {...props} />,
			a: ({ node, ...props }) => <a className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
		}}
	>
		{children}
	</ReactMarkdown>
);

// Add SortableImageCard component for drag and drop functionality
const SortableImageCard = ({ image, onClick, dragModeEnabled, isReordering }: {
	image: GalleryImage;
	onClick: () => void;
	dragModeEnabled: boolean;
	isReordering: boolean;
}) => {
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
		transition,
		isDragging,
	} = useSortable({
		id: image.id,
		data: {
			type: 'image',
			image,
		},
		disabled: isReordering,
	});

	const style = {
		transform: CSS.Transform.toString(transform),
		transition,
		opacity: isDragging ? 0.4 : isReordering ? 0.7 : 1,
		zIndex: isDragging ? 10 : 1,
		position: 'relative' as const,
	};

	// Prevent click event from propagating when clicking the drag handle
	const handleDragClick = (e: React.MouseEvent) => {
		if (isReordering) return;
		e.stopPropagation();
		e.preventDefault();
	};

	// Only open image detail dialog if not in drag mode and not currently dragging
	const handleImageClick = (e: React.MouseEvent) => {
		if (!dragModeEnabled && !isDragging) {
			onClick();
		} else {
			// Prevent default behavior and propagation in drag mode
			e.stopPropagation();
			e.preventDefault();
		}
	};

	return (
		<div
			ref={setNodeRef}
			style={style}
			className={`relative group transition-all duration-200 ${isDragging ? 'ring-2 ring-blue-500 rounded-lg shadow-lg scale-105' : ''} ${isReordering ? 'pointer-events-none' : ''}`}
		>
			{/* Drag handle */}
			{dragModeEnabled && (
				<div
					className={`absolute top-2 right-2 z-10 ${isReordering ? 'opacity-50' : 'opacity-100'} transition-opacity`}
					onClick={handleDragClick}
				>
					<Button
						variant="ghost"
						size="icon"
						className={`h-8 w-8 rounded-full bg-black/50 text-white hover:bg-black/70 ${isReordering ? 'cursor-not-allowed' : 'cursor-grab active:cursor-grabbing'}`}
						title={isReordering ? "Saving order..." : "Drag to reorder"}
						{...listeners}
						{...attributes}
						disabled={isReordering}
					>
						<IoMdMove className="h-4 w-4" />
					</Button>
				</div>
			)}

			{/* Drag mode indicator overlay */}
			{(dragModeEnabled || isDragging) && (
				<div className={`absolute inset-0 bg-black/5 dark:bg-white/5 z-5 pointer-events-none rounded-lg ${isDragging ? 'bg-blue-500/10' : ''} ${isReordering ? 'bg-gray-200/20 dark:bg-gray-700/20' : ''}`}></div>
			)}

			<div
				onClick={handleImageClick}
				className={`transform transition-transform duration-200 ${isDragging ? 'cursor-grabbing' : dragModeEnabled ? (isReordering ? 'cursor-default' : 'cursor-grab') : 'cursor-pointer'}`}
			>
				<ImageCard image={image} onClick={() => { }} />
			</div>
		</div>
	);
};

// Add ImageCard component for better image handling
const ImageCard = ({ image, onClick }: { image: GalleryImage; onClick: () => void }) => {
	const [imageLoaded, setImageLoaded] = useState(false);
	const [imageError, setImageError] = useState(false);

	const handleImageLoad = () => {
		console.log(`✅ Image loaded successfully: ${image.url}`);
		setImageLoaded(true);
		setImageError(false);
	};

	const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
		console.error(`❌ Image failed to load: ${image.url}`);
		setImageError(true);
		setImageLoaded(false);
	};

	// Format file size helper
	const formatFileSize = (bytes: number) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	};

	return (
		<Card
			className="group cursor-pointer hover:shadow-lg transition-all duration-300 overflow-hidden"
			onClick={onClick}
		>
			<div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-gray-800">
				{!imageLoaded && !imageError && (
					<div className="absolute inset-0 backdrop-blur-sm flex items-center justify-center z-50">
						<div className="relative w-12 h-6 mr-4 bg-gradient-to-t from-orange-400 via-yellow-400 to-yellow-200 rounded-t-full shadow-lg shadow-orange-300/50">
							<Image
								src="/assets/running-dog.gif"
								alt="loading..."
								fill
								priority
								className="object-contain"
							/>
						</div>
					</div>
				)}

				{imageError && (
					<div className="absolute inset-0 flex items-center justify-center flex-col text-gray-500">
						<ImageIcon className="h-12 w-12 mb-2" />
						<span className="text-sm">Failed to load</span>
					</div>
				)}

				<div className="relative w-full h-full">
					<Image
						src={image.url}
						alt={image.title}
						className={`object-cover group-hover:scale-105 transition-transform duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'
							}`}
						fill
						onLoad={handleImageLoad}
						onError={handleImageError}
						loading="lazy"
						crossOrigin="anonymous"
					/>
				</div>

				<div className="absolute inset-0 group-hover:backdrop-blur-sm bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
					<Eye className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
				</div>
			</div>
			<CardContent className="p-3">
				<h3 className="font-medium text-sm truncate">{image.title}</h3>
				{/* <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
<StyledMarkdown>{image.description}</StyledMarkdown>
</div> */}
				<div className="flex items-center justify-between mt-2">
					<span className="text-xs text-gray-500">{formatFileSize(image.file_size)}</span>
					<span className="text-xs text-gray-500">{image.width}×{image.height}</span>
				</div>
			</CardContent>
		</Card>
	);
};

// Add ImageListItem component for list view
const ImageListItem = ({ image, onClick }: { image: GalleryImage; onClick: () => void }) => {
	const [imageLoaded, setImageLoaded] = useState(false);
	const [imageError, setImageError] = useState(false);

	const handleImageLoad = () => {
		console.log(`✅ List image loaded successfully: ${image.url}`);
		setImageLoaded(true);
		setImageError(false);
	};

	const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
		console.error(`❌ List image failed to load: ${image.url}`);
		setImageError(true);
		setImageLoaded(false);
	};

	// Format file size helper
	const formatFileSize = (bytes: number) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	};

	// Format date helper
	const formatDate = (dateString: string) => {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	return (
		<Card
			className="cursor-pointer hover:shadow-md transition-shadow"
			onClick={onClick}
		>
			<CardContent className="p-4 flex items-center gap-4">
				<div className="min-w-16 w-16 h-16 relative rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 flex-shrink-0">
					{!imageLoaded && !imageError && (
						<div className="absolute inset-0 flex items-center justify-center">
							<div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
						</div>
					)}

					{imageError && (
						<div className="absolute inset-0 flex items-center justify-center">
							<ImageIcon className="h-6 w-6 text-gray-400" />
						</div>
					)}

					<Image
						src={image.url}
						alt={image.title}
						className={`object-cover ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
						fill
						onLoad={handleImageLoad}
						onError={handleImageError}
						loading="lazy"
						crossOrigin="anonymous"
					/>
				</div>
				<div className="flex-1 min-w-0">
					<h3 className="font-medium truncate text-sm whitespace-nowrap overflow-hidden overflow-ellipsis max-w-full">{image.title}</h3>
					<div className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
						<StyledMarkdown>{image.description}</StyledMarkdown>
					</div>
					<div className="max-[450px]:hidden flex items-center gap-4 mt-1 text-xs text-gray-500">
						<span>{formatFileSize(image.file_size)}</span>
						<span>{image.width}×{image.height}</span>
						<span>{formatDate(image.uploaded_at)}</span>
					</div>
				</div>
				<Button variant="ghost" size="sm" className="flex-shrink-0">
					<Eye className="h-4 w-4" />
				</Button>
			</CardContent>
		</Card>
	);
};

// Add FullScreenImage component
const FullScreenImage = ({
	imageUrl,
	onClose
}: {
	imageUrl: string | null;
	onClose: () => void
}) => {
	// Use a ref for the close button
	const closeButtonRef = useRef<HTMLButtonElement>(null);

	// Add keyboard event listener for Escape key
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				onClose();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => {
			window.removeEventListener('keydown', handleKeyDown);
		};
	}, [onClose]);

	return (
		<>
			<div
				className="fixed min-h-screen inset-0 bg-black opacity-85 z-[9999]"
				onClick={onClose}
			/>
			<div className="fixed inset-0 z-[10000] flex items-center justify-center pointer-events-none min-h-screen">
				{imageUrl && (
					<img
						src={imageUrl}
						alt="Full Screen Image"
						className="max-h-[90vh] max-w-[90vw] object-contain pointer-events-auto"
						onClick={(e) => e.stopPropagation()}
						crossOrigin="anonymous"
					/>
				)}
				<button
					ref={closeButtonRef}
					className="absolute top-4 right-4 h-12 w-12 rounded-full bg-black/50 text-white hover:bg-black/70 flex items-center justify-center pointer-events-auto"
					onClick={onClose}
					type="button"
					aria-label="Close full screen view"
				>
					<X className="h-6 w-6" />
				</button>
			</div>
		</>
	);
};

// Create a draggable image card component
const DraggableImageCard = ({ image, onClick, onDragStart }: { image: GalleryImage; onClick: () => void; onDragStart: () => void }) => {
	const [imageLoaded, setImageLoaded] = useState(false);
	const [imageError, setImageError] = useState(false);
	const [isDragging, setIsDragging] = useState(false);

	const handleImageLoad = () => {
		setImageLoaded(true);
	};

	const handleImageError = () => {
		setImageError(true);
	};

	// Format date for display
	const formatDate = (dateString: string) => {
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
		}).format(date);
	};

	return (
		<Card
			className="group cursor-pointer hover:shadow-lg transition-all duration-300 overflow-hidden relative"
			onClick={onClick}
		>
			<div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-gray-800">
				{!imageLoaded && !imageError && (
					<div className="absolute inset-0 backdrop-blur-sm flex items-center justify-center z-50">
						<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
					</div>
				)}

				{imageError && (
					<div className="absolute inset-0 flex items-center justify-center flex-col text-gray-500">
						<ImageIcon className="h-12 w-12 mb-2" />
						<span className="text-sm">Failed to load</span>
					</div>
				)}

				<div className="relative w-full h-full">
					<Image
						src={image.url}
						alt={image.title}
						className={`object-cover group-hover:scale-105 transition-transform duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'
							}`}
						fill
						onLoad={handleImageLoad}
						onError={handleImageError}
						loading="lazy"
						crossOrigin="anonymous"
					/>
				</div>

				<div className="absolute inset-0 group-hover:backdrop-blur-sm bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
					<Eye className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
				</div>
			</div>
			<CardContent className="p-3">
				<h3 className="font-medium text-sm truncate">{image.title}</h3>
				<p className="text-xs text-gray-500">{formatDate(image.uploaded_at)}</p>
			</CardContent>
		</Card>
	);
};

// Droppable folder card component
const DroppableFolderCard = ({ folder, onClick, onEdit, onDelete, onAddImages }: {
	folder: FolderData;
	onClick: () => void;
	onEdit: (folder: FolderData) => void;
	onDelete: (folder: FolderData) => void;
	onAddImages: (folder: FolderData) => void;
}) => {
	const [imageLoaded, setImageLoaded] = useState(false);
	const [imageError, setImageError] = useState(false);

	const handleImageLoad = () => {
		setImageLoaded(true);
		setImageError(false);
	};

	const handleImageError = () => {
		setImageError(true);
		setImageLoaded(false);
	};

	return (
		<div className="cursor-pointer group relative transition-all duration-200">
			<div className="rounded-lg hover:shadow-md transition-all duration-300" onClick={onClick}>
				<div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-gray-800 rounded-t-lg">
					{folder.thumbnail_url ? (
						<>
							{!imageLoaded && !imageError && (
								<div className="absolute inset-0 flex items-center justify-center">
									<div className="animate-pulse w-full h-full bg-gray-200 dark:bg-gray-700"></div>
								</div>
							)}
							<Image
								src={folder.thumbnail_url}
								alt={folder.name}
								className={`object-cover group-hover:scale-105 transition-transform duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
								fill
								onLoad={handleImageLoad}
								onError={handleImageError}
								crossOrigin="anonymous"
							/>
						</>
					) : (
						<div className="absolute inset-0 flex items-center justify-center">
							<Folder className="h-16 w-16 text-gray-400" />
						</div>
					)}

					{/* Hover overlay with folder icon */}
					<div className="absolute inset-0 group-hover:backdrop-blur-sm bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
						<Folder className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
					</div>

					<div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
						<div className="flex items-center gap-1">
							<ImageIcon className="h-4 w-4 text-white" />
							<span className="text-sm font-medium text-white">{folder.image_count}</span>
						</div>
					</div>
				</div>
				<div className="p-3 border border-t-0 rounded-b-lg dark:border-neutral-800 dark:bg-neutral-900">
					<div className="flex justify-between items-start">
						<div className="flex-1 min-w-0">
							<h3 className="font-medium text-sm truncate">{folder.name}</h3>
							<p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 h-fit">
								{folder.description}
							</p>
						</div>
						
						{/* Menu */}
						<div className="ml-2 mt-1 relative" onClick={(e) => e.stopPropagation()}>
							<NativeMenu 
								onEdit={() => onEdit(folder)}
								onDelete={() => onDelete(folder)}
								onAddImages={() => onAddImages(folder)}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
};

const GalleryPage = () => {
	// Existing state
	const [images, setImages] = useState<GalleryImage[]>([]);
	const [filteredImages, setFilteredImages] = useState<GalleryImage[]>([]);
	const [loading, setLoading] = useState(true);
	const [uploadLoading, setUploadLoading] = useState(false);
	const [searchQuery, setSearchQuery] = useState('');
	const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
	const [selectedImage, setSelectedImage] = useState<GalleryImage | null>(null);
	const [showUploadDialog, setShowUploadDialog] = useState(false);
	// Update the sortBy state definition
	const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'name' | 'size' | 'custom'>('custom');
	const [stats, setStats] = useState<GalleryStats | null>(null);
	const [page, setPage] = useState(0);
	const [hasMore, setHasMore] = useState(true);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [imageToDelete, setImageToDelete] = useState<number | null>(null);
	const deleteConfirmRef = useRef<HTMLDivElement>(null);
	// Drag and drop state
	const [activeId, setActiveId] = useState<number | null>(null);
	const [isDragging, setIsDragging] = useState(false);
	const [dragModeEnabled, setDragModeEnabled] = useState(false);
	const [draggedImage, setDraggedImage] = useState<GalleryImage | null>(null);
	const [editingDescription, setEditingDescription] = useState(false);
	const [descriptionValue, setDescriptionValue] = useState('');
	const [isSavingDescription, setIsSavingDescription] = useState(false);
	// Add title editing state
	const [editingTitle, setEditingTitle] = useState(false);
	const [titleValue, setTitleValue] = useState('');
	const [isSavingTitle, setIsSavingTitle] = useState(false);
	// Add a new state for tracking reordering operations
	const [isReordering, setIsReordering] = useState(false);
	// Add state for full screen view
	const [isFullScreen, setIsFullScreen] = useState(false);
	const [fullScreenImageUrl, setFullScreenImageUrl] = useState<string | null>(null);
	// Add folder-related state
	const [folders, setFolders] = useState<FolderData[]>([]);
	const [loadingFolders, setLoadingFolders] = useState(true);
	const [showCreateFolderDialog, setShowCreateFolderDialog] = useState(false);
	const [newFolderName, setNewFolderName] = useState('');
	const [newFolderDescription, setNewFolderDescription] = useState('');
	const [showMoveToFolderDialog, setShowMoveToFolderDialog] = useState(false);
	const [selectedFolderId, setSelectedFolderId] = useState<number | null>(null);
	const [imageToMove, setImageToMove] = useState<number | null>(null);
	const [currentFolderId, setCurrentFolderId] = useState<number | null>(null);
	const [isInFolderView, setIsInFolderView] = useState(false);
	const [currentFolder, setCurrentFolder] = useState<FolderData | null>(null);
	const [showFolderDropdown, setShowFolderDropdown] = useState(false);
	const folderDropdownRef = useRef<HTMLDivElement>(null);
	const [isLoading, setIsLoading] = useState(false);

	// Add state for drag-to-folder functionality
	const [draggingImageId, setDraggingImageId] = useState<number | null>(null);
	const [folderDropTargetId, setFolderDropTargetId] = useState<number | null>(null);
	
	// Add state for active tab
	const [activeTab, setActiveTab] = useState<'photos' | 'collections'>('photos');
	
	// Add state for How It Works dialog
	const [howItWorksDialogOpen, setHowItWorksDialogOpen] = useState(false);
	
	const router = useRouter();
	
	// Set up sensors for drag and drop
	const sensors = useSensors(
		useSensor(PointerSensor),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		})
	);



	// Handle drag start
	const handleDragStart = (event: DragStartEvent) => {
		const { active } = event;
		setActiveId(Number(active.id));
		setIsDragging(true);

		// Find the image being dragged but don't set it as selectedImage
		// This prevents the detail dialog from opening
		const image = images.find(img => img.id === Number(active.id));
		if (image) {
			setDraggedImage(image);
		}
	};

	// Handle drag end
	const handleDragEnd = async (event: DragEndEvent) => {
		const { active, over } = event;
		
		setIsDragging(false);
		setActiveId(null);
		setDraggedImage(null);
		
		// Prevent multiple reordering operations from happening simultaneously
		if (isReordering) return;

		if (over && active.id !== over.id) {
			const oldIndex = images.findIndex(img => img.id === Number(active.id));
			const newIndex = images.findIndex(img => img.id === Number(over.id));

			if (oldIndex !== -1 && newIndex !== -1) {
				// Set reordering state to show loading UI
				setIsReordering(true);

				// Create a new array with the reordered images
				const newImages = arrayMove(images, oldIndex, newIndex);
				
				// Update images state immediately
				setImages(newImages);

				// Extract the IDs in the new order for saving to backend
				const imageIds = newImages.map(img => img.id);

				// Save the new order to the backend
				try {
					const response = await axios.post(
						`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/reorder`,
						{ imageIds },
						{ withCredentials: true }
					);

					if (response.data.success) {
						toast.success('Image order updated');
					} else {
						toast.error('Failed to save image order');
						fetchImages(); // Refetch the correct order from the server
					}
				} catch (error) {
					console.error('Error saving image order:', error);
					toast.error('Failed to save image order');
					fetchImages(); // Refetch the correct order from the server
				} finally {
					setIsReordering(false);
				}
			}
		}
	};

	// Filter images based on search query
	useEffect(() => {
		if (searchQuery.trim() === '') {
			setFilteredImages(images);
		} else {
			const query = searchQuery.toLowerCase();
			setFilteredImages(images.filter(img => 
				(img.title?.toLowerCase() || '').includes(query) || 
				(img.description?.toLowerCase() || '').includes(query)
			));
		}
	}, [searchQuery, images]);

	// Handle clicks outside of delete confirmation dialog
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (deleteConfirmRef.current && !deleteConfirmRef.current.contains(event.target as Node)) {
				setShowDeleteConfirm(false);
			}
		}

		document.addEventListener("mousedown", handleClickOutside);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
		};
	}, []);

	// Handle clicks outside of folder dropdown
	useEffect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (folderDropdownRef.current && !folderDropdownRef.current.contains(event.target as Node)) {
				setShowFolderDropdown(false);
			}
		}

		if (showFolderDropdown) {
			document.addEventListener("mousedown", handleClickOutside);
			return () => {
				document.removeEventListener("mousedown", handleClickOutside);
			};
		}
	}, [showFolderDropdown]);

	// Function to download image as a file
	const downloadImage = async (imageUrl: string, fileName: string) => {
		try {
			const absoluteUrl = imageUrl.startsWith('http')
				? imageUrl
				: `${process.env.NEXT_PUBLIC_API_BASE_URL}${imageUrl}`;

			// Fetch the image as a blob
			const response = await fetch(absoluteUrl);
			const blob = await response.blob();

			// Create a blob URL and use it for download
			const blobUrl = window.URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = blobUrl;
			anchor.download = fileName || 'image';
			anchor.style.display = 'none';
			document.body.appendChild(anchor);
			anchor.click();

			// Clean up
			setTimeout(() => {
				document.body.removeChild(anchor);
				window.URL.revokeObjectURL(blobUrl);
			}, 100);
		} catch (error) {
			console.error('Error downloading image:', error);
			toast.error('Failed to download image');
		}
	};

	// Fetch gallery images
	const fetchImages = useCallback(async (loadMore = false) => {
		try {
			setLoading(!loadMore);
			const offset = loadMore ? images.length : 0;

			console.log(`🔍 Fetching images: loadMore=${loadMore}, offset=${offset}, searchQuery="${searchQuery}"`);

			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images`, {
				withCredentials: true,
				params: {
					limit: 20,
					offset,
					search: searchQuery || undefined
				}
			});

			console.log(`📡 Gallery API response:`, response.data);

			if (response.data.success) {
				// Validate and normalize image data to prevent errors
				const newImages = response.data.images.map((img: any) => ({
					id: img.id || 0,
					url: img.url || '',
					title: img.title || img.original_filename || 'Untitled Image',
					description: img.description || 'No description available',
					uploaded_at: img.uploaded_at || new Date().toISOString(),
					file_size: img.file_size || 0,
					width: img.width || 0,
					height: img.height || 0,
					metadata: img.metadata || {},
					original_filename: img.original_filename || '',
					display_order: img.display_order || 0
				}));

				console.log(`✅ Fetched ${newImages.length} images`);
				if (newImages.length > 0) {
					console.log(`🖼️ First image URL: ${newImages[0].url}`);
					console.log(`🖼️ Sample image data:`, newImages[0]);
				}

				if (loadMore) {
					setImages(prev => [...prev, ...newImages]);
					setFilteredImages(prev => [...prev, ...newImages]);
				} else {
					setImages(newImages);
					setFilteredImages(newImages);
				}
				setHasMore(response.data.has_more);
			}
		} catch (error) {
			console.error('❌ Error fetching images:', error);
			toast.error('Failed to load images');
		} finally {
			setLoading(false);
		}
	}, [searchQuery, images.length]);

	// Fetch gallery statistics
	const fetchStats = async () => {
		try {
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/stats`, {
				withCredentials: true
			});

			if (response.data.success) {
				setStats(response.data.stats);
			}
		} catch (error) {
			console.error('Error fetching stats:', error);
		}
	};

	// Handle image upload
	const handleImageUpload = async (files: FileList | null) => {
		if (!files || files.length === 0) return;

		setUploadLoading(true);
		const uploadPromises = Array.from(files).map(async (file) => {
			const formData = new FormData();
			formData.append('image', file);
			console.log(`📤 Uploading image from gallery: ${file.name}`);

			try {
				const response = await axios.post(
					`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/upload`,
					formData,
					{
						withCredentials: true,
						headers: { 'Content-Type': 'multipart/form-data' }
					}
				);

				if (response.data.success) {
					console.log(`✅ Upload successful for ${file.name}, description: ${response.data.image?.description || 'empty'}`);
					toast.success(`${file.name} uploaded successfully!`);
					return response.data.image;
				} else {
					console.error(`❌ Upload failed for ${file.name}: ${response.data.message}`);
					toast.error(`Failed to upload ${file.name}: ${response.data.message}`);
					return null;
				}
			} catch (error) {
				console.error(`❌ Error uploading ${file.name}:`, error);
				toast.error(`Error uploading ${file.name}`);
				return null;
			}
		});

		try {
			const results = await Promise.all(uploadPromises);
			const successfulUploads = results.filter(Boolean);

			if (successfulUploads.length > 0) {
				// Refresh the gallery
				fetchImages();
				fetchStats();
				setShowUploadDialog(false);
			}
		} catch (error) {
			toast.error('Some uploads failed');
		} finally {
			setUploadLoading(false);
		}
	};

	// Handle image deletion
	const handleDeleteImage = async (imageId: number) => {
		try {
			const response = await axios.delete(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/${imageId}`,
				{ withCredentials: true }
			);

			if (response.data.success) {
				setImages(prev => prev.filter(img => img.id !== imageId));
				setFilteredImages(prev => prev.filter(img => img.id !== imageId));
				setSelectedImage(null);
				toast.success('Image deleted successfully');
				fetchStats();
			} else {
				toast.error(response.data.message);
			}
		} catch (error) {
			toast.error('Failed to delete image');
		} finally {
			setShowDeleteConfirm(false);
			setImageToDelete(null);
		}
	};

	// Show delete confirmation dialog
	const confirmDelete = (imageId: number) => {
		setImageToDelete(imageId);
		setShowDeleteConfirm(true);
	};

	// Filter and sort images
	useEffect(() => {
		// Normal filtering and sorting for non-drag mode
		let filtered = [...images];

		// Apply search filter
		if (searchQuery) {
			filtered = filtered.filter(img =>
				(img.title?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
				(img.description?.toLowerCase() || '').includes(searchQuery.toLowerCase())
			);
		}

		// Apply sorting
		filtered.sort((a, b) => {
			// If custom order is active, respect display_order
			if (sortBy === 'custom') {
				return (a.display_order || 0) - (b.display_order || 0);
			}

			// Use the selected sort method
			switch (sortBy) {
				case 'newest':
					return new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime();
				case 'oldest':
					return new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime();
				case 'name':
					// Handle null or undefined titles
					const titleA = a.title || '';
					const titleB = b.title || '';
					return titleA.localeCompare(titleB);
				case 'size':
					return b.file_size - a.file_size;
				default:
					return (a.display_order || 0) - (b.display_order || 0);
			}
		});

		setFilteredImages(filtered);
	}, [images, searchQuery, sortBy]);

	// Fetch folders with thumbnails
	const fetchFolders = useCallback(async () => {
		try {
			setLoadingFolders(true);

			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/list`, {
				withCredentials: true
			});

			if (response.data.success) {
				// Process folders to get thumbnails
				const foldersWithThumbnails = await Promise.all(
					response.data.folders.map(async (folder: FolderData) => {
						if (folder.image_count > 0) {
							try {
								// Get the first image from the folder to use as thumbnail
								const folderResponse = await axios.get(
									`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folder.id}?limit=1`,
									{ withCredentials: true }
								);
								
								if (folderResponse.data.success && folderResponse.data.images.length > 0) {
									console.log(`Found thumbnail for folder ${folder.id}:`, folderResponse.data.images[0].url);
									return {
										...folder,
										thumbnail_url: folderResponse.data.images[0].url
									};
								}
							} catch (error) {
								console.error(`Error fetching thumbnail for folder ${folder.id}:`, error);
							}
						}
						return folder;
					})
				);
				
				console.log("Folders with thumbnails:", foldersWithThumbnails);
				setFolders(foldersWithThumbnails);
				setFilteredFolders(foldersWithThumbnails); // Initialize filtered folders
			}
		} catch (error) {
			console.error('Error fetching folders:', error);
			toast.error('Failed to load folders');
		} finally {
			setLoadingFolders(false);
		}
	}, []);

	// Create a new folder
	const handleCreateFolder = async () => {
		if (!newFolderName.trim()) {
			toast.error('Folder name is required');
			return;
		}

		setIsCreatingFolder(true);
		try {
			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/create`,
				{
					name: newFolderName.trim(),
					description: newFolderDescription.trim()
				},
				{
					withCredentials: true
				}
			);

			if (response.data.success) {
				toast.success('Folder created successfully');
				setShowCreateFolderDialog(false);
				setNewFolderName('');
				setNewFolderDescription('');
				fetchFolders();
			} else {
				toast.error(response.data.message || 'Failed to create folder');
			}
		} catch (error) {
			console.error('Error creating folder:', error);
			toast.error('Failed to create folder');
		} finally {
			setIsCreatingFolder(false);
		}
	};

	// Move image to folder
	const handleMoveImageToFolder = async () => {
		if (!selectedFolderId || !imageToMove) {
			toast.error('Please select a folder');
			return;
		}

		try {
			setIsLoading(true);
			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${selectedFolderId}/add-image`,
				{
					image_id: imageToMove
				},
				{
					withCredentials: true
				}
			);

			if (response.data.success) {
				toast.success('Image moved to folder successfully');
				setShowMoveToFolderDialog(false);
				setSelectedFolderId(null);
				setImageToMove(null);
				setSelectedImage(null);

				// Refresh images if in folder view
				if (isInFolderView && currentFolderId) {
					fetchFolderImages(currentFolderId);
				} else {
					fetchImages(); // Refresh main gallery
				}

				// Refresh folders to update image counts
				fetchFolders();
			}
		} catch (error) {
			console.error('Error moving image to folder:', error);
			toast.error('Failed to move image to folder');
		} finally {
			setIsLoading(false);
		}
	};

	// Fetch images from a specific folder
	const fetchFolderImages = async (folderId: number) => {
		try {
			setLoading(true);

			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderId}`, {
				withCredentials: true
			});

			if (response.data.success) {
				setImages(response.data.images);
				setFilteredImages(response.data.images);
				setCurrentFolder(response.data.folder);
				setIsInFolderView(true);
				setCurrentFolderId(folderId);
				setHasMore(false); // Folder view doesn't support pagination yet
			}
		} catch (error) {
			console.error('Error fetching folder images:', error);
			toast.error('Failed to load folder images');
		} finally {
			setLoading(false);
		}
	};

	// Handle folder click
	const handleFolderClick = (folder: FolderData) => {
		router.push(`/gallery/folder/${folder.id}`);
		// fetchFolderImages(folder.id);
	};

	// Return to main gallery
	const handleReturnToGallery = () => {
		setIsInFolderView(false);
		setCurrentFolder(null);
		setCurrentFolderId(null);
		fetchImages();
	};

	// Initial load
	useEffect(() => {
		fetchImages();
		fetchStats();
		fetchFolders();
	}, []);

	// Show notification when drag mode is toggled
	useEffect(() => {
		if (dragModeEnabled) {
			toast.success('Arrange mode enabled. Drag images to reorder them.');
		}
	}, [dragModeEnabled]);

	// Format file size
	const formatFileSize = (bytes: number) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	};

	// Format date
	const formatDate = (dateString: string) => {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	// Toggle full screen view
	const toggleFullScreen = (imageUrl: string) => {
		// Store the URL and set fullscreen mode to true
		setFullScreenImageUrl(imageUrl);
		setIsFullScreen(true);
	};

	// Close full screen view
	const closeFullScreen = () => {
		console.log("Closing fullscreen view");
		setIsFullScreen(false);
		setFullScreenImageUrl(null);
	};

	// Handle editing image description
	const startEditingDescription = () => {
		if (selectedImage) {
			setDescriptionValue(selectedImage.description || '');
			setEditingDescription(true);
		}
	};

	const cancelEditingDescription = () => {
		setEditingDescription(false);
	};

	const saveImageDescription = async () => {
		if (!selectedImage) return;

		setIsSavingDescription(true);

		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/${selectedImage.id}/description`,
				{ description: descriptionValue },
				{ withCredentials: true }
			);

			if (response.data.success) {
				// Update the selected image with the new description
				setSelectedImage({
					...selectedImage,
					description: descriptionValue
				});

				// Update the image in the images array
				setImages(prev => prev.map(img =>
					img.id === selectedImage.id
						? { ...img, description: descriptionValue }
						: img
				));

				setEditingDescription(false);
				toast.success('Description updated successfully');
			} else {
				toast.error('Failed to update description');
			}
		} catch (error) {
			console.error('Error updating description:', error);
			toast.error('Error updating description');
		} finally {
			setIsSavingDescription(false);
		}
	};

	// Handle editing image title
	const startEditingTitle = () => {
		if (selectedImage) {
			setTitleValue(selectedImage.title || '');
			setEditingTitle(true);
		}
	};

	const cancelEditingTitle = () => {
		setEditingTitle(false);
	};

	const saveImageTitle = async () => {
		if (!selectedImage) return;

		setIsSavingTitle(true);

		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/${selectedImage.id}/title`,
				{ title: titleValue },
				{ withCredentials: true }
			);

			if (response.data.success) {
				// Update the selected image with the new title
				setSelectedImage({
					...selectedImage,
					title: titleValue
				});

				// Update the image in the images array
				setImages(prev => prev.map(img =>
					img.id === selectedImage.id
						? { ...img, title: titleValue }
						: img
				));

				// Also update filtered images
				setFilteredImages(prev => prev.map(img =>
					img.id === selectedImage.id
						? { ...img, title: titleValue }
						: img
				));

				setEditingTitle(false);
				toast.success('Title updated successfully');
			} else {
				toast.error('Failed to update title');
			}
		} catch (error) {
			console.error('Error updating title:', error);
			toast.error('Error updating title');
		} finally {
			setIsSavingTitle(false);
		}
	};

	// Handle image click
	const handleImageClick = (image: GalleryImage) => {
		if (dragModeEnabled) return;

		setSelectedImage(image);
		setDescriptionValue(image.description);
		setTitleValue(image.title);
		setEditingDescription(false);
		setEditingTitle(false);
	};

	// Handle move to folder option in image detail dialog
	const handleOpenMoveToFolder = () => {
		if (selectedImage) {
			setImageToMove(selectedImage.id);
			setShowMoveToFolderDialog(true);
		}
	};

	// Handle drag start for image-to-folder drag
	const handleImageDragStart = (imageId: number) => {
		setDraggingImageId(imageId);
	};

	// Handle drag over for folder drop target
	const handleDragOver = (folderId: number) => {
		setFolderDropTargetId(folderId);
	};

	// Handle drag end for image-to-folder drag
	const handleImageDragEnd = async () => {
		// If we have both a dragging image and a folder target
		if (draggingImageId !== null && folderDropTargetId !== null) {
			try {
				const response = await axios.post(
					`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderDropTargetId}/add-image`,
					{
						image_id: draggingImageId
					},
					{
						withCredentials: true
					}
				);

				if (response.data.success) {
					toast.success('Image moved to folder successfully');

					// Refresh images if in folder view
					if (isInFolderView && currentFolderId) {
						fetchFolderImages(currentFolderId);
					} else {
						fetchImages(); // Refresh main gallery
					}

					// Refresh folders to update image counts
					fetchFolders();
				}
			} catch (error) {
				console.error('Error moving image to folder:', error);
				toast.error('Failed to move image to folder');
			}
		}

		// Reset drag state
		setDraggingImageId(null);
		setFolderDropTargetId(null);
	};

	// Add state for folder creation loading and filtered folders
	const [isCreatingFolder, setIsCreatingFolder] = useState(false);
	const [filteredFolders, setFilteredFolders] = useState<FolderData[]>([]);

	// Update useEffect for search to filter both images and folders
	useEffect(() => {
		// Filter images
		if (searchQuery.trim() === '') {
			setFilteredImages(images);
			setFilteredFolders(folders);
		} else {
			const query = searchQuery.toLowerCase();
			
			// Filter images
			setFilteredImages(images.filter(img => 
				img.title.toLowerCase().includes(query) || 
				img.description.toLowerCase().includes(query)
			));
			
			// Filter folders
			setFilteredFolders(folders.filter(folder => 
				folder.name.toLowerCase().includes(query) || 
				(folder.description && folder.description.toLowerCase().includes(query))
			));
		}
	}, [searchQuery, images, folders]);

	// Add new state variables for folder operations
	const [editFolderDialog, setEditFolderDialog] = useState(false);
	const [deleteFolderDialog, setDeleteFolderDialog] = useState(false);
	const [addImagesDialog, setAddImagesDialog] = useState(false);
	const [selectedFolder, setSelectedFolder] = useState<FolderData | null>(null);
	const [editFolderName, setEditFolderName] = useState('');
	const [editFolderDescription, setEditFolderDescription] = useState('');
	const [isEditingFolder, setIsEditingFolder] = useState(false);
	const [isDeletingFolder, setIsDeletingFolder] = useState(false);
	const [selectedImages, setSelectedImages] = useState<number[]>([]);
	const [isAddingImages, setIsAddingImages] = useState(false);
	const [availableImages, setAvailableImages] = useState<GalleryImage[]>([]);

	// Handle edit folder dialog open
	const handleEditFolder = (folder: FolderData) => {
		setSelectedFolder(folder);
		setEditFolderName(folder.name);
		setEditFolderDescription(folder.description || '');
		setEditFolderDialog(true);
	};

	// Handle delete folder dialog open
	const handleDeleteFolder = (folder: FolderData) => {
		setSelectedFolder(folder);
		setDeleteFolderDialog(true);
	};

	// Handle add images dialog open
	const handleAddImages = async (folder: FolderData) => {
		setSelectedFolder(folder);
		setSelectedImages([]);
		
		try {
			// Fetch all images that are not in the folder
			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images`, {
				withCredentials: true
			});
			
			if (response.data.success) {
				// Get folder images to exclude them
				const folderResponse = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folder.id}`, {
					withCredentials: true
				});
				
				if (folderResponse.data.success) {
					const folderImageIds = folderResponse.data.images.map((img: GalleryImage) => img.id);
					// Filter out images already in the folder
					const availableImgs = response.data.images.filter((img: GalleryImage) => 
						!folderImageIds.includes(img.id)
					);
					setAvailableImages(availableImgs);
					setAddImagesDialog(true);
				}
			}
		} catch (error) {
			console.error('Error fetching available images:', error);
			toast.error('Failed to load images');
		}
	};

	// Handle save folder edit
	const handleSaveFolderEdit = async () => {
		if (!selectedFolder) return;
		if (!editFolderName.trim()) {
			toast.error('Folder name is required');
			return;
		}
		
		setIsEditingFolder(true);
		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${selectedFolder.id}`,
				{
					name: editFolderName.trim(),
					description: editFolderDescription.trim()
				},
				{ withCredentials: true }
			);
			
			if (response.data.success) {
				toast.success('Folder updated successfully');
				setEditFolderDialog(false);
				fetchFolders();
			} else {
				toast.error(response.data.message || 'Failed to update folder');
			}
		} catch (error) {
			console.error('Error updating folder:', error);
			toast.error('Failed to update folder');
		} finally {
			setIsEditingFolder(false);
		}
	};

	// Handle confirm folder delete
	const handleConfirmDeleteFolder = async () => {
		if (!selectedFolder) return;
		
		setIsDeletingFolder(true);
		try {
			const response = await axios.delete(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${selectedFolder.id}`,
				{ withCredentials: true }
			);
			
			if (response.data.success) {
				toast.success('Folder deleted successfully');
				setDeleteFolderDialog(false);
				fetchFolders();
			} else {
				toast.error(response.data.message || 'Failed to delete folder');
			}
		} catch (error) {
			console.error('Error deleting folder:', error);
			toast.error('Failed to delete folder');
		} finally {
			setIsDeletingFolder(false);
		}
	};

	// Handle toggle image selection
	const toggleImageSelection = (imageId: number) => {
		setSelectedImages(prev => {
			if (prev.includes(imageId)) {
				return prev.filter(id => id !== imageId);
			} else {
				return [...prev, imageId];
			}
		});
	};

	// Handle add selected images to folder
	const handleAddSelectedImages = async () => {
		if (!selectedFolder || selectedImages.length === 0) {
			toast.error('Please select at least one image');
			return;
		}
		
		setIsAddingImages(true);
		try {
			// Add each image to the folder
			const promises = selectedImages.map(imageId => 
				axios.post(
					`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${selectedFolder.id}/add-image`,
					{ image_id: imageId },
					{ withCredentials: true }
				)
			);
			
			await Promise.all(promises);
			
			toast.success(`${selectedImages.length} images added to folder`);
			setAddImagesDialog(false);
			fetchFolders();
		} catch (error) {
			console.error('Error adding images to folder:', error);
			toast.error('Failed to add images to folder');
		} finally {
			setIsAddingImages(false);
		}
	};

	return (
		<div className="min-h-screen bg-background p-4">
			<div className="max-w-7xl mx-auto space-y-6">
				{/* Header */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					className="rounded-xl shadow-sm pt-6 w-fit"
				>
					<div className="flex flex-row items-center lg:flex-row lg:items-center lg:justify-between gap-4">
						<div>
							<h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
								<ImageIcon className="h-8 w-8 text-blue-600" />
								{isInFolderView && currentFolder ? (
									<>
										Photo Gallery / <span className="text-blue-600">{currentFolder.name}</span>
									</>
								) : (
									"Photo Gallery"
								)}
							</h1>
						</div>
						
						{/* Add Help Button */}
						<Button
							variant="ghost"
							size="sm"
							onClick={() => setHowItWorksDialogOpen(true)}
							className="ml-auto lg:ml-0 flex items-center gap-1"
						>
							<HelpCircle className="h-4 w-4" />
							<span className="max-[490px]:hidden">How It Works</span>
						</Button>
					</div>

					{/* Statistics */}
					{stats && (
						<div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
							<div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
								<div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.total_images}</div>
								<div className="text-sm text-gray-600 dark:text-gray-400">Total Images</div>
							</div>
							<div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
								<div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.recent_uploads}</div>
								<div className="text-sm text-gray-600 dark:text-gray-400">Recent (7 days)</div>
							</div>
							<div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
								<div className="text-2xl font-bold text-green-600 dark:text-green-400">{folders.length}</div>
								<div className="text-sm text-gray-600 dark:text-gray-400">Folders</div>
							</div>
						</div>
					)}
				</motion.div>

				{/* Controls */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ delay: 0.1 }}
					className="bg-white dark:bg-neutral-900 rounded-xl shadow-sm border p-4"
				>
					<div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
						<div className="flex flex-1 items-center gap-3">
							<div className="relative flex-1 max-w-md">
								<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
								<Input
									placeholder="Search images..."
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									className="pl-10"
								/>
							</div>
						</div>

						<div className="flex items-center gap-2">
							{activeTab === 'photos' && (
								<>
									<Button
										onClick={() => setShowUploadDialog(true)}
										size="sm"
									>
										<Upload className="h-4 w-4 max-[490px]:mr-0 mr-2" />
										<span className="max-[490px]:hidden">Upload Images</span>
									</Button>
									<Button
										variant={viewMode === 'grid' ? 'default' : 'outline'}
										size="sm"
										onClick={() => setViewMode('grid')}
									>
										<Grid className="h-4 w-4" />
									</Button>
									<Button
										variant={viewMode === 'list' ? 'default' : 'outline'}
										size="sm"
										onClick={() => setViewMode('list')}
									>
										<List className="h-4 w-4" />
									</Button>
									{viewMode === 'grid' && (
										<Button
											variant={dragModeEnabled ? 'default' : 'outline'}
											size="sm"
											onClick={() => setDragModeEnabled(!dragModeEnabled)}
											className="flex items-center gap-1"
											disabled={isReordering}
										>
											{isReordering ? (
												<>
													<svg className="animate-spin h-4 w-4 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
														<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
														<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
													</svg>
													<span className="max-[490px]:hidden">Saving Order...</span>
												</>
											) : (
												<>
													<IoMdMove className="h-4 w-4 max-[490px]:mr-0 mr-2" />
													<span className="max-[490px]:hidden">{dragModeEnabled ? 'Exit Arrange' : 'Arrange'}</span>
												</>
											)}
										</Button>
									)}
								</>
							)}
							{activeTab === 'collections' && (
								<Button
									onClick={() => setShowCreateFolderDialog(true)}
									size="sm"
								>
									<FolderPlus className="h-4 w-4 max-[490px]:mr-0 mr-2" />
									<span className="max-[490px]:hidden">New Collection</span>
								</Button>
							)}
						</div>
					</div>
				</motion.div>

				{/* Tabs */}
				<UITabs 
					defaultValue="photos" 
					value={activeTab}
					onValueChange={(value) => setActiveTab(value as 'photos' | 'collections')}
					className="w-full"
				>
					<UITabsList className="grid w-full grid-cols-2 mb-6 items-center h-fit">
						<UITabsTrigger value="photos" className="text-base py-3">Photos</UITabsTrigger>
						<UITabsTrigger value="collections" className="text-base py-3">Collections</UITabsTrigger>
					</UITabsList>
					
					{/* Photos Tab Content */}
					<UITabsContent value="photos" className="mt-0">
						{isInFolderView && (
							<div className="mb-6">
								<Button
									variant="outline"
									onClick={handleReturnToGallery}
									className="flex items-center gap-2"
								>
									<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-arrow-left"><path d="m12 19-7-7 7-7" /><path d="M19 12H5" /></svg>
									Return to Gallery
								</Button>

								{currentFolder && (
									<h2 className="text-xl font-semibold mt-4 flex items-center gap-2">
										<Folder className="h-5 w-5 text-blue-600" />
										{currentFolder.name}
									</h2>
								)}
							</div>
						)}

						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ delay: 0.2 }}
							className="mb-20"
						>
							{loading ? (
								<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
									{[...Array(8)].map((_, i) => (
										<div key={i} className="aspect-square bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
									))}
								</div>
							) : filteredImages.length === 0 ? (
								<Card className="p-12 text-center">
									<ImageIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
									<h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No images found</h3>
									<p className="text-gray-600 dark:text-gray-400 mb-4">
										{searchQuery ? 'Try adjusting your search query' : 'Upload your first image to get started'}
									</p>
									{!searchQuery && (
										<Button onClick={() => setShowUploadDialog(true)}>
											<Upload className="h-4 w-4 mr-2" />
											Upload Images
										</Button>
									)}
								</Card>
							) : (
								<>
									{viewMode === 'grid' ? (
										<DndContext
											sensors={sensors}
											collisionDetection={closestCenter}
											onDragStart={dragModeEnabled ? handleDragStart : undefined}
											onDragEnd={dragModeEnabled ? handleDragEnd : undefined}
											modifiers={[]}
										>
											<SortableContext
												items={filteredImages.map(image => image.id)}
												strategy={rectSortingStrategy}
											>
												<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
													{filteredImages.map((image) => (
														<SortableImageCard
															key={image.id}
															image={image}
															onClick={() => handleImageClick(image)}
															dragModeEnabled={dragModeEnabled}
															isReordering={isReordering}
														/>
													))}
												</div>
											</SortableContext>
											{isDragging && draggedImage && (
												<DragOverlay adjustScale={true}>
													<div className="w-full aspect-square max-w-xs transform scale-105 opacity-90 shadow-xl rounded-lg overflow-hidden border-2 border-blue-500">
														<ImageCard image={draggedImage} onClick={() => { }} />
													</div>
												</DragOverlay>
											)}
										</DndContext>
									) : (
										<div className="space-y-2">
											{filteredImages.map((image, index) => (
												<motion.div
													key={image.id}
													initial={{ opacity: 0, x: -20 }}
													animate={{ opacity: 1, x: 0 }}
													transition={{ delay: index * 0.02 }}
												>
													<ImageListItem image={image} onClick={() => setSelectedImage(image)} />
												</motion.div>
											))}
										</div>
									)}

									{/* Load More Button */}
									{hasMore && (
										<div className="text-center mt-8">
											<Button onClick={() => fetchImages(true)} variant="outline">
												Load More Images
											</Button>
										</div>
									)}
								</>
							)}
						</motion.div>
					</UITabsContent>
					
					{/* Collections Tab Content */}
					<UITabsContent value="collections" className="pt-6">
						{loadingFolders ? (
							<div className="flex justify-center py-20">
								<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
							</div>
						) : filteredFolders.length > 0 ? (
							<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
								{filteredFolders.map((folder) => (
									<div key={folder.id} className="group">
										<DroppableFolderCard
											folder={folder}
											onClick={() => handleFolderClick(folder)}
											onEdit={handleEditFolder}
											onDelete={handleDeleteFolder}
											onAddImages={handleAddImages}
										/>
									</div>
								))}
							</div>
						) : (
							<div className="text-center py-8 border border-dashed rounded-lg mb-8">
								<Folder className="h-12 w-12 mx-auto text-gray-400 mb-2" />
								<p className="text-gray-500">
									{searchQuery ? 'No collections match your search' : 'No collections created yet'}
								</p>
								{!searchQuery && (
									<Button
										variant="outline"
										className="mt-4"
										onClick={() => setShowCreateFolderDialog(true)}
									>
										<FolderPlus className="h-4 w-4 mr-2" />
										Create Collection
									</Button>
								)}
							</div>
						)}
					</UITabsContent>
				</UITabs>

				{/* Upload Dialog */}
				<Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
					<DialogContent className="sm:max-w-md">
						<DialogHeader>
							<DialogTitle>Upload Images</DialogTitle>
							<DialogDescription>
								Select images to upload to your gallery.
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4">
							<div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
								<Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
								<p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
									Choose images to upload
								</p>
								<input
									type="file"
									multiple
									accept="image/*"
									onChange={(e) => handleImageUpload(e.target.files)}
									className="hidden"
									id="image-upload"
									disabled={uploadLoading}
								/>
								<label
									htmlFor="image-upload"
									className="inline-flex items-center px-4 py-2 bg-[var(--mrwhite-primary-color)] text-black font-semibold font-sans rounded-lg hover:bg-[var(--mrwhite-primary-color)]/80 cursor-pointer disabled:opacity-50"
								>
									{uploadLoading ? 'Uploading...' : 'Select Images'}
								</label>
							</div>

							<p className="text-xs text-gray-500 text-center">
								Supported formats: JPG, PNG, GIF, WebP. Max size: <span className="font-bold">&lt;1 MB</span> per image.
							</p>
						</div>
					</DialogContent>
				</Dialog>

				{/* Create Folder Dialog */}
				<Dialog open={showCreateFolderDialog} onOpenChange={setShowCreateFolderDialog}>
					<DialogContent>
						<DialogHeader>
							<DialogTitle>Create New Folder</DialogTitle>
							<DialogDescription>
								Create a folder to organize your images
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4">
							<div className="space-y-2">
								<label htmlFor="folder-name" className="text-sm font-medium">
									Folder Name
								</label>
								<Input
									id="folder-name"
									placeholder="Enter folder name"
									value={newFolderName}
									onChange={(e) => setNewFolderName(e.target.value)}
								/>
							</div>

							<div className="space-y-2">
								<label htmlFor="folder-description" className="text-sm font-medium">
									Description (Optional)
								</label>
								<Textarea
									id="folder-description"
									placeholder="Enter folder description"
									value={newFolderDescription}
									onChange={(e) => setNewFolderDescription(e.target.value)}
									rows={3}
								/>
							</div>
						</div>

						<DialogFooter>
							<Button variant="outline" onClick={() => setShowCreateFolderDialog(false)} disabled={isCreatingFolder}>
								Cancel
							</Button>
							<Button onClick={handleCreateFolder} disabled={isCreatingFolder}>
								{isCreatingFolder ? (
									<>
										<svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
											<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
											<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Creating...
									</>
								) : (
									'Create Folder'
								)}
							</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>

				{/* Move to Folder Dialog */}
				<Dialog
					open={showMoveToFolderDialog}
					onOpenChange={(open) => {
						setShowMoveToFolderDialog(open);
						if (!open) {
							setShowFolderDropdown(false);
						}
					}}
				>
					<DialogContent className="sm:max-w-md">
						<DialogHeader>
							<DialogTitle>Add to Folder</DialogTitle>
							<DialogDescription>
								Select a folder to move this image to
							</DialogDescription>
						</DialogHeader>

						<div className="space-y-4 py-4">
							<div className="space-y-2">
								<label className="text-sm font-medium">
									Select Folder
								</label>
								<div className="relative" ref={folderDropdownRef}>
									<div
										className="border rounded-md px-3 py-2 flex items-center justify-between bg-background cursor-pointer"
										onClick={() => setShowFolderDropdown(!showFolderDropdown)}
									>
										<span className="text-sm">
											{selectedFolderId
												? folders.find(f => f.id === selectedFolderId)?.name || "Select a folder"
												: "Select a folder"}
										</span>
										<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 opacity-50"><path d="m6 9 6 6 6-6" /></svg>
									</div>

									{showFolderDropdown && (
										<div className="absolute inset-x-0 top-full mt-1 z-50 bg-popover text-popover-foreground shadow-md rounded-md border overflow-hidden max-h-60 overflow-y-auto">
											{folders.map((folder) => (
												<div
													key={folder.id}
													className={`px-3 py-2 text-sm cursor-pointer hover:bg-accent hover:text-accent-foreground ${selectedFolderId === folder.id ? 'bg-accent text-accent-foreground' : ''}`}
													onClick={() => {
														setSelectedFolderId(folder.id);
														setShowFolderDropdown(false);
													}}
												>
													{folder.name}
												</div>
											))}
										</div>
									)}
								</div>
							</div>
						</div>

						<div className="flex justify-end gap-2">
							<Button
								variant="outline"
								onClick={() => setShowMoveToFolderDialog(false)}
							>
								Cancel
							</Button>
							<Button onClick={handleMoveImageToFolder} disabled={isLoading}>
								{isLoading ? (
									<div className="flex items-center">
										<div className="relative w-6 h-6 mr-2">
											<Image 
												src="/assets/running-dog.gif" 
												alt="Loading" 
												fill
												priority
												className="object-contain"
											/>
										</div>
										<span>Adding...</span>
									</div>
								) : 'Add Image'}
							</Button>
						</div>
					</DialogContent>
				</Dialog>

				{/* Image Detail Dialog */}
				<Dialog
					open={!!selectedImage && !isDragging && !dragModeEnabled}
					onOpenChange={(open) => {
						// Only allow opening the dialog if not dragging
						if (!isDragging && !dragModeEnabled) {
							if (!open) {
								// If we're in full-screen mode, don't close the detail dialog
								if (!isFullScreen) {
									setSelectedImage(null);
								}
							}
						}
					}}
				>
					<DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-hidden" style={{ zIndex: isFullScreen ? 40 : 50 }}>
						{selectedImage && (
							<>
								<DialogHeader>
									<div className="flex justify-between items-center">
										{!editingTitle ? (
											<div className="flex items-center gap-2">
												<DialogTitle>{selectedImage.title || 'Untitled'}</DialogTitle>
												<Button
													variant="ghost"
													size="sm"
													onClick={startEditingTitle}
													className="h-7 w-7 p-0 rounded-full"
													title="Edit title"
												>
													<Pencil className="h-3.5 w-3.5" />
												</Button>
											</div>
										) : (
											<div className="flex items-center gap-2 w-full max-w-md">
												<Input
													value={titleValue}
													onChange={(e) => setTitleValue(e.target.value)}
													placeholder="Enter a title for this image..."
													className="h-9"
													disabled={isSavingTitle}
													autoFocus
												/>
												<div className="flex gap-1">
													<Button
														variant="ghost"
														size="sm"
														onClick={cancelEditingTitle}
														className="h-8 px-2"
														disabled={isSavingTitle}
													>
														<X className="h-4 w-4" />
													</Button>
													<Button
														variant="default"
														size="sm"
														onClick={saveImageTitle}
														className="h-8 px-2"
														disabled={isSavingTitle}
													>
														<Save className="h-4 w-4 mr-1" />
														{isSavingTitle ? 'Saving...' : 'Save'}
													</Button>
												</div>
											</div>
										)}
									</div>
									<DialogDescription>
										Uploaded {formatDate(selectedImage.uploaded_at)}
									</DialogDescription>
								</DialogHeader>

								<div className="grid md:grid-cols-2 gap-6 overflow-y-auto custom-scrollbar max-h-[calc(90vh-120px)] pr-2">
									<div>
										<div className="relative">
											<img
												src={selectedImage.url}
												alt={selectedImage.title}
												className="w-full h-auto rounded-lg"
												onLoad={() => console.log('Modal image loaded:', selectedImage.url)}
												onError={(e) => {
													console.error('Modal image failed to load:', selectedImage.url, e);
													const target = e.target as HTMLImageElement;
													target.style.backgroundColor = '#f3f4f6';
													target.style.display = 'flex';
													target.style.alignItems = 'center';
													target.style.justifyContent = 'center';
													target.alt = 'Failed to load image';
												}}
												crossOrigin="anonymous"
											/>
											<Button
												variant="ghost"
												size="icon"
												className="absolute top-2 right-2 h-8 w-8 rounded-full bg-black/50 text-white hover:bg-black/70"
												onClick={(e) => {
													e.stopPropagation();
													if (selectedImage) {
														toggleFullScreen(selectedImage.url);
													}
												}}
												title="View full screen"
											>
												<Maximize2 className="h-4 w-4" />
											</Button>
										</div>
									</div>

									<div className="space-y-4">
										<div>
											<div className="flex justify-between items-center mb-2">
												<h4 className="font-medium">Description</h4>
												{!editingDescription ? (
													<Button
														variant="ghost"
														size="sm"
														onClick={startEditingDescription}
														className="h-8 px-2"
													>
														<Pencil className="h-4 w-4 mr-1" />
														Edit
													</Button>
												) : (
													<div className="flex gap-1">
														<Button
															variant="ghost"
															size="sm"
															onClick={cancelEditingDescription}
															className="h-8 px-2"
															disabled={isSavingDescription}
														>
															<X className="h-4 w-4" />
														</Button>
														<Button
															variant="default"
															size="sm"
															onClick={saveImageDescription}
															className="h-8 px-2"
															disabled={isSavingDescription}
														>
															<Save className="h-4 w-4 mr-1" />
															{isSavingDescription ? 'Saving...' : 'Save'}
														</Button>
													</div>
												)}
											</div>
											{!editingDescription ? (
												<div className="text-sm text-neutral-300 max-h-[200px] overflow-y-auto custom-scrollbar pr-2">
													{selectedImage.description ? (
														<StyledMarkdown>{selectedImage.description}</StyledMarkdown>
													) : (
														<p className="text-gray-400 italic">No description available</p>
													)}
												</div>
											) : (
												<Textarea
													value={descriptionValue}
													onChange={(e) => setDescriptionValue(e.target.value)}
													placeholder="Enter a description for this image..."
													className="h-[150px] resize-none"
													disabled={isSavingDescription}
												/>
											)}
										</div>

										<div className="grid grid-cols-2 gap-4 text-sm">
											<div>
												<span className="text-gray-600 dark:text-gray-400">Dimensions:</span>
												<div className="font-medium">{selectedImage.width} × {selectedImage.height}</div>
											</div>
											<div>
												<span className="text-gray-600 dark:text-gray-400">File Size:</span>
												<div className="font-medium">{formatFileSize(selectedImage.file_size)}</div>
											</div>
											<div>
												<span className="text-gray-600 dark:text-gray-400">Format:</span>
												<div className="font-medium">{selectedImage.metadata?.format || 'Unknown'}</div>
											</div>
											<div>
												<span className="text-gray-600 dark:text-gray-400">Uploaded:</span>
												<div className="font-medium">{formatDate(selectedImage.uploaded_at)}</div>
											</div>
										</div>

										<div className="pt-4 flex flex-wrap gap-2">
											<Button
												variant="outline"
												size="sm"
												className="flex items-center gap-2"
												onClick={handleOpenMoveToFolder}
											>
												<Folder className="h-4 w-4" />
												Add to Folder
											</Button>

											<Button
												variant="outline"
												size="sm"
												className="flex items-center gap-2"
												onClick={() => window.open(selectedImage.url, '_blank')}
											>
												<Download className="h-4 w-4" />
												Download
											</Button>
											<Button
												className="bg-red-500 text-white"
												onClick={() => confirmDelete(selectedImage.id)}
											>
												<Trash2 className="h-4 w-4 mr-2" />
												Delete
											</Button>
										</div>
									</div>
								</div>
							</>
						)}
					</DialogContent>
				</Dialog>

				{/* Delete Confirmation Dialog */}
				<Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
					<DialogContent className="sm:max-w-sm">
						<DialogHeader>
							<DialogTitle>Confirm Deletion</DialogTitle>
							<DialogDescription>
								Are you sure you want to delete this image? This action cannot be undone.
							</DialogDescription>
						</DialogHeader>
						<div className="flex justify-end gap-2 mt-4">
							<Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
								No
							</Button>
							<Button onClick={() => imageToDelete && handleDeleteImage(imageToDelete)}>
								Yes
							</Button>
						</div>
					</DialogContent>
				</Dialog>

				{/* Full Screen Image View */}
				{isFullScreen && fullScreenImageUrl && (
					<FullScreenImage
						imageUrl={fullScreenImageUrl}
						onClose={closeFullScreen}
					/>
				)}

				{/* Edit Folder Dialog */}
				<Dialog open={editFolderDialog} onOpenChange={setEditFolderDialog}>
					<DialogContent className="sm:max-w-md">
						<DialogHeader>
							<DialogTitle>Edit Folder</DialogTitle>
							<DialogDescription>
								Update folder name and description
							</DialogDescription>
						</DialogHeader>
						
						<div className="space-y-4 py-2">
							<div className="space-y-2">
								<label htmlFor="folder-name" className="text-sm font-medium">
									Folder Name
								</label>
								<Input
									id="folder-name"
									value={editFolderName}
									onChange={(e) => setEditFolderName(e.target.value)}
									placeholder="Enter folder name"
								/>
							</div>
							
							<div className="space-y-2">
								<label htmlFor="folder-description" className="text-sm font-medium">
									Description (optional)
								</label>
								<Textarea
									id="folder-description"
									value={editFolderDescription}
									onChange={(e) => setEditFolderDescription(e.target.value)}
									placeholder="Enter folder description"
									className="min-h-[100px]"
								/>
							</div>
						</div>
						
						<DialogFooter>
							<Button variant="outline" onClick={() => setEditFolderDialog(false)} disabled={isEditingFolder}>
								Cancel
							</Button>
							<Button onClick={handleSaveFolderEdit} disabled={isEditingFolder}>
								{isEditingFolder ? (
									<>
										<svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
											<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
											<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Saving...
									</>
								) : (
									'Save Changes'
								)}
							</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>
				
				{/* Delete Folder Dialog */}
				<Dialog open={deleteFolderDialog} onOpenChange={setDeleteFolderDialog}>
					<DialogContent className="sm:max-w-md">
						<DialogHeader>
							<DialogTitle>Delete Folder</DialogTitle>
							<DialogDescription>
								Are you sure you want to delete this folder? This action cannot be undone.
							</DialogDescription>
						</DialogHeader>
						
						{selectedFolder && (
							<div className=" bg-neutral-900/40 p-4 rounded-sm border-2 border-neutral-800">
								<p className="font-medium">{selectedFolder.name}</p>
								<p className="text-sm text-gray-500">
									This folder contains {selectedFolder.image_count} images. 
									The images will not be deleted from your gallery.
								</p>
							</div>
						)}
						
						<DialogFooter>
							<Button variant="outline" onClick={() => setDeleteFolderDialog(false)} disabled={isDeletingFolder}>
								Cancel
							</Button>
							<Button variant="destructive" onClick={handleConfirmDeleteFolder} disabled={isDeletingFolder} className='!bg-red-500 hover:!bg-red-600'>
								{isDeletingFolder ? (
									<>
										<svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
											<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
											<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Deleting...
									</>
								) : (
									'Delete Folder'
								)}
							</Button>
						</DialogFooter>
					</DialogContent>
				</Dialog>
				
				{/* Add Images to Folder Dialog */}
				<Dialog open={addImagesDialog} onOpenChange={setAddImagesDialog}>
					<DialogContent className="sm:max-w-[800px] max-h-[80vh]">
						<DialogHeader>
							<DialogTitle>Add Images to Folder</DialogTitle>
							<DialogDescription>
								{selectedFolder && `Select images to add to "${selectedFolder.name}"`}
							</DialogDescription>
						</DialogHeader>
						
						<div className="py-4 overflow-y-auto custom-scrollbar max-h-[60vh]">
							{availableImages.length === 0 ? (
								<div className="text-center py-8">
									<p className="text-gray-500">No images available to add</p>
								</div>
							) : (
								<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
									{availableImages.map((image) => (
										<div 
											key={image.id} 
											className={`relative cursor-pointer border-2 rounded-md overflow-hidden transition-all ${
												selectedImages.includes(image.id) 
													? 'border-blue-500 ring-2 ring-blue-500 ring-opacity-50' 
													: 'border-transparent hover:border-gray-300'
											}`}
											onClick={() => toggleImageSelection(image.id)}
										>
											<div className="aspect-square relative">
												<Image 
													src={image.url} 
													alt={image.title}
													fill
													className="object-cover"
													crossOrigin="anonymous"
												/>
											</div>
											
											{selectedImages.includes(image.id) && (
												<div className="absolute top-2 right-2 bg-blue-500 rounded-full w-6 h-6 flex items-center justify-center text-white">
													<Check className="h-4 w-4" />
												</div>
											)}
											
											<div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
												<p className="text-white text-xs truncate">{image.title}</p>
											</div>
										</div>
									))}
								</div>
							)}
						</div>
						
						<DialogFooter>
							<div className="flex items-center justify-between w-full">
								<p className="text-sm text-gray-500">
									{selectedImages.length} images selected
								</p>
								<div className="flex gap-2">
									<Button variant="outline" onClick={() => setAddImagesDialog(false)} disabled={isAddingImages}>
										Cancel
									</Button>
									<Button onClick={handleAddSelectedImages} disabled={isAddingImages || selectedImages.length === 0}>
										{isAddingImages ? (
											<>
												<svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
													<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
													<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												Adding...
											</>
										) : (
											'Add Selected Images'
										)}
									</Button>
								</div>
							</div>
						</DialogFooter>
					</DialogContent>
				</Dialog>
			</div>
			
			{/* How It Works Dialog */}
			<Dialog open={howItWorksDialogOpen} onOpenChange={setHowItWorksDialogOpen}>
				<DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col help-dialog-content">
					<DialogHeader>
						<DialogTitle className="flex items-center text-xl">
							<HelpCircle className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
							How It Works: Photo Gallery
						</DialogTitle>
					</DialogHeader>
					<div className="py-4 flex-1 overflow-y-auto pr-2 custom-scrollbar">
						<div className="space-y-6">
							{/* Overview Section */}
							<div>
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<Info className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Overview
								</h3>
								<p className="text-sm text-muted-foreground help-section-content">
									The Photo Gallery allows you to manage, organize, and view all your uploaded images. You can create collections, 
									search for specific images, and customize how your gallery is displayed.
								</p>
							</div>
							
							{/* Photos Tab Section */}
							<div>
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<ImageIcon className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Photos Tab
								</h3>
								<p className="text-sm text-muted-foreground mb-2 help-section-content">
									The Photos tab displays all your uploaded images:
								</p>
								<ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1 help-section-list help-section-content">
									<li><span className="font-medium">Upload Images:</span> Click the "Upload Images" button to add new photos to your gallery</li>
									<li><span className="font-medium">View Modes:</span> Toggle between Grid view and List view using the buttons in the top right</li>
									<li><span className="font-medium">Arrange Mode:</span> In Grid view, click "Arrange" to drag and reorder your images</li>
									<li><span className="font-medium">Image Details:</span> Click on any image to view its details, edit metadata, or perform actions</li>
									<li><span className="font-medium">Search:</span> Use the search bar to find images by title or description</li>
								</ul>
							</div>
							
							{/* Collections Tab Section */}
							<div>
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<Folder className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Collections Tab
								</h3>
								<p className="text-sm text-muted-foreground mb-2 help-section-content">
									The Collections tab helps you organize your images into folders:
								</p>
								<ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1 help-section-list help-section-content">
									<li><span className="font-medium">Create Collection:</span> Click "New Collection" to create a new folder</li>
									<li><span className="font-medium">View Collection:</span> Click on any collection to view the images inside</li>
									<li><span className="font-medium">Edit Collection:</span> Use the menu on each collection to edit name, description, or delete</li>
									<li><span className="font-medium">Add Images:</span> Add images to a collection from the collection menu or from the image details view</li>
									<li><span className="font-medium">Organization:</span> Images can belong to multiple collections</li>
								</ul>
							</div>
							
							{/* Image Details Section */}
							<div>
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<Eye className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Image Details
								</h3>
								<p className="text-sm text-muted-foreground mb-2 help-section-content">
									When you click on an image, a details dialog opens with several options:
								</p>
								<ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1 help-section-list help-section-content">
									<li><span className="font-medium">Edit Title:</span> Click the pencil icon next to the title to rename the image</li>
									<li><span className="font-medium">Edit Description:</span> Add or modify the description text</li>
									<li><span className="font-medium">Full Screen:</span> Click the expand icon to view the image in full screen mode</li>
									<li><span className="font-medium">Add to Folder:</span> Add the image to any of your collections</li>
									<li><span className="font-medium">Download:</span> Save the image to your device</li>
									<li><span className="font-medium">Delete:</span> Remove the image from your gallery (this cannot be undone)</li>
								</ul>
							</div>
							
							{/* Image Management Section */}
							<div>
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<MoveVertical className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Arranging Images
								</h3>
								<p className="text-sm text-muted-foreground mb-2 help-section-content">
									You can customize how your images are organized:
								</p>
								<ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1 help-section-list help-section-content">
									<li><span className="font-medium">Arrange Mode:</span> Click "Arrange" to enter drag-and-drop mode</li>
									<li><span className="font-medium">Drag to Reorder:</span> In arrange mode, drag images to change their display order</li>
									<li><span className="font-medium">Automatic Saving:</span> New order is automatically saved when you drop an image</li>
									<li><span className="font-medium">Exit Arrange:</span> Click "Exit Arrange" to return to normal viewing mode</li>
								</ul>
							</div>
							
							{/* Tips Section */}
							<div className="bg-neutral-900 p-4 rounded-md border border-neutral-800">
								<h3 className="text-lg font-medium mb-2 flex items-center help-section-title">
									<PlusCircle className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
									Pro Tips
								</h3>
								<ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1 help-section-list help-section-content">
									<li>Use descriptive titles and detailed descriptions to make searching easier</li>
									<li>Create collections for different themes or projects to keep your gallery organized</li>
									<li>Images can be added to multiple collections without creating duplicates</li>
									<li>The gallery supports various image formats including JPG, PNG, GIF, and WebP</li>
									<li>Use the search function to quickly find specific images by title or description</li>
								</ul>
							</div>
						</div>
					</div>
					<DialogFooter className="pt-2 border-t">
						<Button onClick={() => setHowItWorksDialogOpen(false)}>
							Got it!
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
			<style jsx>{`
                .slider-custom::-webkit-slider-thumb {
                    appearance: none;
                    height: 16px;
                    width: 16px;
                    border-radius: 50%;
                    background: #D3B86A;
                    cursor: pointer;
                    border: 2px solid #1e293b;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    transition: all 0.2s ease;
                }
                
                // ... existing styles ...
                
                /* Help dialog responsive styles */
                @media (max-width: 640px) {
                    .help-dialog-content {
                        padding: 16px !important;
                        max-width: 95vw !important;
                    }
                    
                    .help-section-title {
                        font-size: 16px;
                    }
                    
                    .help-section-content {
                        font-size: 12px;
                    }
                    
                    .help-section-list {
                        padding-left: 16px;
                    }
                }
            `}</style>
		</div>
	);
};

export default GalleryPage;