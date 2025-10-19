'use client'

import { FiCopy, FiThumbsUp, FiThumbsDown, FiVolume2, FiRefreshCw, FiFile } from 'react-icons/fi'
import { FiCheck } from 'react-icons/fi'
import { motion } from 'framer-motion'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MessageProps {
    id: string;
    content: string;
    type: 'user' | 'ai';
    timestamp?: string;
    attachments?: Array<{
        type: 'image' | 'file';
        url: string;
        name: string;
    }>;
    liked?: boolean;
    disliked?: boolean;
    onCopy?: (content: string, stripFormatting?: boolean) => void;
    onLike?: (id: string, isLike: boolean) => void;
    onSpeak?: (content: string) => void;
    onRetry?: (id: string) => void;
    onDownload?: (url: string, filename: string) => void;
}

export default function Message({
    id,
    content,
    type,
    timestamp,
    attachments,
    liked,
    disliked,
    onCopy,
    onLike,
    onSpeak,
    onRetry,
    onDownload
}: MessageProps) {
    const [copied, setCopied] = useState(false);
    
    const handleCopy = (text: string) => {
        if (onCopy) {
            onCopy(text, false); // Keep formatting by default
            setCopied(true);
            setTimeout(() => {
                setCopied(false);
            }, 2000); // Show checkmark for 2 seconds
        }
    };
    
    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${type === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
        >
            <div className={`
                ${type === 'user' ? 'bg-neutral-900' : 'bg-transparent'} 
                text-[20px] font-public-sans font-light text-white px-4 py-2 rounded-lg 
                max-w-[80%]
            `}>
                {/* Message Content with Markdown */}
                {type === 'ai' ? (
                    <div className="markdown-content text-[20px] max-[640px]:text-[14px]">
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                                p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                                h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-2" {...props} />,
                                h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-2" {...props} />,
                                h3: ({node, ...props}) => <h3 className="text-lg font-bold mb-2" {...props} />,
                                ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-4" {...props} />,
                                ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-4" {...props} />,
                                li: ({node, ...props}) => <li className="mb-1" {...props} />,
                                a: ({node, ...props}) => <a className="text-blue-400 hover:underline" {...props} />,
                                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-neutral-500 pl-4 italic my-4" {...props} />,
                                code: ({node, className, inline, ...props}: any) => 
                                    inline 
                                        ? <code className="bg-neutral-800 px-1 py-0.5 rounded" {...props} />
                                        : <code className="block bg-neutral-800 p-2 rounded my-2 overflow-x-auto" {...props} />,
                                pre: ({node, ...props}) => <pre className="bg-neutral-800 p-2 rounded my-2 overflow-x-auto" {...props} />,
                                strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                                em: ({node, ...props}) => <em className="italic" {...props} />,
                                table: ({node, ...props}) => <table className="border-collapse w-full my-4" {...props} />,
                                th: ({node, ...props}) => <th className="border border-neutral-600 px-2 py-1 bg-neutral-800" {...props} />,
                                td: ({node, ...props}) => <td className="border border-neutral-600 px-2 py-1" {...props} />
                            }}
                        >
                            {content}
                        </ReactMarkdown>
                    </div>
                ) : (
                    <p className="whitespace-pre-wrap text-[20px] max-[640px]:text-[14px]">{content}</p>
                )}

                {/* Attachments */}
                <div className="mt-2 space-y-2">
                    {attachments?.map((attachment, index) => (
                        <div 
                            key={index} 
                            className="flex items-center gap-2 p-2 bg-neutral-800/50 rounded"
                        >
                            <FiFile className="text-neutral-400" />
                            <span className="text-sm truncate">{attachment.name}</span>
                            {onDownload && (
                                <button 
                                    onClick={() => onDownload(attachment.url, attachment.name)}
                                    className="ml-auto text-[12px] text-neutral-400 hover:text-white"
                                >
                                    Download
                                </button>
                            )}
                        </div>
                    ))}
                </div>

                {/* Action Buttons for AI messages */}
                {type === 'ai' && (
                    <div className="flex items-center gap-2 mt-2 pt-2">
                        {onCopy && (
                            <button
                                onClick={() => handleCopy(content)}
                                className={`${copied ? 'text-green-400' : 'hover:text-white'} p-1`}
                                title={copied ? "Copied!" : "Copy"}
                            >
                                {copied ? <FiCheck size={14} /> : <FiCopy size={14} />}
                            </button>
                        )}
                        {onLike && (
                            <>
                                <button
                                    onClick={() => onLike(id, true)}
                                    className={`p-1 ${liked ? 'text-green-400' : 'text-white hover:text-white/80'}`}
                                    title="Like"
                                >
                                    <FiThumbsUp size={14} />
                                </button>
                                <button
                                    onClick={() => onLike(id, false)}
                                    className={`p-1 ${disliked ? 'text-red-400' : 'text-white hover:text-white/80'}`}
                                    title="Dislike"
                                >
                                    <FiThumbsDown size={14} />
                                </button>
                            </>
                        )}
                        {onSpeak && (
                            <button
                                onClick={() => onSpeak(content)}
                                className="hover:text-white/80 p-1"
                                title="Read aloud"
                            >
                                <FiVolume2 size={14} />
                            </button>
                        )}
                        {onRetry && (
                            <button
                                onClick={() => onRetry(id)}
                                className="hover:text-white/80 p-1"
                                title="Retry"
                            >
                                <FiRefreshCw size={14} />
                            </button>
                        )}
                    </div>
                )}

                {/* Timestamp */}
                {timestamp && (
                    <div className="text-[10px] text-neutral-500 mt-4">
                        {timestamp}
                    </div>
                )}
            </div>
        </motion.div>
    )
} 