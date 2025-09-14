'use client';

import { useState, useEffect } from 'react';
import Map, { Marker, Popup } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

interface Court {
  id: number;
  name: string;
  type: string;
  lat: number;
  lng: number;
  address: string;
  surface: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

interface CourtsMapProps {
  className?: string;
}

export default function CourtsMap({ className = '' }: CourtsMapProps) {
  const [courts, setCourts] = useState<Court[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCourt, setSelectedCourt] = useState<Court | null>(null);

  // Default viewport (you can adjust this to your area)
  const [viewport, setViewport] = useState({
    longitude: -73.9851, // NYC default - adjust for your location
    latitude: 40.7589,
    zoom: 12
  });

  useEffect(() => {
    fetchCourts();
  }, []);

  const fetchCourts = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/courts`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        setCourts(result.data);
        
        // Auto-center map on first court if available
        if (result.data.length > 0) {
          const firstCourt = result.data[0];
          setViewport(prev => ({
            ...prev,
            longitude: firstCourt.lng,
            latitude: firstCourt.lat,
            zoom: 13
          }));
        }
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch courts');
      console.error('Error fetching courts:', err);
    } finally {
      setLoading(false);
    }
  };

  const getCourtIcon = (type: string) => {
    // You can customize these icons later
    switch (type.toLowerCase()) {
      case 'basketball':
        return '🏀';
      case 'tennis':
        return '🎾';
      case 'soccer':
        return '⚽';
      case 'football':
        return '🏈';
      default:
        return '🏟️';
    }
  };

  const getCourtColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'basketball':
        return '#ff6b6b';
      case 'tennis':
        return '#4ecdc4';
      case 'soccer':
        return '#45b7d1';
      case 'football':
        return '#96ceb4';
      default:
        return '#feca57';
    }
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-96 bg-gray-100 rounded-lg ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading courts map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-96 bg-red-50 rounded-lg border border-red-200 ${className}`}>
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️</div>
          <h3 className="text-red-800 font-semibold mb-2">Error loading map</h3>
          <p className="text-red-600 mb-4">{error}</p>
          <button 
            onClick={fetchCourts}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div className="absolute top-4 left-4 z-10 bg-white p-3 rounded-lg shadow-lg">
        <h3 className="font-semibold text-gray-800 mb-1">Courts Map</h3>
        <p className="text-sm text-gray-600">
          {courts.length} court{courts.length !== 1 ? 's' : ''} found
        </p>
      </div>

      <Map
        {...viewport}
        onMove={evt => setViewport(evt.viewState)}
        style={{ width: '100%', height: '500px' }}
        mapStyle={`https://api.maptiler.com/maps/streets-v2/style.json?key=${process.env.NEXT_PUBLIC_MAPTILER_API_KEY || 'demo'}`}
        attributionControl={true}
        logoPosition="bottom-left"
      >
        {courts.map((court) => (
          <Marker
            key={court.id}
            longitude={court.lng}
            latitude={court.lat}
            onClick={() => setSelectedCourt(court)}
          >
            <div
              className="cursor-pointer transform hover:scale-110 transition-transform"
              style={{
                background: getCourtColor(court.type),
                borderRadius: '50%',
                width: '30px',
                height: '30px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '16px',
                border: '2px solid white',
                boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
              }}
              title={`${court.name} (${court.type})`}
            >
              {getCourtIcon(court.type)}
            </div>
          </Marker>
        ))}

        {selectedCourt && (
          <Popup
            longitude={selectedCourt.lng}
            latitude={selectedCourt.lat}
            onClose={() => setSelectedCourt(null)}
            closeButton={true}
            closeOnClick={false}
            anchor="bottom"
          >
            <div className="p-2 min-w-[250px]">
              <h3 className="font-semibold text-lg mb-2">{selectedCourt.name}</h3>
              <div className="space-y-1 text-sm">
                <p><span className="font-medium">Type:</span> {selectedCourt.type}</p>
                <p><span className="font-medium">Surface:</span> {selectedCourt.surface}</p>
                <p><span className="font-medium">Address:</span> {selectedCourt.address}</p>
                <p><span className="font-medium">Public:</span> {selectedCourt.is_public ? 'Yes' : 'No'}</p>
                <p><span className="font-medium">Coordinates:</span> {selectedCourt.lat.toFixed(6)}, {selectedCourt.lng.toFixed(6)}</p>
              </div>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}
