'use client'

import React, { useState, useRef, useCallback } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
    Upload,
    File,
    FileText,
    Image,
    FileSpreadsheet,
    X,
    CheckCircle,
    AlertCircle,
    Loader2,
    Info,
    Camera,
    FileIcon,
    Pencil
} from 'lucide-react'
import toast from '@/components/ui/sound-toast'

interface EnhancedFileUploadModalProps {
    isOpen: boolean
    onClose: () => void
    onFilesUploaded?: (files: File[], imageDescriptions?: Record<string, string>) => void
    onUploadComplete?: (results: any[]) => void
    mode?: 'images' | 'documents' | 'both'
}

interface UploadFile {
    file: File
    id: string
    status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
    progress: number
    error?: string
    result?: any
    type: 'image' | 'document'
    description?: string
}

const IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
const DOCUMENT_TYPES = [
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/csv'
]

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export default function EnhancedFileUploadModal({
    isOpen,
    onClose,
    onFilesUploaded,
    onUploadComplete,
    mode = 'both'
}: EnhancedFileUploadModalProps) {
    const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([])
    const [isUploading, setIsUploading] = useState(false)
    const [activeTab, setActiveTab] = useState(mode === 'documents' ? 'documents' : 'images')
    const [dragActive, setDragActive] = useState(false)
    const [editingDescriptionId, setEditingDescriptionId] = useState<string | null>(null)
    const imageInputRef = useRef<HTMLInputElement>(null)
    const documentInputRef = useRef<HTMLInputElement>(null)

    const getFileIcon = (fileType: string, type: 'image' | 'document') => {
        if (type === 'image') {
            return <Image className="w-6 h-6 text-green-500" />
        }

        if (fileType === 'application/pdf') return <FileText className="w-6 h-6 text-red-500" />
        if (fileType.includes('word')) return <FileText className="w-6 h-6 text-blue-500" />
        if (fileType === 'text/csv') return <FileSpreadsheet className="w-6 h-6 text-green-500" />
        return <File className="w-6 h-6 text-gray-500" />
    }

    const validateFile = (file: File, type: 'image' | 'document'): string | null => {
        const allowedTypes = type === 'image' ? IMAGE_TYPES : DOCUMENT_TYPES

        if (!allowedTypes.includes(file.type)) {
            return `File type ${file.type} is not supported for ${type} uploads.`
        }
        if (file.size > MAX_FILE_SIZE) {
            return 'File size exceeds 10MB limit.'
        }
        return null
    }

    const handleFiles = useCallback((files: FileList | File[], type: 'image' | 'document') => {
        const newFiles: UploadFile[] = []

        Array.from(files).forEach(file => {
            const error = validateFile(file, type)
            if (error) {
                toast.error(error)
                return
            }

            const uploadFile: UploadFile = {
                file,
                id: Math.random().toString(36).substr(2, 9),
                status: 'pending',
                progress: 0,
                type,
                description: ''
            }
            newFiles.push(uploadFile)
        })

        setUploadFiles(prev => [...prev, ...newFiles])
    }, [])

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true)
        } else if (e.type === 'dragleave') {
            setDragActive(false)
        }
    }, [])

    const handleDrop = useCallback((e: React.DragEvent, type: 'image' | 'document') => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files, type)
        }
    }, [handleFiles])

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'image' | 'document') => {
        if (e.target.files) {
            handleFiles(e.target.files, type)
        }
    }, [handleFiles])

    const removeFile = (id: string) => {
        setUploadFiles(prev => prev.filter(file => file.id !== id))
    }

    const startEditingDescription = (id: string) => {
        setEditingDescriptionId(id);
    };

    const updateFileDescription = (id: string, description: string) => {
        setUploadFiles(prev => prev.map(file =>
            file.id === id ? { ...file, description } : file
        ));
    };

    const finishEditingDescription = () => {
        setEditingDescriptionId(null);
    };

    const uploadFile = async (uploadFile: UploadFile) => {
        const formData = new FormData()
        formData.append(uploadFile.type === 'image' ? 'image' : 'file', uploadFile.file)

        try {
            setUploadFiles(prev => prev.map(f =>
                f.id === uploadFile.id
                    ? { ...f, status: 'uploading', progress: 0 }
                    : f
            ))

            const endpoint = uploadFile.type === 'image'
                ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/gallery/upload`
                : `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/upload`

            const response = await axios.post(
                endpoint,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    withCredentials: true,
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round(
                            (progressEvent.loaded * 100) / (progressEvent.total || 1)
                        )
                        setUploadFiles(prev => prev.map(f =>
                            f.id === uploadFile.id
                                ? { ...f, progress: percentCompleted }
                                : f
                        ))
                    }
                }
            )

            if (response.data.success) {
                setUploadFiles(prev => prev.map(f =>
                    f.id === uploadFile.id
                        ? {
                            ...f,
                            status: 'processing',
                            progress: 100,
                            result: response.data
                        }
                        : f
                ))

                // Simulate processing time
                setTimeout(() => {
                    setUploadFiles(prev => prev.map(f =>
                        f.id === uploadFile.id
                            ? { ...f, status: 'completed' }
                            : f
                    ))

                    if (onUploadComplete) {
                        onUploadComplete([response.data])
                    }

                    const fileName = uploadFile.file.name
                    if (uploadFile.type === 'image') {
                        toast.success(`Image "${fileName}" uploaded and analyzed successfully!`)
                    } else {
                        toast.success(`Document "${fileName}" uploaded and processed successfully!`)
                    }
                }, 2000)
            } else {
                throw new Error(response.data.message || 'Upload failed')
            }
        } catch (error: any) {
            console.error('Upload error:', error)
            const errorMessage = error.response?.data?.message || error.message || 'Upload failed'

            setUploadFiles(prev => prev.map(f =>
                f.id === uploadFile.id
                    ? { ...f, status: 'error', error: errorMessage }
                    : f
            ))

            toast.error(`Failed to upload "${uploadFile.file.name}": ${errorMessage}`)
        }
    }

    const uploadAllFiles = async () => {
        setIsUploading(true)

        const pendingFiles = uploadFiles.filter(f => f.status === 'pending')
        console.log(`📤 Uploading ${pendingFiles.length} files`);

        // If using onFilesUploaded (for chat), pass files directly
        if (onFilesUploaded && !pendingFiles.some(f => f.type === 'document')) {
            // Create a map of filenames to descriptions
            const imageDescriptions: Record<string, string> = {};
            pendingFiles.forEach(file => {
                if (file.type === 'image' && file.description) {
                    imageDescriptions[file.file.name] = file.description;
                    console.log(`📝 Adding description for ${file.file.name}: ${file.description.substring(0, 50)}...`);
                }
            });

            console.log(`📝 Image descriptions to send: `, imageDescriptions);
            console.log(`📤 Files to send: `, pendingFiles.map(f => f.file.name));

            onFilesUploaded(pendingFiles.map(f => f.file), imageDescriptions);
            handleClose();
            return;
        }

        try {
            await Promise.all(pendingFiles.map(uploadFile))
        } finally {
            setIsUploading(false)
        }
    }

    const handleClose = () => {
        if (isUploading) {
            toast.error('Please wait for uploads to complete')
            return
        }
        setUploadFiles([])
        onClose()
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending': return 'text-gray-500'
            case 'uploading': return 'text-blue-500'
            case 'processing': return 'text-yellow-500'
            case 'completed': return 'text-green-500'
            case 'error': return 'text-red-500'
            default: return 'text-gray-500'
        }
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pending': return <Info className="w-4 h-4" />
            case 'uploading': return <Loader2 className="w-4 h-4 animate-spin" />
            case 'processing': return <Loader2 className="w-4 h-4 animate-spin" />
            case 'completed': return <CheckCircle className="w-4 h-4" />
            case 'error': return <AlertCircle className="w-4 h-4" />
            default: return <Info className="w-4 h-4" />
        }
    }

    const renderUploadArea = (type: 'image' | 'document') => {
        const fileInputRef = type === 'image' ? imageInputRef : documentInputRef
        const acceptedFiles = type === 'image'
            ? '.jpg,.jpeg,.png,.gif,.webp'
            : '.pdf,.txt,.doc,.docx,.csv'

        return (
            <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 hover:border-gray-400'
                    }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={(e) => handleDrop(e, type)}
            >
                {type === 'image' ? (
                    <Camera className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                ) : (
                    <FileIcon className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                )}

                <p className="text-lg font-medium mb-2">
                    Drag & drop your {type === 'image' ? 'images' : 'documents'} here
                </p>
                <p className="text-sm text-gray-500 mb-4">
                    or click to browse files
                </p>
                <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                >
                    Browse {type === 'image' ? 'Images' : 'Documents'}
                </Button>
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept={acceptedFiles}
                    onChange={(e) => handleFileInput(e, type)}
                    className="hidden"
                />
            </div>
        )
    }

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Upload className="w-5 h-5" />
                        Upload Files
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {mode === 'both' ? (
                        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                            <TabsList className="grid w-full grid-cols-2">
                                <TabsTrigger value="images" className="flex items-center gap-2">
                                    <Image className="w-4 h-4" />
                                    Images
                                </TabsTrigger>
                                <TabsTrigger value="documents" className="flex items-center gap-2">
                                    <FileText className="w-4 h-4" />
                                    Documents
                                </TabsTrigger>
                            </TabsList>

                            <TabsContent value="images" className="space-y-4">
                                {renderUploadArea('image')}
                                <div className="text-sm text-gray-500">
                                    <p className="font-medium mb-1">Supported image types:</p>
                                    <p>JPEG, PNG, GIF, WebP • Maximum file size: 10MB</p>
                                    <p className="text-xs mt-1">Images will be analyzed by AI and stored in your gallery</p>
                                </div>
                            </TabsContent>

                            <TabsContent value="documents" className="space-y-4">
                                {renderUploadArea('document')}
                                <div className="text-sm text-gray-500">
                                    <p className="font-medium mb-1">Supported document types:</p>
                                    <p>PDF, Word documents (.doc, .docx), Text files (.txt), CSV files</p>
                                    <p>Maximum file size: 10MB</p>
                                    <p className="text-xs mt-1">Documents will be processed by AI and stored in your knowledge base</p>
                                </div>
                            </TabsContent>
                        </Tabs>
                    ) : (
                        <>
                            {renderUploadArea(mode === 'documents' ? 'document' : 'image')}
                            <div className="text-sm text-gray-500">
                                {mode === 'documents' ? (
                                    <>
                                        <p className="font-medium mb-1">Supported document types:</p>
                                        <p>PDF, Word documents (.doc, .docx), Text files (.txt), CSV files</p>
                                        <p>Maximum file size: 10MB</p>
                                    </>
                                ) : (
                                    <>
                                        <p className="font-medium mb-1">Supported image types:</p>
                                        <p>JPEG, PNG, GIF, WebP • Maximum file size: 10MB</p>
                                    </>
                                )}
                            </div>
                        </>
                    )}

                    {/* File List */}
                    {uploadFiles.length > 0 && (
                        <div className="space-y-2">
                            <h3 className="font-medium">Files to Upload ({uploadFiles.length}):</h3>
                            {uploadFiles.map((uploadFile) => (
                                <Card key={uploadFile.id} className="border">
                                    <CardContent className="p-4">
                                        <div className="flex items-center gap-3">
                                            {getFileIcon(uploadFile.file.type, uploadFile.type)}
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium truncate">
                                                    {uploadFile.file.name}
                                                </p>
                                                <p className="text-sm text-gray-500">
                                                    {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB • {uploadFile.type}
                                                </p>

                                                {/* Add description editing for images */}
                                                {uploadFile.type === 'image' && uploadFile.status === 'pending' && (
                                                    <div className="mt-2">
                                                        {editingDescriptionId === uploadFile.id ? (
                                                            <div className="space-y-2">
                                                                <Textarea
                                                                    placeholder="Add a description for this image..."
                                                                    value={uploadFile.description || ''}
                                                                    onChange={(e) => updateFileDescription(uploadFile.id, e.target.value)}
                                                                    className="h-20 text-sm"
                                                                />
                                                                <Button
                                                                    size="sm"
                                                                    variant="outline"
                                                                    onClick={finishEditingDescription}
                                                                    className="text-xs"
                                                                >
                                                                    Done
                                                                </Button>
                                                            </div>
                                                        ) : (
                                                            <div
                                                                className="flex items-center gap-1 text-xs text-blue-500 cursor-pointer mt-1"
                                                                onClick={() => startEditingDescription(uploadFile.id)}
                                                            >
                                                                <Pencil className="h-3 w-3" />
                                                                {uploadFile.description ? 'Edit description' : 'Add description'}
                                                                {uploadFile.description && (
                                                                    <span className="text-gray-500 ml-1">
                                                                        ({uploadFile.description.length > 20 ?
                                                                            uploadFile.description.substring(0, 20) + '...' :
                                                                            uploadFile.description})
                                                                    </span>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className={`flex items-center gap-1 ${getStatusColor(uploadFile.status)}`}>
                                                    {getStatusIcon(uploadFile.status)}
                                                    <span className="text-sm capitalize">
                                                        {uploadFile.status === 'processing' ? 'Processing...' : uploadFile.status}
                                                    </span>
                                                </div>
                                                {uploadFile.status === 'pending' && (
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => removeFile(uploadFile.id)}
                                                    >
                                                        <X className="w-4 h-4" />
                                                    </Button>
                                                )}
                                            </div>
                                        </div>

                                        {uploadFile.status === 'uploading' && (
                                            <div className="mt-2">
                                                <Progress value={uploadFile.progress} className="h-2" />
                                                <p className="text-sm text-gray-500 mt-1">
                                                    {uploadFile.progress}% uploaded
                                                </p>
                                            </div>
                                        )}

                                        {uploadFile.status === 'error' && uploadFile.error && (
                                            <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-600">
                                                {uploadFile.error}
                                            </div>
                                        )}

                                        {uploadFile.status === 'completed' && uploadFile.result && (
                                            <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded text-sm">
                                                <p className="font-medium">
                                                    {uploadFile.type === 'image' ? 'AI Analysis:' : 'Processing Summary:'}
                                                </p>
                                                <p className="text-green-600">
                                                    {uploadFile.type === 'image'
                                                        ? uploadFile.result.image?.description || 'Image analyzed successfully'
                                                        : uploadFile.result.processing_summary?.summary || 'Document processed successfully'
                                                    }
                                                </p>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-2 pt-4">
                        <Button
                            variant="outline"
                            onClick={handleClose}
                            disabled={isUploading}
                        >
                            Cancel
                        </Button>
                        {uploadFiles.length > 0 && (
                            <Button
                                onClick={uploadAllFiles}
                                disabled={isUploading || uploadFiles.every(f => f.status !== 'pending')}
                            >
                                {isUploading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Uploading...
                                    </>
                                ) : (
                                    <>
                                        <Upload className="w-4 h-4 mr-2" />
                                        Upload {uploadFiles.filter(f => f.status === 'pending').length} Files
                                    </>
                                )}
                            </Button>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
} 