import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Upload, File, Image, X, CheckCircle, AlertCircle, Eye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

interface FileUploadModalProps {
    isOpen: boolean;
    onClose: () => void;
    onFilesUploaded: (files: File[]) => void;
    onUploadComplete?: (results: any[]) => void;
    allowMultiple?: boolean;
    maxFiles?: number;
    maxSizeMB?: number;
    acceptedTypes?: string[];
    uploadEndpoint?: string;
    showPreview?: boolean;
}

interface FileWithPreview extends File {
    preview?: string;
    uploadStatus?: 'pending' | 'uploading' | 'success' | 'error';
    aiDescription?: string;
    errorMessage?: string;
    uploadProgress?: number;
}

const FileUploadModal: React.FC<FileUploadModalProps> = ({
    isOpen,
    onClose,
    onFilesUploaded,
    onUploadComplete,
    allowMultiple = true,
    maxFiles = 10,
    maxSizeMB = 10,
    acceptedTypes = ['image/*', 'application/pdf', '.txt', '.doc', '.docx'],
    uploadEndpoint,
    showPreview = true
}) => {
    const [files, setFiles] = useState<FileWithPreview[]>([]);
    const [uploading, setUploading] = useState(false);
    const [uploadResults, setUploadResults] = useState<any[]>([]);

    // Handle file drop
    const onDrop = useCallback((acceptedFiles: File[]) => {
        const newFiles = acceptedFiles.slice(0, maxFiles - files.length).map(file => {
            const fileWithPreview = Object.assign(file, {
                preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
                uploadStatus: 'pending' as const,
                uploadProgress: 0
            });

            return fileWithPreview;
        });

        setFiles(prev => [...prev, ...newFiles]);
    }, [files.length, maxFiles]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: acceptedTypes.reduce((acc, type) => {
            acc[type] = [];
            return acc;
        }, {} as any),
        maxSize: maxSizeMB * 1024 * 1024,
        multiple: allowMultiple,
        disabled: uploading
    });

    // Remove file
    const removeFile = (index: number) => {
        setFiles(prev => {
            const newFiles = [...prev];
            if (newFiles[index].preview) {
                URL.revokeObjectURL(newFiles[index].preview!);
            }
            newFiles.splice(index, 1);
            return newFiles;
        });
    };

    // Handle file upload
    const handleUpload = async () => {
        if (files.length === 0) return;

        setUploading(true);
        const results: any[] = [];

        try {
            // If using custom upload endpoint (like gallery), upload files individually
            if (uploadEndpoint) {
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];

                    // Update file status
                    setFiles(prev => prev.map((f, idx) =>
                        idx === i ? { ...f, uploadStatus: 'uploading', uploadProgress: 50 } : f
                    ));

                    try {
                        const formData = new FormData();
                        formData.append('image', file);

                        const response = await fetch(uploadEndpoint, {
                            method: 'POST',
                            body: formData,
                            credentials: 'include'
                        });

                        const data = await response.json();

                        if (data.success) {
                            setFiles(prev => prev.map((f, idx) =>
                                idx === i ? {
                                    ...f,
                                    uploadStatus: 'success',
                                    uploadProgress: 100,
                                    aiDescription: data.image?.description
                                } : f
                            ));
                            results.push(data.image);
                        } else {
                            setFiles(prev => prev.map((f, idx) =>
                                idx === i ? {
                                    ...f,
                                    uploadStatus: 'error',
                                    errorMessage: data.message
                                } : f
                            ));
                        }
                    } catch (error) {
                        setFiles(prev => prev.map((f, idx) =>
                            idx === i ? {
                                ...f,
                                uploadStatus: 'error',
                                errorMessage: 'Upload failed'
                            } : f
                        ));
                    }
                }

                setUploadResults(results);
                if (onUploadComplete) {
                    onUploadComplete(results);
                }
            } else {
                // For chat uploads, just pass files to parent
                onFilesUploaded(files);
                handleClose();
            }
        } finally {
            setUploading(false);
        }
    };

    // Close modal and cleanup
    const handleClose = () => {
        files.forEach(file => {
            if (file.preview) {
                URL.revokeObjectURL(file.preview);
            }
        });
        setFiles([]);
        setUploadResults([]);
        onClose();
    };

    // Format file size
    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    // Get file type icon
    const getFileIcon = (file: File) => {
        if (file.type.startsWith('image/')) return <Image className="h-4 w-4" />;
        return <File className="h-4 w-4" />;
    };

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'success': return 'text-green-600';
            case 'error': return 'text-red-600';
            case 'uploading': return 'text-blue-600';
            default: return 'text-gray-600';
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Upload Files</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* Upload Area */}
                    {!uploading && files.length < maxFiles && (
                        <div
                            {...getRootProps()}
                            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragActive
                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                                }`}
                        >
                            <input {...getInputProps()} />
                            <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                                {isDragActive
                                    ? 'Drop files here...'
                                    : 'Drag & drop files here, or click to select'
                                }
                            </p>
                            <p className="text-xs text-gray-500">
                                Max {maxFiles} files, {maxSizeMB}MB each
                            </p>
                            <div className="flex flex-wrap gap-1 justify-center mt-2">
                                {acceptedTypes.map(type => (
                                    <Badge key={type} variant="outline" className="text-xs">
                                        {type.replace('application/', '').replace('*', 'all')}
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* File List */}
                    {files.length > 0 && (
                        <div className="space-y-2">
                            <h4 className="font-medium text-sm">Selected Files ({files.length})</h4>
                            <AnimatePresence>
                                {files.map((file, index) => (
                                    <motion.div
                                        key={`${file.name}-${index}`}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                        className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-slate-700 rounded-lg"
                                    >
                                        {/* File Preview/Icon */}
                                        <div className="flex-shrink-0">
                                            {showPreview && file.preview ? (
                                                <img
                                                    src={file.preview}
                                                    alt={file.name}
                                                    className="w-10 h-10 object-cover rounded"
                                                />
                                            ) : (
                                                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-600 rounded flex items-center justify-center">
                                                    {getFileIcon(file)}
                                                </div>
                                            )}
                                        </div>

                                        {/* File Info */}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium truncate">{file.name}</p>
                                            <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>

                                            {/* AI Description */}
                                            {file.aiDescription && (
                                                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                                                    AI: {file.aiDescription.slice(0, 60)}...
                                                </p>
                                            )}

                                            {/* Error Message */}
                                            {file.errorMessage && (
                                                <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                                                    {file.errorMessage}
                                                </p>
                                            )}

                                            {/* Upload Progress */}
                                            {file.uploadStatus === 'uploading' && (
                                                <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                                                    <div
                                                        className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                                                        style={{ width: `${file.uploadProgress}%` }}
                                                    />
                                                </div>
                                            )}
                                        </div>

                                        {/* Status Icon */}
                                        <div className="flex-shrink-0 flex items-center gap-2">
                                            {file.uploadStatus === 'success' && (
                                                <CheckCircle className="h-4 w-4 text-green-600" />
                                            )}
                                            {file.uploadStatus === 'error' && (
                                                <AlertCircle className="h-4 w-4 text-red-600" />
                                            )}
                                            {file.uploadStatus === 'uploading' && (
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
                                            )}

                                            {/* Remove button */}
                                            {!uploading && file.uploadStatus !== 'uploading' && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => removeFile(index)}
                                                    className="h-6 w-6 p-0"
                                                >
                                                    <X className="h-3 w-3" />
                                                </Button>
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}

                    {/* Upload Results Summary */}
                    {uploadResults.length > 0 && (
                        <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                            <p className="text-sm text-green-700 dark:text-green-300">
                                ✅ Successfully uploaded {uploadResults.length} file(s) with AI analysis
                            </p>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-2 pt-4">
                        <Button variant="outline" onClick={handleClose} disabled={uploading}>
                            {uploadResults.length > 0 ? 'Close' : 'Cancel'}
                        </Button>
                        {files.length > 0 && (
                            <Button
                                onClick={handleUpload}
                                disabled={uploading || files.length === 0}
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                            >
                                {uploading ? 'Uploading...' : `Upload ${files.length} file(s)`}
                            </Button>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default FileUploadModal;