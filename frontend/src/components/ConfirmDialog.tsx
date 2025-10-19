'use client'

import React from 'react'
import { motion } from 'motion/react'
import { FiAlertTriangle, FiX } from 'react-icons/fi'
import { cn } from '@/lib/utils'

interface ConfirmDialogProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: () => void
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    type?: 'danger' | 'warning' | 'info'
}

export default function ConfirmDialog({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    type = 'danger'
}: ConfirmDialogProps) {
    if (!isOpen) return null

    // Handle confirm action
    const handleConfirm = () => {
        onConfirm()
        onClose()
    }

    // Determine button styles based on type
    const buttonStyles = {
        danger: 'bg-red-600 hover:bg-red-700',
        warning: 'bg-yellow-600 hover:bg-yellow-700',
        info: 'bg-blue-600 hover:bg-blue-700'
    }

    // Determine icon styles based on type
    const iconStyles = {
        danger: 'text-red-500',
        warning: 'text-yellow-500',
        info: 'text-blue-500'
    }

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 bg-black/70 z-50" onClick={onClose} />

            {/* Dialog */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md max-[500px]:w-3/4"
            >
                <div className="bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b border-neutral-800">
                        <div className="flex items-center gap-3">
                            <FiAlertTriangle className={cn("w-5 h-5", iconStyles[type])} />
                            <h3 className="text-lg font-semibold max-[500px]:text-sm">{title}</h3>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-neutral-400 hover:text-white p-1 rounded-full hover:bg-neutral-800"
                        >
                            <FiX className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Body */}
                    <div className="p-6">
                        <p className="text-neutral-300 max-[500px]:text-sm">{message}</p>
                    </div>

                    {/* Footer */}
                    <div className="flex justify-end gap-3 p-4 border-t border-neutral-800">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 max-[500px]:px-2 max-[500px]:py-1 bg-neutral-800 hover:bg-neutral-700 text-white rounded "
                        >
                            {cancelText}
                        </button>
                        <button
                            onClick={handleConfirm}
                            className={cn("px-4 py-2 max-[500px]:px-2 max-[500px]:py-1 text-white rounded", buttonStyles[type])}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </motion.div>
        </>
    )
} 