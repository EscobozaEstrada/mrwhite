'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
    Calendar,
    Heart,
    Activity,
    TrendingUp,
    Bell,
    MessageCircle,
    Plus,
    Search,
    Filter,
    Download,
    AlertTriangle,
    CheckCircle,
    Clock,
    DollarSign,
    Shield
} from 'lucide-react';

// Types
interface HealthRecord {
    id: number;
    pet_id?: number;
    record_type: string;
    title: string;
    description?: string;
    record_date: string;
    veterinarian_name?: string;
    clinic_name?: string;
    cost?: number;
    insurance_covered: boolean;
    insurance_amount?: number;
    notes?: string;
    tags?: string;
    created_at: string;
    updated_at: string;
    vaccination_details?: any[];
    medication_details?: any[];
}

interface HealthReminder {
    id: number;
    pet_id?: number;
    reminder_type: string;
    title: string;
    description?: string;
    due_date: string;
    reminder_date?: string;
    status: string;
    send_email: boolean;
    send_push: boolean;
    created_at: string;
}

interface HealthInsight {
    id: number;
    pet_id?: number;
    insight_type: string;
    title: string;
    content: string;
    confidence_score?: number;
    shown_to_user: boolean;
    user_feedback?: string;
    created_at: string;
}

interface HealthSummary {
    total_records: number;
    total_cost: number;
    insurance_savings: number;
    record_types: { [key: string]: number };
    recent_records: number;
    upcoming_reminders: number;
    overdue_reminders: number;
}

const HealthDashboard: React.FC = () => {
    // State management
    const [activeTab, setActiveTab] = useState('overview');
    const [healthRecords, setHealthRecords] = useState<HealthRecord[]>([]);
    const [reminders, setReminders] = useState<HealthReminder[]>([]);
    const [insights, setInsights] = useState<HealthInsight[]>([]);
    const [summary, setSummary] = useState<HealthSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Search and filter states
    const [searchQuery, setSearchQuery] = useState('');
    const [recordTypeFilter, setRecordTypeFilter] = useState('');
    const [dateRange, setDateRange] = useState({ start: '', end: '' });

    // Chat states
    const [chatMessage, setChatMessage] = useState('');
    const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
    const [chatLoading, setChatLoading] = useState(false);

    // Load data on component mount
    useEffect(() => {
        loadHealthData();
    }, []);

    const loadHealthData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Load all health data in parallel
            const [records, reminders, insights, summary] = await Promise.all([
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/records`, {
                    credentials: 'include'
                }),
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/reminders`, {
                    credentials: 'include'
                }),
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/insights`, {
                    credentials: 'include'
                }),
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/summary`, {
                    credentials: 'include'
                })
            ]);

            if (!records.ok || !reminders.ok || !insights.ok || !summary.ok) {
                throw new Error('Failed to load health data');
            }

            const [recordsData, remindersData, insightsData, summaryData] = await Promise.all([
                records.json(),
                reminders.json(),
                insights.json(),
                summary.json()
            ]);

            setHealthRecords(recordsData.records || []);
            setReminders(remindersData.reminders || []);
            setInsights(insightsData.insights || []);
            setSummary(summaryData.summary || null);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load health data');
            console.error('Error loading health data:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            loadHealthData();
            return;
        }

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/records?search=${encodeURIComponent(searchQuery)}`, {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();
            setHealthRecords(data.records || []);
        } catch (err) {
            console.error('Search error:', err);
        }
    };

    const handleChatSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!chatMessage.trim()) return;

        const userMessage = chatMessage.trim();
        setChatMessage('');
        setChatHistory(prev => [...prev, { role: 'user', content: userMessage }]);
        setChatLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    message: userMessage,
                    context: 'health_dashboard'
                })
            });

            if (!response.ok) throw new Error('Chat request failed');

            const data = await response.json();
            setChatHistory(prev => [...prev, { role: 'assistant', content: data.response }]);
        } catch (err) {
            setChatHistory(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            }]);
        } finally {
            setChatLoading(false);
        }
    };

    const completeReminder = async (reminderId: number) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/enhanced-reminders/complete/${reminderId}`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    completion_method: 'web_portal',
                    notes: ''
                })
            });

            if (!response.ok) throw new Error('Failed to complete reminder');

            const data = await response.json();
            if (data.success) {
                // Refresh reminders
                setReminders(prev => prev.filter(r => r.id !== reminderId));
            }
        } catch (err) {
            console.error('Error completing reminder:', err);
        }
    };

    const generateInsights = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health/insights/generate`, {
                method: 'POST',
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to generate insights');

            const data = await response.json();
            setInsights(data.insights || []);
        } catch (err) {
            console.error('Error generating insights:', err);
        }
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const getRecordTypeColor = (type: string) => {
        const colors: { [key: string]: string } = {
            vaccination: 'bg-green-100 text-green-800',
            vet_visit: 'bg-blue-100 text-blue-800',
            medication: 'bg-purple-100 text-purple-800',
            surgery: 'bg-red-100 text-red-800',
            checkup: 'bg-yellow-100 text-yellow-800',
            emergency: 'bg-red-100 text-red-800',
            dental: 'bg-indigo-100 text-indigo-800'
        };
        return colors[type] || 'bg-gray-100 text-gray-800';
    };

    const getReminderUrgency = (dueDate: string) => {
        const today = new Date();
        const due = new Date(dueDate);
        const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

        if (diffDays < 0) return { color: 'bg-red-100 text-red-800', text: 'Overdue' };
        if (diffDays <= 3) return { color: 'bg-orange-100 text-orange-800', text: 'Due Soon' };
        if (diffDays <= 7) return { color: 'bg-yellow-100 text-yellow-800', text: 'Upcoming' };
        return { color: 'bg-green-100 text-green-800', text: 'Scheduled' };
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2">Loading health data...</span>
            </div>
        );
    }

    if (error) {
        return (
            <Alert className="m-4">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
            </Alert>
        );
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Health & Savings Tracker</h1>
                    <p className="text-gray-600">Monitor your pet's health journey and manage care expenses</p>
                </div>
                <Button onClick={loadHealthData} variant="outline">
                    <Activity className="w-4 h-4 mr-2" />
                    Refresh Data
                </Button>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-5">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="records">Health Records</TabsTrigger>
                    <TabsTrigger value="reminders">Reminders</TabsTrigger>
                    <TabsTrigger value="insights">AI Insights</TabsTrigger>
                    <TabsTrigger value="chat">Chat with Data</TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview" className="space-y-6">
                    {summary && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Total Records</CardTitle>
                                    <Heart className="h-4 w-4 text-muted-foreground" />
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{summary.total_records}</div>
                                    <p className="text-xs text-muted-foreground">
                                        {summary.recent_records} added this month
                                    </p>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
                                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{formatCurrency(summary.total_cost)}</div>
                                    <p className="text-xs text-muted-foreground">
                                        {formatCurrency(summary.insurance_savings)} covered by insurance
                                    </p>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Active Reminders</CardTitle>
                                    <Bell className="h-4 w-4 text-muted-foreground" />
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">{summary.upcoming_reminders}</div>
                                    <p className="text-xs text-muted-foreground">
                                        {summary.overdue_reminders} overdue
                                    </p>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle className="text-sm font-medium">Insurance Coverage</CardTitle>
                                    <Shield className="h-4 w-4 text-muted-foreground" />
                                </CardHeader>
                                <CardContent>
                                    <div className="text-2xl font-bold">
                                        {summary.total_cost > 0 ? Math.round((summary.insurance_savings / summary.total_cost) * 100) : 0}%
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Average coverage rate
                                    </p>
                                </CardContent>
                            </Card>
                        </div>
                    )}

                    {/* Recent Activity */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Health Activity</CardTitle>
                            <CardDescription>Latest health records and reminders</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {healthRecords.slice(0, 5).map((record) => (
                                    <div key={record.id} className="flex items-center justify-between p-4 border rounded-lg">
                                        <div className="flex items-center space-x-4">
                                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                            <div>
                                                <p className="font-medium">{record.title}</p>
                                                <p className="text-sm text-gray-600">{formatDate(record.record_date)}</p>
                                            </div>
                                        </div>
                                        <Badge className={getRecordTypeColor(record.record_type)}>
                                            {record.record_type.replace('_', ' ').toUpperCase()}
                                        </Badge>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Health Records Tab */}
                <TabsContent value="records" className="space-y-6">
                    <div className="flex flex-col sm:flex-row gap-4">
                        <div className="flex-1">
                            <div className="relative">
                                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                                <Input
                                    placeholder="Search health records..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10"
                                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                                />
                            </div>
                        </div>
                        <Button onClick={handleSearch}>
                            <Search className="w-4 h-4 mr-2" />
                            Search
                        </Button>
                        <Button>
                            <Plus className="w-4 h-4 mr-2" />
                            Add Record
                        </Button>
                    </div>

                    <div className="grid gap-4">
                        {healthRecords.map((record) => (
                            <Card key={record.id}>
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <CardTitle className="text-lg">{record.title}</CardTitle>
                                            <CardDescription>
                                                {record.clinic_name && `${record.clinic_name} • `}
                                                {formatDate(record.record_date)}
                                            </CardDescription>
                                        </div>
                                        <Badge className={getRecordTypeColor(record.record_type)}>
                                            {record.record_type.replace('_', ' ').toUpperCase()}
                                        </Badge>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    {record.description && (
                                        <p className="text-gray-700 mb-3">{record.description}</p>
                                    )}

                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                        {record.veterinarian_name && (
                                            <div>
                                                <span className="font-medium">Veterinarian:</span>
                                                <p className="text-gray-600">{record.veterinarian_name}</p>
                                            </div>
                                        )}

                                        {record.cost && (
                                            <div>
                                                <span className="font-medium">Cost:</span>
                                                <p className="text-gray-600">{formatCurrency(record.cost)}</p>
                                            </div>
                                        )}

                                        {record.insurance_covered && record.insurance_amount && (
                                            <div>
                                                <span className="font-medium">Insurance:</span>
                                                <p className="text-gray-600">{formatCurrency(record.insurance_amount)}</p>
                                            </div>
                                        )}

                                        {record.tags && (
                                            <div>
                                                <span className="font-medium">Tags:</span>
                                                <p className="text-gray-600">{record.tags}</p>
                                            </div>
                                        )}
                                    </div>

                                    {record.notes && (
                                        <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                                            <span className="font-medium text-sm">Notes:</span>
                                            <p className="text-sm text-gray-700 mt-1">{record.notes}</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Reminders Tab */}
                <TabsContent value="reminders" className="space-y-6">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl font-semibold">Health Reminders</h2>
                        <Button>
                            <Plus className="w-4 h-4 mr-2" />
                            Add Reminder
                        </Button>
                    </div>

                    <div className="grid gap-4">
                        {reminders.map((reminder) => {
                            const urgency = getReminderUrgency(reminder.due_date);
                            return (
                                <Card key={reminder.id}>
                                    <CardHeader>
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <CardTitle className="text-lg">{reminder.title}</CardTitle>
                                                <CardDescription>
                                                    Due: {formatDate(reminder.due_date)}
                                                </CardDescription>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge className={urgency.color}>
                                                    {urgency.text}
                                                </Badge>
                                                <Button
                                                    size="sm"
                                                    onClick={() => completeReminder(reminder.id)}
                                                >
                                                    <CheckCircle className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    {reminder.description && (
                                        <CardContent>
                                            <p className="text-gray-700">{reminder.description}</p>
                                        </CardContent>
                                    )}
                                </Card>
                            );
                        })}
                    </div>
                </TabsContent>

                {/* AI Insights Tab */}
                <TabsContent value="insights" className="space-y-6">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl font-semibold">AI Health Insights</h2>
                        <Button onClick={generateInsights}>
                            <TrendingUp className="w-4 h-4 mr-2" />
                            Generate New Insights
                        </Button>
                    </div>

                    <div className="grid gap-4">
                        {insights.map((insight) => (
                            <Card key={insight.id}>
                                <CardHeader>
                                    <CardTitle className="text-lg">{insight.title}</CardTitle>
                                    <CardDescription>
                                        {insight.insight_type.replace('_', ' ').toUpperCase()} •
                                        {insight.confidence_score && ` ${Math.round(insight.confidence_score * 100)}% confidence`}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-gray-700">{insight.content}</p>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Chat Tab */}
                <TabsContent value="chat" className="space-y-6">
                    <Card className="h-96">
                        <CardHeader>
                            <CardTitle className="flex items-center">
                                <MessageCircle className="w-5 h-5 mr-2" />
                                Chat with Your Health Data
                            </CardTitle>
                            <CardDescription>
                                Ask questions about your pet's health history, get personalized advice, and explore your data
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="flex flex-col h-full">
                            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                                {chatHistory.length === 0 ? (
                                    <div className="text-center text-gray-500 py-8">
                                        <MessageCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                        <p>Start a conversation about your pet's health!</p>
                                        <p className="text-sm mt-2">
                                            Try asking: "What vaccinations are due soon?" or "Show me my spending trends"
                                        </p>
                                    </div>
                                ) : (
                                    chatHistory.map((message, index) => (
                                        <div
                                            key={index}
                                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                        >
                                            <div
                                                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${message.role === 'user'
                                                    ? 'bg-blue-500 text-white'
                                                    : 'bg-gray-100 text-gray-900'
                                                    }`}
                                            >
                                                {message.content}
                                            </div>
                                        </div>
                                    ))
                                )}

                                {chatLoading && (
                                    <div className="flex justify-start">
                                        <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                                            <div className="flex items-center space-x-2">
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                                                <span>Thinking...</span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <form onSubmit={handleChatSubmit} className="flex gap-2">
                                <Input
                                    value={chatMessage}
                                    onChange={(e) => setChatMessage(e.target.value)}
                                    placeholder="Ask about your pet's health data..."
                                    disabled={chatLoading}
                                />
                                <Button type="submit" disabled={chatLoading || !chatMessage.trim()}>
                                    Send
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default HealthDashboard; 