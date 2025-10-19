/**
 * Intelligent Timezone Selector Component
 * AI-powered timezone detection and selection with auto-complete
 */

"use client"

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
    MapPin,
    Clock,
    Globe,
    Search,
    CheckCircle,
    AlertCircle,
    Loader2,
    Zap,
    Settings,
    Brain
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import toast from 'react-hot-toast';

interface TimezoneInfo {
    source: 'browser' | 'ip' | 'search';
    timezone: string;
    city: string;
    country: string;
    offset: string;
    is_dst: boolean;
    confidence: number;
    display_name: string;
    recommended: boolean;
}

interface TimezoneSettings {
    timezone: string;
    location_city: string;
    location_country: string;
    auto_detect_timezone: boolean;
    time_format_24h: boolean;
    preferred_reminder_times: Record<string, any>;
    current_local_time: string;
    timezone_abbreviation: string;
    formatted_time: string;
}

interface TimezoneSelectorProps {
    onTimezoneChange?: (timezone: string) => void;
    onSettingsChange?: (settings: Partial<TimezoneSettings>) => void;
    initialTimezone?: string;
    showAdvancedSettings?: boolean;
    compact?: boolean;
    className?: string;
}

const TimezoneSelector: React.FC<TimezoneSelectorProps> = ({
    onTimezoneChange,
    onSettingsChange,
    initialTimezone,
    showAdvancedSettings = true,
    compact = false,
    className = ''
}) => {
    const [suggestions, setSuggestions] = useState<TimezoneInfo[]>([]);
    const [settings, setSettings] = useState<TimezoneSettings | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [detecting, setDetecting] = useState(false);
    const [selectedTimezone, setSelectedTimezone] = useState(initialTimezone || '');

    // Load current settings
    const loadSettings = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/user-settings`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setSettings(data.settings);
                    setSelectedTimezone(data.settings.timezone);
                }
            }
        } catch (error) {
            console.error('Failed to load timezone settings:', error);
        }
    };

    // Auto-detect timezone
    const detectTimezone = async () => {
        setDetecting(true);
        try {
            // Get browser timezone info
            const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const browserOffset = new Date().getTimezoneOffset();

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/detect`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    browser_timezone: browserTimezone,
                    user_ip: '',
                    location_hint: ''
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setSuggestions(data.suggestions);

                    // Auto-select the recommended one
                    const recommended = data.auto_detected;
                    if (recommended && settings?.auto_detect_timezone) {
                        setSelectedTimezone(recommended.timezone);
                        await setTimezone(recommended.timezone, recommended.city, recommended.country);
                    }
                }
            } else {
                toast.error('Failed to detect timezone');
            }
        } catch (error) {
            console.error('Timezone detection error:', error);
            toast.error('Timezone detection failed');
        } finally {
            setDetecting(false);
        }
    };

    // Search for timezones
    const searchTimezones = async (query: string) => {
        if (!query.trim()) {
            setSuggestions([]);
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/detect`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    browser_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    user_ip: '',
                    location_hint: ''
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setSuggestions(data.suggestions);
                }
            }
        } catch (error) {
            console.error('Timezone search error:', error);
        } finally {
            setLoading(false);
        }
    };

    // Set timezone
    const setTimezone = async (timezone: string, city: string = '', country: string = '', autoDetect: boolean = true) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/set`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    timezone,
                    city,
                    country,
                    auto_detect: autoDetect
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    setSelectedTimezone(timezone);
                    toast.success('Timezone updated successfully!');

                    // Reload settings
                    await loadSettings();

                    // Notify parent
                    if (onTimezoneChange) {
                        onTimezoneChange(timezone);
                    }
                } else {
                    toast.error(data.error || 'Failed to set timezone');
                }
            }
        } catch (error) {
            console.error('Set timezone error:', error);
            toast.error('Failed to update timezone');
        }
    };

    // Update other settings
    const updateSettings = async (newSettings: Partial<TimezoneSettings>) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/timezone/user-settings`, {
                method: 'PUT',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    timezone: newSettings.timezone || settings?.timezone,
                    location_city: newSettings.location_city || settings?.location_city,
                    location_country: newSettings.location_country || settings?.location_country,
                    time_format_24h: newSettings.time_format_24h !== undefined ? newSettings.time_format_24h : settings?.time_format_24h,
                    auto_detect_timezone: newSettings.auto_detect_timezone !== undefined ? newSettings.auto_detect_timezone : settings?.auto_detect_timezone,
                    preferred_reminder_times: newSettings.preferred_reminder_times || settings?.preferred_reminder_times
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    toast.success('Settings updated!');
                    await loadSettings();

                    if (onSettingsChange) {
                        onSettingsChange(newSettings);
                    }
                }
            }
        } catch (error) {
            console.error('Update settings error:', error);
            toast.error('Failed to update settings');
        }
    };

    useEffect(() => {
        loadSettings();
    }, []);

    useEffect(() => {
        const debounceTimer = setTimeout(() => {
            if (searchQuery.length >= 2) {
                searchTimezones(searchQuery);
            } else {
                setSuggestions([]);
            }
        }, 300);

        return () => clearTimeout(debounceTimer);
    }, [searchQuery]);

    const getConfidenceBadge = (confidence: number) => {
        if (confidence >= 0.9) return <Badge className="bg-green-100 text-green-800 text-xs">High Confidence</Badge>;
        if (confidence >= 0.7) return <Badge className="bg-yellow-100 text-yellow-800 text-xs">Medium Confidence</Badge>;
        return <Badge className="bg-gray-100 text-gray-800 text-xs">Low Confidence</Badge>;
    };

    const getSourceIcon = (source: string) => {
        switch (source) {
            case 'browser': return <Globe className="w-4 h-4 text-blue-500" />;
            case 'ip': return <MapPin className="w-4 h-4 text-orange-500" />;
            case 'search': return <Search className="w-4 h-4 text-purple-500" />;
            default: return <Clock className="w-4 h-4 text-gray-500" />;
        }
    };

    if (compact) {
        return (
            <div className={`space-y-3 ${className}`}>
                <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium">Current Time Zone:</span>
                    <Badge variant="outline">{settings?.timezone_abbreviation || 'UTC'}</Badge>
                </div>

                {settings && (
                    <div className="text-xs text-gray-500">
                        {settings.formatted_time}
                    </div>
                )}

                <Button
                    onClick={detectTimezone}
                    disabled={detecting}
                    variant="outline"
                    size="sm"
                    className="w-full"
                >
                    {detecting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
                    {detecting ? 'Detecting...' : 'Auto-Detect Timezone'}
                </Button>
            </div>
        );
    }

    return (
        <motion.div
            className={`space-y-6 ${className} overflow-y-auto custom-scrollbar max-h-[60vh] pr-2`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            {/* Current Settings */}
            {settings && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Clock className="w-5 h-5" />
                            Current Timezone
                        </CardTitle>
                        <CardDescription>
                            Your current time and location settings
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="flex items-center justify-between">
                            <span className="text-sm">Timezone:</span>
                            <Badge variant="outline">{settings.timezone}</Badge>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-sm">Local Time:</span>
                            <span className="text-sm font-mono">{settings.formatted_time}</span>
                        </div>

                        {settings.location_city && (
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Location:</span>
                                <span className="text-sm">{settings.location_city}, {settings.location_country}</span>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Auto-Detection */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Brain className="w-5 h-5" />
                        AI Timezone Detection
                    </CardTitle>
                    <CardDescription>
                        Automatically detect your timezone using AI
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <Button
                        onClick={detectTimezone}
                        disabled={detecting}
                        className="w-full"
                    >
                        {detecting ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                Detecting Timezone...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4 mr-2" />
                                Auto-Detect My Timezone
                            </>
                        )}
                    </Button>

                    {/* Search */}
                    <div className="space-y-2">
                        <label htmlFor="search-input" className="text-sm font-medium mb-4">Or search for your city:</label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                placeholder="Enter city or country (e.g., New York, London, Tokyo)"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                id="search-input"
                                className="w-full mt-2 bg-[#000000] border border-gray-700 rounded-lg py-2 pl-10 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                            />
                            {loading && (
                                <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Suggestions */}
            <AnimatePresence>
                {suggestions.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <MapPin className="w-5 h-5" />
                                    Timezone Suggestions
                                </CardTitle>
                                <CardDescription>
                                    AI-powered timezone recommendations
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {suggestions.map((suggestion, index) => (
                                    <motion.div
                                        key={`${suggestion.timezone}-${index}`}
                                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${selectedTimezone === suggestion.timezone
                                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                                            : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                        onClick={() => setTimezone(suggestion.timezone, suggestion.city, suggestion.country)}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.1 }}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                {getSourceIcon(suggestion.source)}
                                                <div>
                                                    <div className="font-medium text-sm">{suggestion.display_name}</div>
                                                    <div className="text-xs text-gray-500">
                                                        {suggestion.timezone} (UTC{suggestion.offset})
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                {suggestion.recommended && (
                                                    <Badge className="bg-green-100 text-green-800 text-xs">
                                                        <CheckCircle className="w-3 h-3 mr-1" />
                                                        Recommended
                                                    </Badge>
                                                )}
                                                {getConfidenceBadge(suggestion.confidence)}
                                            </div>
                                        </div>
                                    </motion.div>
                                ))}
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Advanced Settings */}
            {showAdvancedSettings && settings && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Settings className="w-5 h-5" />
                            Advanced Settings
                        </CardTitle>
                        <CardDescription>
                            Customize your time preferences
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <label className="text-sm font-medium">Auto-detect timezone</label>
                                <div className="text-xs text-gray-500">Automatically update timezone when location changes</div>
                            </div>
                            <Button
                                variant={settings.auto_detect_timezone ? "default" : "outline"}
                                size="sm"
                                onClick={() => updateSettings({ auto_detect_timezone: !settings.auto_detect_timezone })}
                            >
                                {settings.auto_detect_timezone ? 'Enabled' : 'Disabled'}
                            </Button>
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <label className="text-sm font-medium">24-hour format</label>
                                <div className="text-xs text-gray-500">Use 24-hour time format instead of 12-hour</div>
                            </div>
                            <Button
                                variant={settings.time_format_24h ? "default" : "outline"}
                                size="sm"
                                onClick={() => updateSettings({ time_format_24h: !settings.time_format_24h })}
                            >
                                {settings.time_format_24h ? '24h' : '12h'}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </motion.div>
    );
};

export default TimezoneSelector; 