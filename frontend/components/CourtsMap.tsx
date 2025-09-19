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
  surface: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

interface ClusteredCourt {
  cluster_id: string;
  representative_osm_id: string;
  photon_name: string;
  total_courts: number;
  total_hoops: number;
  sports: string[];
  centroid_lat: number;
  centroid_lon: number;
  cluster_bounds: {
    bounds: any;
    center: any;
  };
}

interface CourtsMapProps {
  className?: string;
}

export default function CourtsMap({ className = '' }: CourtsMapProps) {
  const [courts, setCourts] = useState<Court[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [clusterDetails, setClusterDetails] = useState<Court[]>([]);
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

  // Convert courts to GeoJSON features for supercluster
  const mapPoints = useMemo(() => {
    return courts.map(court => ({
      type: 'Feature' as const,
      properties: { 
        id: court.id,
        name: court.name,
        type: court.type,
        surface: court.surface,
        is_public: court.is_public
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [court.lat, court.lng] // Fixed: lat is longitude, lng is latitude in the data
      }
    }));
  }, [courts]);

  // Initialize supercluster
  const [supercluster, setSupercluster] = useState<Supercluster | null>(null);

  // Load points into supercluster when data changes
  useEffect(() => {
    if (mapPoints.length > 0) {
      console.log(JSON.stringify({
        event: 'supercluster_initializing',
        timestamp: new Date().toISOString(),
        mapPointsLength: mapPoints.length,
        SuperclusterType: typeof Supercluster,
        samplePoint: mapPoints[0]
      }));
      
      try {
        const cluster = new Supercluster({
          radius: 40,        // Cluster radius in pixels
          maxZoom: 16,       // Max zoom level to cluster
          minZoom: 0,        // Min zoom level to cluster
          minPoints: 2       // Minimum points to form a cluster
        });
        
        console.log(JSON.stringify({
          event: 'supercluster_loading_points',
          timestamp: new Date().toISOString(),
          pointCount: mapPoints.length
        }));
        
        cluster.load(mapPoints);
        
        console.log(JSON.stringify({
          event: 'supercluster_initialized',
          timestamp: new Date().toISOString(),
          hasGetClusters: typeof cluster.getClusters === 'function',
          clusterMethods: Object.getOwnPropertyNames(Object.getPrototypeOf(cluster))
        }));
        
        setSupercluster(cluster);
      } catch (error) {
        console.error(JSON.stringify({
          event: 'supercluster_initialization_error',
          timestamp: new Date().toISOString(),
          error: error instanceof Error ? error.message : 'Unknown error',
          mapPointsLength: mapPoints.length
        }));
        setSupercluster(null);
      }
    } else {
      setSupercluster(null);
    }
  }, [mapPoints]);

  // Get clusters for current viewport
  const clusters = useMemo(() => {
    if (!supercluster || mapPoints.length === 0) {
      console.log(JSON.stringify({
        event: 'clusters_skipped',
        timestamp: new Date().toISOString(),
        reason: !supercluster ? 'no_supercluster' : 'no_mappoints',
        mapPointsLength: mapPoints.length
      }));
      // Fallback to showing individual points if no clustering
      return mapPoints.map((point, index) => ({
        ...point,
        id: `point-${index}`,
        properties: {
          ...point.properties,
          cluster: false,
          point_count: 1
        }
      }));
    }
    
    const bbox: [number, number, number, number] = [
      viewport.longitude - 0.1, // west
      viewport.latitude - 0.1,  // south
      viewport.longitude + 0.1, // east
      viewport.latitude + 0.1   // north
    ];
    
    try {
      const result = supercluster.getClusters(bbox, Math.floor(viewport.zoom));
      
      console.log(JSON.stringify({
        event: 'clusters_calculated',
        timestamp: new Date().toISOString(),
        clusterCount: result.length,
        zoom: viewport.zoom,
        bbox: bbox
      }));
      
      return result;
    } catch (error) {
      console.error(JSON.stringify({
        event: 'clusters_error',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
        superclusterType: typeof supercluster,
        hasGetClusters: typeof supercluster?.getClusters === 'function'
      }));
      
      // Fallback to showing individual points if clustering fails
      return mapPoints.map((point, index) => ({
        ...point,
        id: `point-${index}`,
        properties: {
          ...point.properties,
          cluster: false,
          point_count: 1
        }
      }));
    }
  }, [supercluster, viewport, mapPoints]);

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
      
      const response = await fetch(`${apiUrl}/api/courts`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });
      
      console.log(JSON.stringify({
        event: 'courts_api_response_received',
        timestamp: new Date().toISOString(),
        status: response.status,
        ok: response.ok,
        statusText: response.statusText,
        url: response.url
      }));
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      console.log(JSON.stringify({
        event: 'courts_api_data_parsed',
        timestamp: new Date().toISOString(),
        success: result.success,
        dataLength: result.data?.length || 0,
        hasData: !!result.data,
        isArray: Array.isArray(result.data)
      }));
      
      if (result.success && Array.isArray(result.data)) {
        console.log(JSON.stringify({
          event: 'courts_loaded',
          timestamp: new Date().toISOString(),
          courtCount: result.data.length,
          sampleCourts: result.data.slice(0, 3).map((court: any) => ({
            id: court.id,
            name: court.name,
            type: court.type,
            lat: court.lat,
            lng: court.lng
          }))
        }));
        
        setCourts(result.data);
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

  const handleClusterClick = (cluster: any) => {
    if (cluster.properties.cluster && supercluster) {
      // It's a cluster - get the children
      const children = supercluster.getChildren(cluster.id);
      setClusterDetails(children.map((child: any) => ({
        id: child.properties.id,
        name: child.properties.name,
        type: child.properties.type,
        surface: child.properties.surface,
        is_public: child.properties.is_public,
        lat: child.geometry.coordinates[1],
        lng: child.geometry.coordinates[0],
        created_at: '',
        updated_at: ''
      })));
      setSelectedCluster(cluster);
    } else {
      // It's an individual court
      setClusterDetails([{
        id: cluster.properties.id,
        name: cluster.properties.name,
        type: cluster.properties.type,
        surface: cluster.properties.surface,
        is_public: cluster.properties.is_public,
        lat: cluster.geometry.coordinates[1],
        lng: cluster.geometry.coordinates[0],
        created_at: '',
        updated_at: ''
      }]);
      setSelectedCluster(cluster);
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
    clustersCount: clusters.length,
    courtsCount: courts.length,
    mapLoaded: mapLoaded
  }));

  return (
    <div className={`relative ${className}`}>
      <div className="absolute top-4 left-4 z-10 bg-white p-3 rounded-lg shadow-lg">
        <h3 className="font-semibold text-gray-800 mb-1">Courts Map</h3>
        <p className="text-sm text-gray-600">
          {clusters.length} location{clusters.length !== 1 ? 's' : ''} found
        </p>
        <p className="text-xs text-gray-500">
          {courts.length} total courts
        </p>
        <p className="text-xs text-gray-500">
          Zoom: {viewport.zoom.toFixed(1)}
        </p>
      </div>

      <Map
        initialViewState={initialViewState}
        onMove={evt => setViewport(evt.viewState)}
        onLoad={() => {
          console.log(JSON.stringify({
            event: 'map_loaded',
            timestamp: new Date().toISOString(),
            clustersCount: clusters.length
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
          const isCluster = cluster.properties.cluster;
          const pointCount = cluster.properties.point_count || 1;
          const displayName = isCluster 
            ? `${pointCount} courts`
            : cluster.properties.name;
            
          const markerSize = isCluster ? 40 : 30;
          
          return (
            <Marker
              key={cluster.id}
              longitude={cluster.geometry.coordinates[0]}
              latitude={cluster.geometry.coordinates[1]}
              onClick={() => handleClusterClick(cluster)}
            >
              <div
                className="cursor-pointer transform hover:scale-110 transition-transform"
                style={{
                  background: isCluster ? '#ff6b6b' : '#feca57',
                  borderRadius: '50%',
                  width: `${markerSize}px`,
                  height: `${markerSize}px`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: isCluster ? '14px' : '16px',
                  fontWeight: isCluster ? 'bold' : 'normal',
                  color: 'white',
                  border: '2px solid white',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
                }}
                title={displayName}
              >
                {isCluster ? pointCount : '🏀'}
              </div>
            </Marker>
          );
        })}

        {mapLoaded && selectedCluster && (
          <Popup
            longitude={selectedCluster.geometry.coordinates[0]}
            latitude={selectedCluster.geometry.coordinates[1]}
            onClose={() => {
              setSelectedCluster(null);
              setClusterDetails([]);
            }}
            closeButton={true}
            closeOnClick={false}
            anchor="bottom"
          >
            <div className="p-3 min-w-[300px] max-w-[400px]">
              <h3 className="font-semibold text-lg mb-2">
                {selectedCluster.properties.cluster 
                  ? `${selectedCluster.properties.point_count} Courts`
                  : selectedCluster.properties.name
                }
              </h3>
              
              {selectedCluster.properties.cluster ? (
                <div className="space-y-2 text-sm mb-3">
                  <p><span className="font-medium">Courts:</span> {selectedCluster.properties.point_count}</p>
                </div>
              ) : (
                <div className="space-y-2 text-sm mb-3">
                  <p><span className="font-medium">Type:</span> {selectedCluster.properties.type}</p>
                  <p><span className="font-medium">Surface:</span> {selectedCluster.properties.surface}</p>
                  <p><span className="font-medium">Public:</span> {selectedCluster.properties.is_public ? 'Yes' : 'No'}</p>
                </div>
              )}
              
              {clusterDetails.length > 0 && (
                <div className="border-t pt-2">
                  <h4 className="font-medium text-sm mb-2">Individual Courts:</h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {clusterDetails.map((court, index) => (
                      <div key={court.id} className="text-xs bg-gray-50 p-2 rounded">
                        <p className="font-medium">{court.name}</p>
                        <p>Type: {court.type}</p>
                        <p>Surface: {court.surface}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}
