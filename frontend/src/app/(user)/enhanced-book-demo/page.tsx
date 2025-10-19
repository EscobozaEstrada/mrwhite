'use client';

import React from 'react';
import EnhancedPDFReader from '@/components/EnhancedPDFReader';
import { motion } from 'framer-motion';
import { BookOpen, Highlighter, MessageSquare, Zap, Target, Sparkles } from 'lucide-react';

const EnhancedBookDemo = () => {
    return (
        <div className="min-h-screen bg-gray-900">
            {/* Demo Header */}
            <motion.div
                className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white"
                initial={{ y: -100, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.8 }}
            >
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center space-x-4 mb-4">
                        <BookOpen className="w-8 h-8" />
                        <h1 className="text-3xl font-bold">Enhanced PDF Reader Demo</h1>
                        <div className="bg-yellow-400 text-black px-3 py-1 rounded-full text-sm font-semibold">
                            BETA
                        </div>
                    </div>

                    <p className="text-xl text-blue-100 mb-6">
                        Experience the future of PDF reading with smart text selection, intelligent highlighting, and seamless note-taking.
                    </p>

                    {/* Feature Highlights */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <Target className="w-6 h-6 text-yellow-400" />
                                <h3 className="font-semibold">Smart Text Selection</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                Precise text selection with automatic word and sentence detection. Works seamlessly across lines and paragraphs.
                            </p>
                        </motion.div>

                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <Highlighter className="w-6 h-6 text-green-400" />
                                <h3 className="font-semibold">Intelligent Highlighting</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                Five color options with smooth animations. Highlights persist across sessions and sync with your notes.
                            </p>
                        </motion.div>

                        <motion.div
                            className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                            whileHover={{ scale: 1.05 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <div className="flex items-center space-x-3 mb-2">
                                <MessageSquare className="w-6 h-6 text-purple-400" />
                                <h3 className="font-semibold">Contextual Notes</h3>
                            </div>
                            <p className="text-sm text-blue-100">
                                Add rich notes to selected text with full context preservation. Quick navigation to any note location.
                            </p>
                        </motion.div>
                    </div>

                    {/* Quick Start Instructions */}
                    <motion.div
                        className="mt-6 bg-white/5 backdrop-blur-sm rounded-lg p-4"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                    >
                        <div className="flex items-center space-x-2 mb-3">
                            <Zap className="w-5 h-5 text-yellow-400" />
                            <h3 className="font-semibold text-lg">Quick Start Guide</h3>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
                            <div className="flex items-center space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">1</span>
                                <span>Select a tool (Highlight/Note)</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">2</span>
                                <span>Choose your color</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">3</span>
                                <span>Select text in the PDF</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">4</span>
                                <span>Watch the magic happen!</span>
                            </div>
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
                <EnhancedPDFReader />
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
                    <h4 className="font-semibold text-white text-sm">Pro Tips</h4>
                </div>
                <div className="space-y-2 text-xs text-gray-300">
                    <p>• Double-click words for instant selection</p>
                    <p>• Use Cmd/Ctrl + A to select all text on page</p>
                    <p>• Click on notes in sidebar to jump to location</p>
                    <p>• Zoom with mouse wheel + Cmd/Ctrl</p>
                    <p>• All progress saves automatically</p>
                </div>
            </motion.div>
        </div>
    );
};

export default EnhancedBookDemo; 