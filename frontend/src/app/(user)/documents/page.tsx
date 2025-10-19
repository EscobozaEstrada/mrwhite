'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
    Upload,
    Search,
    FileText,
    Download,
    Trash2,
    Eye,
    MessageCircle,
    Filter,
    SortAsc,
    SortDesc,
    RefreshCw,
    File
} from 'lucide-react'
import toast from '@/components/ui/sound-toast'
import axios from 'axios'
// Simple date formatting function to replace date-fns
const formatDate = (date: string | Date) => {
    const d = new Date(date)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
import EnhancedFileUploadModal from '@/components/EnhancedFileUploadModal'

interface Document {
    id: number
    filename: string
    file_type: string
    file_size: number
    upload_date: string
    processing_status: string
    summary: string
    document_type: string
    s3_url: string
    is_processed: boolean
}

interface DocumentStats {
    total_documents: number
    processed_documents: number
    processing_rate: number
    document_types: Record<string, number>
    vector_stats: {
        total_vectors: number
        namespace: string
    }
}

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [stats, setStats] = useState<DocumentStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [filteredDocuments, setFilteredDocuments] = useState<Document[]>([])
    const [sortBy, setSortBy] = useState<'date' | 'name' | 'type'>('date')
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
    const [showUploadModal, setShowUploadModal] = useState(false)
    const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
    const [chatQuery, setChatQuery] = useState('')
    const [chatResponse, setChatResponse] = useState('')
    const [chatLoading, setChatLoading] = useState(false)

    // Fetch documents
    const fetchDocuments = async () => {
        try {
            setLoading(true)
            const response = await axios.get(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/list`,
                { withCredentials: true }
            )

            if (response.data.success) {
                setDocuments(response.data.documents)
                setStats(response.data.stats)
            } else {
                toast.error('Failed to load documents')
            }
        } catch (error: any) {
            console.error('Error fetching documents:', error)
            toast.error('Failed to load documents')
        } finally {
            setLoading(false)
        }
    }

    // Search documents
    const searchDocuments = async (query: string) => {
        if (!query.trim()) {
            setFilteredDocuments(documents)
            return
        }

        try {
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/search`,
                { query },
                { withCredentials: true }
            )

            if (response.data.success) {
                // Map search results back to document format
                const searchResults = response.data.documents.map((result: any) => {
                    return documents.find(doc => doc.id === result.document_id) || {
                        id: result.document_id || 0,
                        filename: result.filename,
                        file_type: result.document_type,
                        file_size: 0,
                        upload_date: result.upload_timestamp || new Date().toISOString(),
                        processing_status: 'completed',
                        summary: result.content_preview,
                        document_type: result.document_type,
                        s3_url: result.s3_url || '',
                        is_processed: true
                    }
                })
                setFilteredDocuments(searchResults)
            } else {
                toast.error('Search failed')
            }
        } catch (error: any) {
            console.error('Error searching documents:', error)
            toast.error('Search failed')
        }
    }

    // Chat with documents
    const chatWithDocuments = async (query: string) => {
        if (!query.trim()) return

        try {
            setChatLoading(true)
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/chat`,
                { query },
                { withCredentials: true }
            )

            if (response.data.success) {
                setChatResponse(response.data.response)
                toast.success('AI response generated')
            } else {
                toast.error('Chat failed')
            }
        } catch (error: any) {
            console.error('Error chatting with documents:', error)
            toast.error('Chat failed')
        } finally {
            setChatLoading(false)
        }
    }

    // Delete document
    const deleteDocument = async (documentId: number) => {
        if (!confirm('Are you sure you want to delete this document?')) return

        try {
            const response = await axios.delete(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/${documentId}`,
                { withCredentials: true }
            )

            if (response.data.success) {
                toast.success('Document deleted successfully')
                fetchDocuments() // Refresh list
            } else {
                toast.error('Failed to delete document')
            }
        } catch (error: any) {
            console.error('Error deleting document:', error)
            toast.error('Failed to delete document')
        }
    }

    // Download document
    const downloadDocument = (document: Document) => {
        if (document.s3_url) {
            window.open(document.s3_url, '_blank')
        } else {
            toast.error('Download link not available')
        }
    }

    // Sort documents
    const sortDocuments = (docs: Document[]) => {
        return [...docs].sort((a, b) => {
            let aValue: any, bValue: any

            switch (sortBy) {
                case 'name':
                    aValue = a.filename.toLowerCase()
                    bValue = b.filename.toLowerCase()
                    break
                case 'type':
                    aValue = a.document_type
                    bValue = b.document_type
                    break
                case 'date':
                default:
                    aValue = new Date(a.upload_date)
                    bValue = new Date(b.upload_date)
                    break
            }

            if (sortOrder === 'asc') {
                return aValue > bValue ? 1 : -1
            } else {
                return aValue < bValue ? 1 : -1
            }
        })
    }

    // Format file size
    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // Get status color
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800'
            case 'processing': return 'bg-yellow-100 text-yellow-800'
            case 'failed': return 'bg-red-100 text-red-800'
            default: return 'bg-gray-100 text-gray-800'
        }
    }

    // Get document type icon
    const getDocumentIcon = (fileType: string) => {
        if (fileType === 'pdf') return <FileText className="w-4 h-4 text-red-500" />
        if (fileType.includes('word')) return <FileText className="w-4 h-4 text-blue-500" />
        return <File className="w-4 h-4 text-gray-500" />
    }

    useEffect(() => {
        fetchDocuments()
    }, [])

    useEffect(() => {
        if (searchQuery.trim()) {
            const debounceTimer = setTimeout(() => {
                searchDocuments(searchQuery)
            }, 500)
            return () => clearTimeout(debounceTimer)
        } else {
            setFilteredDocuments(documents)
        }
    }, [searchQuery, documents])

    useEffect(() => {
        setFilteredDocuments(sortDocuments(filteredDocuments))
    }, [sortBy, sortOrder])

    if (loading) {
        return (
            <div className="min-h-screen bg-black text-white flex items-center justify-center">
                <div className="text-center">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
                    <p>Loading your documents...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-black text-white p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold mb-2">Document Management</h1>
                        <p className="text-gray-400">Manage your AI-processed documents and chat with them</p>
                    </div>
                    <Button
                        onClick={() => setShowUploadModal(true)}
                        className="bg-blue-600 hover:bg-blue-700"
                    >
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Documents
                    </Button>
                </div>

                {/* Stats Cards */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                        <Card className="bg-gray-900 border-gray-700">
                            <CardContent className="p-4">
                                <div className="text-2xl font-bold text-blue-400">{stats.total_documents}</div>
                                <div className="text-sm text-gray-400">Total Documents</div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gray-900 border-gray-700">
                            <CardContent className="p-4">
                                <div className="text-2xl font-bold text-green-400">{stats.processed_documents}</div>
                                <div className="text-sm text-gray-400">Processed</div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gray-900 border-gray-700">
                            <CardContent className="p-4">
                                <div className="text-2xl font-bold text-yellow-400">{stats.processing_rate.toFixed(1)}%</div>
                                <div className="text-sm text-gray-400">Success Rate</div>
                            </CardContent>
                        </Card>
                        <Card className="bg-gray-900 border-gray-700">
                            <CardContent className="p-4">
                                <div className="text-2xl font-bold text-purple-400">{stats.vector_stats.total_vectors}</div>
                                <div className="text-sm text-gray-400">Vector Chunks</div>
                            </CardContent>
                        </Card>
                    </div>
                )}

                {/* Search and Sort */}
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <Input
                            placeholder="Search documents by name or content..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 bg-gray-900 border-gray-700 text-white"
                        />
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSortBy(sortBy === 'date' ? 'name' : sortBy === 'name' ? 'type' : 'date')}
                            className="border-gray-700 text-gray-300"
                        >
                            <Filter className="w-4 h-4 mr-2" />
                            Sort by {sortBy}
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                            className="border-gray-700 text-gray-300"
                        >
                            {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
                        </Button>
                    </div>
                </div>

                {/* Document Chat */}
                <Card className="bg-gray-900 border-gray-700 mb-6">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <MessageCircle className="w-5 h-5" />
                            Chat with Your Documents
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-2 mb-4">
                            <Input
                                placeholder="Ask questions about your documents..."
                                value={chatQuery}
                                onChange={(e) => setChatQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && chatWithDocuments(chatQuery)}
                                className="bg-gray-800 border-gray-600 text-white"
                            />
                            <Button
                                onClick={() => chatWithDocuments(chatQuery)}
                                disabled={chatLoading || !chatQuery.trim()}
                                className="bg-green-600 hover:bg-green-700"
                            >
                                {chatLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Ask'}
                            </Button>
                        </div>
                        {chatResponse && (
                            <div className="p-4 bg-gray-800 rounded-lg">
                                <p className="text-sm text-gray-300">{chatResponse}</p>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Documents List */}
                <div className="space-y-4">
                    {filteredDocuments.length === 0 ? (
                        <Card className="bg-gray-900 border-gray-700">
                            <CardContent className="p-8 text-center">
                                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                                <h3 className="text-lg font-medium mb-2">No documents found</h3>
                                <p className="text-gray-400 mb-4">
                                    {searchQuery ? 'Try a different search term' : 'Upload your first document to get started'}
                                </p>
                                <Button
                                    onClick={() => setShowUploadModal(true)}
                                    variant="outline"
                                    className="border-gray-600 text-gray-300"
                                >
                                    <Upload className="w-4 h-4 mr-2" />
                                    Upload Document
                                </Button>
                            </CardContent>
                        </Card>
                    ) : (
                        filteredDocuments.map((doc) => (
                            <Card key={doc.id} className="bg-gray-900 border-gray-700">
                                <CardContent className="p-6">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-4">
                                            {getDocumentIcon(doc.file_type)}
                                            <div>
                                                <h3 className="font-medium text-white">{doc.filename}</h3>
                                                <div className="flex items-center gap-4 text-sm text-gray-400 mt-1">
                                                    <span>{formatFileSize(doc.file_size)}</span>
                                                    <span>•</span>
                                                    <span>{format(new Date(doc.upload_date), 'MMM dd, yyyy')}</span>
                                                    <span>•</span>
                                                    <Badge className={getStatusColor(doc.processing_status)}>
                                                        {doc.processing_status}
                                                    </Badge>
                                                    {doc.document_type && (
                                                        <>
                                                            <span>•</span>
                                                            <span className="capitalize">{doc.document_type}</span>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => downloadDocument(doc)}
                                                className="text-gray-400 hover:text-white"
                                            >
                                                <Download className="w-4 h-4" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => setSelectedDocument(doc)}
                                                className="text-gray-400 hover:text-white"
                                            >
                                                <Eye className="w-4 h-4" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => deleteDocument(doc.id)}
                                                className="text-gray-400 hover:text-red-400"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </div>
                                    {doc.summary && (
                                        <div className="mt-4 p-3 bg-gray-800 rounded-lg">
                                            <p className="text-sm text-gray-300">{doc.summary}</p>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ))
                    )}
                </div>

                {/* Upload Modal */}
                <EnhancedFileUploadModal
                    isOpen={showUploadModal}
                    onClose={() => setShowUploadModal(false)}
                    onUploadComplete={() => {
                        setShowUploadModal(false)
                        fetchDocuments()
                    }}
                    mode="documents"
                />
            </div>
        </div>
    )
} 