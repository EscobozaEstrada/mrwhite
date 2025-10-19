'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { FiMic, FiUpload, FiX, FiPause, FiPlay, FiTrash, FiCheck, FiLoader } from 'react-icons/fi'
import toast from '@/components/ui/sound-toast'
import axios from 'axios'
import { FaCheckCircle } from 'react-icons/fa'

interface VoiceMessageModalProps {
    isOpen: boolean
    onClose: () => void
    onVoiceMessageReady: (file: File, transcription: string) => void
}

// Define a custom type for blob with S3 URL
interface EnhancedBlob extends Blob {
    s3Url?: string;
}

export default function VoiceMessageModal({
    isOpen,
    onClose,
    onVoiceMessageReady
}: VoiceMessageModalProps) {
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const [recordedBlob, setRecordedBlob] = useState<EnhancedBlob | null>(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [isTranscribing, setIsTranscribing] = useState(false)
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [transcription, setTranscription] = useState('')
    const [isProcessing, setIsProcessing] = useState(false)
    const [isRecordingSupported, setIsRecordingSupported] = useState(true)
    
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const audioChunksRef = useRef<Blob[]>([])
    const audioRef = useRef<HTMLAudioElement | null>(null)
    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    
    // Check browser compatibility on mount
    useEffect(() => {
        const checkRecordingSupport = () => {
            if (!navigator.mediaDevices || 
                !navigator.mediaDevices.getUserMedia || 
                !window.MediaRecorder) {
                setIsRecordingSupported(false)
                console.warn('Audio recording not supported in this browser/environment')
            }
        }
        
        checkRecordingSupport()
    }, [])
    
    // Timer for recording duration
    useEffect(() => {
        if (isRecording) {
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1)
            }, 1000)
        } else if (timerRef.current) {
            clearInterval(timerRef.current)
        }
        
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
            }
        }
    }, [isRecording])
    
    // Format seconds to MM:SS
    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    
    // Automatically transcribe when we have a new recording or uploaded file
    // But don't show the transcription to the user
    useEffect(() => {
        if (recordedBlob || uploadedFile) {
            transcribeAudio();
        }
    }, [recordedBlob, uploadedFile]);
    
    // Start recording
    const startRecording = async () => {
        try {
            // Check if the browser supports the required APIs
            if (!navigator.mediaDevices) {
                throw new Error('MediaDevices API not supported. Please use HTTPS or a compatible browser.')
            }
            
            if (!navigator.mediaDevices.getUserMedia) {
                throw new Error('getUserMedia not supported in this browser.')
            }
            
            if (!window.MediaRecorder) {
                throw new Error('MediaRecorder not supported in this browser.')
            }
            
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            
            const mediaRecorder = new MediaRecorder(stream)
            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []
            
            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    audioChunksRef.current.push(e.data)
                }
            }
            
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
                setRecordedBlob(audioBlob)
                
                // Create audio element for playback
                const audioUrl = URL.createObjectURL(audioBlob)
                if (audioRef.current) {
                    audioRef.current.src = audioUrl
                }
                
                // Stop all tracks in the stream
                stream.getTracks().forEach(track => track.stop())
            }
            
            mediaRecorder.start()
            setIsRecording(true)
            setRecordingTime(0)
            
            // Reset previous recording data
            setRecordedBlob(null)
            setUploadedFile(null)
            setTranscription('')
            
        } catch (error: unknown) {
            console.error('Error accessing microphone:', error)
            
            // Provide specific error messages based on the error type
            let errorMessage = 'Could not access microphone. '
            
            if (error instanceof Error) {
                if (error.name === 'NotAllowedError') {
                    errorMessage += 'Permission denied. Please allow microphone access and try again.'
                } else if (error.name === 'NotFoundError') {
                    errorMessage += 'No microphone found. Please connect a microphone and try again.'
                } else if (error.name === 'NotSupportedError') {
                    errorMessage += 'Your browser does not support audio recording.'
                } else if (error.message.includes('HTTPS')) {
                    errorMessage += 'Recording requires HTTPS. Please use a secure connection.'
                } else if (error.message.includes('MediaDevices')) {
                    errorMessage += 'Your browser does not support the required media APIs.'
                } else {
                    errorMessage += 'Please check your permissions and try again.'
                }
            } else {
                errorMessage += 'Please check your permissions and try again.'
            }
            
            toast.error(errorMessage)
        }
    }
    
    // Stop recording
    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            setIsRecording(false)
        }
    }
    
    // Play recorded audio
    const playAudio = () => {
        if (audioRef.current) {
            audioRef.current.play()
            setIsPlaying(true)
        }
    }
    
    // Pause playback
    const pauseAudio = () => {
        if (audioRef.current) {
            audioRef.current.pause()
            setIsPlaying(false)
        }
    }
    
    // Handle audio end event
    const handleAudioEnded = () => {
        setIsPlaying(false)
    }
    
    // Handle file upload
    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0]
            
            // Check if file is audio
            if (!file.type.startsWith('audio/')) {
                toast.error('Please select an audio file')
                return
            }
            
            setUploadedFile(file)
            setRecordedBlob(null) // Clear any recorded audio
            
            // Create audio element for playback
            const audioUrl = URL.createObjectURL(file)
            if (audioRef.current) {
                audioRef.current.src = audioUrl
            }
        }
    }
    
    // Transcribe the audio in the background
    const transcribeAudio = async () => {
        try {
            setIsTranscribing(true)
            
            // Prepare FormData with the audio file
            const formData = new FormData()
            
            if (recordedBlob) {
                // Convert Blob to File
                const file = new File([recordedBlob], 'recording.webm', { type: 'audio/webm' })
                formData.append('audio', file)
            } else if (uploadedFile) {
                formData.append('audio', uploadedFile)
            } else {
                setIsTranscribing(false)
                return
            }
            
            // Call the API
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/speech-to-text`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    },
                    withCredentials: true
                }
            )
            
            if (response.data && response.data.success) {
                // Store transcription but don't show it to user
                setTranscription(response.data.transcription)
                
                // If the API returned an S3 URL for the audio, use it instead of the local blob
                if (response.data.s3_url && recordedBlob) {
                    // Fetch the blob from S3 URL
                    const newBlob = await fetch(response.data.s3_url).then(r => r.blob()) as EnhancedBlob;
                    
                    // Add the S3 URL as a property
                    newBlob.s3Url = response.data.s3_url;
                    
                    // Replace the recordedBlob with this new blob
                    setRecordedBlob(newBlob);
                }
            }
            
        } catch (error) {
            console.error('Error transcribing audio:', error)
            // Silent fail - don't show error to user
        } finally {
            setIsTranscribing(false)
        }
    }
    
    // Submit the voice message
    const submitVoiceMessage = () => {
        // This function should only be called when button is enabled
        // (i.e., when NOT transcribing and NOT processing)
        
        // Set processing state to show "Submitting..."
        setIsProcessing(true);
        
        // If we have a transcription, use it; otherwise use a placeholder
        const finalTranscription = transcription || "Voice message (transcription not available)"
        
        if (recordedBlob) {
            // Convert Blob to File with a more descriptive filename including timestamp
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const file = new File([recordedBlob], `voice-message-${timestamp}.webm`, { type: 'audio/webm' }) as File & { s3Url?: string };
            
            // If we have an S3 URL from the transcription process, add it to the file
            if (recordedBlob.s3Url) {
                file.s3Url = recordedBlob.s3Url;
            }
            
            onVoiceMessageReady(file, finalTranscription)
            handleClose()
        } else if (uploadedFile) {
            onVoiceMessageReady(uploadedFile, finalTranscription)
            handleClose()
        }
        
        // Reset processing state (though handleClose will also reset it)
        setIsProcessing(false);
    }
    
    // Reset all state when closing
    const handleClose = () => {
        if (isRecording) {
            stopRecording()
        }
        
        if (isPlaying && audioRef.current) {
            audioRef.current.pause()
        }
        
        // Clean up audio URL if it exists
        if (audioRef.current && audioRef.current.src) {
            URL.revokeObjectURL(audioRef.current.src)
        }
        
        setIsRecording(false)
        setRecordingTime(0)
        setRecordedBlob(null)
        setIsPlaying(false)
        setUploadedFile(null)
        setTranscription('')
        setIsProcessing(false)
        
        onClose()
    }
    
    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md font-public-sans bg-neutral-900 text-white border-neutral-700">
                <DialogHeader>
                    <DialogTitle className="text-xl font-bold text-white">Voice Message</DialogTitle>
                </DialogHeader>
                
                <div className="space-y-4 py-4 flex flex-col items-center justify-center">
                    {/* Audio Player (hidden) */}
                    <audio 
                        ref={audioRef}
                        onEnded={handleAudioEnded}
                        className="hidden"
                    />
                    
                    {/* Recording UI */}
                    <div className="flex flex-col items-center justify-center gap-4">
                        {/* Recording Status */}
                        {isRecording ? (
                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 rounded-full bg-red-500 flex items-center justify-center animate-pulse mb-2">
                                    <FiMic className="w-8 h-8 text-white" />
                                </div>
                                <p className="text-lg font-medium">{formatTime(recordingTime)}</p>
                                <p className="text-sm text-red-400">Recording...</p>
                            </div>
                        ) : recordedBlob || uploadedFile ? (
                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 rounded-full bg-neutral-700 flex items-center justify-center mb-2">
                                    {isPlaying ? (
                                        <FiPause className="w-8 h-8 text-white" />
                                    ) : (
                                        <FiPlay className="w-8 h-8 text-white" />
                                    )}
                                </div>
                                <p className="text-sm">
                                    {uploadedFile ? uploadedFile.name : 'Voice recording'}
                                </p>
                                {isTranscribing && (
                                    <div className="flex items-center text-xs text-neutral-400 mt-2">
                                        <FiLoader className="animate-spin mr-1" />
                                        Processing voice message...
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center">
                                <div className="w-16 h-16 rounded-full bg-neutral-700 flex items-center justify-center mb-2">
                                    <FiMic className="w-8 h-8 text-white" />
                                </div>
                                <p className="text-sm">
                                    {isRecordingSupported ? 'Ready to record' : 'Recording not supported'}
                                </p>
                                {!isRecordingSupported && (
                                    <p className="text-xs text-neutral-400 mt-1 text-center">
                                        Please use the upload option or try HTTPS
                                    </p>
                                )}
                            </div>
                        )}
                        
                        {/* Action Buttons */}
                        <div className="flex items-center gap-3">
                            {isRecording ? (
                                <Button
                                    onClick={stopRecording}
                                    className="bg-red-500 hover:bg-red-600 text-white rounded-full w-12 h-12 p-0 flex items-center justify-center"
                                >
                                    <FiX className="w-6 h-6" />
                                </Button>
                            ) : recordedBlob || uploadedFile ? (
                                <>
                                    {isPlaying ? (
                                        <Button
                                            onClick={pauseAudio}
                                            className="bg-neutral-700 hover:bg-neutral-600 text-white rounded-full w-12 h-12 p-0 flex items-center justify-center"
                                        >
                                            <FiPause className="w-6 h-6" />
                                        </Button>
                                    ) : (
                                        <Button
                                            onClick={playAudio}
                                            className="bg-neutral-700 hover:bg-neutral-600 text-white rounded-full w-12 h-12 p-0 flex items-center justify-center"
                                        >
                                            <FiPlay className="w-6 h-6" />
                                        </Button>
                                    )}
                                    
                                    <Button
                                        onClick={() => {
                                            setRecordedBlob(null)
                                            setUploadedFile(null)
                                            if (audioRef.current) {
                                                URL.revokeObjectURL(audioRef.current.src)
                                                audioRef.current.src = ''
                                            }
                                            setTranscription('')
                                        }}
                                        className="bg-red-500 hover:bg-red-600 text-white rounded-full w-12 h-12 p-0 flex items-center justify-center"
                                    >
                                        <FiTrash className="w-6 h-6" />
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button
                                        onClick={isRecordingSupported ? startRecording : () => toast.error('Recording not supported. Please upload an audio file instead.')}
                                        disabled={!isRecordingSupported}
                                        className={`${isRecordingSupported 
                                            ? 'bg-[var(--mrwhite-primary-color)] hover:bg-[var(--mrwhite-primary-color)]/80 text-black' 
                                            : 'bg-neutral-600 text-neutral-400 cursor-not-allowed'
                                        } rounded-full w-12 h-12 p-0 flex items-center justify-center`}
                                        title={isRecordingSupported ? 'Start recording' : 'Recording not supported in this browser/environment'}
                                    >
                                        <FiMic className="w-6 h-6" />
                                    </Button>
                                    
                                    <Button
                                        onClick={() => fileInputRef.current?.click()}
                                        className="bg-neutral-700 hover:bg-neutral-600 text-white rounded-full w-12 h-12 p-0 flex items-center justify-center"
                                        title="Upload audio file"
                                    >
                                        <FiUpload className="w-6 h-6" />
                                    </Button>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        onChange={handleFileUpload}
                                        accept="audio/*"
                                        className="hidden"
                                    />
                                </>
                            )}
                        </div>
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex justify-end gap-2 mt-4">
                        <Button
                            onClick={handleClose}
                            variant="outline"
                            className="border-neutral-600 cursor-pointer"
                        >
                            Cancel
                        </Button>
                        
                        <Button
                            onClick={submitVoiceMessage}
                            disabled={isProcessing || isTranscribing || (!recordedBlob && !uploadedFile)}
                            className="bg-[var(--mrwhite-primary-color)] hover:bg-[var(--mrwhite-primary-color)]/80 text-black disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isProcessing || isTranscribing ? (
                                <>
                                    <FiLoader className="animate-spin mr-2 h-4 w-4" />
                                    {isTranscribing ? 'Processing...' : 'Submitting...'}
                                </>
                            ) : (
                                <>
                                    <FaCheckCircle className="mr-2 h-4 w-4" />
                                    Use Voice Message
                                </>
                            )}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
} 