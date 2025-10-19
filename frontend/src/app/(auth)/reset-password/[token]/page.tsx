"use client"
import React, { useState, useEffect } from 'react';
import { Lock, Eye, EyeOff, RefreshCcw, Loader2, ArrowLeft } from 'lucide-react';
import Image from 'next/image';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import { motion } from 'motion/react';

const ResetPasswordPage = () => {
  const { user } = useAuth();
  const router = useRouter();
  const params = useParams();
  const token = params.token as string;

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTokenValid, setIsTokenValid] = useState(false);
  const [isVerifying, setIsVerifying] = useState(true);
  const [isRedirecting, setIsRedirecting] = useState(false);

  // Redirect if user is already logged in
  useEffect(() => {
    if (user) {
      router.push('/');
    }
  }, [user, router]);

  // Verify token on component mount
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) return;

      try {
        const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/verify-reset-token/${token}`);
        setIsTokenValid(true);
      } catch (error) {
        console.error('Invalid or expired token:', error);
        setError('This password reset link is invalid or has expired. Please request a new one.');
      } finally {
        setIsVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async () => {
    if (!password || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/reset-password`, {
        token,
        password,
        confirm_password: confirmPassword
      });
      
      setSuccess('Your password has been successfully reset.');
      setPassword('');
      setConfirmPassword('');
      
      // Show redirecting overlay
      setIsRedirecting(true);
      
      // Redirect to login after 2 seconds
      setTimeout(() => {
        router.push('/login');
      }, 2000);
    } catch (error: any) {
      console.error('Password reset error:', error);
      if (error?.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Error resetting password. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  // If still loading, show nothing or a loading spinner
  if (user) {
    return null; // Already redirecting in the useEffect
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-black relative">
      <div className="glow-effect"></div>

      {/* Back Button */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        onClick={handleGoBack}
        className="absolute top-4 left-4 text-gray-400 hover:text-white flex items-center gap-2 z-20"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </motion.button>
      <div className="w-full max-w-md relative z-10">
        <div className="bg-black rounded-lg p-8 shadow-2xl flex flex-col items-center">
          {/* Header */}
          <div className="text-center mb-8 flex gap-4">
            <div className="flex justify-center mb-4">
              <Image src="/assets/logo.png" alt="Dog" width={60} height={60} />
            </div>
            <div className="flex flex-col justify-center mb-4">
              <h1 className="text-2xl font-bold text-[var(--mrwhite-primary-color)]">Mr. White</h1>
              <p className="text-gray-400 text-sm">Guide to All Paws</p>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mb-4">Reset Your Password</h2>

          {isVerifying ? (
            <div className="flex flex-col items-center justify-center py-8">
              <Loader2 className="w-8 h-8 text-[var(--mrwhite-primary-color)] animate-spin mb-4" />
              <p className="text-gray-400">Verifying your reset link...</p>
            </div>
          ) : isTokenValid ? (
            <>
              <p className="text-gray-400 text-sm mb-6 text-center">
                Enter your new password below.
              </p>

              {/* Form */}
              <div className="space-y-4 w-full">
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="New Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-12 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>

                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm Password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-12 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white cursor-pointer"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>

                {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
                {success && <p className="text-green-500 text-sm mt-2">{success}</p>}

                <button
                  onClick={handleSubmit}
                  disabled={isLoading}
                  className="w-full bg-[var(--mrwhite-primary-color)] hover:bg-[var(--mrwhite-primary-color)] text-black font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="relative w-12 h-6">
                  <Image 
                    src="/assets/running-dog.gif" 
                    alt="Loading" 
                    fill
                    priority
                    className="object-cover"
                  />
                </div>
                  ) : (
                    <RefreshCcw className="w-5 h-5" />
                  )}
                  {isLoading ? 'Resetting...' : 'Reset Password'}
                </button>
              </div>
            </>
          ) : (
            <div className="text-center py-6">
              <p className="text-red-500 mb-4">{error}</p>
              <button
                onClick={() => router.push('/forgot-password')}
                className="text-[var(--mrwhite-primary-color)] cursor-pointer hover:opacity-80"
              >
                Request a new password reset link
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Redirecting overlay */}
      {isRedirecting && (
        <div className="fixed inset-0 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="relative w-12 h-6 mr-4 bg-gradient-to-t from-orange-400 via-yellow-400 to-yellow-200 rounded-t-full shadow-lg shadow-orange-300/50">
            <Image 
              src="/assets/running-dog.gif" 
              alt="Redirecting" 
              fill
              priority
              className="object-contain"
            />
          </div>
          <p className="text-[var(--mrwhite-primary-color)] text-lg font-semibold">Redirecting to login...</p>
        </div>
      )}
    </div>
  );
};

export default ResetPasswordPage; 