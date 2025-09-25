'use client';

import { useState } from 'react';

interface MapTypeToggleProps {
  currentMapType: 'streets' | 'satellite';
  onMapTypeChange: (mapType: 'streets' | 'satellite') => void;
}

export default function MapTypeToggle({ currentMapType, onMapTypeChange }: MapTypeToggleProps) {
  const [isOpen, setIsOpen] = useState(false);

  const mapTypes = [
    {
      id: 'streets' as const,
      name: 'Streets',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      )
    },
    {
      id: 'satellite' as const,
      name: 'Satellite',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    }
  ];

  const currentMapTypeData = mapTypes.find(type => type.id === currentMapType);

  return (
    <div className="absolute bottom-4 right-4 z-10">
      <div className="relative">
        {/* Main Toggle Button */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-4 py-3 bg-white rounded-lg shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-200 group"
        >
          <div className="text-gray-600 group-hover:text-gray-800">
            {currentMapTypeData?.icon}
          </div>
          <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
            {currentMapTypeData?.name}
          </span>
          <svg 
            className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute bottom-full right-0 mb-2 w-48 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden">
            {mapTypes.map((mapType) => (
              <button
                key={mapType.id}
                onClick={() => {
                  onMapTypeChange(mapType.id);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors duration-150 ${
                  currentMapType === mapType.id 
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-500' 
                    : 'text-gray-700 hover:text-gray-900'
                }`}
              >
                <div className={`${currentMapType === mapType.id ? 'text-blue-600' : 'text-gray-500'}`}>
                  {mapType.icon}
                </div>
                <span className="text-sm font-medium">{mapType.name}</span>
                {currentMapType === mapType.id && (
                  <svg className="w-4 h-4 text-blue-600 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
