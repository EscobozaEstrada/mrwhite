import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Folder as FolderIcon, Image as ImageIcon } from 'lucide-react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';

interface FolderDialogProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
    folder?: {
        id: number;
        name: string;
        description?: string;
        cover_image_id?: number;
    };
    availableImages?: Array<{
        id: number;
        url: string;
        title: string;
    }>;
}

const FolderDialog: React.FC<FolderDialogProps> = ({
    open,
    onClose,
    onSuccess,
    folder,
    availableImages = []
}) => {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [coverImageId, setCoverImageId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [showImageSelector, setShowImageSelector] = useState(false);

    const isEditMode = !!folder;

    // Reset form when dialog opens/closes or folder changes
    useEffect(() => {
        if (open && folder) {
            setName(folder.name || '');
            setDescription(folder.description || '');
            setCoverImageId(folder.cover_image_id || null);
        } else if (open) {
            // New folder mode
            setName('');
            setDescription('');
            setCoverImageId(null);
        }
    }, [open, folder]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!name.trim()) {
            toast.error('Folder name is required');
            return;
        }

        setLoading(true);

        try {
            const payload = {
                name,
                description: description || undefined,
                cover_image_id: coverImageId || undefined
            };

            let response;
            
            if (isEditMode && folder) {
                // Update existing folder
                response = await axios.put(
                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/folders/${folder.id}`,
                    payload,
                    { withCredentials: true }
                );
            } else {
                // Create new folder
                response = await axios.post(
                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/folders`,
                    payload,
                    { withCredentials: true }
                );
            }

            if (response.data.success) {
                toast.success(isEditMode ? 'Folder updated successfully' : 'Folder created successfully');
                onSuccess();
                onClose();
            } else {
                toast.error(response.data.message || 'Failed to save folder');
            }
        } catch (error) {
            console.error('Error saving folder:', error);
            toast.error('Error saving folder');
        } finally {
            setLoading(false);
        }
    };

    const toggleImageSelector = () => {
        setShowImageSelector(!showImageSelector);
    };

    const selectCoverImage = (imageId: number) => {
        setCoverImageId(imageId === coverImageId ? null : imageId);
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>{isEditMode ? 'Edit Folder' : 'Create New Folder'}</DialogTitle>
                    <DialogDescription>
                        {isEditMode 
                            ? 'Update your folder details below' 
                            : 'Create a new folder to organize your images'}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label htmlFor="folder-name">Folder Name</Label>
                        <Input
                            id="folder-name"
                            placeholder="Enter folder name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={loading}
                            autoFocus
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="folder-description">Description (optional)</Label>
                        <Textarea
                            id="folder-description"
                            placeholder="Enter folder description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            disabled={loading}
                            className="resize-none h-20"
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between items-center">
                            <Label>Cover Image (optional)</Label>
                            <Button 
                                type="button" 
                                variant="outline" 
                                size="sm"
                                onClick={toggleImageSelector}
                            >
                                {showImageSelector ? 'Hide Images' : 'Select Image'}
                            </Button>
                        </div>

                        {coverImageId ? (
                            <div className="relative h-32 bg-gray-100 dark:bg-gray-800 rounded-md overflow-hidden">
                                {availableImages.find(img => img.id === coverImageId) ? (
                                    <img
                                        src={availableImages.find(img => img.id === coverImageId)?.url}
                                        alt="Cover"
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <div className="flex items-center justify-center h-full">
                                        <ImageIcon className="h-8 w-8 text-gray-400" />
                                        <span className="ml-2 text-sm text-gray-500">Image ID: {coverImageId}</span>
                                    </div>
                                )}
                                <Button
                                    type="button"
                                    variant="destructive"
                                    size="sm"
                                    className="absolute top-2 right-2"
                                    onClick={() => setCoverImageId(null)}
                                >
                                    Remove
                                </Button>
                            </div>
                        ) : (
                            <div className="flex items-center justify-center h-32 bg-gray-100 dark:bg-gray-800 rounded-md">
                                <FolderIcon className="h-10 w-10 text-gray-400" />
                                <span className="ml-2 text-gray-500">No cover image selected</span>
                            </div>
                        )}

                        {showImageSelector && availableImages.length > 0 && (
                            <div className="grid grid-cols-4 gap-2 mt-2 max-h-40 overflow-y-auto p-2 border rounded-md">
                                {availableImages.map(image => (
                                    <div 
                                        key={image.id}
                                        className={`
                                            relative cursor-pointer rounded-md overflow-hidden h-16
                                            ${coverImageId === image.id ? 'ring-2 ring-blue-500' : ''}
                                        `}
                                        onClick={() => selectCoverImage(image.id)}
                                    >
                                        <img
                                            src={image.url}
                                            alt={image.title}
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                ))}
                            </div>
                        )}

                        {showImageSelector && availableImages.length === 0 && (
                            <div className="text-center p-4 text-gray-500">
                                No images available to use as cover
                            </div>
                        )}
                    </div>

                    <DialogFooter className="pt-4">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={onClose}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={loading || !name.trim()}
                        >
                            {loading ? 'Saving...' : isEditMode ? 'Update Folder' : 'Create Folder'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
};

export default FolderDialog; 