'use client'

import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Heart, Image as ImageIcon, FileText, BookOpen, Mic, Send, PlusCircle } from 'lucide-react';
import { BiBookAlt } from 'react-icons/bi';
import { RiVoiceprintFill } from 'react-icons/ri';
import { FiPaperclip } from 'react-icons/fi';
import { IoImageOutline } from 'react-icons/io5';

interface HowItWorksModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const HowItWorksModal: React.FC<HowItWorksModalProps> = ({ isOpen, onClose }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] bg-neutral-900 text-white border-neutral-700">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-white mb-2">How Mr. White Works</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6 max-h-[60vh] custom-scrollbar pr-2 py-4 overflow-y-auto">
          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <Send className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              Basic Chat
            </h3>
            <p className="text-neutral-300">
              Simply type your message in the input box and press send. Mr. White will respond to your questions about pets, care advice, and general inquiries.
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <Heart className="h-5 w-5  text-[var(--mrwhite-primary-color)]" fill="currentColor" />
              Health Mode
            </h3>
            <p className="text-neutral-300">
              Toggle Health Mode to access enhanced AI capabilities that can analyze your pet's health records, vaccination history, and provide personalized care recommendations. This premium feature uses 15 credits per message.
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <FiPaperclip className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              File Attachments
            </h3>
            <p className="text-neutral-300">
              Upload documents like medical records, care instructions, or any text files. Mr. White can analyze these documents and reference them in conversations. Supported formats include PDF, TXT, DOC, and DOCX.
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <IoImageOutline className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              Image Upload
            </h3>
            <p className="text-neutral-300">
              Share images of your pet for visual context. Mr. White can analyze images to provide more relevant advice. Supported formats include JPG, JPEG, PNG, and GIF.
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <BiBookAlt className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              Book Generation
            </h3>
            <p className="text-neutral-300">
              Create personalized pet storybooks with customizable options for tone, dimensions, typography, and color schemes. Perfect for creating memorable keepsakes about your furry friends.
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <RiVoiceprintFill className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              Voice Messages
            </h3>
            <p className="text-neutral-300">
              Record voice messages for a hands-free experience. Mr. White can transcribe and respond to your spoken questions (coming soon).
            </p>
          </section>

          <section>
            <h3 className="text-xl font-semibold flex items-center gap-2 mb-3">
              <PlusCircle className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
              Credits System
            </h3>
            <p className="text-neutral-300">
              Free users receive daily credits for basic chat. Premium features like Health Mode and advanced document analysis require additional credits. Premium subscribers receive monthly credit allowances.
            </p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm bg-neutral-800 p-3 rounded-sm">
              <div>• Basic Chat: 2 credits</div>
              <div>• Voice Message: 3 credits</div>
              <div>• File Upload: 4 credits</div>
              <div>• Health Mode: 8 credits</div>
              <div>• Book Generation: 10 credits</div>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default HowItWorksModal; 