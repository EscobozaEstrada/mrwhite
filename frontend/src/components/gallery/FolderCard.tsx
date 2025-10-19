import React, { useState } from 'react';
import { Folder as FolderIcon, FolderOpen, MoreVertical, Edit, Trash2, Image as ImageIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import Image from 'next/image';

interface FolderCardProps {
    folder: {
        id: number;
        name: string;
        description?: string;
        cover_image_url?: string;
        image_count: number;
    };
    onClick: () => void;
    onEdit: () => void;
    onDelete: () => void;
    isDropTarget?: boolean;
    isDragOver?: boolean;
    onDragOver?: () => void;
    onDragLeave?: () => void;
    onDrop?: () => void;
}

const FolderCard: React.FC<FolderCardProps> = ({ 
    folder, 
    onClick, 
    onEdit, 
    onDelete, 
    isDropTarget = false,
    isDragOver = false,
    onDragOver,
    onDragLeave,
    onDrop
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

    const handleDropdownClick = (e: React.MouseEvent) => {
        e.stopPropagation();
    };

    const handleEditClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        onEdit();
    };

    const handleDeleteClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        onDelete();
    };

    // Handle drag events
    const handleDragOver = (e: React.DragEvent) => {
        if (isDropTarget && onDragOver) {
            e.preventDefault();
            onDragOver();
        }
    };

    const handleDragLeave = (e: React.DragEvent) => {
        if (isDropTarget && onDragLeave) {
            e.preventDefault();
            onDragLeave();
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        if (isDropTarget && onDrop) {
            e.preventDefault();
            onDrop();
        }
    };

    return (
        <Card 
            className={`
                group cursor-pointer hover:shadow-lg transition-all duration-300 overflow-hidden
                ${isDropTarget ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}
                ${isDragOver ? 'ring-2 ring-green-500 bg-green-50 dark:bg-green-900/20' : ''}
            `}
            onClick={onClick}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            <div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-gray-800">
                {/* Folder icon or cover image */}
                {folder.cover_image_url && !imageError ? (
                    <>
                        {!imageLoaded && (
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                            </div>
                        )}
                        <div className="relative w-full h-full">
                            <Image
                                src={folder.cover_image_url}
                                alt={folder.name}
                                className={`object-cover group-hover:scale-105 transition-transform duration-300 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
                                fill
                                onLoad={handleImageLoad}
                                onError={handleImageError}
                                loading="lazy"
                                crossOrigin="anonymous"
                            />
                            <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                                <FolderOpen className="h-16 w-16 text-white drop-shadow-lg" />
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <FolderIcon className="h-20 w-20 text-blue-500 dark:text-blue-400" />
                    </div>
                )}

                {/* Actions dropdown */}
                <div className="absolute top-2 right-2 z-10">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={handleDropdownClick}>
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-8 w-8 rounded-full bg-black/50 text-white hover:bg-black/70"
                            >
                                <MoreVertical className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={handleEditClick}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit Folder
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={handleDeleteClick} className="text-red-500 focus:text-red-500">
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete Folder
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
            <CardContent className="p-3">
                <h3 className="font-medium text-sm truncate">{folder.name}</h3>
                <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500 flex items-center">
                        <ImageIcon className="h-3 w-3 mr-1" />
                        {folder.image_count} {folder.image_count === 1 ? 'image' : 'images'}
                    </span>
                </div>
            </CardContent>
        </Card>
    );
};

export default FolderCard; 