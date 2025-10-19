'use client';

import React, { useState, useEffect } from 'react';

export default function BookTestPage() {
    const [tests, setTests] = useState({
        frontend: false,
        backend: false,
        pdfFile: false,
        pdfjs: false,
        apiCalls: false
    });

    const [results, setResults] = useState<string[]>([]);

    const addResult = (message: string) => {
        setResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
        console.log(message);
    };

    useEffect(() => {
        runDiagnostics();
    }, []);

    const runDiagnostics = async () => {
        addResult("🔍 Starting diagnostics...");

        // Test 1: Frontend server
        try {
            const response = await fetch('/manifest.json');
            if (response.ok) {
                setTests(prev => ({ ...prev, frontend: true }));
                addResult("✅ Frontend server is running");
            } else {
                addResult("❌ Frontend server issue");
            }
        } catch (err) {
            addResult("❌ Frontend server not accessible");
        }

        // Test 2: Backend API
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user-books/test-copy?title=The%20Way%20of%20the%20Dog%20Anahata&type=public`);
            const data = await response.json();
            if (data.success) {
                setTests(prev => ({ ...prev, backend: true }));
                addResult(`✅ Backend API working - Book ID: ${data.book_copy.id}`);
                addResult(`📄 PDF URL: ${data.book_copy.original_pdf_url}`);

                // Test 3: PDF file accessibility
                try {
                    const pdfResponse = await fetch(data.book_copy.original_pdf_url, { method: 'HEAD' });
                    if (pdfResponse.ok) {
                        setTests(prev => ({ ...prev, pdfFile: true }));
                        addResult(`✅ PDF file accessible - Size: ${pdfResponse.headers.get('content-length')} bytes`);
                    } else {
                        addResult(`❌ PDF file not accessible - Status: ${pdfResponse.status}`);
                    }
                } catch (err) {
                    addResult(`❌ PDF file fetch error: ${err}`);
                }

                // Test API calls
                await testApiCalls(data.book_copy.id);
            } else {
                addResult("❌ Backend API error");
            }
        } catch (err) {
            addResult(`❌ Backend API error: ${err}`);
        }

        // Test 4: PDF.js loading
        try {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
            script.onload = () => {
                setTests(prev => ({ ...prev, pdfjs: true }));
                addResult("✅ PDF.js loaded successfully");
                addResult(`📚 PDF.js version: ${(window as any).pdfjsLib?.version || 'unknown'}`);
            };
            script.onerror = () => {
                addResult("❌ PDF.js failed to load from CDN");
            };
            document.head.appendChild(script);
        } catch (err) {
            addResult(`❌ PDF.js loading error: ${err}`);
        }
    };

    const testApiCalls = async (bookCopyId: number) => {
        try {
            const [progressRes, notesRes, highlightsRes] = await Promise.all([
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user-books/test-progress/${bookCopyId}`),
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user-books/test-notes/${bookCopyId}`),
                fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user-books/test-highlights/${bookCopyId}`)
            ]);

            const [progressData, notesData, highlightsData] = await Promise.all([
                progressRes.json(),
                notesRes.json(),
                highlightsRes.json()
            ]);

            if (progressData.success && notesData.success && highlightsData.success) {
                setTests(prev => ({ ...prev, apiCalls: true }));
                addResult(`✅ All API calls working - Progress: ${progressData.progress?.current_page}/${progressData.progress?.total_pages}`);
                addResult(`📝 Notes: ${notesData.notes?.length || 0}, Highlights: ${highlightsData.highlights?.length || 0}`);
            } else {
                addResult("❌ Some API calls failed");
            }
        } catch (err) {
            addResult(`❌ API calls error: ${err}`);
        }
    };

    const testPDFViewer = () => {
        window.open('/book', '_blank');
        addResult("🚀 Opened book page in new tab - Check browser console for errors");
    };

    return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-3xl font-bold mb-8">📚 Book Reader Diagnostics</h1>

                {/* Test Status */}
                <div className="grid grid-cols-5 gap-4 mb-8">
                    <div className={`p-4 rounded text-center ${tests.frontend ? 'bg-green-800' : 'bg-red-800'}`}>
                        <div className="text-2xl mb-2">{tests.frontend ? '✅' : '❌'}</div>
                        <div className="text-sm">Frontend</div>
                    </div>
                    <div className={`p-4 rounded text-center ${tests.backend ? 'bg-green-800' : 'bg-red-800'}`}>
                        <div className="text-2xl mb-2">{tests.backend ? '✅' : '❌'}</div>
                        <div className="text-sm">Backend</div>
                    </div>
                    <div className={`p-4 rounded text-center ${tests.pdfFile ? 'bg-green-800' : 'bg-red-800'}`}>
                        <div className="text-2xl mb-2">{tests.pdfFile ? '✅' : '❌'}</div>
                        <div className="text-sm">PDF File</div>
                    </div>
                    <div className={`p-4 rounded text-center ${tests.pdfjs ? 'bg-green-800' : 'bg-red-800'}`}>
                        <div className="text-2xl mb-2">{tests.pdfjs ? '✅' : '❌'}</div>
                        <div className="text-sm">PDF.js</div>
                    </div>
                    <div className={`p-4 rounded text-center ${tests.apiCalls ? 'bg-green-800' : 'bg-red-800'}`}>
                        <div className="text-2xl mb-2">{tests.apiCalls ? '✅' : '❌'}</div>
                        <div className="text-sm">API Calls</div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex space-x-4 mb-8">
                    <button
                        onClick={runDiagnostics}
                        className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded"
                    >
                        🔄 Re-run Tests
                    </button>
                    <button
                        onClick={testPDFViewer}
                        className="bg-green-600 hover:bg-green-700 px-6 py-3 rounded"
                    >
                        🚀 Test Book Page
                    </button>
                    <button
                        onClick={() => window.open(`${process.env.NEXT_PUBLIC_FRONTEND_URL}/books/the-way-of-the-dog-anahata.pdf`, '_blank')}
                        className="bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded"
                    >
                        📄 View PDF Directly
                    </button>
                </div>

                {/* Results Log */}
                <div className="bg-gray-800 rounded p-4">
                    <h3 className="text-lg font-semibold mb-4">📋 Diagnostic Log</h3>
                    <div className="space-y-1 max-h-96 overflow-y-auto font-mono text-sm">
                        {results.map((result, index) => (
                            <div key={index} className="text-gray-300">
                                {result}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Quick Fixes */}
                <div className="mt-8 bg-gray-800 rounded p-4">
                    <h3 className="text-lg font-semibold mb-4">🔧 Quick Fixes</h3>
                    <div className="space-y-2 text-sm">
                        <div>• If PDF.js fails: Check network connection or try using VPN</div>
                        <div>• If PDF file fails: Ensure file was copied correctly to frontend/public/books/</div>
                        <div>• If backend fails: Check if backend server is running on port 5001</div>
                        <div>• If all tests pass but book doesn't show: Check browser console for JavaScript errors</div>
                    </div>
                </div>
            </div>
        </div>
    );
} 