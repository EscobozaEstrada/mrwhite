'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    BookOpen,
    Clock,
    Target,
    TrendingUp,
    Calendar,
    Award,
    Play,
    Pause,
    BarChart3,
    BookMarked,
    Timer,
    Flame,
    Trophy
} from 'lucide-react';
import { motion } from 'motion/react';

interface ReadingProgressData {
    id: number;
    current_page: number;
    total_pages: number;
    progress_percentage: number;
    reading_time_minutes: number;
    session_count: number;
    last_read_at: string;
    reading_started_at: string;
    estimated_completion_date?: string;
}

interface ReadingSession {
    id: number;
    start_time: string;
    end_time?: string;
    duration_minutes?: number;
    pages_read: number;
    notes_created: number;
    highlights_created: number;
}

interface ProgressTrackerProps {
    progress: ReadingProgressData;
    currentSession?: ReadingSession | null;
    isReading: boolean;
    onStartSession: () => void;
    onEndSession: () => void;
    className?: string;
}

const ReadingProgressTracker: React.FC<ProgressTrackerProps> = ({
    progress,
    currentSession,
    isReading,
    onStartSession,
    onEndSession,
    className = ''
}) => {
    const [sessionTime, setSessionTime] = useState(0);
    const [readingStreak, setReadingStreak] = useState(0);

    useEffect(() => {
        let interval: NodeJS.Timeout;

        if (isReading && currentSession) {
            interval = setInterval(() => {
                const startTime = new Date(currentSession.start_time).getTime();
                const now = Date.now();
                const elapsed = Math.floor((now - startTime) / 1000 / 60); // minutes
                setSessionTime(elapsed);
            }, 60000); // Update every minute
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isReading, currentSession]);

    // Calculate reading statistics
    const calculateReadingSpeed = () => {
        if (progress.reading_time_minutes === 0) return 0;
        return Math.round(progress.current_page / (progress.reading_time_minutes / 60)); // pages per hour
    };

    const calculateTimeToFinish = () => {
        const remainingPages = progress.total_pages - progress.current_page;
        const readingSpeed = calculateReadingSpeed();
        if (readingSpeed === 0) return 0;
        return Math.round(remainingPages / readingSpeed * 60); // minutes
    };

    const getProgressColor = () => {
        if (progress.progress_percentage < 25) return 'bg-red-500';
        if (progress.progress_percentage < 50) return 'bg-orange-500';
        if (progress.progress_percentage < 75) return 'bg-yellow-500';
        return 'bg-green-500';
    };

    const formatTime = (minutes: number) => {
        if (minutes < 60) return `${minutes}m`;
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hours}h ${mins}m`;
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    return (
        <div className={`space-y-4 ${className}`}>
            {/* Main Progress Card */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                        <BookOpen className="h-5 w-5" />
                        Reading Progress
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        {isReading ? (
                            <Button onClick={onEndSession} variant="destructive" size="sm">
                                <Pause className="h-4 w-4 mr-1" />
                                End Session
                            </Button>
                        ) : (
                            <Button onClick={onStartSession} size="sm">
                                <Play className="h-4 w-4 mr-1" />
                                Start Reading
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Progress Bar */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span>Page {progress.current_page} of {progress.total_pages}</span>
                            <span className="font-semibold">{Math.round(progress.progress_percentage)}%</span>
                        </div>
                        <Progress value={progress.progress_percentage} className="h-3" />
                        <div className="flex justify-between text-xs text-muted-foreground">
                            <span>Started: {formatDate(progress.reading_started_at)}</span>
                            <span>Last read: {formatDate(progress.last_read_at)}</span>
                        </div>
                    </div>

                    {/* Current Session Info */}
                    {isReading && currentSession && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-muted/50 p-3 rounded-lg border border-primary/20"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                    <span className="text-sm font-medium">Reading Session Active</span>
                                </div>
                                <Badge variant="outline" className="text-xs">
                                    {sessionTime} min
                                </Badge>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-xs">
                                <div className="text-center">
                                    <div className="font-medium">{currentSession.notes_created || 0}</div>
                                    <div className="text-muted-foreground">Notes</div>
                                </div>
                                <div className="text-center">
                                    <div className="font-medium">{currentSession.highlights_created || 0}</div>
                                    <div className="text-muted-foreground">Highlights</div>
                                </div>
                                <div className="text-center">
                                    <div className="font-medium">{currentSession.pages_read || 0}</div>
                                    <div className="text-muted-foreground">Pages</div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </CardContent>
            </Card>

            {/* Statistics Tabs */}
            <Card>
                <Tabs defaultValue="overview" className="w-full">
                    <CardHeader className="pb-3">
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
                            <TabsTrigger value="analytics" className="text-xs">Analytics</TabsTrigger>
                            <TabsTrigger value="achievements" className="text-xs">Goals</TabsTrigger>
                        </TabsList>
                    </CardHeader>

                    <CardContent>
                        <TabsContent value="overview" className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <Clock className="h-4 w-4" />
                                        Total Reading Time
                                    </div>
                                    <div className="text-2xl font-bold">
                                        {formatTime(progress.reading_time_minutes)}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <BookMarked className="h-4 w-4" />
                                        Reading Sessions
                                    </div>
                                    <div className="text-2xl font-bold">
                                        {progress.session_count}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <TrendingUp className="h-4 w-4" />
                                        Reading Speed
                                    </div>
                                    <div className="text-2xl font-bold">
                                        {calculateReadingSpeed()} <span className="text-sm font-normal">pages/hr</span>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <Timer className="h-4 w-4" />
                                        Time to Finish
                                    </div>
                                    <div className="text-2xl font-bold">
                                        {formatTime(calculateTimeToFinish())}
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="analytics" className="space-y-4">
                            <div className="space-y-3">
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>Progress Completion</span>
                                        <span>{Math.round(progress.progress_percentage)}%</span>
                                    </div>
                                    <div className="w-full bg-muted rounded-full h-2">
                                        <div
                                            className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                                            style={{ width: `${progress.progress_percentage}%` }}
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3 text-sm">
                                    <div className="bg-muted/50 p-3 rounded-lg">
                                        <div className="font-medium">Average Session</div>
                                        <div className="text-lg font-bold">
                                            {progress.session_count > 0
                                                ? formatTime(Math.round(progress.reading_time_minutes / progress.session_count))
                                                : '0m'
                                            }
                                        </div>
                                    </div>

                                    <div className="bg-muted/50 p-3 rounded-lg">
                                        <div className="font-medium">Pages Remaining</div>
                                        <div className="text-lg font-bold">
                                            {progress.total_pages - progress.current_page}
                                        </div>
                                    </div>
                                </div>

                                {progress.estimated_completion_date && (
                                    <div className="bg-primary/5 p-3 rounded-lg border border-primary/20">
                                        <div className="flex items-center gap-2 text-sm font-medium text-primary">
                                            <Target className="h-4 w-4" />
                                            Estimated Completion
                                        </div>
                                        <div className="text-lg font-bold mt-1">
                                            {formatDate(progress.estimated_completion_date)}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </TabsContent>

                        <TabsContent value="achievements" className="space-y-4">
                            <div className="space-y-3">
                                {/* Progress Milestones */}
                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium flex items-center gap-2">
                                        <Trophy className="h-4 w-4" />
                                        Progress Milestones
                                    </h4>

                                    <div className="space-y-2">
                                        {[25, 50, 75, 100].map((milestone) => (
                                            <div key={milestone} className="flex items-center gap-3">
                                                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${progress.progress_percentage >= milestone
                                                    ? 'bg-primary text-primary-foreground'
                                                    : 'bg-muted text-muted-foreground'
                                                    }`}>
                                                    {progress.progress_percentage >= milestone ? '✓' : milestone}
                                                </div>
                                                <span className={`text-sm ${progress.progress_percentage >= milestone
                                                    ? 'text-foreground font-medium'
                                                    : 'text-muted-foreground'
                                                    }`}>
                                                    {milestone}% Complete
                                                </span>
                                                {progress.progress_percentage >= milestone && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        <Award className="h-3 w-3 mr-1" />
                                                        Achieved
                                                    </Badge>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Reading Streak */}
                                <div className="bg-orange-50 dark:bg-orange-950/20 p-3 rounded-lg border border-orange-200 dark:border-orange-800">
                                    <div className="flex items-center gap-2 text-sm font-medium text-orange-700 dark:text-orange-300">
                                        <Flame className="h-4 w-4" />
                                        Reading Streak
                                    </div>
                                    <div className="text-xl font-bold text-orange-600 dark:text-orange-400 mt-1">
                                        {readingStreak} days
                                    </div>
                                    <div className="text-xs text-orange-600/80 dark:text-orange-400/80 mt-1">
                                        Keep it up! Read daily to maintain your streak.
                                    </div>
                                </div>

                                {/* Session Goals */}
                                <div className="space-y-2">
                                    <h4 className="text-sm font-medium">Session Goals</h4>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className="bg-muted/50 p-2 rounded">
                                            <div className="font-medium">Daily Goal</div>
                                            <div className="text-lg font-bold">30 min</div>
                                        </div>
                                        <div className="bg-muted/50 p-2 rounded">
                                            <div className="font-medium">Today's Progress</div>
                                            <div className="text-lg font-bold">{sessionTime} min</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>
                    </CardContent>
                </Tabs>
            </Card>

            {/* Quick Stats Summary */}
            <div className="grid grid-cols-4 gap-2">
                <Card className="p-3">
                    <div className="text-center">
                        <div className="text-lg font-bold">{Math.round(progress.progress_percentage)}%</div>
                        <div className="text-xs text-muted-foreground">Complete</div>
                    </div>
                </Card>

                <Card className="p-3">
                    <div className="text-center">
                        <div className="text-lg font-bold">{progress.session_count}</div>
                        <div className="text-xs text-muted-foreground">Sessions</div>
                    </div>
                </Card>

                <Card className="p-3">
                    <div className="text-center">
                        <div className="text-lg font-bold">{calculateReadingSpeed()}</div>
                        <div className="text-xs text-muted-foreground">Pages/hr</div>
                    </div>
                </Card>

                <Card className="p-3">
                    <div className="text-center">
                        <div className="text-lg font-bold">{Math.round(progress.reading_time_minutes / 60)}</div>
                        <div className="text-xs text-muted-foreground">Hours</div>
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default ReadingProgressTracker; 