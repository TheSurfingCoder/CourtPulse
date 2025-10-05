'use client';

import CourtsMap from '../components/CourtsMap';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import RateLimitModal from '../components/RateLimitModal';
import SentryTest from '../components/SentryTest';
import { useState } from 'react';

export default function Home() {
  const [filters, setFilters] = useState({
    sport: 'basketball', // Start with basketball like the original
    surface_type: '',
    is_public: undefined as boolean | undefined
  });

  const [loading, setLoading] = useState(false);
  const [needsNewSearch, setNeedsNewSearch] = useState(false);
  const [viewport, setViewport] = useState({ 
    longitude: -122.4194, 
    latitude: 37.7849, 
    zoom: 14 
  });
  const [rateLimitModal, setRateLimitModal] = useState({
    isOpen: false,
    retryAfter: 60
  });
  const [rateLimitUntil, setRateLimitUntil] = useState<number | null>(null);
  const [showSentryTest, setShowSentryTest] = useState(false);

  const handleRefresh = () => {
    // Trigger a manual search in the CourtsMap component
    // This will be handled by the CourtsMap component's internal logic
    console.log('Refresh triggered');
  };

  const handleLoadingChange = (loading: boolean) => {
    setLoading(loading);
  };

  const handleNeedsNewSearchChange = (needsNewSearch: boolean) => {
    setNeedsNewSearch(needsNewSearch);
  };

  const handleViewportChange = (viewport: { longitude: number; latitude: number; zoom: number }) => {
    setViewport(viewport);
  };

  const handleRateLimitExceeded = (retryAfter: number) => {
    const until = Date.now() + (retryAfter * 1000);
    setRateLimitUntil(until);
    setRateLimitModal({
      isOpen: true,
      retryAfter
    });
  };

  const closeRateLimitModal = () => {
    setRateLimitModal({
      isOpen: false,
      retryAfter: 60
    });
  };

  const handleRetry = () => {
    // Check if rate limit period has passed
    if (rateLimitUntil && Date.now() < rateLimitUntil) {
      const remainingSeconds = Math.ceil((rateLimitUntil - Date.now()) / 1000);
      setRateLimitModal({
        isOpen: true,
        retryAfter: remainingSeconds
      });
      return; // Don't retry yet
    }
    
    // Close the modal and reset rate limit
    setRateLimitModal({
      isOpen: false,
      retryAfter: 60
    });
    setRateLimitUntil(null);
    
    // Trigger a new search by setting needsNewSearch to true
    setNeedsNewSearch(true);
  };

  return (
    <div className="flex flex-col w-full h-screen">
      <Header />
      <FilterBar 
        filters={filters}
        setFilters={setFilters}
      />
      <main className="flex-1 flex flex-col w-full overflow-hidden">
        <CourtsMap 
          filters={filters}
          onFiltersChange={setFilters}
          onRefresh={handleRefresh}
          loading={loading}
          needsNewSearch={needsNewSearch}
          viewport={viewport}
          onLoadingChange={handleLoadingChange}
          onNeedsNewSearchChange={handleNeedsNewSearchChange}
          onViewportChange={handleViewportChange}
          onRateLimitExceeded={handleRateLimitExceeded}
        />
      </main>
      
      {/* Sentry Test Panel - Show in all environments for testing */}
      {true && (
        <div className="fixed bottom-4 right-4 z-50">
          {showSentryTest ? (
            <div>
              <SentryTest />
              <button
                onClick={() => setShowSentryTest(false)}
                className="mt-2 w-full px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                Hide Test Panel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowSentryTest(true)}
              className="px-3 py-2 text-xs bg-purple-600 text-white rounded hover:bg-purple-700"
            >
              🐛 Test Sentry
            </button>
          )}
        </div>
      )}
      
      <RateLimitModal 
        isOpen={rateLimitModal.isOpen}
        onClose={closeRateLimitModal}
        onRetry={handleRetry}
        retryAfter={rateLimitModal.retryAfter}
      />
    </div>
  )
}