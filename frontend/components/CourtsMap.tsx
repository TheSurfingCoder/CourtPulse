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


//used for React prop-passing for styling
interface CourtsMapProps {
  className?: string;
}

export default function CourtsMap({ className = '' }: CourtsMapProps) {
  const [courts, setCourts] = useState<Court[]>([]); //array of court objects from API
  const [loading, setLoading] = useState(false); // boolean for fetch status
  const [error, setError] = useState<string | null>(null); // 
  const [selectedCluster, setSelectedCluster] = useState<any>(null); //used for popup trigger
  const [clusterDetails, setClusterDetails] = useState<Court[]>([]); //array of courts in selected cluster
  const [mapLoaded, setMapLoaded] = useState(false); //true when Maplibre GL finishes loading tiles/rendering.
/*
Why both:
loading - Data isn't ready yet
mapLoaded - Data is ready, but map isn't rendered yet
loading=true → fetch data → loading=false → map renders → mapLoaded=true → show markers
*/

  // Ref for immediate court data updates (prevents flickering)
  const courtsRef = useRef<Court[]>([]);
  
  const [viewport, setViewport] = useState({
    longitude: -122.4194,
    latitude: 37.7749,
    zoom: 12
  }); //updates on every mouse / zoom 
  
  // Debounced viewport for cluster calculations
  const [debouncedViewport, setDebouncedViewport] = useState({
    longitude: -122.4194,
    latitude: 37.7749,
    zoom: 12
  }); //same thing as viewport but delayed every 500ms
  
  // Debounce timer ref
  const debounceTimer = useRef<NodeJS.Timeout | null>(null); //debouncertimer ref. good to use ref here
  
  // Filter state for search functionality
  const [filters, setFilters] = useState({
    sport: '',
    surface_type: '',
    is_public: undefined as boolean | undefined
  });
  
  // Court data cache for performance optimization (caches raw API responses)
  const courtCache = useRef<Record<string, Court[]>>({});
  const MAX_CACHE_SIZE = 50; // Limit cache size to prevent memory issues

  // Use initialViewState centered on San Francisco (where the courts are located)
  // DEBUGGING: Memoize initialViewState to prevent map re-mounting
  const initialViewState = useMemo(() => ({
    longitude: -122.4194, // San Francisco longitude
    latitude: 37.7749,    // San Francisco latitude
    zoom: 12
  }), []); // Empty dependency array - never changes

  // DEBUGGING: Track component re-renders with more detail
  console.log(JSON.stringify({
    event: 'courts_map_render',
    timestamp: new Date().toISOString(),
    courtsLength: courts.length,
    loading: loading,
    error: error,
    mapLoaded: mapLoaded,
    viewport: viewport,
    renderCount: Math.random() // Add random number to track each render
  }));

  // Helper function to create cache key from viewport and filters
  const createCacheKey = (viewport: { longitude: number; latitude: number; zoom: number }, bbox: [number, number, number, number], filters: { sport: string; surface_type: string; is_public: boolean | undefined }) => {
    // Round zoom to nearest 0.5 for better cache efficiency
    const roundedZoom = Math.round(viewport.zoom * 2) / 2;
    // Round bbox coordinates to 1 decimal place for much better cache hits (0.1 degrees = ~7 miles)
    const roundedBbox = bbox.map(coord => Math.round(coord * 10) / 10);
    // Create filter key for cache differentiation
    const filterKey = JSON.stringify(filters);
    return `${roundedZoom}:${roundedBbox.join(',')}:${filterKey}`;
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

  // Check if two bounding boxes overlap
  const doBoundingBoxesOverlap = (bbox1: [number, number, number, number], bbox2: [number, number, number, number]) => {
    const [west1, south1, east1, north1] = bbox1;
    const [west2, south2, east2, north2] = bbox2;
    
    // Two rectangles overlap if one is not completely to the left, right, top, or bottom of the other
    return !(east1 < west2 || west1 > east2 || north1 < south2 || south1 > north2);
  };

  // Check if a point is within a bounding box
  const isPointInBoundingBox = (point: { lng: number; lat: number }, bbox: [number, number, number, number]) => {
    const [west, south, east, north] = bbox;
    return point.lng >= west && point.lng <= east && point.lat >= south && point.lat <= north;
  };

  // Get courts from cache that overlap with the current search area
  const getOverlappingCourtsFromCache = (searchBbox: [number, number, number, number], filters: any) => {
    const overlappingCourts: Court[] = [];
    const cacheKeys = Object.keys(courtCache.current);
    
    for (const cacheKey of cacheKeys) {
      // Parse cache key to get bbox and filters
      const parts = cacheKey.split(':');
      if (parts.length >= 3) {
        const cacheBbox = parts[1].split(',').map(coord => parseFloat(coord)) as [number, number, number, number];
        const cacheFilters = JSON.parse(parts.slice(2).join(':'));
        
        // Check if filters match and bboxes overlap
        if (JSON.stringify(cacheFilters) === JSON.stringify(filters) && 
            doBoundingBoxesOverlap(searchBbox, cacheBbox)) {
          
          const cachedCourts = courtCache.current[cacheKey];
          console.log(JSON.stringify({
            event: 'cache_overlap_found',
            timestamp: new Date().toISOString(),
            cacheKey: cacheKey,
            cacheBbox: cacheBbox,
            searchBbox: searchBbox,
            overlappingCourtCount: cachedCourts.length
          }));
          
          overlappingCourts.push(...cachedCourts);
        }
      }
    }
    
    // Remove duplicates based on court ID
    const uniqueCourts = overlappingCourts.filter((court, index, self) => 
      index === self.findIndex(c => c.id === court.id)
    );
    
    return uniqueCourts;
  };

  // Convert courts to GeoJSON features for supercluster
  //takes the data fetch / data stored in courts and stores it in mappoints which is an array of objects
  const mapPoints = useMemo(() => {
    // DEBUGGING: Comment out ref system temporarily
    // const courtsData = courtsRef.current.length > 0 ? courtsRef.current : courts;
    
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
        coordinates: [court.lng, court.lat] // GeoJSON format: [longitude, latitude]
      }
    }));
  }, [courts]);

  // DEBUGGING: Comment out ALL clustering logic
  const [supercluster, setSupercluster] = useState<Supercluster | null>(null);

  // Initialize Supercluster when mapPoints change
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
        console.time('cluster-init');
        const initStartTime = performance.now();
        
        const cluster = new Supercluster({
          radius: 40,
          maxZoom: 16,
          minZoom: 0,
          minPoints: 2
        });
        
        console.log(JSON.stringify({
          event: 'supercluster_loading_points',
          timestamp: new Date().toISOString(),
          pointCount: mapPoints.length
        }));
        
        cluster.load(mapPoints);
        
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

  // Debounce viewport changes to prevent excessive clustering recalculations
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    
    console.log(JSON.stringify({
      event: 'viewport_debounce_started',
      timestamp: new Date().toISOString(),
      viewport: viewport,
      zoom: viewport.zoom
    }));
    
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
    
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [viewport]);

  // Helper function to create fallback points
  const createFallbackPoints = () => {
      return mapPoints.map((point, index) => ({
        ...point,
        id: `point-${index}`,
        properties: {
          ...point.properties,
          cluster: false,
          point_count: 1
        }
      }));
  };

  // Get clusters for current viewport (using debounced viewport)
  const clusters = useMemo(() => {
    console.time('cluster-calc');
    const calcStartTime = performance.now();
    
    if (!supercluster) return [];
    
    const { bbox, widthMiles, heightMiles, degreesPerPixel } = calculateBoundingBox(debouncedViewport);

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
    
    try {
      const result = supercluster.getClusters(bbox, Math.floor(debouncedViewport.zoom));
      
      console.log(JSON.stringify({
        event: 'clusters_calculated',
        timestamp: new Date().toISOString(),
        clusterCount: result.length,
        viewport: debouncedViewport,
        calcDuration: performance.now() - calcStartTime
      }));
      
      console.timeEnd('cluster-calc');
      
      return result;
    } catch (error) {
      console.error(JSON.stringify({
        event: 'cluster_calculation_error',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
        viewport: debouncedViewport
      }));
      
      // Fallback: return individual points
      return createFallbackPoints();
    }
  }, [supercluster, debouncedViewport, mapPoints]);


  //runs once when CourtsMap first renders. Calls fetchcourts
  // Initial data fetch - search for basketball courts in San Francisco
  useEffect(() => {
    console.log(JSON.stringify({
      event: 'courts_map_initialized',
      timestamp: new Date().toISOString(),
      component: 'CourtsMap'
    }));
    
    // Set initial filter for basketball courts
    setFilters(prev => ({ ...prev, sport: 'basketball' }));
    
    // Trigger initial search after a short delay to ensure viewport is set
    const timer = setTimeout(() => {
      console.log(JSON.stringify({
        event: 'initial_search_triggered',
        timestamp: new Date().toISOString(),
        filters: { sport: 'basketball' },
        viewport: viewport
      }));
      fetchCourtsWithFilters();
    }, 100);
    
    return () => clearTimeout(timer);
  }, []);

  // Auto-fetch when filters change (debounced to avoid excessive API calls)
  useEffect(() => {
    // Skip initial render (filters are set in the first useEffect)
    if (filters.sport === '' && filters.surface_type === '' && filters.is_public === undefined) {
      return;
    }
    
    console.log(JSON.stringify({
      event: 'filters_changed',
      timestamp: new Date().toISOString(),
      filters: filters,
      viewport: viewport
    }));
    
    // Debounce filter changes to avoid excessive API calls
    const filterTimer = setTimeout(() => {
      console.log(JSON.stringify({
        event: 'auto_fetch_triggered_by_filter_change',
        timestamp: new Date().toISOString(),
        filters: filters
      }));
      fetchCourtsWithFilters();
    }, 300); // 300ms debounce
    
    return () => clearTimeout(filterTimer);
  }, [filters.sport, filters.surface_type, filters.is_public]);

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

  const fetchCourtsWithFilters = async () => {
    // DEBUGGING: Log when search starts
    console.log(JSON.stringify({
      event: 'search_button_clicked',
      timestamp: new Date().toISOString(),
      currentCourtsLength: courts.length,
      currentLoading: loading,
      currentViewport: viewport
    }));
    
    // Prevent multiple simultaneous requests
    if (loading) {
      console.log(JSON.stringify({
        event: 'search_already_in_progress',
        timestamp: new Date().toISOString()
      }));
      return;
    }
    
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      
      // Calculate bounding box from current viewport
      const { bbox } = calculateBoundingBox(viewport);
      
      // Create cache key for this request
      const cacheKey = createCacheKey(viewport, bbox, filters);
      
      // Check for exact cache hit first
      if (courtCache.current[cacheKey]) {
        const cachedCourts = courtCache.current[cacheKey];
        console.log(JSON.stringify({
          event: 'court_cache_hit',
          timestamp: new Date().toISOString(),
          cacheKey: cacheKey,
          courtCount: cachedCourts.length,
          cacheSize: Object.keys(courtCache.current).length,
          allCacheKeys: Object.keys(courtCache.current)
        }));
        
        console.log(JSON.stringify({
          event: 'no_api_call_needed',
          timestamp: new Date().toISOString(),
          reason: 'exact_cache_hit',
          cacheKey: cacheKey,
          courtCount: cachedCourts.length
        }));
        
        setCourts(cachedCourts);
        setLoading(false);
        return;
      }

      // INCREMENTAL FETCHING: Get overlapping courts from cache
      const overlappingCourts = getOverlappingCourtsFromCache(bbox, filters);
      console.log(JSON.stringify({
        event: 'incremental_fetch_start',
        timestamp: new Date().toISOString(),
        overlappingCourtCount: overlappingCourts.length,
        searchBbox: bbox,
        filters: filters
      }));
      
      // Check if zoom level allows searching
      if (viewport.zoom <= 11) {
        console.log(JSON.stringify({
          event: 'search_skipped_low_zoom',
          timestamp: new Date().toISOString(),
          zoom: viewport.zoom
        }));
        
        // Even at low zoom, show overlapping cached data if available
        if (overlappingCourts.length > 0) {
          console.log(JSON.stringify({
            event: 'no_api_call_needed',
            timestamp: new Date().toISOString(),
            reason: 'low_zoom_using_cached_data',
            overlappingCourtCount: overlappingCourts.length,
            zoom: viewport.zoom
          }));
          setCourts(overlappingCourts);
        } else {
          console.log(JSON.stringify({
            event: 'no_api_call_needed',
            timestamp: new Date().toISOString(),
            reason: 'low_zoom_no_cached_data',
            zoom: viewport.zoom
          }));
          setCourts([]);
        }
        
        setLoading(false);
        return;
      }
      
      // Build query parameters
      const queryParams = new URLSearchParams({
        zoom: viewport.zoom.toString(),
        bbox: bbox.join(',')
      });
      
      // Add filters to query params
      if (filters.sport) queryParams.append('sport', filters.sport);
      if (filters.surface_type) queryParams.append('surface_type', filters.surface_type);
      if (filters.is_public !== undefined) queryParams.append('is_public', filters.is_public.toString());
      
      console.log(JSON.stringify({
        event: 'new_api_call_started',
        timestamp: new Date().toISOString(),
        filters: filters,
        bbox: bbox,
        zoom: viewport.zoom,
        overlappingCachedCount: overlappingCourts.length,
        reason: 'cache_miss_or_incremental_fetch'
      }));
      
      const response = await fetch(`${apiUrl}/api/courts/search?${queryParams.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      console.log(JSON.stringify({
        event: 'courts_search_completed',
        timestamp: new Date().toISOString(),
        success: result.success,
        dataLength: result.data?.length || 0,
        filters: filters
      }));
      
            if (result.success && Array.isArray(result.data)) {
              // INCREMENTAL FETCHING: Combine new API data with overlapping cached data
              const combinedCourts = [...overlappingCourts, ...result.data];
              
              // Remove duplicates based on court ID
              const uniqueCourts = combinedCourts.filter((court, index, self) => 
                index === self.findIndex(c => c.id === court.id)
              );
              
              console.log(JSON.stringify({
                event: 'incremental_fetch_completed',
                timestamp: new Date().toISOString(),
                newApiDataCount: result.data.length,
                overlappingCachedCount: overlappingCourts.length,
                combinedCount: uniqueCourts.length,
                duplicatesRemoved: combinedCourts.length - uniqueCourts.length
              }));
              
              // Store new API data in cache
              const cacheKeys = Object.keys(courtCache.current);
              if (cacheKeys.length >= MAX_CACHE_SIZE) {
                // Remove oldest entry (first key)
                const firstKey = cacheKeys[0];
                delete courtCache.current[firstKey];
                console.log(JSON.stringify({
                  event: 'cache_entry_evicted',
                  timestamp: new Date().toISOString(),
                  evictedKey: firstKey,
                  cacheSize: cacheKeys.length
                }));
              }
              courtCache.current[cacheKey] = result.data;
              
              console.log(JSON.stringify({
                event: 'court_cache_stored',
                timestamp: new Date().toISOString(),
                cacheKey: cacheKey,
                courtCount: result.data.length,
                cacheSize: Object.keys(courtCache.current).length,
                filters: filters
              }));
        
              // Set the combined data (cached + new)
              setCourts(uniqueCourts);
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch courts';
      setError(errorMessage);
      
      console.log(JSON.stringify({
        event: 'fetch_courts_with_filters_error',
        timestamp: new Date().toISOString(),
        error: errorMessage
      }));
    } finally {
      setLoading(false);
    }
  };

  // Handle cluster clicks to show popup with cluster details
  const handleClusterClick = (cluster: any) => {
    if (cluster.properties.cluster && supercluster) {
      // It's a cluster - get the children
      const children = supercluster.getChildren(cluster.id);
      // Convert cluster features back to Court objects for display
      const courtDetails = children.map((child: any) => ({
        id: child.properties.id || child.id,
        name: child.properties.name || 'Unknown Court',
        type: child.properties.type || 'unknown',
        lat: child.geometry.coordinates[1],
        lng: child.geometry.coordinates[0],
        surface: child.properties.surface || 'Unknown',
        is_public: child.properties.is_public,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }));
      setClusterDetails(courtDetails);
      setSelectedCluster(cluster);
    } else {
      // It's an individual court - convert to Court object
      const courtDetail = {
        id: cluster.properties.id || cluster.id,
        name: cluster.properties.name || 'Unknown Court',
        type: cluster.properties.type || 'unknown',
        lat: cluster.geometry.coordinates[1],
        lng: cluster.geometry.coordinates[0],
        surface: cluster.properties.surface || 'Unknown',
        is_public: cluster.properties.is_public,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setClusterDetails([courtDetail]);
      setSelectedCluster(cluster);
    }
  };

  

  // DEBUGGING: Don't unmount the map during loading - this was causing the flickering!
  // if (loading) {
  //   console.log(JSON.stringify({
  //     event: 'map_loading_state',
  //     timestamp: new Date().toISOString(),
  //     state: 'loading'
  //   }));
  //   
  //   return (
  //     <div className={`flex items-center justify-center h-96 bg-gray-100 rounded-lg ${className}`}>
  //       <div className="text-center">
  //         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
  //         <p className="text-gray-600">Loading courts map...</p>
  //       </div>
  //     </div>
  //   );
  // }

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
      {/* Loading Overlay - Only show when loading, don't unmount map */}
      {loading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-20 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 font-medium">Searching courts...</p>
          </div>
        </div>
      )}
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
              Cache: {Object.keys(courtCache.current).length}/{MAX_CACHE_SIZE}
            </p>
            <p className="text-xs text-gray-500">
              Viewport: {clusters?.length ? 
                `${Math.round(calculateBoundingBox(debouncedViewport).widthMiles * 10) / 10} × ${Math.round(calculateBoundingBox(debouncedViewport).heightMiles * 10) / 10}` 
                : '0 × 0'} miles
            </p>
            
            {/* Cache Status Indicator */}
            <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
              <p className="font-medium text-gray-700">Cache Status:</p>
              {Object.keys(courtCache.current).length > 0 ? (
                <p className="text-green-600">✅ Cache Active ({Object.keys(courtCache.current).length} entries)</p>
              ) : (
                <p className="text-yellow-600">⚠️ No cache entries yet</p>
              )}
            </div>
        
      </div>

      {/* Search and Filter Controls - Pill Design Top Center */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10">
        <div className="bg-white/95 backdrop-blur-sm rounded-full shadow-lg border border-gray-200 px-6 py-3 flex items-center gap-4">
          {/* Sport Filter */}
          <select
            value={filters.sport}
            onChange={(e) => setFilters(prev => ({ ...prev, sport: e.target.value }))}
            className="px-3 py-1 text-sm border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:outline-none bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <option value="">All Sports</option>
            <option value="basketball">Basketball</option>
            <option value="tennis">Tennis</option>
            <option value="soccer">Soccer</option>
            <option value="volleyball">Volleyball</option>
            <option value="handball">Handball</option>
          </select>

          {/* Surface Filter */}
          <select
            value={filters.surface_type}
            onChange={(e) => setFilters(prev => ({ ...prev, surface_type: e.target.value }))}
            className="px-3 py-1 text-sm border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:outline-none bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <option value="">All Surfaces</option>
            <option value="asphalt">Asphalt</option>
            <option value="concrete">Concrete</option>
            <option value="wood">Wood</option>
            <option value="synthetic">Synthetic</option>
            <option value="clay">Clay</option>
            <option value="grass">Grass</option>
          </select>

          {/* Public/Private Toggle */}
          <select
            value={filters.is_public === undefined ? '' : filters.is_public.toString()}
            onChange={(e) => setFilters(prev => ({ 
              ...prev, 
              is_public: e.target.value === '' ? undefined : e.target.value === 'true' 
            }))}
            className="px-3 py-1 text-sm border-0 rounded-full focus:ring-2 focus:ring-blue-500 focus:outline-none bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <option value="">All Access</option>
            <option value="true">Public Only</option>
            <option value="false">Private Only</option>
          </select>

          {/* Divider */}
          <div className="w-px h-6 bg-gray-300"></div>

          {/* Refresh Button */}
          <button
            onClick={fetchCourtsWithFilters}
            disabled={viewport.zoom <= 11}
            className={`px-4 py-1 rounded-full font-medium transition-all duration-200 flex items-center gap-2 ${
              viewport.zoom <= 11
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : loading
                ? 'bg-blue-100 text-blue-600 cursor-wait'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg'
            }`}
            title="Filters auto-update, but you can manually refresh if needed"
          >
            {loading ? (
              <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
          </button>

          {/* Clear Filters */}
          {(filters.sport || filters.surface_type || filters.is_public !== undefined) && (
            <button
              onClick={() => setFilters({ sport: '', surface_type: '', is_public: undefined })}
              className="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 transition-colors rounded-full hover:bg-gray-100"
              title="Clear all filters"
            >
              ✕
            </button>
          )}
        </div>

        {/* Status Indicators - Below the pill */}
        <div className="mt-2 flex justify-center gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${viewport.zoom > 11 ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            {viewport.zoom > 11 ? 'Auto-Search Active' : 'Zoom In to Search'}
          </div>
          {loading && (
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
              Auto-searching...
            </div>
          )}
          {Object.keys(courtCache.current).length > 0 && (
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-purple-500"></div>
              {Object.keys(courtCache.current).length} cached
            </div>
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
