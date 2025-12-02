'use client';

import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, SlidersIcon } from 'lucide-react';

interface FilterBarProps {
  filters: {
    sport: string[];
    surface_type: string[];
    school: boolean | undefined;
  };
  setFilters: (filters: {
    sport: string[];
    surface_type: string[];
    school: boolean | undefined;
  }) => void;
}

export default function FilterBar({ 
  filters, 
  setFilters
}: FilterBarProps) {
  const [availableSports, setAvailableSports] = useState<string[]>([]);
  const [availableSurfaces, setAvailableSurfaces] = useState<string[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [isSportsDropdownOpen, setIsSportsDropdownOpen] = useState(false);
  const [isSurfacesDropdownOpen, setIsSurfacesDropdownOpen] = useState(false);
  const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
  
  const sportsDropdownRef = useRef<HTMLDivElement>(null);
  const surfacesDropdownRef = useRef<HTMLDivElement>(null);
  const locationDropdownRef = useRef<HTMLDivElement>(null);

  // Fetch metadata on mount
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        setIsLoadingMetadata(true);
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/courts/metadata`);
        if (response.ok) {
          const result = await response.json();
          if (result.success && result.data) {
            setAvailableSports(result.data.sports || []);
            setAvailableSurfaces(result.data.surfaceTypes || []);
          }
        }
      } catch (error) {
        console.error('Failed to fetch metadata:', error);
      } finally {
        setIsLoadingMetadata(false);
      }
    };

    fetchMetadata();
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        (sportsDropdownRef.current && !sportsDropdownRef.current.contains(event.target as Node)) &&
        (surfacesDropdownRef.current && !surfacesDropdownRef.current.contains(event.target as Node)) &&
        (locationDropdownRef.current && !locationDropdownRef.current.contains(event.target as Node))
      ) {
        setIsSportsDropdownOpen(false);
        setIsSurfacesDropdownOpen(false);
        setIsLocationDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleSport = (sport: string) => {
    setFilters({
      ...filters,
      sport: filters.sport.includes(sport)
        ? filters.sport.filter(s => s !== sport)
        : [...filters.sport, sport]
    });
  };

  const toggleSurface = (surface: string) => {
    setFilters({
      ...filters,
      surface_type: filters.surface_type.includes(surface)
        ? filters.surface_type.filter(s => s !== surface)
        : [...filters.surface_type, surface]
    });
  };

  const toggleSchool = (schoolValue: boolean | undefined) => {
    setFilters({
      ...filters,
      school: filters.school === schoolValue ? undefined : schoolValue
    });
  };

  const clearAllFilters = () => {
    setFilters({
      sport: [],
      surface_type: [],
      school: undefined
    });
  };

  const hasActiveFilters = filters.sport.length > 0 || filters.surface_type.length > 0 || filters.school !== undefined;

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-3">
      <div className="flex items-center gap-6">
        {/* Filters Label */}
        <div className="flex items-center gap-2">
          <SlidersIcon className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Filters:</span>
          <div className="w-px h-4 bg-gray-300"></div>
        </div>

        {/* Sport Filter - Multi-select */}
        <div className="relative" ref={sportsDropdownRef}>
          <button
            onClick={() => setIsSportsDropdownOpen(!isSportsDropdownOpen)}
            className="bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer flex items-center gap-2"
          >
            <span>Sports ({filters.sport.length})</span>
            <ChevronDown className={`w-4 h-4 text-gray-500 pointer-events-none transition-transform ${isSportsDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isSportsDropdownOpen && (
            <div className="absolute top-full mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-50 min-w-[200px] max-h-[300px] overflow-y-auto">
              {availableSports.map((sport) => (
                <label key={sport} className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.sport.includes(sport)}
                    onChange={() => toggleSport(sport)}
                    className="mr-2"
                  />
                  <span className="text-sm capitalize">{sport}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Surface Filter - Multi-select */}
        <div className="relative" ref={surfacesDropdownRef}>
          <button
            onClick={() => setIsSurfacesDropdownOpen(!isSurfacesDropdownOpen)}
            className="bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer flex items-center gap-2"
          >
            <span>Surfaces ({filters.surface_type.length})</span>
            <ChevronDown className={`w-4 h-4 text-gray-500 pointer-events-none transition-transform ${isSurfacesDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isSurfacesDropdownOpen && (
            <div className="absolute top-full mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-50 min-w-[200px] max-h-[300px] overflow-y-auto">
              {availableSurfaces.map((surface) => (
                <label key={surface} className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.surface_type.includes(surface)}
                    onChange={() => toggleSurface(surface)}
                    className="mr-2"
                  />
                  <span className="text-sm capitalize">{surface}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Location Filter - Radio button style for school/non-school/unknown */}
        <div className="relative" ref={locationDropdownRef}>
          <button
            onClick={() => setIsLocationDropdownOpen(!isLocationDropdownOpen)}
            className="bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer flex items-center gap-2"
          >
            <span>Location {filters.school === true ? '(Schools)' : filters.school === false ? '(Non-schools)' : ''}</span>
            <ChevronDown className={`w-4 h-4 text-gray-500 pointer-events-none transition-transform ${isLocationDropdownOpen ? 'rotate-180' : ''}`} />
          </button>
          {isLocationDropdownOpen && (
            <div className="absolute top-full mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-50 min-w-[200px]">
              <label className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                <input
                  type="radio"
                  name="location"
                  checked={filters.school === undefined}
                  onChange={() => toggleSchool(undefined)}
                  className="mr-2"
                />
                <span className="text-sm">All Locations</span>
              </label>
              <label className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                <input
                  type="radio"
                  name="location"
                  checked={filters.school === true}
                  onChange={() => toggleSchool(true)}
                  className="mr-2"
                />
                <span className="text-sm">Schools Only</span>
              </label>
              <label className="flex items-center px-4 py-2 hover:bg-gray-50 cursor-pointer">
                <input
                  type="radio"
                  name="location"
                  checked={filters.school === false}
                  onChange={() => toggleSchool(false)}
                  className="mr-2"
                />
                <span className="text-sm">Non-Schools Only</span>
              </label>
            </div>
          )}
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button
            onClick={clearAllFilters}
            className="px-3 py-2 text-sm text-red-500 hover:text-red-700 transition-colors rounded-lg hover:bg-red-50 border border-red-200 hover:border-red-300"
            title="Clear all filters"
          >
            ✕ Clear
          </button>
        )}
      </div>
    </div>
  );
}
