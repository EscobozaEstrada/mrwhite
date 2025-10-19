"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Upload, Grid, List, Download, Trash2, Eye, Filter, Image as ImageIcon, Calendar, FileText } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import axios from 'axios';
import { toast } from 'sonner';

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
}

interface GalleryStats {
    total_images: number;
    total_size_mb: number;
    recent_uploads: number;
    storage_limit_mb: number;
    storage_used_percent: number;
}

// Enhanced ImageCard component with loading states and error handling
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
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                )}

                {imageError && (
                    <div className="absolute inset-0 flex items-center justify-center flex-col text-gray-500">
                        <ImageIcon className="h-12 w-12 mb-2" />
                        <span className="text-sm">Failed to load</span>
                    </div>
                )}

                <img
                    src={image.url}
                    alt={image.title}
                    className={`w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'
                        }`}
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                    loading="lazy"
                    crossOrigin="anonymous"
                />

                <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
                    <Eye className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </div>
            </div>
            <CardContent className="p-3">
                <h3 className="font-medium text-sm truncate">{image.title}</h3>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                    {image.description}
                </p>
                <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500">{formatFileSize(image.file_size)}</span>
                    <span className="text-xs text-gray-500">{image.width}×{image.height}</span>
                </div>
            </CardContent>
        </Card>
    );
};

// Enhanced ImageListItem component for list view
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
                <div className="w-16 h-16 relative rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800">
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

                    <img
                        src={image.url}
                        alt={image.title}
                        className={`w-full h-full object-cover ${imageLoaded ? 'opacity-100' : 'opacity-0'
                            }`}
                        onLoad={handleImageLoad}
                        onError={handleImageError}
                        loading="lazy"
                        crossOrigin="anonymous"
                    />
                </div>
                <div className="flex-1">
                    <h3 className="font-medium">{image.title}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
                        {image.description}
                    </p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{formatFileSize(image.file_size)}</span>
                        <span>{image.width}×{image.height}</span>
                        <span>{formatDate(image.uploaded_at)}</span>
                    </div>
                </div>
                <Button variant="ghost" size="sm">
                    <Eye className="h-4 w-4" />
                </Button>
            </CardContent>
        </Card>
    );
};

const GalleryPage = () => {
    // State management
    const [images, setImages] = useState<GalleryImage[]>([]);
    const [filteredImages, setFilteredImages] = useState<GalleryImage[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploadLoading, setUploadLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [selectedImage, setSelectedImage] = useState<GalleryImage | null>(null);
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'name' | 'size'>('newest');
    const [stats, setStats] = useState<GalleryStats | null>(null);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);

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
                const newImages = response.data.images;
                console.log(`✅ Fetched ${newImages.length} images`);
                if (newImages.length > 0) {
                    console.log(`🖼️  First image URL: ${newImages[0].url}`);
                    console.log(`🖼️  Sample image data:`, newImages[0]);
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
                    toast.success(`${file.name} uploaded and analyzed successfully!`);
                    return response.data.image;
                } else {
                    toast.error(`Failed to upload ${file.name}: ${response.data.message}`);
                    return null;
                }
            } catch (error) {
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
        }
    };

    // Filter and sort images
    useEffect(() => {
        let filtered = [...images];

        // Apply search filter
        if (searchQuery) {
            filtered = filtered.filter(img =>
                img.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                img.description.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        // Apply sorting
        filtered.sort((a, b) => {
            switch (sortBy) {
                case 'newest':
                    return new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime();
                case 'oldest':
                    return new Date(a.uploaded_at).getTime() - new Date(b.uploaded_at).getTime();
                case 'name':
                    return a.title.localeCompare(b.title);
                case 'size':
                    return b.file_size - a.file_size;
                default:
                    return 0;
            }
        });

        setFilteredImages(filtered);
    }, [images, searchQuery, sortBy]);

    // Initial load
    useEffect(() => {
        fetchImages();
        fetchStats();
    }, []);

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

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-900 dark:to-slate-800 p-4">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border p-6"
                >
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <ImageIcon className="h-8 w-8 text-blue-600" />
                                Photo Gallery
                            </h1>
                            <p className="text-gray-600 dark:text-gray-300 mt-1">
                                View and manage your uploaded images with AI-powered descriptions
                            </p>
                        </div>

                        <Button
                            onClick={() => setShowUploadDialog(true)}
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                        >
                            <Upload className="h-4 w-4 mr-2" />
                            Upload Images
                        </Button>
                    </div>

                    {/* Statistics */}
                    {stats && (
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
                            <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.total_images}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Total Images</div>
                            </div>
                            <div className="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-green-600 dark:text-green-400">{stats.total_size_mb}MB</div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Storage Used</div>
                            </div>
                            <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.recent_uploads}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Recent (7 days)</div>
                            </div>
                            <div className="text-center p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{stats.storage_used_percent}%</div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">Storage Used</div>
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* Controls */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border p-4"
                >
                    <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
                        <div className="flex flex-1 items-center gap-3">
                            <div className="relative flex-1 max-w-md">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                                <Input
                                    placeholder="Search images by description or filename..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10"
                                />
                            </div>

                            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                                <SelectTrigger className="w-40">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="newest">Newest First</SelectItem>
                                    <SelectItem value="oldest">Oldest First</SelectItem>
                                    <SelectItem value="name">Name A-Z</SelectItem>
                                    <SelectItem value="size">Largest First</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-center gap-2">
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
                        </div>
                    </div>
                </motion.div>

                {/* Gallery */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
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
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                    {filteredImages.map((image, index) => (
                                        <motion.div
                                            key={image.id}
                                            initial={{ opacity: 0, scale: 0.9 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            transition={{ delay: index * 0.05 }}
                                        >
                                            <ImageCard image={image} onClick={() => setSelectedImage(image)} />
                                        </motion.div>
                                    ))}
                                </div>
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

                {/* Upload Dialog */}
                <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
                    <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle>Upload Images</DialogTitle>
                            <DialogDescription>
                                Select images to upload. They will be automatically analyzed with AI.
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
                                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer disabled:opacity-50"
                                >
                                    {uploadLoading ? 'Uploading...' : 'Select Images'}
                                </label>
                            </div>

                            <p className="text-xs text-gray-500 text-center">
                                Supported formats: JPG, PNG, GIF, WebP. Max size: 10MB per image.
                            </p>
                        </div>
                    </DialogContent>
                </Dialog>

                {/* Image Detail Dialog */}
                <Dialog open={!!selectedImage} onOpenChange={() => setSelectedImage(null)}>
                    <DialogContent className="sm:max-w-4xl">
                        {selectedImage && (
                            <>
                                <DialogHeader>
                                    <DialogTitle>{selectedImage.title}</DialogTitle>
                                    <DialogDescription>
                                        Uploaded {formatDate(selectedImage.uploaded_at)}
                                    </DialogDescription>
                                </DialogHeader>

                                <div className="grid md:grid-cols-2 gap-6">
                                    <div>
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
                                    </div>

                                    <div className="space-y-4">
                                        <div>
                                            <h4 className="font-medium mb-2">AI Description</h4>
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                                {selectedImage.description}
                                            </p>
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

                                        <div className="flex gap-2 pt-4">
                                            <Button asChild variant="outline">
                                                <a href={selectedImage.url} target="_blank" rel="noopener noreferrer">
                                                    <Download className="h-4 w-4 mr-2" />
                                                    Download
                                                </a>
                                            </Button>
                                            <Button
                                                variant="destructive"
                                                onClick={() => handleDeleteImage(selectedImage.id)}
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
            </div>
        </div>
    );
};

export default GalleryPage;