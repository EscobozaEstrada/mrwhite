"use client"

import React, { useState, useEffect, Suspense } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { PremiumGate } from '@/components/PremiumGate';
import { CreditTracker } from '@/components/CreditTracker';
import {
    FileText,
    Upload,
    Calendar,
    Activity,
    Search,
    Bell,
    TrendingUp,
    Heart,
    Plus,
    Filter
} from 'lucide-react';
import { motion } from 'motion/react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { KnowledgeBaseStats, TimelineItem, CareRecord, CareCategory } from '@/types/care-archive';
import EnhancedChatInterface from '@/components/care-archive/EnhancedChatInterface';
import Image from 'next/image';

const CareArchiveDashboard = () => {
    const { user } = useAuth();
    const [stats, setStats] = useState<KnowledgeBaseStats | null>(null);
    const [timeline, setTimeline] = useState<TimelineItem[]>([]);
    const [reminders, setReminders] = useState<CareRecord[]>([]);
    const [categories, setCategories] = useState<CareCategory[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        if (user) {
            fetchDashboardData();
        }
    }, [user]);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);

            // Fetch multiple endpoints in parallel
            const [statsResponse, timelineResponse, remindersResponse, categoriesResponse] =
                await Promise.all([
                    axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/knowledge-base-stats`, {
                        withCredentials: true
                    }),
                    axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/care-timeline?limit=10`, {
                        withCredentials: true
                    }),
                    axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/reminders`, {
                        withCredentials: true
                    }),
                    axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/categories`, {
                        withCredentials: true
                    })
                ]);

            setStats(statsResponse.data.stats);
            setTimeline(timelineResponse.data.timeline);
            setReminders(remindersResponse.data.reminders);
            setCategories(categoriesResponse.data.categories);

        } catch (error: any) {
            console.error('Error fetching dashboard data:', error);
            toast.error('Failed to load care archive data');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const getTimeAgo = (dateString: string) => {
        const now = new Date();
        const date = new Date(dateString);
        const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

        if (diffInHours < 24) {
            return `${diffInHours}h ago`;
        } else {
            const diffInDays = Math.floor(diffInHours / 24);
            return `${diffInDays}d ago`;
        }
    };

    if (loading) {
        return (
            <div className="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50">
                <div className="relative w-16 h-8 mr-4 bg-gradient-to-t from-orange-400 via-yellow-400 to-yellow-200 rounded-t-full shadow-lg shadow-orange-300/50">
                    <Image
                        src="/assets/running-dog.gif"
                        alt="Redirecting"
                        fill
                        priority
                        className="object-contain"
                    />
                </div>
            </div>
        );
    }

    return (
        <PremiumGate
            feature="Care Archive"
        >
            <div className="min-h-screen bg-background">
                <div className="container mx-auto px-4 py-8">
                    {/* Header Section */}
                    <div className="mb-8">
                        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
                            <div>
                                <h1 className="text-3xl font-bold mb-2">Care Archive</h1>
                                <p className="text-gray-400">
                                    Your comprehensive pet care history with AI-powered insights
                                </p>
                            </div>

                            {/* Credit Tracker */}
                            <div className="lg:w-80">
                                <CreditTracker compact={true} showPurchaseOptions={false} />
                            </div>
                        </div>

                        {/* Credit Usage Information */}
                        <div className="mt-4 p-4 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                            <div className="flex items-center gap-2 text-blue-400 text-sm">
                                <Activity className="w-4 h-4" />
                                <span className="font-medium">Credit Usage for Care Archive Features:</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2 text-xs text-blue-300">
                                <div>• Archive Search: 4 credits per query</div>
                                <div>• Enhanced Chat: 8 credits per message</div>
                                <div>• Care Summary: 15 credits per report</div>
                            </div>
                        </div>
                    </div>

                    <Suspense fallback={
                        <div className="flex justify-center items-center h-96">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                        </div>
                    }>
                        <EnhancedChatInterface />
                    </Suspense>
                </div>
            </div>
        </PremiumGate>
    );
};

export default CareArchiveDashboard; 