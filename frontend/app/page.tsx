'use client';

import CourtsMap from '../components/CourtsMap';
import Header from '../components/Header';
import FilterBar from '../components/FilterBar';
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
        />
      </main>
    </div>
  )
}