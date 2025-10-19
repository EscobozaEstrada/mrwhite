"use client"

import { usePathname } from "next/navigation"
import { useState, useRef, useEffect } from "react"
import { animate, inView, scroll, stagger } from "motion"

import { Button } from "@/components/ui/button"
import Link from "next/link"
import { TbLogin } from "react-icons/tb"
import { IoChatbubble } from "react-icons/io5"
import { RxHamburgerMenu } from "react-icons/rx"
import { IoMdClose } from "react-icons/io"
import { IoChevronDown } from "react-icons/io5"
import ImagePop from "@/components/ImagePop"
import { useRouter } from "next/navigation"
import ShakingIcon from "./ShakingIcon"
import { useAuth } from "@/context/AuthContext"
import { CreditDisplay } from "@/components/CreditDisplay"
import { Coins, Crown, User, Settings, LogOut, Image, Home, Info, BookOpen, MessageSquare, Calendar, Gift, MapPin, Sparkles } from "lucide-react"
import axios from "axios"
import Script from "next/script"
import { FaRoad } from "react-icons/fa"

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const isActive = (path: string) => pathname === path;
  const { user, setUser } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    try {
      const response = await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/logout`, {}, { withCredentials: true })
      setUser(null)

      // Check if the current path includes '/talk/' and redirect to login if it does
      if (pathname.includes('/talk/')) {
        router.push('/login');
      }
      setMobileMenuOpen(false);
      setUserMenuOpen(false);
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  // Function to safely navigate to talk page
  const navigateToTalk = () => {
    if (user?.id) {
      // Use user ID if available
      router.push(`/talk/${user.id}/conversation/latest`);
    } else {
      // Fallback to a default path if user ID is undefined
      router.push('/talk');
    }
    setMobileMenuOpen(false);
  }

  const navigateTo = (path: string) => {
    router.push(path);
    setMobileMenuOpen(false);
  }

  return (
    <>
      <Script id="structured-data" type="application/ld+json" dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Mr. White",
          "url": process.env.NEXT_PUBLIC_FRONTEND_URL || "https://mrwhiteaidogbuddy.com/",
          "logo": `${process.env.NEXT_PUBLIC_FRONTEND_URL || "https://mrwhiteaidogbuddy.com/"}/assets/logo.png`,
          "sameAs": [
            "https://twitter.com/MrWhiteAIBuddy",
            "https://www.instagram.com/mrwhiteai",
            "https://www.facebook.com/mrwhiteai"
          ],
          "description": "AI-powered dog care assistant and guide for all dog breeds"
        })
      }} />

      <header className="bg-black border-b border-neutral-800/50 fixed top-0 left-0 right-0 z-50">
        <div className="h-[70px] sm:h-[80px] md:h-[95px]  flex justify-between items-center px-3 sm:px-4 md:px-8 max-w-[1440px] mx-auto z-50">
          <div className="flex gap-[10px] sm:gap-[20px] md:gap-[50px] items-center">
            <div className="flex items-center gap-[8px] sm:gap-[10px]">
              <div className="w-[42px] h-[42px] max-[1200px]:w-[36px] max-[1200px]:h-[36px] relative cursor-pointer" onClick={() => router.push('/')}>
                <ImagePop
                  src="/assets/logo.png"
                  alt="Mr. White Logo"
                  fill
                  containerClassName="w-full h-full"
                />
              </div>
              <div className="cursor-pointer" onClick={() => router.push('/')}>
                <h1 className="text-[18px] sm:text-[20px] md:text-[21px]/6 font-semibold font-work-sans tracking-tighter text-[var(--mrwhite-primary-color)]">Mr. White</h1>
                <p className="text-[10px] sm:text-[11px] font-light font-public-sans tracking-tight text-white/80">Guide to all paws</p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="max-[1060px]:hidden flex gap-[20px] lg:gap-[40px]" aria-label="Main Navigation">
              <Link className={`font-semibold text-[18px] lg:text-[20px] ${isActive("/") ? "active-link" : ""} hover:scale-105 transition-all duration-300`} href="/" aria-current={isActive("/") ? "page" : undefined}>
                Home
              </Link>

              <Link className={`font-semibold text-[18px] lg:text-[20px] ${isActive("/about") ? "active-link" : ""} hover:scale-105 transition-all duration-300`} href="/about" aria-current={isActive("/about") ? "page" : undefined}>
                About
              </Link>

              <Link className={`font-semibold text-[18px] lg:text-[20px] ${isActive("/subscription") ? "active-link" : ""} hover:scale-105 transition-all duration-300`} href="/subscription" aria-current={isActive("/subscription") ? "page" : undefined}>
                Subscription
              </Link>

              {user && (
                <>
                  <Link
                    className={`font-semibold text-[18px] lg:text-[20px] ${pathname.startsWith("/talk") ? "active-link" : ""} hover:scale-105 transition-all duration-300`}
                    href={`/talk/conversation/new-chat`}
                    aria-current={pathname.startsWith("/talk") ? "page" : undefined}
                  >
                    Talk
                  </Link>
                </>
              )}

              {/* More Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  className={`font-semibold text-[18px] lg:text-[20px] flex items-center gap-1 ${isActive("/questbook") || isActive("/product") || isActive("/hub") || isActive("/payment") || isActive("/reminders") ? "active-link" : ""
                    } hover:scale-105 transition-all duration-300 transform-gpu origin-center`}
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  aria-expanded={dropdownOpen}
                  aria-controls="dropdown-menu"
                >
                  More <IoChevronDown className={`transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
                </button>

                {dropdownOpen && (
                  <div id="dropdown-menu" className="absolute top-full left-0 mt-2 w-40 bg-black/95 border border-neutral-800 rounded-md shadow-lg z-50 overflow-hidden max-h-[80vh] overflow-y-auto" role="menu">
                    {user && (
                      <Link
                        className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/reminders") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                        href="/reminders"
                        onClick={() => setDropdownOpen(false)}
                        role="menuitem"
                        aria-current={isActive("/reminders") ? "page" : undefined}
                      >
                        Reminders
                      </Link>
                    )}
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/questbook") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/questbook"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/questbook") ? "page" : undefined}
                    >
                      Questbook
                    </Link>
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/product") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/product"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/product") ? "page" : undefined}
                    >
                      Product
                    </Link>
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/my-hub") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/my-hub"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/my-hub") ? "page" : undefined}
                    >
                      My Hub
                    </Link>
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/the-way") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/the-way"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/the-way") ? "page" : undefined}
                    >
                      The Way
                    </Link>
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/events") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/events"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/events") ? "page" : undefined}
                    >
                      Events
                    </Link>
                    <Link
                      className={`block px-4 py-2 hover:bg-neutral-800 font-semibold text-[16px] ${isActive("/gallery") ? "text-[var(--mrwhite-primary-color)]" : ""}`}
                      href="/gallery"
                      onClick={() => setDropdownOpen(false)}
                      role="menuitem"
                      aria-current={isActive("/gallery") ? "page" : undefined}
                    >
                      Gallery
                    </Link>
                  </div>
                )}
              </div>
            </nav>
          </div>

          {/* Desktop Buttons */}
          <div className="max-[1060px]:hidden flex gap-[10px] lg:gap-[20px] items-center">
            {/* Credit Display for logged in users */}
            {user && <CreditDisplay variant="navbar" />}

            {user ? (
              /* User Menu Dropdown */
              <div className="relative" ref={userMenuRef}>
                <Button
                  variant="ghost"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="px-3 lg:px-4 py-1 lg:py-2 flex items-center w-[120px] lg:w-[140px] h-[35px] lg:h-[39px] gap-[8px] lg:gap-[10px] text-[16px] lg:text-[20px] font-medium font-work-sans"
                >
                  <User className="!w-5 !h-5 lg:!w-6 lg:!h-6" aria-hidden="true" />
                  <span className="max-[1200px]:hidden">Account</span>
                  <IoChevronDown className={`transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
                </Button>

                {userMenuOpen && (
                  <div className="absolute top-full right-0 mt-2 w-48 bg-black/95 border border-neutral-800 rounded-md shadow-lg z-50 overflow-hidden max-h-[80vh] overflow-y-auto">
                    <div className="px-4 py-3 border-b border-neutral-800">
                      <div className="text-sm font-medium text-white">{user.name}</div>
                      <div className="text-xs text-gray-400">{user.email}</div>
                      {user.is_premium && (
                        <div className="flex items-center gap-1 text-xs text-yellow-400 mt-1">
                          <Crown className="w-3 h-3" />
                          Elite Member
                        </div>
                      )}
                    </div>

                    <Link
                      href="/account/credits"
                      className="flex items-center px-4 py-2 hover:bg-neutral-800 text-sm"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      <Coins className="w-4 h-4 mr-3" />
                      Credit Management
                    </Link>

                    <Link
                      href="/account/settings"
                      className="flex items-center px-4 py-2 hover:bg-neutral-800 text-sm"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      <Settings className="w-4 h-4 mr-3" />
                      Account Settings
                    </Link>

                    {user.is_premium && (
                      <Link
                        href="/subscription/manage"
                        className="flex items-center px-4 py-2 hover:bg-neutral-800 text-sm"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <Crown className="w-4 h-4 mr-3" />
                        Manage Subscription
                      </Link>
                    )}

                    <button
                      onClick={handleLogout}
                      className="flex items-center w-full px-4 py-2 hover:bg-neutral-800 text-sm text-left"
                    >
                      <LogOut className="w-4 h-4 mr-3" />
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Button variant="ghost" onClick={() => router.push('/login')} className="w-[120px] lg:w-[140px] h-[35px] lg:h-[39px] px-3 lg:px-4 py-1 lg:py-2 flex items-center gap-[8px] lg:gap-[10px] text-[16px] lg:text-[20px] font-medium font-work-sans">
                <TbLogin className="!w-5 !h-5 lg:!w-6 lg:!h-6" aria-hidden="true" />
                Login
              </Button>
            )}

            <Button onClick={() => router.push('/contact')} className="px-3 lg:px-4 py-1 lg:py-2 flex items-center w-[120px] lg:w-[140px] h-[35px] lg:h-[39px] gap-[8px] lg:gap-[10px] text-[16px] lg:text-[20px] font-medium font-work-sans">
              <ShakingIcon icon={<IoChatbubble className="w-[16px] h-[16px] lg:w-[20px] lg:h-[20px]" aria-hidden="true" />} />
              Contact
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            className="max-[1060px]:flex hidden p-2 hover:bg-neutral-800/50 transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          >
            <RxHamburgerMenu size={24} className="text-white" aria-hidden="true" />
          </Button>

          {/* Mobile Menu Overlay */}
          {mobileMenuOpen && (
            <div
              id="mobile-menu"
              className="min-h-screen fixed inset-0 z-50 bg-black/98 backdrop-blur-sm overflow-y-auto transition-opacity duration-300 ease-in-out"
              role="dialog"
              aria-modal="true"
              ref={(el) => {
                if (el && mobileMenuOpen) {
                  // Animate the menu overlay
                  animate(el, { opacity: [0, 1] }, { duration: 0.3 })

                  // Animate the menu items with stagger effect
                  const menuItems = el.querySelectorAll('.menu-item');
                  animate(
                    menuItems,
                    {
                      opacity: [0, 1],
                      x: [-20, 0]
                    },
                    {
                      delay: stagger(0.05),
                      duration: 0.3
                    }
                  );
                }
              }}
            >
              <Button
                variant="ghost"
                className="absolute top-5 sm:top-6 md:top-7 right-3 sm:right-4 p-2 hover:bg-neutral-800/50 transition-colors rounded-full"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
              >
                <IoMdClose size={24} aria-hidden="true" />
              </Button>

              <div className="flex flex-col items-center pb-10 pt-[70px] sm:pt-[80px] md:pt-[95px] px-6 sm:px-8">
                {/* Mobile Credit Display */}
                {user && (
                  <div className="w-full max-w-sm mb-8 bg-neutral-900/70 p-4 rounded-lg border border-neutral-800/70">
                    <CreditDisplay variant="mobile" />
                  </div>
                )}

                <nav className="flex flex-col gap-6 items-start w-full max-w-sm mx-auto" aria-label="Mobile Navigation">
                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/") ? "page" : undefined}
                    >
                      <Home className="mr-3 w-5 h-5" />
                      Home
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/about") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/about"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/about") ? "page" : undefined}
                    >
                      <Info className="mr-3 w-5 h-5" />
                      About
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/subscription") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/subscription"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/subscription") ? "page" : undefined}
                    >
                      <Crown className="mr-3 w-5 h-5" />
                      Subscription
                    </Link>
                  </div>

                  {user && (
                    <>
                      <div className="w-full menu-item">
                        <Link
                          className={`font-semibold text-[20px] ${pathname.startsWith("/talk") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                          href={`/talk/conversation/new-chat`}
                          onClick={() => setMobileMenuOpen(false)}
                          aria-current={pathname.startsWith("/talk") ? "page" : undefined}
                        >
                          <MessageSquare className="mr-3 w-5 h-5" />
                          Talk
                        </Link>
                      </div>

                      <div className="w-full menu-item">
                        <Link
                          className={`font-semibold text-[20px] ${pathname.startsWith("/account") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                          href="/account/credits"
                          onClick={() => setMobileMenuOpen(false)}
                          aria-current={pathname.startsWith("/account") ? "page" : undefined}
                        >
                          <User className="mr-3 w-5 h-5" />
                          Account
                        </Link>
                      </div>

                      <div className="w-full menu-item">
                        <Link
                          className={`font-semibold text-[20px] ${pathname === "/gallery" ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                          href="/gallery"
                          onClick={() => setMobileMenuOpen(false)}
                          aria-current={pathname === "/gallery" ? "page" : undefined}
                        >
                          <Image className="mr-3 w-5 h-5" />
                          Gallery
                        </Link>
                      </div>

                      <div className="w-full menu-item">
                        <Link
                          className={`font-semibold text-[20px] ${isActive("/reminders") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                          href="/reminders"
                          onClick={() => setMobileMenuOpen(false)}
                          aria-current={isActive("/reminders") ? "page" : undefined}
                        >
                          <Calendar className="mr-3 w-5 h-5" />
                          Reminders
                        </Link>
                      </div>
                    </>
                  )}

                  <div className="w-full h-px bg-neutral-800/70 my-2"></div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/questbook") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/questbook"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/questbook") ? "page" : undefined}
                    >
                      <BookOpen className="mr-3 w-5 h-5" />
                      Questbook
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/product") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/product"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/product") ? "page" : undefined}
                    >
                      <Gift className="mr-3 w-5 h-5" />
                      Product
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/hub") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/my-hub"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/my-hub") ? "page" : undefined}
                    >
                      <MapPin className="mr-3 w-5 h-5" />
                      My Hub
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/the-way") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/the-way"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/the-way") ? "page" : undefined}
                    >
                      <FaRoad className="mr-3 w-5 h-5" />
                      The Way
                    </Link>
                  </div>

                  <div className="w-full menu-item">
                    <Link
                      className={`font-semibold text-[20px] ${isActive("/events") ? "bg-neutral-800/70 border-l-4 border-[var(--mrwhite-primary-color)]" : ""} w-full px-3 py-2 hover:bg-neutral-800/50 rounded-md transition-colors duration-200 flex items-center`}
                      href="/events"
                      onClick={() => setMobileMenuOpen(false)}
                      aria-current={isActive("/events") ? "page" : undefined}
                    >
                      <Sparkles className="mr-3 w-5 h-5" />
                      Events
                    </Link>
                  </div>

                  <div className="w-full h-px bg-neutral-800/70 my-2"></div>

                  <div className="flex flex-col gap-4 mt-4 w-full justify-start">
                    {
                      user ? (
                        <div className="w-full menu-item">
                          <Button onClick={handleLogout} variant="ghost" className="px-4 py-2 flex items-center h-[45px] gap-[10px] text-[18px] sm:text-[20px] font-medium font-work-sans justify-start bg-neutral-800/70 hover:bg-neutral-700/70 w-full rounded-md transition-colors duration-200">
                            <LogOut className="!w-5 !h-5 sm:!w-6 sm:!h-6" aria-hidden="true" />
                            Logout
                          </Button>
                        </div>
                      ) : (
                        <div className="w-full menu-item">
                          <Button
                            variant="ghost"
                            onClick={() => navigateTo('/login')}
                            className="px-4 py-2 flex items-center h-[45px] gap-[10px] text-[18px] sm:text-[20px] font-medium font-work-sans justify-start bg-neutral-800/70 hover:bg-neutral-700/70 w-full rounded-md transition-colors duration-200"
                          >
                            <TbLogin className="!w-5 !h-5 sm:!w-6 sm:!h-6" aria-hidden="true" />
                            Login
                          </Button>
                        </div>
                      )
                    }
                    <div className="w-full menu-item">
                      <Button
                        onClick={() => navigateTo('/contact')}
                        className="px-4 py-2 flex items-center h-[45px] gap-[10px] text-[18px] sm:text-[20px] font-medium font-work-sans justify-start w-full bg-[var(--mrwhite-primary-color)] hover:bg-[var(--mrwhite-primary-color)]/90 text-black rounded-md transition-colors duration-200"
                      >
                        <ShakingIcon icon={<IoChatbubble className="w-[18px] h-[18px] sm:w-[20px] sm:h-[20px]" aria-hidden="true" />} />
                        Contact
                      </Button>
                    </div>
                  </div>
                </nav>
              </div>
            </div>
          )}
        </div>
      </header>
    </>
  )
}