"use client"

import { Button } from "@/components/ui/button"
import Image from "next/image"
import Link from "next/link"
import { IoChatbubble } from "react-icons/io5"
import ImagePop from "@/components/ImagePop"
import ShakingIcon from "./ShakingIcon"
import { motion } from "framer-motion"
import { useRef } from "react"
import { FaDiscord, FaHome, FaInfo, FaTelegramPlane } from "react-icons/fa"
import { FaCircleInfo, FaCoins } from "react-icons/fa6"
import { useRouter } from "next/navigation"

export default function Footer() {
  const footerRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: {
        duration: 0.6,
        ease: [0.25, 0.1, 0.25, 1]
      }
    }
  }

  const bottomBarVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: {
        duration: 0.5,
        delay: 0.4,
        ease: [0.25, 0.1, 0.25, 1]
      }
    }
  }

  return (
    <div className="min-h-[253px] bg-gradient-to-b from-white/10 to-black" ref={footerRef}>
      <motion.div 
        className=" min-h-[212px] py-8 flex max-lg:flex-wrap max-lg:justify-center max-xl:gap-10 gap-[80px] justify-between items-start px-4 sm:px-6 md:px-10 max-w-[1440px] mx-auto"
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
      >
        <motion.div className="w-full max-w-[224px] flex flex-col gap-[10px]" variants={itemVariants}>
          <div className="flex items-center gap-[10px] cursor-pointer" onClick={() => router.push('/')}>
            <div className="w-[40px] h-[40px] sm:w-[47px] sm:h-[47px] relative">
              <ImagePop
                src="/assets/logo.png"
                alt="logo"
                fill
                containerClassName="w-full h-full"
              />
            </div>
            <div>
              <h1 className="text-[18px] sm:text-[21px]/6 font-semibold font-work-sans tracking-tighter text-[var(--mrwhite-primary-color)]">Mr. White</h1>
              <p className="text-[10px] sm:text-[11px] font-light font-public-sans tracking-tight text-white/80">AI Assistant for Dog Care & Beyond</p>
            </div>
          </div>
          <p className="text-[14px] font-public-sans font-light tracking-tighter">Your trusted companion for all dog-related advice, training tips, and pet care resources.</p>
        </motion.div>
        
        <motion.div className="w-full max-w-[224px]" variants={itemVariants}>
          <h3 className="text-[16px] font-work-sans font-semibold mb-4 text-[var(--mrwhite-primary-color)]"><span className="text-white text-[20px]/6 font-extrabold">|</span> Navigation</h3>
          <div className="flex flex-col gap-[10px] text-[14px] font-public-sans font-light">
            <Link href="/">
            <FaHome className="w-4 h-4 inline-block mr-2 " />
            Home
            </Link>
            <Link href="/about">
            <FaCircleInfo className="inline-block mr-2 " />
            About
            </Link>
            <Link href="/subscription">
            <FaCoins className="inline-block mr-2 " />
            Subscriptions
            </Link>
          </div>
        </motion.div>
        
        <motion.div className="w-full max-w-[224px]" variants={itemVariants}>
          <h3 className="text-[16px] font-work-sans font-semibold text-[var(--mrwhite-primary-color)] mb-4"><span className="text-white text-[20px]/6 font-extrabold">|</span> Social Media</h3>
          <div className="flex flex-col gap-[10px] text-[14px] font-public-sans font-light">
            <Link className="flex items-center gap-[10px]" href="/">
              <div className="relative w-4 h-4">
                <Image src="/assets/instagram-logo.png" alt="instagram" fill sizes="250px" priority className="object-contain" />
              </div>
              Instagram
            </Link>
            <Link className="flex items-center gap-[10px]" href="/">
              <div className="relative w-4 h-4">
                <Image src="/assets/facebook-logo.png" alt="facebook" fill sizes="250px" priority className="object-contain" />
              </div>
              Facebook
            </Link>
            <Link className="flex items-center gap-[10px]" href="/">
              <div className="relative w-4 h-4">
                <Image src="/assets/x-logo.png" alt="twitter" fill sizes="250px" priority className="object-contain" />
              </div>
              X.com
            </Link>
            <Link className="flex items-center gap-[10px]" href="/">
              <div className="relative w-4 h-4">
                <Image src="/assets/youtube-logo.png" alt="youtube" fill sizes="250px" priority className="object-contain" />
              </div>
              Youtube
            </Link>
          </div>
        </motion.div>
        
        <motion.div className="w-full max-w-[224px]" variants={itemVariants}>
          <h3 className="text-[16px] font-work-sans font-semibold text-[var(--mrwhite-primary-color)] mb-4"><span className="text-white text-[20px]/6 font-extrabold">|</span> Community</h3>
          <div className="flex flex-col gap-[5px] text-[14px] font-public-sans font-light">
            <Link href="/">
            <FaDiscord className="w-4 h-4 inline-block mr-2 text-blue-800" />
            Discord
            </Link>
            <Link href="/">
            <FaTelegramPlane className="w-4 h-4 inline-block mr-2 text-blue-200" />
            Telegram
            </Link>
          </div>
        </motion.div>
        
        <motion.div className="w-full max-w-[224px] flex max-lg:justify-center" variants={itemVariants}>
          <Button className="w-[140px] h-[40px] text-[18px] sm:text-[20px] font-medium font-public-sans flex items-center gap-[10px]">
            <ShakingIcon icon={<IoChatbubble className="!w-[18px] !h-[18px] sm:!w-[20px] sm:!h-[20px]"/>} />
            <Link href="/contact">
              Contact
            </Link>
          </Button>
        </motion.div>
      </motion.div>
      
      <div className=" bg-white/10"> 
      <div className="min-h-[41px] py-2 flex max-sm:gap-2 max-sm:items-center justify-between items-center px-4 sm:px-8 md:px-12 text-white/80 max-w-[1440px] mx-auto">
        <p className="text-[12px] sm:text-[14px] font-public-sans font-light">All rights reserved ©</p>
        <div className="text-[12px] sm:text-[14px] font-public-sans font-light max-sm:flex max-sm:flex-col max-sm:items-center max-sm:gap-1">
          <Link href="/">Terms of Service</Link>
          <span className="mx-6 max-sm:hidden">/</span>
          <Link href="/">Privacy Policy</Link>
        </div>
      </div>
      </div>
    </div>
  )
} 