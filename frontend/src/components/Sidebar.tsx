'use client'

import { useEffect, useRef, useState } from 'react'
import { FiX, FiTrash } from 'react-icons/fi'
import { BiSolidTrash } from "react-icons/bi";
import { cn } from '@/lib/utils'

interface SidebarProps {
    isOpen: boolean
    onClose: () => void
    title: string
    children: React.ReactNode
    isBookGenerated: boolean
    onClearHistory?: () => void
}

export default function Sidebar({
    isOpen,
    onClose,
    title,
    isBookGenerated,
    onClearHistory,
    children
}: SidebarProps) {
    const sidebarRef = useRef<HTMLDivElement>(null)
    // Add state to track if any dropdown is open
    const [isAnyDropdownOpen, setIsAnyDropdownOpen] = useState(false)

    // Create a function to check if any Radix UI dropdown is open
    const checkForOpenDropdowns = () => {
        // Check for any elements with data-state="open" which indicates an open Radix UI component
        const openElements = document.querySelectorAll('[data-state="open"]');
        const selectContentElements = document.querySelectorAll('[data-radix-select-content]');
        const popperContentElements = document.querySelectorAll('[data-radix-popper-content-wrapper]');

        return openElements.length > 0 || selectContentElements.length > 0 || popperContentElements.length > 0;
    }

    useEffect(() => {
        // Check for open dropdowns periodically when sidebar is open
        if (isOpen) {
            const interval = setInterval(() => {
                setIsAnyDropdownOpen(checkForOpenDropdowns());
            }, 100);

            return () => clearInterval(interval);
        }
    }, [isOpen]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Element;

            // If any dropdown is open, don't close the sidebar
            if (isAnyDropdownOpen) {
                return;
            }

            // Check if the click is inside the sidebar
            if (sidebarRef.current && sidebarRef.current.contains(target)) {
                return;
            }

            // Check if the click is on a Radix UI popover/dialog or portal
            // These elements are often appended to the body and not within our sidebar ref
            if (
                target.closest('[data-radix-popper-content-wrapper]') ||
                target.closest('[role="dialog"]') ||
                target.closest('[role="listbox"]') ||
                target.closest('[data-state="open"]') ||
                target.closest('[data-radix-portal]') ||
                target.closest('[data-radix-select-content]') ||
                target.closest('[data-radix-dropdown-menu-content]')
            ) {
                return;
            }

            // If we get here, it's a genuine outside click
            onClose();
        }

        if (isOpen) {
            // Use mousedown for the initial click, but also handle mouseup events
            document.addEventListener('mousedown', handleClickOutside)
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [isOpen, onClose, isAnyDropdownOpen])

    return (
        <>
            {/* Backdrop */}
            <div
                className={cn(
                    'fixed inset-0 bg-black/50 z-40 transition-opacity duration-300',
                    isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none',
                )}
                onClick={(e) => {
                    // Only close if clicking directly on the backdrop, not on any of its children
                    // And only if no dropdown is open
                    if (e.target === e.currentTarget && !isAnyDropdownOpen) {
                        onClose();
                    }
                }}
            />

            {/* Sidebar */}
            <div
                ref={sidebarRef}
                className={cn(
                    'fixed top-0 right-0 h-screen w-full max-w-[596px] bg-gradient-to-r from-neutral-800 to-black z-40',
                    'transform transition-transform duration-300 ease-in-out',
                    isBookGenerated ? 'max-w-[1192px]' : 'max-w-[596px]',
                    isOpen ? 'translate-x-0' : 'translate-x-full',
                    'pt-[70px] sm:pt-[80px] md:pt-[95px]' // Add padding top to account for navbar height
                )}
                style={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-neutral-800">
                    <div className="flex items-center ">
                        <button
                            onClick={onClose}
                            className="p-1 mr-2 border-2 border-white hover:bg-neutral-800 rounded-full transition-colors cursor-pointer"
                        >
                            <FiX className="w-3 h-3" />
                        </button>
                        <h2 className="text-2xl max-[360px]:text-xl font-work-sans font-bold">{title}</h2>
                    </div>
                    
                    {/* Clear History button only for History sidebar */}
                    {title === "History" && onClearHistory && (
                        <button
                            onClick={onClearHistory}
                            className="p-2 max-[360px]:p-1 max-[360px]:text-sm text-neutral-400 hover:text-white flex items-center gap-1 rounded bg-neutral-800 hover:bg-neutral-700 cursor-pointer"
                        >
                            <BiSolidTrash className="w-5 h-5" />
                            <span className="text-sm">Clear History</span>
                        </button>
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 p-4 overflow-y-auto custom-scrollbar" style={{
                    maxHeight: 'calc(100vh - 70px)'
                }}>
                    {children}
                </div>
            </div>
        </>
    )
} 