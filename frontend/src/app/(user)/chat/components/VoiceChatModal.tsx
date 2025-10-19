"use client";

import { useState, useRef, useEffect } from "react";
import { FiMic, FiX, FiLoader } from "react-icons/fi";
import { BsStopCircle } from "react-icons/bs";

interface VoiceChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTranscriptionReady: (transcription: string) => void;
}

export default function VoiceChatModal({
  isOpen,
  onClose,
  onTranscriptionReady,
}: VoiceChatModalProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Timer for recording duration
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording]);

  // Format seconds to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Start recording
  const startRecording = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setRecordedBlob(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
    } catch (err) {
      console.error("Error starting recording:", err);
      setError("Failed to access microphone. Please check permissions.");
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Transcribe audio using backend API
  const transcribeAudio = async () => {
    if (!recordedBlob) return;

    try {
      setIsTranscribing(true);
      setError(null);

      const formData = new FormData();
      const file = new File([recordedBlob], "recording.webm", { type: "audio/webm" });
      formData.append("audio", file);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/speech-to-text`,
        {
          method: "POST",
          body: formData,
          credentials: "include",
        }
      );

      if (!response.ok) {
        throw new Error(`Transcription failed: ${response.statusText}`);
      }

      const data = await response.json();

      if (data.success && data.transcription) {
        onTranscriptionReady(data.transcription);
        handleClose();
      } else {
        throw new Error("No transcription received");
      }
    } catch (err: any) {
      console.error("Transcription error:", err);
      setError(err.message || "Failed to transcribe audio. Please try again.");
    } finally {
      setIsTranscribing(false);
    }
  };

  // Handle close
  const handleClose = () => {
    if (isRecording) {
      stopRecording();
    }
    setRecordedBlob(null);
    setRecordingTime(0);
    setError(null);
    onClose();
  };

  // Auto-transcribe when recording stops
  useEffect(() => {
    if (recordedBlob && !isRecording) {
      transcribeAudio();
    }
  }, [recordedBlob, isRecording]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-[#1a1a1a] rounded-lg p-6 max-w-md w-full mx-4 border border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Voice Message</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white cursor-pointer transition-colors"
            disabled={isTranscribing}
          >
            <FiX size={24} />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Recording Status */}
        <div className="flex flex-col items-center space-y-6">
          {/* Microphone Icon with Animation */}
          <div
            className={`relative flex items-center justify-center w-32 h-32 rounded-full ${
              isRecording
                ? "bg-red-600 animate-pulse"
                : isTranscribing
                ? "bg-blue-600"
                : "bg-purple-600"
            }`}
          >
            {isTranscribing ? (
              <FiLoader size={48} className="text-white animate-spin" />
            ) : (
              <FiMic size={48} className="text-white" />
            )}
          </div>

          {/* Status Text */}
          <div className="text-center">
            {isTranscribing ? (
              <p className="text-white text-lg">Transcribing...</p>
            ) : isRecording ? (
              <>
                <p className="text-white text-lg mb-2">Recording...</p>
                <p className="text-gray-400 text-3xl font-mono">{formatTime(recordingTime)}</p>
              </>
            ) : (
              <p className="text-gray-400">Click the button below to start recording</p>
            )}
          </div>

          {/* Control Buttons */}
          <div className="flex space-x-4">
            {!isRecording && !isTranscribing && (
              <button
                onClick={startRecording}
                className="px-6 py-3 cursor-pointer bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                <FiMic size={20} />
                <span>Start Recording</span>
              </button>
            )}

            {isRecording && (
              <button
                onClick={stopRecording}
                className="px-6 py-3 cursor-pointer bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                <BsStopCircle size={20} />
                <span>Stop & Send</span>
              </button>
            )}
          </div>

          {/* Instructions */}
          {!isRecording && !isTranscribing && (
            <p className="text-gray-500 text-sm text-center max-w-xs">
              Speak your message clearly. It will be automatically transcribed and sent to Mr. White.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

