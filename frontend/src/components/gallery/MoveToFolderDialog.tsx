import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { FolderPlus, Folder as FolderIcon, Home, Loader2 } from 'lucide-react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';

interface Folder {
    id: number;
    name: string;
    description?: string;
    cover_image_url?: string;
    image_count: number;
}

interface MoveToFolderDialogProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
    imageIds: number[];
    currentFolderId: number | null;
}

const MoveToFolderDialog: React.FC<MoveToFolderDialogProps> = ({
    open,
    onClose,
    onSuccess,
    imageIds,
    currentFolderId
}) => {
    const [folders, setFolders] = useState<Folder[]>([]);
    const [loading, setLoading] = useState(false);
    const [movingTo, setMovingTo] = useState<number | null>(null);
    const [loadingFolders, setLoadingFolders] = useState(false);

    // Fetch folders when dialog opens
    useEffect(() => {
        if (open) {
            fetchFolders();
        }
    }, [open]);

    const fetchFolders = async () => {
        setLoadingFolders(true);
        try {
            const response = await axios.get(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/folders`,
                { withCredentials: true }
            );

            if (response.data.success) {
                setFolders(response.data.folders);
            } else {
                toast.error('Failed to load folders');
            }
        } catch (error) {
            console.error('Error fetching folders:', error);
            toast.error('Error loading folders');
        } finally {
            setLoadingFolders(false);
        }
    };

    const moveToFolder = async (folderId: number | null) => {
        if (imageIds.length === 0) {
            toast.error('No images selected to move');
            return;
        }

        setMovingTo(folderId);
        setLoading(true);

        try {
            const response = await axios.put(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/images/move-batch`,
                {
                    image_ids: imageIds,
                    folder_id: folderId
                },
                { withCredentials: true }
            );

            if (response.data.success) {
                const destination = folderId ? `folder "${folders.find(f => f.id === folderId)?.name}"` : 'root';
                toast.success(`Moved ${imageIds.length} image${imageIds.length !== 1 ? 's' : ''} to ${destination}`);
                onSuccess();
                onClose();
            } else {
                toast.error(response.data.message || 'Failed to move images');
            }
        } catch (error) {
            console.error('Error moving images:', error);
            toast.error('Error moving images');
        } finally {
            setLoading(false);
            setMovingTo(null);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Move to Folder</DialogTitle>
                    <DialogDescription>
                        Select a destination folder for {imageIds.length} image{imageIds.length !== 1 ? 's' : ''}
                    </DialogDescription>
                </DialogHeader>

                <div className="py-4">
                    <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-2">
                        {/* Move to root option */}
                        <Button
                            variant={currentFolderId === null ? "default" : "outline"}
                            className="w-full justify-start mb-4"
                            onClick={() => moveToFolder(null)}
                            disabled={loading || currentFolderId === null}
                        >
                            {movingTo === null && loading ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Home className="h-4 w-4 mr-2" />
                            )}
                            Root (No Folder)
                        </Button>

                        {loadingFolders ? (
                            <div className="flex justify-center py-4">
                                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                            </div>
                        ) : folders.length > 0 ? (
                            folders.map(folder => (
                                <Button
                                    key={folder.id}
                                    variant={currentFolderId === folder.id ? "default" : "outline"}
                                    className="w-full justify-start mb-2"
                                    onClick={() => moveToFolder(folder.id)}
                                    disabled={loading || currentFolderId === folder.id}
                                >
                                    {movingTo === folder.id && loading ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <FolderIcon className="h-4 w-4 mr-2" />
                                    )}
                                    {folder.name}
                                    <span className="ml-auto text-xs text-gray-500">
                                        {folder.image_count} image{folder.image_count !== 1 ? 's' : ''}
                                    </span>
                                </Button>
                            ))
                        ) : (
                            <div className="text-center py-8 text-gray-500">
                                <FolderPlus className="h-10 w-10 mx-auto mb-2 text-gray-400" />
                                <p>No folders available</p>
                                <p className="text-sm">Create a folder first</p>
                            </div>
                        )}
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={onClose}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default MoveToFolderDialog; 