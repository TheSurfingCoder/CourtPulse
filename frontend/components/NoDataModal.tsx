'use client';

interface NoDataModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function NoDataModal({ isOpen, onClose }: NoDataModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="text-center">
          <div className="text-6xl mb-4">😔</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Sorry!
          </h2>
          <p className="text-gray-600 mb-6">
            We don't have any courts in your area yet. Try zooming out or searching a different location.
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
