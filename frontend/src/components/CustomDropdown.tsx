'use client';

import React, { useState, useRef, useEffect } from 'react';
import { IoChevronDown } from 'react-icons/io5';

interface DropdownOption {
  id: string;
  name: string;
}

interface CustomDropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = "Select an option",
  label
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const selectedOption = options.find(option => option.id === value);

  return (
    <div className="w-full">
      {label && <div className="mb-2">{label}</div>}
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          className="flex items-center justify-between w-full px-4 py-2 text-left font-semibold bg-black/95 border border-neutral-800 rounded-md hover:bg-neutral-800 transition-colors"
          onClick={() => setIsOpen(!isOpen)}
        >
          <span>{selectedOption?.name || placeholder}</span>
          <IoChevronDown className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 w-full bg-black/95 border border-neutral-800 rounded-md shadow-lg z-50 overflow-hidden">
            {options.map((option) => (
              <div
                key={option.id}
                className={`px-4 py-2 hover:bg-neutral-800 cursor-pointer font-semibold text-[16px] ${
                  option.id === value ? "text-[var(--mrwhite-primary-color)]" : ""
                }`}
                onClick={() => {
                  onChange(option.id);
                  setIsOpen(false);
                }}
              >
                {option.name}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomDropdown; 