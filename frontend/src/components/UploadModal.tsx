'use client'

import React, { useState, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { FiUpload, FiX } from 'react-icons/fi'
import Image from 'next/image'
import toast from '@/components/ui/sound-toast'

interface UploadModalProps {
    isOpen: boolean
    onClose: () => void
    onUpload: (files: File[]) => void
    type: 'file' | 'image'
}

export default function UploadModal({
    isOpen,
    onClose,
    onUpload,
    type
}: UploadModalProps) {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFiles, setSelectedFiles] = useState<File[]>([])
    const inputRef = useRef<HTMLInputElement>(null)
    
    // Maximum number of files allowed
    const MAX_FILES = 5

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true)
        } else if (e.type === "dragleave") {
            setDragActive(false)
        }
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        const files = Array.from(e.dataTransfer.files)
        if (files && files.length > 0) {
            handleFiles(files)
        }
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault()
        if (e.target.files && e.target.files.length > 0) {
            handleFiles(Array.from(e.target.files))
        }
    }

    // Define allowed file types
    const IMAGE_TYPES = [
        'image/jpeg', 
        'image/jpg', 
        'image/png', 
        'image/gif', 
        'image/webp',
        'image/svg+xml'
    ]
    
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
    ]
    
    // Function to show file limit error
    const showFileLimitError = () => {
        console.log('Showing file limit error toast')
        const message = `You can only upload a maximum of ${MAX_FILES} files at once.`
        toast.error(message)
    }
    
    const handleFiles = (files: File[]) => {
        console.log(`Attempting to add ${files.length} files. Currently have ${selectedFiles.length}/${MAX_FILES} files.`)
        
        // Check if adding these files would exceed the maximum
        if (selectedFiles.length >= MAX_FILES) {
            console.log('Maximum file limit reached, showing toast notification')
            showFileLimitError()
            return
        }
        
        // Filter files by type
        const validFiles = files.filter(file => {
            if (type === 'image') {
                return IMAGE_TYPES.includes(file.type)
            }
            // Only allow image and text-based files
            return IMAGE_TYPES.includes(file.type) || TEXT_BASED_TYPES.includes(file.type)
        })
        
        // Show error message if some files were filtered out due to type
        if (validFiles.length < files.length) {
            console.log(`${files.length - validFiles.length} files were filtered out due to invalid file types`)
            toast.error('Some files were not added. Only image and text-based files are allowed.')
        }
        
        // Enforce the maximum file limit
        const availableSlots = MAX_FILES - selectedFiles.length
        const filesToAdd = validFiles.slice(0, availableSlots)
        
        // Show warning if some files were cut off due to the limit
        if (filesToAdd.length < validFiles.length) {
            console.log(`${validFiles.length - filesToAdd.length} files were cut off due to the ${MAX_FILES} file limit`)
            toast.error(`Only ${availableSlots} more files could be added due to the ${MAX_FILES} file limit.`)
        }
        
        setSelectedFiles(prev => [...prev, ...filesToAdd])
    }

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index))
    }

    const handleUpload = () => {
        onUpload(selectedFiles)
        setSelectedFiles([])
        onClose()
    }

    // No longer showing test toast on modal open
    
    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-[500px] bg-neutral-900 border-neutral-800">
                <DialogHeader>
                    <DialogTitle className="text-xl font-semibold">
                        Upload {type === 'image' ? 'Images' : 'Files'}
                    </DialogTitle>
                </DialogHeader>

                <div 
                    className={`
                        mt-4 p-8 border-2 border-dashed rounded-lg
                        ${dragActive ? 'border-[var(--mrwhite-primary-color)]' : 'border-neutral-700'}
                        ${dragActive ? 'bg-neutral-800/50' : 'bg-neutral-800/20'}
                        transition-colors duration-200
                    `}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    <div className="flex flex-col items-center justify-center gap-4">
                        <FiUpload className="w-10 h-10 text-neutral-400" />
                        <p className="text-center text-neutral-400">
                            Drag and drop your {type === 'image' ? 'images' : 'files'} here, or{' '}
                            <button
                                onClick={() => inputRef.current?.click()}
                                className="text-[var(--mrwhite-primary-color)] hover:underline"
                            >
                                browse
                            </button>
                        </p>
                        <input
                            ref={inputRef}
                            type="file"
                            multiple
                            accept={type === 'image' ? 
                                'image/jpeg,image/jpg,image/png,image/gif,image/webp,image/svg+xml' : 
                                'image/jpeg,image/jpg,image/png,image/gif,image/webp,image/svg+xml,text/plain,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/rtf,text/markdown,text/csv,application/json,application/xml,text/xml,text/html'}
                            onChange={handleChange}
                            className="hidden"
                        />
                        <div className="text-xs text-neutral-500 text-center mt-2 space-y-1">
                            <p>
                                {type === 'image' ? 
                                    'Supported formats: JPEG, PNG, GIF, WebP, SVG' : 
                                    'Supported formats: Images (JPEG, PNG, GIF, WebP, SVG) and text-based files (PDF, DOC, TXT, RTF, MD, CSV, JSON, XML, HTML)'}
                            </p>
                            <p>Maximum {MAX_FILES} files allowed ({selectedFiles.length}/{MAX_FILES} selected)</p>
                        </div>
                    </div>
                </div>

                {selectedFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                        <p className="text-sm text-neutral-400">Selected files:</p>
                        <div className="max-h-[200px] overflow-y-auto custom-scrollbar pr-2 space-y-2">
                            {selectedFiles.map((file, index) => (
                                <div 
                                    key={index}
                                    className="flex items-center justify-between bg-neutral-800 p-2 rounded"
                                >
                                    <div className="flex items-center gap-2">
                                        {type === 'image' && (
                                            <div className="relative w-8 h-8">
                                                <Image
                                                    src={URL.createObjectURL(file)}
                                                    alt={file.name}
                                                    fill
                                                    className="object-cover rounded"
                                                />
                                            </div>
                                        )}
                                        <span className="text-sm truncate max-w-[300px]">
                                            {file.name}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => removeFile(index)}
                                        className="text-neutral-400 hover:text-white"
                                    >
                                        <FiX />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="mt-6 flex justify-end gap-2">
                    <Button
                        variant="ghost"
                        onClick={onClose}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleUpload}
                        disabled={selectedFiles.length === 0}
                    >
                        Upload {selectedFiles.length > 0 ? `(${selectedFiles.length}/${MAX_FILES})` : ''}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
} 