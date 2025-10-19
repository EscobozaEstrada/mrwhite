'use client'

import { FiFile, FiImage, FiX } from 'react-icons/fi'
import Image from 'next/image'

interface SelectedFile {
    file: File;
    type: 'file' | 'image';
    previewUrl?: string;
}

interface SelectedFilesProps {
    files: SelectedFile[];
    onRemove: (index: number) => void;
}

export default function SelectedFiles({
    files,
    onRemove,
}: SelectedFilesProps) {
    return (
        <div className="flex items-center gap-2 flex-wrap">
            {files.map((file, index) => (
                <div key={index} className="relative group">
                    <div className="w-12 h-12 bg-neutral-800 rounded-sm flex items-center justify-center relative">
                        {file.type === 'image' && file.previewUrl ? (
                            <Image
                                src={file.previewUrl}
                                alt={file.file.name}
                                fill
                                className="object-cover rounded-sm"
                            />
                        ) : (
                            <FiFile className="w-6 h-6 text-neutral-400" />
                        )}
                        <button
                            onClick={() => onRemove(index)}
                            className="absolute -top-2 -right-2 bg-neutral-700 rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <FiX className="w-3 h-3" />
                        </button>
                    </div>
                    <p className="text-[10px] text-neutral-400 mt-1 text-center truncate w-12">
                        {file.file.name.split('.').pop()?.toUpperCase()}
                    </p>
                </div>
            ))}
        </div>
    )
} 