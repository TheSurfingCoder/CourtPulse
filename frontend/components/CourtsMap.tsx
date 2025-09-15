'use client';

import { useState, useEffect, useMemo } from 'react';
import Map, { Marker, Popup } from 'react-map-gl/maplibre';
import Supercluster from 'supercluster';
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
  const [mapLoaded, setMapLoaded] = useState(false);
  const [viewport, setViewport] = useState({
    longitude: -122.4194,
    latitude: 37.7749,
    zoom: 11
  });

  // Use initialViewState centered on San Francisco (where the courts are located)
  const initialViewState = {
    longitude: -122.4194, // San Francisco longitude
    latitude: 37.7749,    // San Francisco latitude
    zoom: 11
  };

  // Clustering logic
  const cluster = useMemo(() => {
    const supercluster = new Supercluster({
      radius: 60,
      maxZoom: 14,
      minZoom: 0,
    });

    const points = courts.map(court => ({
      type: 'Feature' as const,
      properties: { court },
      geometry: {
        type: 'Point' as const,
        coordinates: [court.lng, court.lat]
      }
    }));

    supercluster.load(points);
    return supercluster;
  }, [courts]);

  const clusters = useMemo(() => {
    return cluster.getClusters([-180, -90, 180, 90], Math.floor(viewport.zoom));
  }, [cluster, viewport.zoom]);

  useEffect(() => {
    console.log(JSON.stringify({
      event: 'courts_map_initialized',
      timestamp: new Date().toISOString(),
      component: 'CourtsMap'
    }));
    fetchCourts();
  }, []);

  const fetchCourts = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      
      console.log(JSON.stringify({
        event: 'fetch_courts_started',
        timestamp: new Date().toISOString(),
        apiUrl: apiUrl
      }));
      
      const response = await fetch(`${apiUrl}/api/courts`);
      
      console.log(JSON.stringify({
        event: 'api_response_received',
        timestamp: new Date().toISOString(),
        status: response.status,
        ok: response.ok
      }));
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      console.log(JSON.stringify({
        event: 'api_data_parsed',
        timestamp: new Date().toISOString(),
        success: result.success,
        dataLength: result.data?.length || 0,
        hasData: !!result.data,
        isArray: Array.isArray(result.data)
      }));
      
      if (result.success && Array.isArray(result.data)) {
        // Log sample raw data to see what we're getting
        console.log(JSON.stringify({
          event: 'raw_court_data_sample',
          timestamp: new Date().toISOString(),
          sampleCourts: result.data.slice(0, 3).map((court: any) => ({
            id: court.id,
            name: court.name,
            lat: court.lat,
            lng: court.lng,
            latType: typeof court.lat,
            lngType: typeof court.lng
          }))
        }));
        
        // Fix coordinate data - lat/lng are swapped in the API response
        const validCourts = result.data.filter((court: any) => {
          if (!court || typeof court.lat !== 'number' || typeof court.lng !== 'number' ||
              court.lat === 0 || court.lng === 0 || isNaN(court.lat) || isNaN(court.lng)) {
            return false;
          }
          
          // The API has lat/lng swapped, so we need to swap them back
          const correctedLat = court.lng; // API's lng is actually latitude
          const correctedLng = court.lat; // API's lat is actually longitude
          
          // Validate the corrected coordinates
          const isValidLat = correctedLat >= -90 && correctedLat <= 90;
          const isValidLng = correctedLng >= -180 && correctedLng <= 180;
          
          if (isValidLat && isValidLng) {
            // Store corrected coordinates
            court.lat = correctedLat;
            court.lng = correctedLng;
            return true;
          }
          
          return false;
        });
        
        // Log invalid courts for debugging
        const invalidCourts = result.data.filter((court: any) => {
          const hasValidLat = court && 
            typeof court.lat === 'number' && 
            !isNaN(court.lat) && 
            court.lat >= -90 && 
            court.lat <= 90 &&
            court.lat !== 0;
            
          const hasValidLng = court && 
            typeof court.lng === 'number' && 
            !isNaN(court.lng) && 
            court.lng >= -180 && 
            court.lng <= 180 &&
            court.lng !== 0;
            
          return !(hasValidLat && hasValidLng);
        });

        if (invalidCourts.length > 0) {
          console.log(JSON.stringify({
            event: 'invalid_courts_found',
            timestamp: new Date().toISOString(),
            invalidCount: invalidCourts.length,
            sampleInvalidCourts: invalidCourts.slice(0, 3).map((court: any) => ({
              id: court.id,
              name: court.name,
              lat: court.lat,
              lng: court.lng,
              latType: typeof court.lat,
              lngType: typeof court.lng
            }))
          }));
        }

        console.log(JSON.stringify({
          event: 'courts_filtered',
          timestamp: new Date().toISOString(),
          originalCount: result.data.length,
          validCount: validCourts.length,
          filteredOut: result.data.length - validCourts.length
        }));
        
        setCourts(validCourts);
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch courts';
      setError(errorMessage);
      
      console.log(JSON.stringify({
        event: 'fetch_courts_error',
        timestamp: new Date().toISOString(),
        error: errorMessage,
        errorType: err?.constructor?.name || 'Unknown'
      }));
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
    console.log(JSON.stringify({
      event: 'map_loading_state',
      timestamp: new Date().toISOString(),
      state: 'loading'
    }));
    
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
    console.log(JSON.stringify({
      event: 'map_error_state',
      timestamp: new Date().toISOString(),
      state: 'error',
      error: error
    }));
    
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

  // Use a simple, stable map style to avoid MapLibre GL issues
  const mapStyle = {
    version: 8 as const,
    sources: {
      'osm': {
        type: 'raster' as const,
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors'
      }
    },
    layers: [
      {
        id: 'osm',
        type: 'raster' as const,
        source: 'osm'
      }
    ]
  };

  console.log(JSON.stringify({
    event: 'map_rendering',
    timestamp: new Date().toISOString(),
    state: 'success',
    courtsCount: courts.length,
    mapLoaded: mapLoaded
  }));

  return (
    <div className={`relative ${className}`}>
      <div className="absolute top-4 left-4 z-10 bg-white p-3 rounded-lg shadow-lg">
        <h3 className="font-semibold text-gray-800 mb-1">Courts Map</h3>
        <p className="text-sm text-gray-600">
          {courts.length} court{courts.length !== 1 ? 's' : ''} found
        </p>
      </div>

      <Map
        initialViewState={initialViewState}
        onMove={evt => setViewport(evt.viewState)}
        onLoad={() => {
          console.log(JSON.stringify({
            event: 'map_loaded',
            timestamp: new Date().toISOString(),
            courtsCount: courts.length
          }));
          setMapLoaded(true);
        }}
        onError={(error) => {
          console.log(JSON.stringify({
            event: 'map_error',
            timestamp: new Date().toISOString(),
            error: error.error?.message || 'Unknown map error',
            errorType: (error.error as any)?.type || 'Unknown'
          }));
        }}
        style={{ width: '100%', height: '500px' }}
        mapStyle={mapStyle}
        attributionControl={false}
        logoPosition="bottom-left"
      >
        {mapLoaded && clusters.map((cluster) => {
          const [longitude, latitude] = cluster.geometry.coordinates;
          const {
            cluster: isCluster,
            point_count: pointCount
          } = cluster.properties;

          if (isCluster) {
            // Render cluster marker
            return (
              <Marker
                key={`cluster-${cluster.id}`}
                longitude={longitude}
                latitude={latitude}
              >
                <div
                  className="cursor-pointer transform hover:scale-110 transition-transform"
                  style={{
                    background: '#3b82f6',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    color: 'white',
                    border: '2px solid white',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
                  }}
                  title={`${pointCount} courts`}
                >
                  {pointCount}
                </div>
              </Marker>
            );
          } else {
            // Render individual court marker
            const court = cluster.properties.court;
            return (
              <Marker
                key={court.id}
                longitude={longitude}
                latitude={latitude}
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
            );
          }
        })}

        {mapLoaded && selectedCourt && (
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
