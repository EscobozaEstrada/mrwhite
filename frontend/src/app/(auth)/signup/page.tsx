'use client';

import React, { useState, useEffect } from 'react';
import { User, Mail, Lock, Eye, EyeOff, CreditCard, Loader2, ArrowLeft } from 'lucide-react';
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

const SignupPage = () => {
  const { user, setUser } = useAuth();
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [signupForm, setSignupForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  useEffect(() => {
    if (user) {
      router.push('/');
    }
  }, [user, router]);

  const handleSignupSubmit = async () => {
    if (!signupForm.username || !signupForm.email || !signupForm.password || !signupForm.confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (signupForm.password !== signupForm.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // 🌍 GLOBAL TIMEZONE DETECTION: Automatically detect user's timezone
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    setIsLoading(true);
    setError('');

    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/signup`, {
        username: signupForm.username,
        email: signupForm.email,
        password: signupForm.password,
        confirm_password: signupForm.confirmPassword,
        timezone: userTimezone, // 🌍 Send user's detected timezone
      }, { withCredentials: true });

      // Extract token from cookie and store in localStorage for cross-port access
      const tokenCookie = document.cookie.split('; ').find(row => row.startsWith('token='));
      if (tokenCookie) {
        const token = tokenCookie.split('=')[1];
        localStorage.setItem('token', token);
        console.log('✅ Token stored in localStorage for cross-port access');
      }

      const userRes = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`, {
        withCredentials: true,
      });
      setUser(userRes.data);

      // Check for redirect after signup
      const redirectUrl = localStorage.getItem('redirectAfterLogin');
      if (redirectUrl) {
        localStorage.removeItem('redirectAfterLogin');
        router.push(redirectUrl);
      } else {
        router.push('/');
      }
    } catch (error: any) {
      console.error('Signup error:', error);
      if (error?.response?.data?.message) {
        setError(error.response.data.message);
      } else if (error?.message?.includes('duplicate key') || error?.message?.includes('already exists')) {
        setError('This email address is already registered. Please use a different email or login instead.');
      } else {
        setError('Error creating account. Please try again.');
      }
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      e.preventDefault();
      handleSignupSubmit();
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  if (user) return null;

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
              <p className="text-gray-400 text-sm ">AI Assistant for Dog Care & Beyond</p>
            </motion.div>
          </motion.div>

          {/* Signup Form */}
          <motion.div
            className="space-y-4 w-full font-work-sans"
            onKeyDown={handleKeyDown}
            initial="hidden"
            animate="visible"
            variants={{ hidden: {}, visible: {} }}
          >
            {[
              {
                icon: <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />,
                type: 'text',
                name: 'username',
                placeholder: 'Username',
              },
              {
                icon: <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />,
                type: 'email',
                name: 'email',
                placeholder: 'Email',
              },
            ].map((field, i) => (
              <motion.div className="relative" variants={fadeInUp} custom={i + 3} key={field.name}>
                {field.icon}
                <input
                  type={field.type}
                  name={field.name}
                  placeholder={field.placeholder}
                  value={signupForm[field.name as keyof typeof signupForm]}
                  onChange={(e) => setSignupForm({ ...signupForm, [field.name]: e.target.value })}
                  className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                  required
                />
              </motion.div>
            ))}

            {[true, false].map((isConfirm, i) => (
              <motion.div className="relative" variants={fadeInUp} custom={i + 5} key={i}>
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type={
                    isConfirm
                      ? showPassword
                        ? 'text'
                        : 'password'
                      : showConfirmPassword
                        ? 'text'
                        : 'password'
                  }
                  name={isConfirm ? 'password' : 'confirmPassword'}
                  placeholder={isConfirm ? 'Password' : 'Confirm Password'}
                  value={signupForm[isConfirm ? 'password' : 'confirmPassword']}
                  onChange={(e) =>
                    setSignupForm({ ...signupForm, [isConfirm ? 'password' : 'confirmPassword']: e.target.value })
                  }
                  className="w-full bg-[#000000] border border-gray-700 rounded-lg py-3 pl-10 pr-12 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                  required
                />
                <button
                  type="button"
                  onClick={() => (isConfirm ? setShowPassword(!showPassword) : setShowConfirmPassword(!showConfirmPassword))}
                  className="absolute cursor-pointer right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {(isConfirm ? showPassword : showConfirmPassword) ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </motion.div>
            ))}

            {error && (
              <motion.p className="text-red-500 text-sm mt-2" variants={fadeInUp} custom={7}>
                {error}
              </motion.p>
            )}

            <motion.div className="text-center" variants={fadeInUp} custom={8}>
              <button
                type="button"
                onClick={() => router.push('/login')}
                className="text-[var(--mrwhite-primary-color)] hover:underline text-sm cursor-pointer"
              >
                Already have an account? Login
              </button>
            </motion.div>

            <motion.button
              onClick={handleSignupSubmit}
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              variants={fadeInUp}
              custom={9}
              className="w-full cursor-pointer bg-[var(--mrwhite-primary-color)] text-black font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ?
               <div className="relative w-12 h-6 flex-shrink-0">
                  <Image 
                    src="/assets/running-dog.gif" 
                    alt="Loading" 
                    fill
                    priority
                    className="object-contain"
                  />
                </div> : <User className="w-5 h-5" />}
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </motion.button>

            <motion.button
              type="button"
              disabled={isLoading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              variants={fadeInUp}
              custom={10}
              className="w-full cursor-pointer bg-gray-700 hover:bg-gray-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 border border-gray-600 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              <CreditCard className="w-5 h-5" />
              Connect with Social
            </motion.button>
          </motion.div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default SignupPage;
