"use client";

import { useState, useRef, useEffect } from "react";
import { FiX, FiUpload } from "react-icons/fi";
import { FaPaw } from "react-icons/fa";
import { IoDocumentText } from "react-icons/io5";

interface DogFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: DogFormData) => void;
  initialData?: DogFormData | null;
}

interface DogFormData {
  name: string;
  breed: string;
  age?: string;
  dateOfBirth?: string;
  weight?: string;
  gender?: string;
  color?: string;
  additionalDetails?: string;
  image?: string;
  vetReport?: File;
}

export default function DogFormDialog({ isOpen, onClose, onSubmit, initialData }: DogFormDialogProps) {
  const [formData, setFormData] = useState<DogFormData>({
    name: "",
    breed: "",
    age: "",
    dateOfBirth: "",
    weight: "",
    gender: "",
    color: "",
    additionalDetails: "",
  });
  const [imagePreview, setImagePreview] = useState<string>("");
  const [vetReportName, setVetReportName] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const vetReportInputRef = useRef<HTMLInputElement>(null);

  // Populate form with initial data when editing
  useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name || "",
        breed: initialData.breed || "",
        age: initialData.age || "",
        dateOfBirth: initialData.dateOfBirth || "",
        weight: initialData.weight || "",
        gender: initialData.gender || "",
        color: initialData.color || "",
        additionalDetails: initialData.additionalDetails || "",
      });
      if (initialData.image) {
        setImagePreview(initialData.image);
      }
      if (initialData.vetReport) {
        setVetReportName(initialData.vetReport.name || "Existing report");
      }
    }
  }, [initialData]);

  if (!isOpen) return null;

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
        setFormData((prev) => ({ ...prev, image: reader.result as string }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handleVetReportSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setVetReportName(file.name);
      setFormData((prev) => ({ ...prev, vetReport: file }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name && formData.breed) {
      setIsSubmitting(true);
      try {
        await onSubmit(formData);
        setFormData({ name: "", breed: "", age: "", dateOfBirth: "", weight: "", gender: "", color: "", additionalDetails: "" });
        setImagePreview("");
        setVetReportName("");
      } catch (error) {
        console.error("Failed to submit dog form:", error);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleClose = () => {
    setFormData({ name: "", breed: "", age: "", dateOfBirth: "", weight: "", gender: "", color: "", additionalDetails: "" });
    setImagePreview("");
    setVetReportName("");
    setIsSubmitting(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 backdrop-blur-sm bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="bg-[#1a1a1a] rounded-lg max-w-2xl w-full border border-gray-800">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <h2 className="text-2xl font-bold text-white">
            {initialData ? "Edit Dog Profile" : "Add New Dog"}
          </h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-[#2a2a2a] rounded-lg transition-colors"
          >
            <FiX size={24} className="text-gray-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[80vh] custom-scrollbar overflow-y-auto">
          {/* Dog Image Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Dog Image (Optional)
            </label>
            <div className="flex items-center space-x-4">
              {/* Image Preview */}
              <div className="w-24 h-24 rounded-full bg-[#2a2a2a] flex items-center justify-center overflow-hidden">
                {imagePreview ? (
                  <img src={imagePreview} alt="Dog preview" className="w-full h-full object-cover" />
                ) : (
                  <FaPaw className="text-gray-500" size={32} />
                )}
              </div>

              {/* Upload Button */}
              <button
                type="button"
                onClick={() => imageInputRef.current?.click()}
                className="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors cursor-pointer"
              >
                <FiUpload size={18} />
                <span>Upload Image</span>
              </button>
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageSelect}
                className="hidden"
              />
            </div>
          </div>

          {/* Name (Required) */}
          <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., Max, Bella"
              className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700 placeholder-gray-500"
            />
          </div>

          {/* Breed (Required) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Breed <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.breed}
              onChange={(e) => setFormData((prev) => ({ ...prev, breed: e.target.value }))}
              placeholder="e.g., Golden Retriever, Labrador"
              className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700 placeholder-gray-500"
            />
            </div>
          </div>

          {/* Age, DOB, Weight, Color in Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Age */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Age (Optional)
              </label>
              <input
                type="number"
                min="0"
                max="30"
                value={formData.age || ""}
                onChange={(e) => setFormData((prev) => ({ ...prev, age: e.target.value }))}
                placeholder="e.g., 3"
                className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700 placeholder-gray-500"
              />
            </div>

            {/* Date of Birth */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Date of Birth (Optional)
              </label>
              <input
                type="date"
                value={formData.dateOfBirth || ""}
                onChange={(e) => setFormData((prev) => ({ ...prev, dateOfBirth: e.target.value }))}
                className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700"
              />
            </div>

            {/* Weight */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Weight (lbs) (Optional)
              </label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={formData.weight || ""}
                onChange={(e) => setFormData((prev) => ({ ...prev, weight: e.target.value }))}
                placeholder="e.g., 65.5"
                className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700 placeholder-gray-500"
              />
            </div>

            {/* Gender */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Gender (Optional)
              </label>
              <select
                value={formData.gender || ""}
                onChange={(e) => setFormData((prev) => ({ ...prev, gender: e.target.value }))}
                className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700"
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Color (Optional)
              </label>
              <input
                type="text"
                value={formData.color || ""}
                onChange={(e) => setFormData((prev) => ({ ...prev, color: e.target.value }))}
                placeholder="e.g., Golden, Black"
                className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 border border-gray-700 placeholder-gray-500"
              />
            </div>
          </div>

          {/* Additional Details (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Additional Details (Optional)
            </label>
            <textarea
              value={formData.additionalDetails}
              onChange={(e) => setFormData((prev) => ({ ...prev, additionalDetails: e.target.value }))}
              placeholder="Age, weight, temperament, allergies, etc."
              rows={4}
              className="w-full bg-[#2a2a2a] text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-purple-600 resize-none border border-gray-700 placeholder-gray-500"
            />
          </div>

          {/* Vet Report Upload (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Vet Report (Optional)
            </label>
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => vetReportInputRef.current?.click()}
                className="flex items-center space-x-2 px-4 py-2 bg-[#2a2a2a] hover:bg-[#333333] text-gray-300 rounded-lg transition-colors border border-gray-700 cursor-pointer"
              >
                <FiUpload size={18} />
                <span>Upload Report</span>
              </button>
              {vetReportName && (
                <span className="text-sm text-gray-400 flex items-center space-x-1">
                  <IoDocumentText size={16} />
                  <span>{vetReportName}</span>
                </span>
              )}
              <input
                ref={vetReportInputRef}
                type="file"
                accept=".pdf,image/*"
                onChange={handleVetReportSelect}
                className="hidden"
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Upload PDF or image of your dog's health records
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleClose}
              className="px-6 py-3 bg-[#2a2a2a] hover:bg-[#333333] text-gray-300 rounded-lg cursor-pointer transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg cursor-pointer transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{initialData ? "Updating..." : "Adding..."}</span>
                </>
              ) : (
                <span>{initialData ? "Update Dog" : "Add Dog"}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

