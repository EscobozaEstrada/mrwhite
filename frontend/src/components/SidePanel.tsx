import { AnimatePresence } from "motion/react";
import { FiClock, FiBookmark, FiSearch, FiX } from "react-icons/fi";
import { motion } from "motion/react";
import { useState } from "react";

interface SidePanelProps {
    type: 'history' | 'bookmarks';
    isOpen: boolean;
    onClose: () => void;
}

interface Message {
    id: number;
    type: string;
    content: string;
    timestamp: Date;
    liked?: boolean;
    disliked?: boolean;
}

interface Bookmark {
    id: number;
    type: string;
    content: string;
    timestamp: Date;
    bookmarkedAt: Date;
}

interface SidePanelProps {
    type: 'history' | 'bookmarks';
    isOpen: boolean;
    onClose: () => void;
}

const SidePanel = ({ type, isOpen, onClose }: SidePanelProps) => {
    
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isExpanded, setIsExpanded] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [showBookmarks, setShowBookmarks] = useState(false);
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [uploadType, setUploadType] = useState('');
    const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
    const [history, setHistory] = useState([

    <AnimatePresence>
        {isOpen && (
            <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed right-0 top-0 h-full w-80 bg-gray-900 border-l z-40"
            >
                <div className="p-4 border-b  flex justify-between items-center">
                    <h2 className="text-white text-lg font-semibold flex items-center gap-2">
                        {type === 'history' ? <FiClock /> : <FiBookmark />}
                        {type === 'history' ? 'History' : 'Bookmarks'}
                    </h2>
                    <div className="flex gap-2">
                        {type === 'history' && (
                            <button className="text-gray-400 hover:text-white text-sm">
                                Clear History
                            </button>
                        )}
                        <button onClick={onClose} className="text-gray-400 hover:text-white">
                            <FiX />
                        </button>
                    </div>
                </div>

                <div className="p-4">
                    <div className="relative mb-4">
                        <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder={`Search ${type}`}
                            className="w-full bg-gray-800 text-white pl-10 pr-4 py-2 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                        />
                    </div>

                    <div className="space-y-4">
                        {type === 'history' ? (
                            history.map((section, index) => (
                                <div key={index}>
                                    <h3 className="text-gray-400 text-sm font-medium mb-2">{section.date}</h3>
                                    <div className="space-y-2">
                                        {section.conversations.map((conv, convIndex) => (
                                            <div key={convIndex} className="text-gray-300 text-sm p-2 hover:bg-gray-800 rounded cursor-pointer">
                                                {conv}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))
                        ) : (
                            bookmarks.map((bookmark, index) => (
                                <div key={index} className="bg-gray-800 p-3 rounded-lg">
                                    <p className="text-gray-300 text-sm">{bookmark.content}</p>
                                    <p className="text-gray-500 text-xs mt-2">
                                        {bookmark.bookmarkedAt?.toLocaleDateString()}
                                    </p>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </motion.div>
        )}
    </AnimatePresence>
    )
};

export default SidePanel;
