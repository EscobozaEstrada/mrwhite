'use client'

import { useState, useRef } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { FiUpload, FiX } from 'react-icons/fi'
import Image from 'next/image'

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

    const handleFiles = (files: File[]) => {
        const validFiles = files.filter(file => {
            if (type === 'image') {
                return file.type.startsWith('image/')
            }
            // Add any file type restrictions here if needed
            return true
        })
        setSelectedFiles(prev => [...prev, ...validFiles])
    }

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index))
    }

    const handleUpload = () => {
        onUpload(selectedFiles)
        setSelectedFiles([])
        onClose()
    }

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
                            accept={type === 'image' ? 'image/*' : undefined}
                            onChange={handleChange}
                            className="hidden"
                        />
                    </div>
                </div>

                {selectedFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                        <p className="text-sm text-neutral-400">Selected files:</p>
                        <div className="max-h-[200px] overflow-y-auto space-y-2">
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
                        Upload
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
} 