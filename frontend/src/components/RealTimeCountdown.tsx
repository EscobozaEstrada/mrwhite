/**
 * Real-Time Countdown Component
 * Shows live countdown until reminder due date with auto-updates
 */

"use client"

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Clock, AlertTriangle, CheckCircle, Timer, Calendar, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface CountdownData {
    totalSeconds: number;
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
    formatted: string;
    urgency: 'low' | 'medium' | 'high' | 'critical';
    color: string;
    isOverdue: boolean;
    dueLocalTime: string;
    dueLocalDate: string;
    dueTimeOnly: string;
}

interface RealTimeCountdownProps {
    dueDateTime: string | Date;
    userTimezone?: string;
    format?: 'compact' | 'detailed' | 'card';
    className?: string;
    onOverdue?: () => void;
    onCritical?: () => void;
}

export default function RealTimeCountdown({
    dueDateTime,
    userTimezone,
    format = 'detailed',
    className = '',
    onOverdue,
    onCritical
}: RealTimeCountdownProps) {
    const [countdown, setCountdown] = useState<CountdownData | null>(null);
    const [userTz, setUserTz] = useState<string>(userTimezone || 'UTC');
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const previousUrgencyRef = useRef<string>('low');

    // Auto-detect user timezone if not provided
    useEffect(() => {
        if (!userTimezone) {
            const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            setUserTz(detectedTz);
        }
    }, [userTimezone]);

    const calculateCountdown = (): CountdownData => {
        try {
            // Parse due date
            const dueDate = new Date(dueDateTime);
            const now = new Date();

            // Calculate difference in milliseconds
            const diffMs = dueDate.getTime() - now.getTime();
            const isOverdue = diffMs < 0;
            const absDiffMs = Math.abs(diffMs);

            // Convert to components
            const totalSeconds = Math.floor(absDiffMs / 1000);
            const days = Math.floor(totalSeconds / 86400);
            const hours = Math.floor((totalSeconds % 86400) / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = totalSeconds % 60;

            // Format due date in user's timezone
            const dueLocalTime = dueDate.toLocaleString('en-US', {
                timeZone: userTz,
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short'
            });

            const dueLocalDate = dueDate.toLocaleDateString('en-US', {
                timeZone: userTz,
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            const dueTimeOnly = dueDate.toLocaleTimeString('en-US', {
                timeZone: userTz,
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });

            // Determine urgency and formatting
            let formatted: string;
            let urgency: 'low' | 'medium' | 'high' | 'critical';
            let color: string;

            if (isOverdue) {
                if (days > 0) {
                    formatted = `Overdue by ${days} day${days !== 1 ? 's' : ''}`;
                } else if (hours > 0) {
                    formatted = `Overdue by ${hours} hour${hours !== 1 ? 's' : ''}`;
                } else if (minutes > 0) {
                    formatted = `Overdue by ${minutes} minute${minutes !== 1 ? 's' : ''}`;
                } else {
                    formatted = `Overdue by ${seconds} second${seconds !== 1 ? 's' : ''}`;
                }
                urgency = 'critical';
                color = '#dc3545';
            } else if (days > 7) {
                formatted = `Due in ${days} days`;
                urgency = 'low';
                color = '#28a745';
            } else if (days > 1) {
                formatted = `Due in ${days} days, ${hours} hours`;
                urgency = 'medium';
                color = '#ffc107';
            } else if (days === 1) {
                formatted = `Due tomorrow at ${dueTimeOnly}`;
                urgency = 'high';
                color = '#fd7e14';
            } else if (hours > 2) {
                formatted = `Due in ${hours} hours, ${minutes} minutes`;
                urgency = 'high';
                color = '#fd7e14';
            } else if (hours > 0) {
                formatted = `Due in ${hours}h ${minutes}m`;
                urgency = 'critical';
                color = '#dc3545';
            } else {
                formatted = `Due in ${minutes}m ${seconds}s`;
                urgency = 'critical';
                color = '#dc3545';
            }

            return {
                totalSeconds: isOverdue ? -totalSeconds : totalSeconds,
                days,
                hours,
                minutes,
                seconds,
                formatted,
                urgency,
                color,
                isOverdue,
                dueLocalTime,
                dueLocalDate,
                dueTimeOnly
            };
        } catch (error) {
            console.error('Error calculating countdown:', error);
            return {
                totalSeconds: 0,
                days: 0,
                hours: 0,
                minutes: 0,
                seconds: 0,
                formatted: 'Time calculation error',
                urgency: 'low',
                color: '#6c757d',
                isOverdue: false,
                dueLocalTime: 'Invalid date',
                dueLocalDate: 'Invalid date',
                dueTimeOnly: 'Invalid time'
            };
        }
    };

    // Start countdown interval
    useEffect(() => {
        const updateCountdown = () => {
            const newCountdown = calculateCountdown();
            setCountdown(newCountdown);

            // Trigger callbacks for state changes
            if (newCountdown.isOverdue && !previousUrgencyRef.current.includes('overdue')) {
                onOverdue?.();
            }

            if (newCountdown.urgency === 'critical' && previousUrgencyRef.current !== 'critical') {
                onCritical?.();
            }

            previousUrgencyRef.current = newCountdown.isOverdue ? 'overdue' : newCountdown.urgency;
        };

        // Initial calculation
        updateCountdown();

        // Update every second
        intervalRef.current = setInterval(updateCountdown, 1000);

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, [dueDateTime, userTz, onOverdue, onCritical]);

    if (!countdown) {
        return (
            <div className={`flex items-center gap-2 ${className}`}>
                <Clock className="w-4 h-4 animate-spin" />
                <span>Loading...</span>
            </div>
        );
    }

    // Compact format
    if (format === 'compact') {
        return (
            <div className={`flex items-center gap-2 ${className}`}>
                <div
                    className={`w-2 h-2 rounded-full ${countdown.urgency === 'critical' ? 'animate-pulse' : ''}`}
                    style={{ backgroundColor: countdown.color }}
                />
                <span
                    className="text-sm font-medium"
                    style={{ color: countdown.color }}
                >
                    {countdown.formatted}
                </span>
            </div>
        );
    }

    // Card format
    if (format === 'card') {
        return (
            <div className={`p-4 rounded-lg border ${className}`} style={{ borderColor: countdown.color }}>
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        {countdown.isOverdue ? (
                            <AlertCircle className="w-5 h-5 text-red-500" />
                        ) : (
                            <Clock className="w-5 h-5" style={{ color: countdown.color }} />
                        )}
                        <span className="font-semibold" style={{ color: countdown.color }}>
                            {countdown.isOverdue ? 'Overdue' : 'Due'}
                        </span>
                    </div>
                    <div className="text-right">
                        <div className="text-sm text-gray-500">
                            {countdown.dueLocalDate}
                        </div>
                        <div className="text-sm font-medium">
                            {countdown.dueTimeOnly}
                        </div>
                    </div>
                </div>

                <div className="text-lg font-bold mb-2" style={{ color: countdown.color }}>
                    {countdown.formatted}
                </div>

                {!countdown.isOverdue && countdown.urgency === 'critical' && (
                    <div className="flex items-center gap-4 text-sm font-mono">
                        {countdown.days > 0 && <span>{countdown.days}d</span>}
                        {countdown.hours > 0 && <span>{countdown.hours}h</span>}
                        <span>{countdown.minutes}m</span>
                        <span>{countdown.seconds}s</span>
                    </div>
                )}
            </div>
        );
    }

    // Detailed format (default)
    return (
        <div className={`flex items-center gap-3 ${className}`}>
            <div className="flex items-center gap-2">
                {countdown.isOverdue ? (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                ) : countdown.urgency === 'critical' ? (
                    <Clock className="w-5 h-5 animate-pulse" style={{ color: countdown.color }} />
                ) : (
                    <Clock className="w-5 h-5" style={{ color: countdown.color }} />
                )}

                <span
                    className="font-semibold text-lg"
                    style={{ color: countdown.color }}
                >
                    {countdown.formatted}
                </span>
            </div>

            {!countdown.isOverdue && countdown.urgency === 'critical' && (
                <div className="flex items-center gap-2 text-sm font-mono opacity-75">
                    {countdown.days > 0 && <span>{countdown.days}d</span>}
                    {countdown.hours > 0 && <span>{countdown.hours}h</span>}
                    <span>{countdown.minutes}m</span>
                    <span className="animate-pulse">{countdown.seconds}s</span>
                </div>
            )}

            <div className="text-sm text-gray-500">
                <Calendar className="w-4 h-4 inline mr-1" />
                {countdown.dueTimeOnly}
            </div>
        </div>
    );
} 