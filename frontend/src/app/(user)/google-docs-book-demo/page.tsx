'use client';

import React from 'react';
import GoogleDocsStylePDFReader from '@/components/GoogleDocsStylePDFReader';
import { motion } from 'framer-motion';
import { BookOpen, MessageSquare, MousePointer, Sparkles, Users, Zap } from 'lucide-react';

const GoogleDocsBookDemo = () => {
    return (
        <div className="min-h-screen bg-gray-900">
            {/* Demo Header */}
            <motion.div
                className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 p-6 text-white"
                initial={{ y: -100, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.8 }}
            >
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center space-x-4 mb-4">
                        <BookOpen className="w-8 h-8" />
                        <h1 className="text-3xl font-bold">Google Docs Style PDF Reader</h1>
                        <div className="bg-yellow-400 text-black px-3 py-1 rounded-full text-sm font-semibold">
                            NEW!
                        </div>
                    </div>

                    <p className="text-xl text-blue-100 mb-6">
                        Experience seamless commenting just like Google Docs! Select any text and add comments instantly.
                    </p>

                    {/* Feature Highlights */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <MousePointer className="w-6 h-6 text-yellow-400" />
                                <h3 className="font-semibold">Natural Text Selection</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                Simply select any text and a comment popover appears automatically. No need to activate tools first!
                            </p>
                        </motion.div>

                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <MessageSquare className="w-6 h-6 text-green-400" />
                                <h3 className="font-semibold">Instant Comments</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                Click "Add comment" in the popover to write your thoughts. Comments save instantly to the database.
                            </p>
                        </motion.div>

                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <Users className="w-6 h-6 text-purple-400" />
                                <h3 className="font-semibold">Collaborative Reading</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                View all comments in the sidebar. Click any comment to jump to its location in the text.
                            </p>
                        </motion.div>
                    </div>

                    {/* Google Docs Style Workflow */}
                    <motion.div
                        className="mt-6 bg-white/5 backdrop-blur-sm rounded-lg p-4"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                    >
                        <div className="flex items-center space-x-2 mb-3">
                            <Zap className="w-5 h-5 text-yellow-400" />
                            <h3 className="font-semibold text-lg">Google Docs-Style Workflow</h3>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
                            <div className="flex items-start space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0 mt-1">1</span>
                                <div>
                                    <p className="font-medium">Select Text</p>
                                    <p className="text-blue-200 text-xs">Click and drag to select any text passage</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0 mt-1">2</span>
                                <div>
                                    <p className="font-medium">Popover Appears</p>
                                    <p className="text-blue-200 text-xs">Comment button shows automatically</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0 mt-1">3</span>
                                <div>
                                    <p className="font-medium">Write Comment</p>
                                    <p className="text-blue-200 text-xs">Add your thoughts in the modal</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold shrink-0 mt-1">4</span>
                                <div>
                                    <p className="font-medium">See Results</p>
                                    <p className="text-blue-200 text-xs">Comment appears with visual indicator</p>
                                </div>
                            </div>
                        </div>
                    </motion.div>

                    {/* Key Features */}
                    <motion.div
                        className="mt-4 bg-gradient-to-r from-green-500/20 to-blue-500/20 backdrop-blur-sm rounded-lg p-4"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7 }}
                    >
                        <div className="flex items-center space-x-2 mb-2">
                            <Sparkles className="w-5 h-5 text-yellow-400" />
                            <h3 className="font-semibold">What Makes This Special</h3>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                            <div className="bg-white/10 rounded px-2 py-1">✨ No tool activation needed</div>
                            <div className="bg-white/10 rounded px-2 py-1">💾 Instant database saving</div>
                            <div className="bg-white/10 rounded px-2 py-1">🎯 Precise text linking</div>
                            <div className="bg-white/10 rounded px-2 py-1">🔄 Real-time updates</div>
                            <div className="bg-white/10 rounded px-2 py-1">👥 Multi-user ready</div>
                            <div className="bg-white/10 rounded px-2 py-1">📱 Mobile friendly</div>
                            <div className="bg-white/10 rounded px-2 py-1">🎨 Beautiful animations</div>
                            <div className="bg-white/10 rounded px-2 py-1">⚡ Lightning fast</div>
                        </div>
                    </motion.div>
                </div>
            </motion.div>

            {/* Enhanced PDF Reader */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.8 }}
            >
                <GoogleDocsStylePDFReader />
            </motion.div>

            {/* Feature Details Overlay */}
            <motion.div
                className="fixed bottom-4 right-4 bg-gray-800/90 backdrop-blur-sm border border-gray-600 rounded-lg p-4 max-w-xs"
                initial={{ opacity: 0, x: 100 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1, duration: 0.5 }}
            >
                <div className="flex items-center space-x-2 mb-2">
                    <Sparkles className="w-4 h-4 text-yellow-400" />
                    <h4 className="font-semibold text-white text-sm">Quick Tips</h4>
                </div>
                <div className="space-y-2 text-xs text-gray-300">
                    <p>• Select any text to see the comment popup</p>
                    <p>• Comments save automatically to database</p>
                    <p>• Click comment icons to view details</p>
                    <p>• Use sidebar to navigate all comments</p>
                    <p>• Works exactly like Google Docs!</p>
                </div>
            </motion.div>
        </div>
    );
};

export default GoogleDocsBookDemo; 