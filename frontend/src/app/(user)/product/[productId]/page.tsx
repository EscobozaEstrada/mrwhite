"use client"

import Image from "next/image";
import { FiShoppingBag, FiChevronDown } from "react-icons/fi";
import { IoWaterOutline } from "react-icons/io5";
import { MdOutlineSecurity } from "react-icons/md";
import { LuDroplet } from "react-icons/lu";
import { TbTruckDelivery } from "react-icons/tb";
import { FaStar, FaStarHalfAlt, FaRegStar, FaShoppingCart, FaGraduationCap } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";

const SingleProductPage = () => {
    const [openSection, setOpenSection] = useState<string | null>(null);
    const [currentBgIndex, setCurrentBgIndex] = useState(0);

    const toggleSection = (section: string) => {
        setOpenSection(openSection === section ? null : section);
    };

    // Background image carousel effect
    useEffect(() => {
        const bgImages = [
            '/assets/product-hero.png',
            '/assets/talk-hero-1.png',
            '/assets/talk-hero-2.png',
            '/assets/talk-hero-3.png'
        ];

        const interval = setInterval(() => {
            setCurrentBgIndex(prevIndex => (prevIndex + 1) % bgImages.length);
        }, 5001); // Change image every 5 seconds

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="flex flex-col gap-y-24 overflow-x-hidden bg-black">

            <section className="flex flex-col md:flex-row gap-10 px-4 md:px-10 mx-auto w-full mt-20 mb-20">

                <div className="w-full md:w-1/2 flex flex-col justify-between h-fit">
                    <div className="w-full h-[400px] md:h-[652px] relative">
                        <Image
                            src="/assets/product-bottle-1.png"
                            alt="product-bottle-main"
                            fill
                            className="object-cover"
                        />
                    </div>

                    <div className="flex justify-between mt-4">
                        <div className="h-[100px] md:h-[171px] w-[30%] relative">
                            <Image
                                src="/assets/product-bottle-2.png"
                                alt="select-image-2"
                                fill
                                className="object-cover border-none outline-none"
                            />
                        </div>
                        <div className="h-[100px] md:h-[171px] w-[30%] relative">
                            <Image
                                src="/assets/product-bottle-3.png"
                                alt="select-image-3"
                                fill
                                className="object-cover"
                            />
                        </div>
                        <div className="h-[100px] md:h-[171px] w-[30%] relative">
                            <Image
                                src="/assets/product-bottle-4.png"
                                alt="select-image-4"
                                fill
                                className="object-cover"
                            />
                        </div>
                    </div>
                </div>

                <div className="w-full md:w-1/2 self-start">
                    {/* Rating and Reviews */}
                    <div className="flex items-center gap-2 mb-2">
                        <div className="flex">
                            <FaStar className="text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="text-[var(--mrwhite-primary-color)]" />
                            <FaStarHalfAlt className="text-[var(--mrwhite-primary-color)]" />
                        </div>
                        <span className="text-sm text-gray-300">4.7/5</span>
                        <span className="text-xs text-gray-400">(106 ratings)</span>
                    </div>

                    {/* Product Title */}
                    <h1 className="text-2xl md:text-3xl font-bold mb-2">32oz 3-in-1 Portable Travel Water Bottle</h1>

                    {/* Price */}
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-gray-400 line-through">$29.99</span>
                        <span className="text-2xl font-bold text-[var(--mrwhite-primary-color)]">$24.99</span>
                    </div>

                    {/* Description */}
                    <p className="text-gray-300 mb-6">
                        The Tail-Wagging Love Portable Hydration bottle is a convenient, pet-themed water bottle
                        designed for dog lovers to stay hydrated on the go.
                    </p>

                    {/* Features */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                        <div className="flex items-center gap-3 bg-neutral-900 p-3 rounded-lg">
                            <div className="bg-neutral-800 p-2 rounded-full">
                                <IoWaterOutline className="text-[var(--mrwhite-primary-color)] text-xl" />
                            </div>
                            <span className="text-sm">2-in-1 Hydration & Feeding</span>
                        </div>

                        <div className="flex items-center gap-3 bg-neutral-900 p-3 rounded-lg">
                            <div className="bg-neutral-800 p-2 rounded-full">
                                <LuDroplet className="text-[var(--mrwhite-primary-color)] text-xl" />
                            </div>
                            <span className="text-sm">Leak-Proof Portability</span>
                        </div>

                        <div className="flex items-center gap-3 bg-neutral-900 p-3 rounded-lg">
                            <div className="bg-neutral-800 p-2 rounded-full">
                                <MdOutlineSecurity className="text-[var(--mrwhite-primary-color)] text-xl" />
                            </div>
                            <span className="text-sm">Safe, BPA-Free Material</span>
                        </div>

                        <div className="flex items-center gap-3 bg-neutral-900 p-3 rounded-lg">
                            <div className="bg-neutral-800 p-2 rounded-full">
                                <FiShoppingBag className="text-[var(--mrwhite-primary-color)] text-xl" />
                            </div>
                            <span className="text-sm">One-Button Dispensing</span>
                        </div>
                    </div>

                    {/* Shipping Info */}
                    <div className="flex items-center justify-center gap-2 bg-neutral-900 p-3 rounded-t-lg rounded-b-none">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="text-sm text-gray-300">Shipped within 24h</span>
                    </div>

                    {/* Buy Button */}
                    <Button className="w-full hover:bg-[var(--mrwhite-primary-color)] text-black font-bold py-4 rounded-b-lg rounded-t-none mb-6 flex items-center justify-center gap-2">
                        <FaShoppingCart className="w-5 h-5" />
                        Buy Now
                    </Button>

                    {/* Additional Info */}
                    <div className="bg-neutral-900 p-2 rounded-lg mb-6">
                        <div className="flex items-center justify-center gap-2 text-sm text-gray-300">
                            <div className="w-8 h-8 rounded-full bg-black flex items-center justify-center">
                                <FaGraduationCap className="w-4 h-4" />
                            </div>
                            Developed with 50 years of dog-care knowledge.
                        </div>
                    </div>

                    {/* Color Options */}
                    <div className="mb-6">
                        <h3 className="text-lg font-medium mb-3">Color</h3>
                        <div className="flex gap-2">
                            <div className="w-10 h-10 bg-black rounded-md"></div>
                            <div className="w-10 h-10 bg-gray-300 rounded-md"></div>
                            <div className="w-10 h-10 bg-pink-100 rounded-md"></div>
                        </div>
                    </div>

                    {/* Collapsible Sections */}
                    <div className="space-y-2">
                        <div className="border-t border-neutral-800">
                            <div
                                className="flex justify-between items-center py-4 cursor-pointer"
                                onClick={() => toggleSection('details')}
                            >
                                <h3 className="font-medium">Details</h3>
                                <FiChevronDown className={`transform transition-transform duration-300 ${openSection === 'details' ? 'rotate-180' : ''}`} />
                            </div>
                            <div className={`overflow-hidden transition-all duration-300 ease-in-out ${openSection === 'details' ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                                }`}>
                                <div className="pb-4 text-sm text-gray-300 space-y-2">
                                    <p>• Material: Premium BPA-free plastic</p>
                                    <p>• Capacity: 32oz / 946ml</p>
                                    <p>• Weight: 12oz / 340g</p>
                                    <p>• Dimensions: 9.5" x 3.2" x 3.2"</p>
                                    <p>• Dishwasher safe (top rack only)</p>
                                    <p>• Includes detachable pet bowl component</p>
                                </div>
                            </div>
                        </div>

                        <div className="border-t border-neutral-800">
                            <div
                                className="flex justify-between items-center py-4 cursor-pointer"
                                onClick={() => toggleSection('shipping')}
                            >
                                <h3 className="font-medium">Shipping</h3>
                                <FiChevronDown className={`transform transition-transform duration-300 ${openSection === 'shipping' ? 'rotate-180' : ''}`} />
                            </div>
                            <div className={`overflow-hidden transition-all duration-300 ease-in-out ${openSection === 'shipping' ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                                }`}>
                                <div className="pb-4 text-sm text-gray-300 space-y-2">
                                    <p>• Free shipping on orders over $35</p>
                                    <p>• Standard shipping: 3-5 business days</p>
                                    <p>• Express shipping: 1-2 business days (additional $12.99)</p>
                                    <p>• International shipping available to select countries</p>
                                    <p>• All orders processed within 24 hours</p>
                                </div>
                            </div>
                        </div>

                        <div className="border-t border-neutral-800">
                            <div
                                className="flex justify-between items-center py-4 cursor-pointer"
                                onClick={() => toggleSection('cleaning')}
                            >
                                <h3 className="font-medium">Cleaning</h3>
                                <FiChevronDown className={`transform transition-transform duration-300 ${openSection === 'cleaning' ? 'rotate-180' : ''}`} />
                            </div>
                            <div className={`overflow-hidden transition-all duration-300 ease-in-out ${openSection === 'cleaning' ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                                }`}>
                                <div className="pb-4 text-sm text-gray-300 space-y-2">
                                    <p>• Dishwasher safe on top rack only</p>
                                    <p>• Hand washing recommended for longer product life</p>
                                    <p>• Use mild soap and warm water</p>
                                    <p>• Bottle brush recommended for thorough cleaning</p>
                                    <p>• Dry completely before storing</p>
                                    <p>• Do not use abrasive cleaners or bleach</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </section>
        </div>
    )
}

export default SingleProductPage;