'use client';

import React, { useState, useEffect, useRef } from 'react';
import { User, Lock, Eye, EyeOff, Zap, CreditCard, Loader2, ArrowLeft } from 'lucide-react';
import Image from 'next/image';
import { useRouter, useSearchParams } from 'next/navigation';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { motion } from 'motion/react';
import toast from '@/components/ui/sound-toast';

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5 },
  }),
};

const LoginPage = () => {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const toastShownRef = useRef(false);

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loginForm, setLoginForm] = useState({
    username: '',
    password: '',
  });

  useEffect(() => {
    // Check for redirect parameter and show appropriate message
    const redirectPath = searchParams.get('redirect');
    if (redirectPath && !toastShownRef.current) {
      toastShownRef.current = true;
      toast.error("Please login to access this page");
    }
  }, [searchParams]);

  useEffect(() => {
    if (user) {
      // If there's a redirect parameter, use it
      const redirectPath = searchParams.get('redirect');
      if (redirectPath) {
        router.push(redirectPath);
      } else {
        router.push('/');
      }
    }
  }, [user, router, searchParams]);

  const handleLoginSubmit = async () => {
    if (!loginForm.username || !loginForm.password) {
      setError('Please fill in all fields');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const loginResponse = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/login`,
        { username: loginForm.username, password: loginForm.password },
        { withCredentials: true }
      );

      // Extract token from cookie and store in localStorage for cross-port access
      const tokenCookie = document.cookie.split('; ').find(row => row.startsWith('token='));
      if (tokenCookie) {
        const token = tokenCookie.split('=')[1];
        localStorage.setItem('token', token);
        console.log('✅ Token stored in localStorage for cross-port access');
      }

      if (loginResponse.data.user) {
        setUser(loginResponse.data.user);

        // Check for redirect after login
        const redirectUrl = localStorage.getItem('redirectAfterLogin');
        if (redirectUrl) {
          localStorage.removeItem('redirectAfterLogin');
          router.push(redirectUrl);
        } else {
          router.push('/');
        }
        return;
      }

      try {
        const userRes = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`, {
          withCredentials: true,
        });

        setUser(userRes.data);

        // Check for redirect after login
        const redirectUrl = localStorage.getItem('redirectAfterLogin');
        if (redirectUrl) {
          localStorage.removeItem('redirectAfterLogin');
          router.push(redirectUrl);
        } else {
          router.push('/');
        }
      } catch (userError: any) {
        setError('Login successful but error loading user data');
        setIsLoading(false);
      }
    } catch (error: any) {
      setError(error?.response?.data?.message || 'Invalid credentials');
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      e.preventDefault();
      handleLoginSubmit();
    }
  };

  const handleGoBack = () => {
    // Check if there's a redirect parameter, if so go to home instead of back
    const redirectPath = searchParams.get('redirect');
    if (redirectPath) {
      router.push('/');
    } else {
      router.back();
    }
  };

  if (user) return null;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-black relative">
      <div className="glow-effect"></div>

      {/* Back Button */}
      <motion.button
        layout
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
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative z-10"
      >
        <motion.div
          layout
          className="bg-black rounded-lg p-8 shadow-2xl flex flex-col items-center"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {},
          }}
        >
          {/* Header */}
          <motion.div layout className="text-center mb-8 flex flex-col sm:flex-row items-center gap-4" variants={fadeInUp} custom={0}>
            <motion.div layout className="flex justify-center" variants={fadeInUp} custom={1}>
              <div className="relative w-16 h-16 flex-shrink-0">
                <Image src="/assets/logo.png" alt="Dog" fill className="object-contain" />
              </div>
            </motion.div>
            <motion.div layout className="flex flex-col font-work-sans justify-center text-center sm:text-left" variants={fadeInUp} custom={2}>
              <h1 className="text-2xl font-bold text-[var(--mrwhite-primary-color)]">Mr. White</h1>
              <p className="text-gray-400 text-sm ">AI Assistant for Dog Care & Beyond</p>
            </motion.div>
          </motion.div>

          {/* Login Form */}
          <motion.div
            layout
            className="space-y-4 w-full font-work-sans"
            onKeyDown={handleKeyDown}
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: {},
            }}
          >
            {[0, 1].map((i) => (
              <motion.div layout key={i} className="relative" variants={fadeInUp} custom={i + 3}>
                {i === 0 ? (
                  <>
                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      type="text"
                      placeholder="Username"
                      name="username"
                      value={loginForm.username}
                      onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                      className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                      autoComplete="username"
                      required
                    />
                  </>
                ) : (
                  <>
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Password"
                      name="password"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                      className="w-full bg-black border border-gray-700 rounded-lg py-3 pl-10 pr-12 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </>
                )}
              </motion.div>
            ))}

            {error && (
              <p className="text-red-500 text-sm mt-2">
                {error}
              </p>
            )}

            <motion.div layout className="flex justify-between text-sm" variants={fadeInUp} custom={6}>
              <button
                type="button"
                onClick={() => router.push('/signup')}
                className="text-[var(--mrwhite-primary-color)] hover:underline cursor-pointer"
              >
                Sign-up
              </button>
              <button
                type="button"
                onClick={() => router.push('/forgot-password')}
                className="text-[var(--mrwhite-primary-color)] hover:underline cursor-pointer"
              >
                Lost your password?
              </button>
            </motion.div>

            <motion.button
              layout
              onClick={handleLoginSubmit}
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              variants={fadeInUp}
              custom={7}
              className="w-full cursor-pointer bg-[var(--mrwhite-primary-color)] text-black font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                // <Loader2 className="w-5 h-5 animate-spin" />
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
                <Zap className="w-5 h-5" />
              )}
              {isLoading ? 'Logging in...' : 'Login'}
            </motion.button>

            <motion.button
              layout
              type="button"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              variants={fadeInUp}
              custom={8}
              className="w-full bg-gray-700 cursor-pointer hover:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 border border-gray-600 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              <CreditCard className="w-5 h-5" />
              Connect
            </motion.button>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default LoginPage;
