import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';

interface RateLimitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRetry: () => void;
  retryAfter?: number;
}

export default function RateLimitModal({ isOpen, onClose, onRetry, retryAfter = 60 }: RateLimitModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-center mb-4">
            <div className="bg-red-100 p-2 rounded-full mr-3">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Rate Limit Exceeded
            </h3>
          </div>
          
          <div className="mb-6">
            <p className="text-gray-600 mb-3">
              You've made too many requests too quickly. Please slow down to help us maintain service quality for everyone.
            </p>
            
            <div className="flex items-center text-sm text-gray-500 bg-gray-50 p-3 rounded-md">
              <Clock className="h-4 w-4 mr-2" />
              <span>
                Please wait <strong>{retryAfter} seconds</strong> before trying again.
              </span>
            </div>
          </div>
          
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
            <button
              onClick={onRetry}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors"
            >
              Retry Now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
