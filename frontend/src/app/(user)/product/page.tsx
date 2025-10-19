"use client";
import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import { ShoppingCartIcon } from "lucide-react";

interface Product {
    id: number;
    name: string;
    price: number;
    originalPrice: number;
    description: string;
    rating: number;
    reviews: number;
    tag: string;
    category: string;
}

const ProductsPage = () => {
    const [products, setProducts] = useState<Product[]>([
        {
            id: 1,
            name: "3-in-1 Portable Travel Water Bottle",
            price: 24.99,
            originalPrice: 39.99,
            description: "The bottle is a convenient, pet-themed water bottle designed for dog lovers to stay hydrated on the go.",
            rating: 4.7,
            reviews: 106,
            tag: "Gravity-Fed",
            category: "Hydration"
        },
        {
            id: 2,
            name: "3-in-1 Portable Travel Water Bottle",
            price: 24.99,
            originalPrice: 39.99,
            description: "The bottle is a convenient, pet-themed water bottle designed for dog lovers to stay hydrated on the go.",
            rating: 4.7,
            reviews: 106,
            tag: "Gravity-Fed",
            category: "Hydration"
        },
        {
            id: 3,
            name: "3-in-1 Portable Travel Water Bottle",
            price: 24.99,
            originalPrice: 39.99,
            description: "The bottle is a convenient, pet-themed water bottle designed for dog lovers to stay hydrated on the go.",
            rating: 4.7,
            reviews: 106,
            tag: "Gravity-Fed",
            category: "Hydration"
        },
        {
            id: 4,
            name: "3-in-1 Portable Travel Water Bottle",
            price: 24.99,
            originalPrice: 39.99,
            description: "The bottle is a convenient, pet-themed water bottle designed for dog lovers to stay hydrated on the go.",
            rating: 4.7,
            reviews: 106,
            tag: "Gravity-Fed",
            category: "Hydration"
        },
    ]);

    const [selectedCategory, setSelectedCategory] = useState<string>("All");
    const [sortBy, setSortBy] = useState<string>("featured");

    const categories = ["All", "Hydration", "Food", "Toys", "Accessories"];

    const filteredProducts = selectedCategory === "All"
        ? products
        : products.filter(product => product.category === selectedCategory);

    const sortedProducts = [...filteredProducts].sort((a, b) => {
        switch (sortBy) {
            case "price-low":
                return a.price - b.price;
            case "price-high":
                return b.price - a.price;
            case "rating":
                return b.rating - a.rating;
            default:
                return 0; // featured - maintain original order
        }
    });

    return (
        <div className="min-h-screen pb-12">

            <div className="container mx-auto max-[1200px]:px-4 px-10 py-8">
                <h1 className="text-3xl font-bold mb-2 text-center">Pet Products</h1>
                <p className="text-center text-gray-600 mb-8">Quality products for your furry friends</p>

                {/* Filter and Sort Section */}
                {/* <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-4 rounded-lg shadow-sm">
          <div className="flex flex-wrap gap-2">
            <span className="text-sm font-medium text-gray-700">Categories:</span>
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  selectedCategory === category
                    ? "bg-[#D3B86A] text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {category}
              </button>
            ))}
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-[#D3B86A] focus:border-transparent"
            >
              <option value="featured">Featured</option>
              <option value="price-low">Price: Low to High</option>
              <option value="price-high">Price: High to Low</option>
              <option value="rating">Highest Rated</option>
            </select>
          </div>
        </div> */}

                {/* Results count */}
                <div className="mb-6 text-sm text-gray-600">
                    Showing {sortedProducts.length} products {selectedCategory !== "All" ? `in ${selectedCategory}` : ""}
                </div>

                {/* Products Grid */}
                {sortedProducts.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {sortedProducts.map((product) => (
                            <div key={product.id} className="bg-neutral-900 rounded-lg overflow-hidden shadow-md hover:shadow-xl transition-shadow duration-300">
                                <div className="relative">
                                    {/* Product image */}
                                    <Link href={`/product/${product.id}`}>
                                        <div className="aspect-square relative">
                                            <Image
                                                src="/assets/product-image-1.png"
                                                alt={product.name}
                                                fill
                                                sizes="(max-width: 768px) 100vw, 50vw"
                                                className="object-cover"
                                            />
                                        </div>
                                    </Link>

                                    {/* Tag and Premium badge */}
                                    <div className="absolute top-3 left-3 bg-[var(--mrwhite-primary-color)] text-white text-xs font-bold px-3 py-1 rounded">
                                        {product.tag}
                                    </div>
                                    <div className="absolute top-3 right-3 bg-black text-white text-xs font-bold px-3 py-1 rounded">
                                        Premium
                                    </div>
                                </div>

                                {/* Product details */}
                                <div className="p-4">
                                    {/* Rating */}
                                    <div className="flex items-center mb-2">
                                        {[...Array(5)].map((_, i) => (
                                            <span key={i} className={`text-sm ${i < Math.floor(product.rating) ? "text-[var(--mrwhite-primary-color)]" : "text-gray-300"}`}>
                                                ★
                                            </span>
                                        ))}
                                        <span className="ml-1 text-sm font-medium">{product.rating}</span>
                                        <span className="ml-1 text-xs text-[var(--mrwhite-primary-color)]">{product.reviews} ratings</span>
                                    </div>

                                    {/* Product name */}
                                    <Link href={`/product/${product.id}`} className="font-semibold text-lg mb-1">{product.name}</Link>

                                    {/* Price */}
                                    <div className="flex items-center mb-3">
                                        <span className="line-through text-gray-500 mr-2">${product.originalPrice.toFixed(2)}</span>
                                        <span className="font-bold text-lg text-[var(--mrwhite-primary-color)]">${product.price.toFixed(2)}</span>
                                    </div>

                                    {/* Description */}
                                    <p className="text-sm text-gray-600 mb-4">{product.description}</p>

                                    {/* Add to cart button */}
                                    <Button
                                        className="w-full hover:bg-opacity-90 text-black font-semibold py-2 px-4 rounded flex items-center justify-center"
                                    >
                                        <ShoppingCartIcon className="h-5 w-5 mr-2" />
                                        Add to Cart
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12  rounded-lg shadow-sm">
                        <p className="text-lg text-gray-600">No products found in this category.</p>
                        <button
                            onClick={() => setSelectedCategory("All")}
                            className="mt-4 px-4 py-2 bg-[#D3B86A] text-black rounded hover:bg-opacity-90"
                        >
                            View All Products
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ProductsPage;