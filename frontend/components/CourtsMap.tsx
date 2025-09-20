'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
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
  
  // Debounced viewport for cluster calculations
  const [debouncedViewport, setDebouncedViewport] = useState({
    longitude: -122.4194,
    latitude: 37.7749,
    zoom: 11
  });
  
  // Debounce timer ref
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  
  // Cluster cache for performance optimization
  const clusterCache = useRef<Record<string, any[]>>({});
  const MAX_CACHE_SIZE = 50; // Limit cache size to prevent memory issues

  // Use initialViewState centered on San Francisco (where the courts are located)
  const initialViewState = {
    longitude: -122.4194, // San Francisco longitude
    latitude: 37.7749,    // San Francisco latitude
    zoom: 11
  };

  // Helper function to create cache key from viewport
  const createCacheKey = (viewport: { longitude: number; latitude: number; zoom: number }, bbox: [number, number, number, number]) => {
    // Round zoom to nearest 0.5 for better cache efficiency
    const roundedZoom = Math.round(viewport.zoom * 2) / 2;
    // Round bbox coordinates to 1 decimal place for much better cache hits (0.1 degrees = ~7 miles)
    const roundedBbox = bbox.map(coord => Math.round(coord * 10) / 10);
    return `${roundedZoom}:${roundedBbox.join(',')}`;
  };

  // Calculate bounding box from actual map viewport bounds
  const calculateBoundingBox = (viewport: { longitude: number; latitude: number; zoom: number }) => {
    // Convert zoom level to approximate degrees per pixel
    // At zoom 0: ~360 degrees / 256 pixels = ~1.4 degrees per pixel
    // Each zoom level doubles the resolution
    const degreesPerPixel = 360 / (256 * Math.pow(2, viewport.zoom));
    
    // Approximate map container dimensions (adjust based on your actual map size)
    const mapWidth = 800;  // pixels
    const mapHeight = 600; // pixels
    
    // Calculate half-width and half-height in degrees
    const halfWidthDegrees = (mapWidth / 2) * degreesPerPixel;
    const halfHeightDegrees = (mapHeight / 2) * degreesPerPixel;
    
    // Create bounding box from actual viewport
    const bbox: [number, number, number, number] = [
      viewport.longitude - halfWidthDegrees,  // west
      viewport.latitude - halfHeightDegrees,  // south
      viewport.longitude + halfWidthDegrees,  // east
      viewport.latitude + halfHeightDegrees   // north
    ];
    
    // Calculate approximate size in miles for logging
    const avgLatitude = viewport.latitude;
    const latFactor = Math.cos(avgLatitude * Math.PI / 180); // Adjust for latitude
    const milesPerDegreeLongitude = 69.172 * latFactor;
    const milesPerDegreeLatitude = 69.172;
    
    const widthMiles = (bbox[2] - bbox[0]) * milesPerDegreeLongitude;
    const heightMiles = (bbox[3] - bbox[1]) * milesPerDegreeLatitude;
    
    return { 
      bbox, 
      widthMiles: Math.round(widthMiles * 100) / 100,
      heightMiles: Math.round(heightMiles * 100) / 100,
      degreesPerPixel: Math.round(degreesPerPixel * 1000000) / 1000000
    };
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
        // Simple timing for cluster initialization
        console.time('cluster-init');
        const initStartTime = performance.now();
        
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
        
        // End cluster init timing
        const initEndTime = performance.now();
        const initDuration = initEndTime - initStartTime;
        console.timeEnd('cluster-init');
        
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

  // Debounce viewport changes for cluster calculations
  useEffect(() => {
    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    
    console.log(JSON.stringify({
      event: 'viewport_debounce_started',
      timestamp: new Date().toISOString(),
      viewport: viewport,
      zoom: viewport.zoom
    }));
    
    // Set new timer for 500ms
    debounceTimer.current = setTimeout(() => {
      console.log(JSON.stringify({
        event: 'viewport_debounced',
        timestamp: new Date().toISOString(),
        previousViewport: debouncedViewport,
        newViewport: viewport,
        zoomChange: Math.abs(viewport.zoom - debouncedViewport.zoom)
      }));
      
      setDebouncedViewport(viewport);
    }, 500);
    
    // Cleanup function
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [viewport]);

  // Get clusters for current viewport (using debounced viewport)
  const clusters = useMemo(() => {
    // Simple timing for cluster calculations
    console.time('cluster-calc');
    const calcStartTime = performance.now();
    
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
    
    // Calculate bounding box from actual map viewport
    const { bbox, widthMiles, heightMiles, degreesPerPixel } = calculateBoundingBox(debouncedViewport);

    // Log bounding box calculation
    console.log(JSON.stringify({
      event: 'bbox_calculated',
      timestamp: new Date().toISOString(),
      zoom: debouncedViewport.zoom,
      degreesPerPixel: degreesPerPixel,
      bbox: bbox,
      widthMiles: widthMiles,
      heightMiles: heightMiles,
      diagonalMiles: Math.round(Math.sqrt(widthMiles * widthMiles + heightMiles * heightMiles) * 100) / 100
    }));
    
    // Create cache key
    const cacheKey = createCacheKey(debouncedViewport, bbox);
    
    // Check cache first
    if (clusterCache.current[cacheKey]) {
      const cachedResult = clusterCache.current[cacheKey];
      console.log(JSON.stringify({
        event: 'cluster_cache_hit',
        timestamp: new Date().toISOString(),
        cacheKey: cacheKey,
        clusterCount: cachedResult?.length || 0,
        cacheSize: Object.keys(clusterCache.current).length,
        zoom: debouncedViewport.zoom,
        widthMiles: widthMiles,
        heightMiles: heightMiles
      }));
      console.timeEnd('cluster-calc');
      return cachedResult;
    }
    
    try {
      const result = supercluster.getClusters(bbox, Math.floor(debouncedViewport.zoom));
      
      console.log(JSON.stringify({
        event: 'clusters_calculated',
        timestamp: new Date().toISOString(),
        clusterCount: result.length,
        zoom: debouncedViewport.zoom,
        bbox: bbox
      }));
      
      // End cluster calculation timing
      const calcEndTime = performance.now();
      const calcDuration = calcEndTime - calcStartTime;
      console.timeEnd('cluster-calc');
      
      console.log(JSON.stringify({
        event: 'clusters_calculated',
        timestamp: new Date().toISOString(),
        clusterCount: result.length,
        calcDurationMs: Math.round(calcDuration),
        zoom: debouncedViewport.zoom,
        widthMiles: widthMiles,
        heightMiles: heightMiles,
        bbox: bbox,
        cacheKey: cacheKey,
        diagonalMiles: Math.round(Math.sqrt(widthMiles * widthMiles + heightMiles * heightMiles) * 100) / 100
      }));
      
      // Log sample cluster data structure for debugging
      if (result.length > 0) {
        console.log(JSON.stringify({
          event: 'cluster_data_sample',
          timestamp: new Date().toISOString(),
          sampleCluster: {
            id: result[0].id,
            type: result[0].type,
            geometry: result[0].geometry,
            properties: result[0].properties
          },
          totalClusters: result.length
        }));
      }
      
      // Store in cache with LRU eviction
      const cacheKeys = Object.keys(clusterCache.current);
      if (cacheKeys.length >= MAX_CACHE_SIZE) {
        // Remove oldest entry (first key)
        const firstKey = cacheKeys[0];
        delete clusterCache.current[firstKey];
        
        console.log(JSON.stringify({
          event: 'cluster_cache_evicted',
          timestamp: new Date().toISOString(),
          evictedKey: firstKey || 'unknown',
          cacheSize: Object.keys(clusterCache.current).length
        }));
      }
      
      // Store new result in cache
      clusterCache.current[cacheKey] = result;
      
      console.log(JSON.stringify({
        event: 'cluster_cache_stored',
        timestamp: new Date().toISOString(),
        cacheKey: cacheKey,
        clusterCount: result.length,
        cacheSize: Object.keys(clusterCache.current).length,
        zoom: debouncedViewport.zoom,
        widthMiles: widthMiles,
        heightMiles: heightMiles
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
  }, [supercluster, debouncedViewport, mapPoints]);

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
      
      // Simple performance timing
      console.time('courts-data-fetch');
      const startTime = performance.now();
      
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
        // End timing and log performance
        const endTime = performance.now();
        const fetchDuration = endTime - startTime;
        console.timeEnd('courts-data-fetch');
        
        console.log(JSON.stringify({
          event: 'courts_loaded',
          timestamp: new Date().toISOString(),
          courtCount: result.data.length,
          fetchDurationMs: Math.round(fetchDuration),
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
    clustersCount: clusters?.length || 0,
    courtsCount: courts.length,
    mapLoaded: mapLoaded
  }));

  return (
    <div className={`relative ${className}`}>
      <div className="absolute top-4 left-4 z-10 bg-white p-3 rounded-lg shadow-lg">
        <h3 className="font-semibold text-gray-800 mb-1">Courts Map</h3>
        <p className="text-sm text-gray-600">
          {clusters?.length || 0} location{(clusters?.length || 0) !== 1 ? 's' : ''} found
        </p>
        <p className="text-xs text-gray-500">
          {courts.length} total courts
        </p>
        <p className="text-xs text-gray-500">
          Zoom: {viewport.zoom.toFixed(1)}
        </p>
            <p className="text-xs text-gray-500">
              Cache: {Object.keys(clusterCache.current).length}/{MAX_CACHE_SIZE}
            </p>
            <p className="text-xs text-gray-500">
              Viewport: {clusters?.length ? 
                `${Math.round(calculateBoundingBox(debouncedViewport).widthMiles * 10) / 10} × ${Math.round(calculateBoundingBox(debouncedViewport).heightMiles * 10) / 10}` 
                : '0 × 0'} miles
            </p>
            
            {/* Cache Status Indicator */}
            <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
              <p className="font-medium text-gray-700">Cache Status:</p>
              {Object.keys(clusterCache.current).length > 0 ? (
                <div>
                  <p className="text-green-600">✅ Cache Active ({Object.keys(clusterCache.current).length} entries)</p>
                  <p className="text-gray-600">Latest key: {Object.keys(clusterCache.current)[Object.keys(clusterCache.current).length - 1]?.substring(0, 30)}...</p>
                </div>
              ) : (
                <p className="text-yellow-600">⚠️ No cache entries yet</p>
              )}
            </div>
        
      </div>

      <Map
        initialViewState={initialViewState}
        onMove={evt => setViewport(evt.viewState)}
        onLoad={() => {
          console.log(JSON.stringify({
            event: 'map_loaded',
            timestamp: new Date().toISOString(),
            clustersCount: clusters?.length || 0
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
        {mapLoaded && clusters && clusters.map((cluster) => {
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
            key={`popup-${selectedCluster.id}`}
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
