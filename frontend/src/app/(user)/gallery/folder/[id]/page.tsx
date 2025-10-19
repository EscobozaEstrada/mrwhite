"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Folder, ArrowLeft, Image as ImageIcon, Upload, Eye, Trash2, Pencil, Download, Save, X, Maximize2, Search, Grid, List } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
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
} from '@dnd-kit/core';
import {
	arrayMove,
	SortableContext,
	sortableKeyboardCoordinates,
	rectSortingStrategy,
	useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { IoMdMove } from 'react-icons/io';
import { FaFolderOpen } from 'react-icons/fa';

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

interface FolderData {
	id: number;
	name: string;
	description: string;
	display_order: number;
	created_at: string;
	updated_at: string;
	image_count: number;
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

// Create a sortable image card component
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
				className="fixed inset-0 bg-black bg-opacity-95 z-[9999]"
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

const FolderPage = () => {
	const router = useRouter();
	const params = useParams();
	const folderId = params.id as string;

	// State management
	const [folder, setFolder] = useState<FolderData | null>(null);
	const [images, setImages] = useState<GalleryImage[]>([]);
	const [filteredImages, setFilteredImages] = useState<GalleryImage[]>([]);
	const [loading, setLoading] = useState(true);
	const [selectedImage, setSelectedImage] = useState<GalleryImage | null>(null);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [imageToDelete, setImageToDelete] = useState<number | null>(null);
	const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
	const [imageToRemove, setImageToRemove] = useState<number | null>(null);
	const [editingDescription, setEditingDescription] = useState(false);
	const [descriptionValue, setDescriptionValue] = useState('');
	const [isSavingDescription, setIsSavingDescription] = useState(false);
	const [editingTitle, setEditingTitle] = useState(false);
	const [titleValue, setTitleValue] = useState('');
	const [isSavingTitle, setIsSavingTitle] = useState(false);
	const [isFullScreen, setIsFullScreen] = useState(false);
	const [fullScreenImageUrl, setFullScreenImageUrl] = useState<string | null>(null);
	const [dragModeEnabled, setDragModeEnabled] = useState(false);
	const [isDragging, setIsDragging] = useState(false);
	const [draggedImage, setDraggedImage] = useState<GalleryImage | null>(null);
	const [isReordering, setIsReordering] = useState(false);
	const [searchQuery, setSearchQuery] = useState('');
	const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
	const [showUploadDialog, setShowUploadDialog] = useState(false);
	const [isUploading, setIsUploading] = useState(false);

	// Add state variables for folder editing
	const [showEditFolderDialog, setShowEditFolderDialog] = useState(false);
	const [editFolderName, setEditFolderName] = useState('');
	const [editFolderDescription, setEditFolderDescription] = useState('');
	const [isEditingFolder, setIsEditingFolder] = useState(false);

	// Set up sensors for drag and drop
	const sensors = useSensors(
		useSensor(PointerSensor, {
			activationConstraint: {
				distance: 8,
			},
		}),
		useSensor(KeyboardSensor, {
			coordinateGetter: sortableKeyboardCoordinates,
		})
	);

	// Fetch folder and images
	const fetchFolderImages = useCallback(async () => {
		try {
			setLoading(true);

			const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderId}`, {
				withCredentials: true
			});

			if (response.data.success) {
				setFolder(response.data.folder);
				const images = response.data.images;
				setImages(images);
				setFilteredImages(images);
			} else {
				toast.error('Failed to load folder');
				router.push('/gallery');
			}
		} catch (error) {
			console.error('Error fetching folder images:', error);
			toast.error('Failed to load folder');
			router.push('/gallery');
		} finally {
			setLoading(false);
		}
	}, [folderId, router]);

	// Filter images based on search query
	useEffect(() => {
		if (searchQuery.trim() === '') {
			setFilteredImages(images);
		} else {
			const query = searchQuery.toLowerCase();
			setFilteredImages(images.filter(img => 
				img.title.toLowerCase().includes(query) || 
				img.description.toLowerCase().includes(query)
			));
		}
	}, [searchQuery, images]);

	// Handle image click
	const handleImageClick = (image: GalleryImage) => {
		if (dragModeEnabled) return;

		setSelectedImage(image);
		setDescriptionValue(image.description);
		setTitleValue(image.title);
		setEditingDescription(false);
		setEditingTitle(false);
	};

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
		const date = new Date(dateString);
		return new Intl.DateTimeFormat('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		}).format(date);
	};

	// Handle drag start
	const handleDragStart = (event: DragStartEvent) => {
		const { active } = event;
		setIsDragging(true);
		const draggedImage = images.find(img => img.id === active.id);
		if (draggedImage) {
			setDraggedImage(draggedImage);
		}
	};

	// Handle drag end
	const handleDragEnd = async (event: DragEndEvent) => {
		const { active, over } = event;

		setIsDragging(false);
		setDraggedImage(null);

		if (over && active.id !== over.id) {
			const oldIndex = images.findIndex(img => img.id === active.id);
			const newIndex = images.findIndex(img => img.id === over.id);

			if (oldIndex !== -1 && newIndex !== -1) {
				// Set reordering state to show loading UI
				setIsReordering(true);

				const newImages = arrayMove(images, oldIndex, newIndex);
				setImages(newImages);

				// Update order on server
				try {
					await axios.post(
						`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderId}/reorder`,
						{
							imageIds: newImages.map(img => img.id)
						},
						{
							withCredentials: true
						}
					);

					toast.success('Image order updated');
				} catch (error) {
					console.error('Error updating image order:', error);
					toast.error('Failed to update image order');
					// Revert to original order
					fetchFolderImages();
				} finally {
					setIsReordering(false);
				}
			}
		}
	};

	// Handle saving image description
	const handleSaveDescription = async () => {
		if (!selectedImage) return;

		setIsSavingDescription(true);
		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/${selectedImage.id}/description`,
				{ description: descriptionValue },
				{ withCredentials: true }
			);

			if (response.data.success) {
				// Update the image in state
				setImages(prevImages =>
					prevImages.map(img =>
						img.id === selectedImage.id ? { ...img, description: descriptionValue } : img
					)
				);

				// Update the selected image
				setSelectedImage({ ...selectedImage, description: descriptionValue });
				setEditingDescription(false);
				toast.success('Description updated successfully');
			} else {
				toast.error('Failed to update description');
			}
		} catch (error) {
			console.error('Error updating description:', error);
			toast.error('Failed to update description');
		} finally {
			setIsSavingDescription(false);
		}
	};

	// Handle saving image title
	const handleSaveTitle = async () => {
		if (!selectedImage) return;

		setIsSavingTitle(true);
		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/${selectedImage.id}/title`,
				{ title: titleValue },
				{ withCredentials: true }
			);

			if (response.data.success) {
				// Update the image in state
				setImages(prevImages =>
					prevImages.map(img =>
						img.id === selectedImage.id ? { ...img, title: titleValue } : img
					)
				);

				// Update the selected image
				setSelectedImage({ ...selectedImage, title: titleValue });
				setEditingTitle(false);
				toast.success('Title updated successfully');
			} else {
				toast.error('Failed to update title');
			}
		} catch (error) {
			console.error('Error updating title:', error);
			toast.error('Failed to update title');
		} finally {
			setIsSavingTitle(false);
		}
	};

	// Handle removing image from folder
	const handleRemoveFromFolder = async (imageId: number) => {
		try {
			const response = await axios.delete(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderId}/remove-image/${imageId}`,
				{
					withCredentials: true
				}
			);

			if (response.data.success) {
				toast.success('Image removed from folder');
				setSelectedImage(null);
				fetchFolderImages();
			} else {
				toast.error('Failed to remove image from folder');
			}
		} catch (error) {
			console.error('Error removing image from folder:', error);
			toast.error('Failed to remove image from folder');
		} finally {
			setShowRemoveConfirm(false);
			setImageToRemove(null);
		}
	};

	// Show remove confirmation dialog
	const confirmRemove = (imageId: number) => {
		setImageToRemove(imageId);
		setShowRemoveConfirm(true);
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

	// Handle image upload to folder
	const handleImageUpload = async (files: FileList | null) => {
		if (!files || files.length === 0) return;

		setIsUploading(true);

		const formData = new FormData();
		Array.from(files).forEach(file => {
			formData.append('images', file);
		});
		formData.append('folderId', folderId);

		try {
			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/upload-to-folder`,
				formData,
				{
					withCredentials: true,
					headers: { 'Content-Type': 'multipart/form-data' }
				}
			);

			if (response.data.success) {
				toast.success(`${files.length} ${files.length === 1 ? 'image' : 'images'} uploaded to folder`);
				fetchFolderImages();
				setShowUploadDialog(false);
			} else {
				toast.error(response.data.message || 'Failed to upload images');
			}
		} catch (error) {
			console.error('Error uploading images to folder:', error);
			toast.error('Failed to upload images');
		} finally {
			setIsUploading(false);
		}
	};

	// Handle opening the edit folder dialog
	const handleOpenEditFolder = () => {
		if (!folder) return;
		setEditFolderName(folder.name);
		setEditFolderDescription(folder.description || '');
		setShowEditFolderDialog(true);
	};

	// Handle saving folder edit
	const handleSaveFolderEdit = async () => {
		if (!folder) return;
		if (!editFolderName.trim()) {
			toast.error('Folder name is required');
			return;
		}
		
		setIsEditingFolder(true);
		try {
			const response = await axios.put(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/folder/${folderId}`,
				{
					name: editFolderName.trim(),
					description: editFolderDescription.trim()
				},
				{ withCredentials: true }
			);
			
			if (response.data.success) {
				toast.success('Folder updated successfully');
				setShowEditFolderDialog(false);
				// Update the local folder state
				setFolder({
					...folder,
					name: editFolderName.trim(),
					description: editFolderDescription.trim()
				});
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

	// Initial load
	useEffect(() => {
		fetchFolderImages();
	}, [fetchFolderImages]);

	return (
		<div className="min-h-screen bg-background p-4">
			<div className="max-w-7xl mx-auto space-y-6 mb-30">
				{/* Header */}
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					className="rounded-xl shadow-sm pt-6 w-fit"
				>
					<div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
						<div>
							<Button
								variant="outline"
								onClick={() => router.push('/gallery')}
								className="flex items-center gap-2 mb-4"
							>
								<ArrowLeft className="h-4 w-4" />
								Back to Gallery
							</Button>

							{folder && (
								<h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
									<FaFolderOpen className="h-8 w-8 text-blue-600" />
									{folder.name}
									<Button
										variant="ghost"
										size="icon"
										className="h-8 w-8 rounded-full"
										onClick={(e) => {
											e.stopPropagation();
											handleOpenEditFolder();
										}}
										title="Edit folder"
									>
										<Pencil className="h-4 w-4" />
									</Button>
								</h1>
							)}

							{folder?.description && (
								<p className="text-gray-600 dark:text-gray-300 mt-1">
									{folder.description}
								</p>
							)}
						</div>
					</div>
				</motion.div>

				{/* Controls - Similar to gallery page */}
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
							<Button
								variant={dragModeEnabled ? "default" : "outline"}
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
						</div>
					</div>
				</motion.div>

				{/* Images section */}
				<div className="mt-6">
					<h2 className="text-lg font-semibold mb-4">Folder Images</h2>

					{loading ? (
						<div className="flex justify-center py-20">
							<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
						</div>
					) : filteredImages.length === 0 ? (
						<div className="text-center py-16 border border-dashed rounded-lg">
							<ImageIcon className="h-12 w-12 mx-auto text-gray-400 mb-2" />
							<p className="text-gray-500">
								{searchQuery ? 'No images match your search' : 'No images in this folder'}
							</p>
							{!searchQuery && (
								<Button 
									variant="outline" 
									className="mt-4"
									onClick={() => setShowUploadDialog(true)}
								>
									<Upload className="h-4 w-4 mr-2" />
									Upload Images
								</Button>
							)}
						</div>
					) : viewMode === 'grid' ? (
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
								<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
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
							{filteredImages.map((image) => (
								<Card
									key={image.id}
									className="cursor-pointer hover:shadow-md transition-shadow"
									onClick={() => handleImageClick(image)}
								>
									<CardContent className="p-4 flex items-center gap-4">
										<div className="min-w-16 w-16 h-16 relative rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 flex-shrink-0">
											<Image
												src={image.url}
												alt={image.title}
												className="object-cover"
												fill
												loading="lazy"
												crossOrigin="anonymous"
											/>
										</div>
										<div className="flex-1 min-w-0">
											<h3 className="font-medium truncate text-sm">{image.title}</h3>
											<div className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
												{image.description}
											</div>
											<div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
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
							))}
						</div>
					)}
				</div>

				{/* Upload Dialog */}
				<Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
					<DialogContent className="sm:max-w-md">
						<DialogHeader>
							<DialogTitle>Upload Images to Folder</DialogTitle>
							<DialogDescription>
								Select images to upload to "{folder?.name}".
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
									id="image-upload-folder"
								/>
								<label
									htmlFor="image-upload-folder"
									className="inline-flex items-center px-4 py-2 bg-[var(--mrwhite-primary-color)] text-black font-semibold font-sans rounded-lg hover:bg-[var(--mrwhite-primary-color)]/80 cursor-pointer disabled:opacity-50"
								>
									{isUploading ? 'Uploading...' : 'Select Images'}
								</label>
							</div>

							<p className="text-xs text-gray-500 text-center">
								Supported formats: JPG, PNG, GIF, WebP. Max size: <span className="font-bold">&lt;1 MB</span> per image.
							</p>
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
													onClick={() => {
														setEditingTitle(true);
														setTitleValue(selectedImage.title);
													}}
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
														onClick={() => {
															setEditingTitle(false);
															setTitleValue(selectedImage.title);
														}}
														className="h-8 px-2"
														disabled={isSavingTitle}
													>
														<X className="h-4 w-4" />
													</Button>
													<Button
														variant="default"
														size="sm"
														onClick={handleSaveTitle}
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
														onClick={() => {
															setEditingDescription(true);
															setDescriptionValue(selectedImage.description);
														}}
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
															onClick={() => {
																setEditingDescription(false);
																setDescriptionValue(selectedImage.description);
															}}
															className="h-8 px-2"
															disabled={isSavingDescription}
														>
															<X className="h-4 w-4" />
														</Button>
														<Button
															variant="default"
															size="sm"
															onClick={handleSaveDescription}
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
												onClick={() => window.open(selectedImage.url, '_blank')}
											>
												<Download className="h-4 w-4" />
												Download
											</Button>
											<Button
												variant="outline"
												size="sm"
												className="flex items-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
												onClick={() => {
													if (selectedImage) {
														confirmRemove(selectedImage.id);
													}
												}}
											>
												<Trash2 className="h-4 w-4" />
												Remove from Folder
											</Button>
										</div>
									</div>
								</div>
							</>
						)}
					</DialogContent>
				</Dialog>
				{/* Full Screen Image View */}
				{isFullScreen && fullScreenImageUrl && (
					<FullScreenImage
						imageUrl={fullScreenImageUrl}
						onClose={closeFullScreen}
					/>
				)}

				{/* Remove from Folder Confirmation Dialog */}
				<Dialog open={showRemoveConfirm} onOpenChange={setShowRemoveConfirm}>
					<DialogContent className="sm:max-w-sm">
						<DialogHeader>
							<DialogTitle>Confirm Removal</DialogTitle>
							<DialogDescription>
								Are you sure you want to remove this image from the folder? The image will still be available in your gallery.
							</DialogDescription>
						</DialogHeader>
						<div className="flex justify-end gap-2 mt-4">
							<Button variant="outline" onClick={() => setShowRemoveConfirm(false)}>
								No
							</Button>
							<Button onClick={() => imageToRemove && handleRemoveFromFolder(imageToRemove)}>
								Yes
							</Button>
						</div>
					</DialogContent>
				</Dialog>

				{/* Edit Folder Dialog */}
			</div>
			<Dialog open={showEditFolderDialog} onOpenChange={setShowEditFolderDialog}>
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
						<Button variant="outline" onClick={() => setShowEditFolderDialog(false)} disabled={isEditingFolder}>
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
		</div>
	);
};

export default FolderPage;