'use client';

// Main court discovery page with interactive map and filtering
import CourtsMap from '../components/CourtsMap';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
import RateLimitModal from '../components/RateLimitModal';
import { useState, useEffect } from 'react';

export default function Home() {
  const [filters, setFilters] = useState<{
    sport: string[];
    surface_type: string[];
    school: boolean | undefined;
  }>({
    sport: [], // Show all sports initially
    surface_type: [],
    school: undefined
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

  // Fetch metadata and select all options initially
  useEffect(() => {
    const fetchMetadataAndSetAllFilters = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/courts/metadata`);
        if (response.ok) {
          const result = await response.json();
          if (result.success && result.data) {
            // Select all sports and all surfaces by default
            setFilters({
              sport: result.data.sports || [],
              surface_type: result.data.surfaceTypes || [],
              school: undefined
            });
          }
        }
      } catch (error) {
        console.error('Failed to fetch metadata:', error);
      }
    };

    fetchMetadataAndSetAllFilters();
  }, []);

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
      
      
      <RateLimitModal 
        isOpen={rateLimitModal.isOpen}
        onClose={closeRateLimitModal}
        onRetry={handleRetry}
        retryAfter={rateLimitModal.retryAfter}
      />
    </div>
  )
}