"use client"
import React, { useState, useEffect } from 'react';
import { Mail, ArrowRight, Loader2, ArrowLeft } from 'lucide-react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import { motion } from 'framer-motion';

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5 },
  }),
};

const ForgotPasswordPage = () => {
  const { user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Redirect if user is already logged in
  useEffect(() => {
    if (user) {
      router.push('/');
    }
  }, [user, router]);

  const handleSubmit = async () => {
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/forgot-password`, { email });
      setSuccess('Reset link sent to your registered email.');
      setEmail('');
    } catch (error: any) {
      console.error('Password reset error:', error);
      if (error?.response?.data?.message) {
        setError(error.response.data.message);
      } else {
        setError('Error sending password reset instructions. Please try again.');
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
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative z-10"
      >
        <motion.div
          className="bg-black rounded-lg p-8 shadow-2xl flex flex-col items-center"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {},
          }}
        >
          {/* Header */}
          <motion.div className="text-center mb-8 flex flex-col sm:flex-row items-center gap-4" variants={fadeInUp} custom={0}>
            <motion.div className="flex justify-center" variants={fadeInUp} custom={1}>
              <div className="relative w-16 h-16 flex-shrink-0">
                <Image src="/assets/logo.png" alt="Dog" fill className="object-contain" />
              </div>
            </motion.div>
            <motion.div className="flex flex-col font-work-sans justify-center text-center sm:text-left" variants={fadeInUp} custom={2}>
              <h1 className="text-2xl font-bold text-[var(--mrwhite-primary-color)]">Mr. White</h1>
              <p className="text-gray-400 text-sm">AI Assistant for Dog Care & Beyond</p>
            </motion.div>
          </motion.div>

          <motion.h2 className="text-xl font-semibold text-white mb-4" variants={fadeInUp} custom={3}>Reset Your Password</motion.h2>
          <motion.p className="text-gray-400 text-sm mb-6 text-center" variants={fadeInUp} custom={4}>
            Enter your email address and we'll send you instructions to reset your password.
          </motion.p>

          {/* Form */}
          <motion.div 
            className="space-y-4 w-full font-work-sans"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {},
            }}
          >
            <motion.div className="relative" variants={fadeInUp} custom={5}>
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                autoComplete="email"
                required
              />
            </motion.div>

            {error && <motion.p className="text-red-500 text-sm mt-2" variants={fadeInUp} custom={6}>{error}</motion.p>}
            {success && <motion.p className="text-green-500 text-sm mt-2" variants={fadeInUp} custom={6}>{success}</motion.p>}

            <motion.div className="flex justify-between text-sm" variants={fadeInUp} custom={7}>
              <button
                type="button"
                onClick={() => router.push('/login')}
                className="text-[var(--mrwhite-primary-color)] cursor-pointer hover:text-[var(--mrwhite-primary-color)] hover:underline"
              >
                Back to Login
              </button>
            </motion.div>

            <motion.button
              onClick={handleSubmit}
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              variants={fadeInUp}
              custom={8}
              className="w-full bg-[var(--mrwhite-primary-color)] cursor-pointer hover:bg-[var(--mrwhite-primary-color)] text-black font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="relative w-12 h-6 flex-shrink-0">
                  <Image 
                    src="/assets/running-dog.gif" 
                    alt="Loading" 
                    fill
                    priority
                    className="object-contain"
                  />
                </div>
              ) : (
                <ArrowRight className="w-5 h-5" />
              )}
              {isLoading ? 'Sending...' : 'Send Reset Instructions'}
            </motion.button>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default ForgotPasswordPage; 