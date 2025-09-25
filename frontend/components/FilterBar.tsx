'use client';

import React from 'react';
import { ChevronDown, SlidersIcon, SearchIcon } from 'lucide-react';

interface FilterBarProps {
  filters: {
    sport: string;
    surface_type: string;
    is_public: boolean | undefined;
  };
  setFilters: (filters: {
    sport: string;
    surface_type: string;
    is_public: boolean | undefined;
  }) => void;
}

export default function FilterBar({ 
  filters, 
  setFilters
}: FilterBarProps) {
  return (
    <div className="bg-white border-b border-gray-200 px-6 py-3">
      <div className="flex items-center gap-6">
        {/* Filters Label */}
        <div className="flex items-center gap-2">
          <SlidersIcon className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Filters:</span>
          <div className="w-px h-4 bg-gray-300"></div>
        </div>

        {/* Sport Filter */}
        <div className="relative">
          <select
            value={filters.sport}
            onChange={(e) => setFilters({ ...filters, sport: e.target.value })}
            className="appearance-none bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
          >
            <option value="">All Sports</option>
            <option value="basketball">Basketball</option>
            <option value="tennis">Tennis</option>
            <option value="soccer">Soccer</option>
            <option value="volleyball">Volleyball</option>
            <option value="handball">Handball</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>

        {/* Surface Filter */}
        <div className="relative">
          <select
            value={filters.surface_type}
            onChange={(e) => setFilters({ ...filters, surface_type: e.target.value })}
            className="appearance-none bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
          >
            <option value="">All Surfaces</option>
            <option value="asphalt">Asphalt</option>
            <option value="concrete">Concrete</option>
            <option value="wood">Wood</option>
            <option value="synthetic">Synthetic</option>
            <option value="clay">Clay</option>
            <option value="grass">Grass</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>

        {/* Access Filter */}
        <div className="relative">
          <select
            value={filters.is_public === undefined ? '' : filters.is_public.toString()}
            onChange={(e) => setFilters({ 
              ...filters, 
              is_public: e.target.value === '' ? undefined : e.target.value === 'true' 
            })}
            className="appearance-none bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer"
          >
            <option value="">All Access</option>
            <option value="true">Public Only</option>
            <option value="false">Private Only</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>

        {/* Clear Filters */}
        {(filters.sport || filters.surface_type || filters.is_public !== undefined) && (
          <button
            onClick={() => setFilters({ sport: '', surface_type: '', is_public: undefined })}
            className="px-3 py-2 text-sm text-red-500 hover:text-red-700 transition-colors rounded-lg hover:bg-red-50 border border-red-200 hover:border-red-300"
            title="Clear all filters"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
