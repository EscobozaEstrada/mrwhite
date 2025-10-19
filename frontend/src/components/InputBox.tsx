'use client';

import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { ChangeEvent, KeyboardEvent, useState, useRef, useEffect } from 'react';

interface InputBoxProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
}

export function InputBox({ inputValue, setInputValue, onSubmit, placeholder = "Write your message here ..." }: InputBoxProps) {
  const [value, setValue] = useState<string>(inputValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200); // Cap max height
      textarea.style.height = `${newHeight}px`;
      textarea.dispatchEvent(new Event('resize', { bubbles: true }));
    }
  }, [value]);

  useEffect(() => {
    setValue(inputValue);
  }, [inputValue]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      console.log('Submitted:', value);
      onSubmit();

      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'; // Reset height after submit
      }
    }
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    setInputValue(e.target.value);
  };

  return (
    <Textarea
      ref={textareaRef}
      value={value}
      onChange={handleChange}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      className={cn(
        'w-full !bg-transparent border-none text-[16px] md:!text-[20px] text-white outline-none ring-0',
        'focus:ring-0 focus:border-none focus:ring-offset-0 focus:shadow-none focus-visible:ring-0 focus-visible:border-none focus-visible:outline-none',
        'placeholder:text-gray-400 font-sans resize-none',
        'min-h-[40px] md:min-h-[48px] px-0 py-2 md:py-3 rounded-sm',
        'scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-transparent scrollbar-thumb-rounded custom-scrollbar'
      )}
      style={{
        lineHeight: '1.5', // Consistent line spacing
      }}
    />
  );
}