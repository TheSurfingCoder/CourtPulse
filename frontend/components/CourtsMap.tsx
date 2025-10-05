'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import Map, { Marker, Popup } from 'react-map-gl/maplibre';
import Supercluster from 'supercluster';
import 'maplibre-gl/dist/maplibre-gl.css';
import { logEvent, logError, logBusinessEvent } from '../lib/logger-with-backend';
import MapTypeToggle from './MapTypeToggle';


interface Court {
  id: number;
  name: string;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean;
  cluster_group_name: string;
  created_at: string;
  updated_at: string;
}


//used for React prop-passing for styling
interface CourtsMapProps {
  className?: string;
  filters: {
    sport: string;
    surface_type: string;
    is_public: boolean | undefined;
  };
  onFiltersChange: (filters: {
    sport: string;
    surface_type: string;
    is_public: boolean | undefined;
  }) => void;
  onRefresh: () => void;
  loading: boolean;
  needsNewSearch: boolean;
  viewport: { longitude: number; latitude: number; zoom: number };
  onLoadingChange: (loading: boolean) => void;
  onNeedsNewSearchChange: (needsNewSearch: boolean) => void;
  onViewportChange: (viewport: { longitude: number; latitude: number; zoom: number }) => void;
  onRateLimitExceeded: (retryAfter: number) => void;
}

export default function CourtsMap({ 
  className = '', 
  filters: externalFilters, 
  onFiltersChange, 
  onRefresh, 
  loading: externalLoading, 
  needsNewSearch: externalNeedsNewSearch, 
  viewport: externalViewport,
  onLoadingChange,
  onNeedsNewSearchChange,
  onViewportChange,
  onRateLimitExceeded
}: CourtsMapProps) {
  const [courts, setCourts] = useState<Court[]>([]); //array of court objects from API
  // Use external loading state only - no internal loading state
  const [error, setError] = useState<string | null>(null); // 
  const [selectedCluster, setSelectedCluster] = useState<any>(null); //used for popup trigger
  const [clusterDetails, setClusterDetails] = useState<Court[]>([]); //array of courts in selected cluster
  const [mapLoaded, setMapLoaded] = useState(false); //true when Maplibre GL finishes loading tiles/rendering.
  const [mapType, setMapType] = useState<'streets' | 'satellite'>('streets'); //current map type
/*
Why both:
loading - Data isn't ready yet
mapLoaded - Data is ready, but map isn't rendered yet
loading=true → fetch data → loading=false → map renders → mapLoaded=true → show markers
*/

  // Ref for immediate court data updates (prevents flickering)
  const courtsRef = useRef<Court[]>([]);
  
  const [viewport, setViewport] = useState(externalViewport); //updates on every mouse / zoom 
  
  // Debounced viewport for cluster calculations
  const [debouncedViewport, setDebouncedViewport] = useState(externalViewport); //same thing as viewport but delayed every 500ms

  // Update parent when viewport changes
  useEffect(() => {
    onViewportChange(viewport);
  }, [viewport, onViewportChange]);
  
  // Debounce timer ref
  const debounceTimer = useRef<NodeJS.Timeout | null>(null); //debouncertimer ref. good to use ref here
  
  // Use external filters only - no internal state
  const filters = externalFilters!;
  const setFilters = onFiltersChange!;
  
  // Court data cache for performance optimization (caches raw API responses)
  // Cache key format: "west,south,east,north" (bbox only, no zoom)
  const courtCache = useRef<Record<string, Court[]>>({});
  const MAX_CACHE_SIZE = 50; // Limit cache size to prevent memory issues
  
  // Track last searched area for smart re-query detection
  const lastSearchedArea = useRef<{
    bbox: [number, number, number, number];
    filters: { sport: string; surface_type: string; is_public: boolean | undefined };
  } | null>(null);

  // Use external needsNewSearch state only - no internal state

  // Use initialViewState centered on San Francisco (where the courts are located)
  // DEBUGGING: Memoize initialViewState to prevent map re-mounting
  const initialViewState = useMemo(() => ({
    longitude: -122.4194, // San Francisco longitude
    latitude: 37.7849,    // Upper half of San Francisco (north of downtown)
    zoom: 14              // More zoomed in for better testing
  }), []); // Empty dependency array - never changes

  // Map render complete

  // Helper function to create cache key from bbox only (no zoom, no filters)
  const createCacheKey = (bbox: [number, number, number, number]) => {
    // Round bbox coordinates to 1 decimal place for better cache hits (0.1 degrees = ~7 miles)
    const roundedBbox = bbox.map(coord => Math.round(coord * 10) / 10);
    return roundedBbox.join(',');
  };

  // Helper function to check if one bbox is contained within another
  const isBboxContained = (innerBbox: [number, number, number, number], outerBbox: [number, number, number, number]) => {
    const [innerWest, innerSouth, innerEast, innerNorth] = innerBbox;
    const [outerWest, outerSouth, outerEast, outerNorth] = outerBbox;
    
    return innerWest >= outerWest && innerSouth >= outerSouth && 
           innerEast <= outerEast && innerNorth <= outerNorth;
  };

  // Helper function to calculate bbox overlap percentage
  const calculateBboxOverlap = (bbox1: [number, number, number, number], bbox2: [number, number, number, number]) => {
    const [west1, south1, east1, north1] = bbox1;
    const [west2, south2, east2, north2] = bbox2;
    
    // Calculate intersection
    const west = Math.max(west1, west2);
    const south = Math.max(south1, south2);
    const east = Math.min(east1, east2);
    const north = Math.min(north1, north2);
    
    // If no intersection, return 0
    if (west >= east || south >= north) return 0;
    
    const intersectionArea = (east - west) * (north - south);
    const unionArea = (east1 - west1) * (north1 - south1) + (east2 - west2) * (north2 - south2) - intersectionArea;
    
    return intersectionArea / unionArea;
  };

  // Helper function to find cache hit based on coverage area
  const findCacheHit = (searchBbox: [number, number, number, number], filters: { sport: string; surface_type: string; is_public: boolean | undefined }) => {
    // Round search bbox to same precision as cache keys
    const roundedSearchBbox: [number, number, number, number] = searchBbox.map(coord => Math.round(coord * 10) / 10) as [number, number, number, number];
    
    // Check cache for coverage area hit
    
    for (const [cacheKey, cachedCourts] of Object.entries(courtCache.current)) {
      const [cacheWest, cacheSouth, cacheEast, cacheNorth] = cacheKey.split(',').map(Number);
      const cacheBbox: [number, number, number, number] = [cacheWest, cacheSouth, cacheEast, cacheNorth];
      
      // Check if search area is within cached area
      
      // Check if search area is within cached area (using rounded coordinates)
      if (isBboxContained(roundedSearchBbox, cacheBbox)) {
        // Found coverage cache hit - filter client-side
        
        // Filter cached results client-side
        const filteredCourts = cachedCourts.filter((court: Court) => {
          if (filters.sport && court.type !== filters.sport) return false;
          if (filters.surface_type && court.surface !== filters.surface_type) return false;
          if (filters.is_public !== undefined && court.is_public !== filters.is_public) return false;
          return true;
        });
        
        // Log partial cache hit
        logEvent('coverage_cache_hit', {
          cacheKey: cacheKey,
          searchBbox: searchBbox,
          cacheBbox: cacheBbox,
          originalCourtCount: cachedCourts.length,
          filteredCourtCount: filteredCourts.length,
          filters: filters
        });
        
        return filteredCourts;
      }
    }
    
    // No cache hit found
    
    return null; // No cache hit
  };

  // Helper function to check if user has moved to a new area requiring search
  const shouldTriggerNewSearch = (currentBbox: [number, number, number, number], currentFilters: { sport: string; surface_type: string; is_public: boolean | undefined }) => {
    if (!lastSearchedArea.current) return false;
    
    // Check if we have cached data that can cover this area
    const cachedResult = findCacheHit(currentBbox, currentFilters);
    if (cachedResult) {
      return false; // No need to search - we have this area cached
    }
    
    // Check if current area is contained within last searched area (cache hit)
    const { bbox: lastBbox } = lastSearchedArea.current;
    if (isBboxContained(currentBbox, lastBbox)) {
      return false; // No need to search - we have this area cached
    }
    
    // Check if current area has < 50% overlap with last searched area (new area)
    const overlap = calculateBboxOverlap(currentBbox, lastBbox);
    return overlap < 0.5;
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
          logEvent('cache_overlap_found', {cacheKey: cacheKey,
            cacheBbox: cacheBbox,
            searchBbox: searchBbox,
            overlappingCourtCount: cachedCourts.length});
          
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
        is_public: court.is_public,
        cluster_group_name: court.cluster_group_name
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
  // Initializing supercluster
      
      try {
        console.time('cluster-init');
        const initStartTime = performance.now();
        
        const cluster = new Supercluster({
          radius: 40,
          maxZoom: 16,
          minZoom: 0,
          minPoints: 2
        });
        
        // Loading points into supercluster
        
        cluster.load(mapPoints);
        
        const initEndTime = performance.now();
        const initDuration = initEndTime - initStartTime;
        console.timeEnd('cluster-init');
        
        // Supercluster initialized
        
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
    
    // Viewport debounce started
    
    debounceTimer.current = setTimeout(() => {
      // Viewport debounced
      
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

    // Bbox calculated
    
    try {
      const result = supercluster.getClusters(bbox, Math.floor(debouncedViewport.zoom));
      
      // Clusters calculated
      
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
    // Courts map initialized
    
    // Trigger initial search after a short delay to ensure viewport is set
    // Note: Filters are already set by parent component
    const timer = setTimeout(() => {
      // Initial search triggered
      fetchCourtsWithFilters();
    }, 100);
    
    return () => clearTimeout(timer);
  }, []);

  // Handle filter changes - check cache first, then search if needed
  useEffect(() => {
    // Skip initial render to prevent double calls with initial useEffect
    const isInitialRender = !lastSearchedArea.current;
    if (isInitialRender) {
      return;
    }
    
    // Debounce filter changes to avoid excessive API calls
    const filterTimer = setTimeout(() => {
      // Check if we have cached data that can be filtered client-side
      const { bbox } = calculateBoundingBox(viewport);
      const cachedResult = findCacheHit(bbox, filters);
      
      if (cachedResult) {
        // Use cached data with client-side filtering
        setCourts(cachedResult);
        onNeedsNewSearchChange(false);
        logEvent('filter_applied_from_cache', {
          filters: filters,
          courtCount: cachedResult.length
        });
      } else {
        // No cache hit, need to search
        logEvent('filter_change_requires_search', {filters: filters});
        fetchCourtsWithFilters();
      }
    }, 300); // 300ms debounce
    
    return () => clearTimeout(filterTimer);
  }, [filters.sport, filters.surface_type, filters.is_public]);

  // Detect when user has moved to a new area requiring search
  useEffect(() => {
    if (!lastSearchedArea.current) return;
    
    const { bbox } = calculateBoundingBox(viewport);
    const shouldSearch = shouldTriggerNewSearch(bbox, filters);
    
    // Update needsNewSearch state
    
    onNeedsNewSearchChange(shouldSearch);
  }, [viewport.longitude, viewport.latitude, viewport.zoom]);


  const fetchCourtsWithFilters = async () => {
    // Prevent multiple simultaneous requests
    if (externalLoading) {
      return;
    }
    
    try {
      onLoadingChange(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      
      // Calculate bounding box from current viewport
      const { bbox } = calculateBoundingBox(viewport);
      
      // Check for coverage area cache hit first
      const cachedResult = findCacheHit(bbox, filters);
      if (cachedResult) {
        logEvent('cache_hit', {
          courtCount: cachedResult.length,
          cacheSize: Object.keys(courtCache.current).length
        });
        
        setCourts(cachedResult);
        onNeedsNewSearchChange(false);
        onLoadingChange(false);
        return;
      }
      
      // Check if zoom level allows searching
      if (viewport.zoom <= 11) {
        logEvent('search_skipped_low_zoom', {zoom: viewport.zoom});
        
        setCourts([]);
        onLoadingChange(false);
        return;
      }
      
      // Build query parameters - DON'T include filters to get raw data for caching
      const queryParams = new URLSearchParams({
        zoom: viewport.zoom.toString(),
        bbox: bbox.join(',')
      });
      
      // Note: We don't add filters to query params here because we want raw data for caching
      // Filters will be applied client-side to the cached data
      
      logEvent('api_search_started', {
        filters: filters,
        zoom: viewport.zoom
      });
      
      const response = await fetch(`${apiUrl}/api/courts/search?${queryParams.toString()}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit'
      });
      
      if (!response.ok) {
        // Handle rate limiting specifically
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After');
          const retryAfterSeconds = retryAfter ? parseInt(retryAfter, 10) : 60;
          onRateLimitExceeded(retryAfterSeconds);
          return; // Don't throw error, just return early
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Search completed
      
      if (result.success && Array.isArray(result.data)) {
        // NEW CACHING STRATEGY: Store by coverage area only (no zoom, no filters)
        const cacheKey = createCacheKey(bbox);
        
        // Manage cache size
        const cacheKeys = Object.keys(courtCache.current);
        if (cacheKeys.length >= MAX_CACHE_SIZE) {
          // Remove oldest entry (first key)
          const firstKey = cacheKeys[0];
          delete courtCache.current[firstKey];
          // Cache entry evicted
        }
        
        // Store the raw API response (all courts in this area)
        courtCache.current[cacheKey] = result.data;
        
        // Apply filters client-side to the raw data
        const filteredCourts = result.data.filter((court: Court) => {
          if (filters.sport && court.type !== filters.sport) return false;
          if (filters.surface_type && court.surface !== filters.surface_type) return false;
          if (filters.is_public !== undefined && court.is_public !== filters.is_public) return false;
          return true;
        });
        
        logEvent('cache_stored', {
          courtCount: result.data.length,
          filteredCourtCount: filteredCourts.length,
          cacheSize: Object.keys(courtCache.current).length,
          filters: filters
        });
        
        // Update last searched area for smart re-query detection
        lastSearchedArea.current = {
          bbox: bbox,
          filters: { ...filters }
        };
        
        setCourts(filteredCourts);
        onNeedsNewSearchChange(false);
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch courts';
      // Don't set error state - just log it and continue with empty courts
      logEvent('fetch_courts_with_filters_error', {error: errorMessage});
      
      // Set empty courts array so map still renders
      setCourts([]);
      onNeedsNewSearchChange(false);
    } finally {
      onLoadingChange(false);
    }
  };

  // Handle cluster clicks to show popup with cluster details
  const handleClusterClick = (cluster: any) => {
    if (cluster.properties.cluster && supercluster) {
      // It's a cluster - don't show popup, just log the click
      logEvent('cluster_clicked_no_popup', {
        clusterId: cluster.id,
        pointCount: cluster.properties.point_count
      });
      return; // Exit early for clusters
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
        cluster_group_name: cluster.properties.cluster_group_name || 'Unknown Group',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setClusterDetails([courtDetail]);
      setSelectedCluster(cluster);
    }
  };

  

  // Map style configuration based on current map type
  const mapStyle = useMemo(() => {
    const maptilerApiKey = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;
    
    if (mapType === 'satellite' && maptilerApiKey) {
      // Maptiler satellite style
      const satelliteStyle = {
        version: 8 as const,
        sources: {
          'maptiler-satellite': {
            type: 'raster' as const,
            tiles: [`https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=${maptilerApiKey}`],
            tileSize: 256,
            attribution: '© Maptiler © DigitalGlobe'
          }
        },
        layers: [
          {
            id: 'maptiler-satellite',
            type: 'raster' as const,
            source: 'maptiler-satellite'
          }
        ]
      };
      return satelliteStyle;
    }
    
    // Default OpenStreetMap style
    const streetStyle = {
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
    return streetStyle;
  }, [mapType]);

  // DEBUGGING: Don't unmount the map during loading - this was causing the flickering!
  // if (loading) {
  //   logEvent('map_loading_state', {
  //     state: 'loading'
  //   });
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

  // Don't block map rendering on API errors - just show empty map
  // The map should always be visible, even without court data

  // Handle map type change
  const handleMapTypeChange = (newMapType: 'streets' | 'satellite') => {
    setMapType(newMapType);
    logEvent('map_type_changed', {
      from: mapType,
      to: newMapType,
      timestamp: new Date().toISOString()
    });
  };

  // Map rendering complete

  return (
    <div className={`relative w-full h-full ${className}`}>
      {/* Loading Overlay - Only show when loading, don't unmount map */}
      {externalLoading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-20 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 font-medium">Searching courts...</p>
                </div>
        </div>
      )}

      {/* Refresh Button Overlay - Centered */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10">
        <button
          onClick={fetchCourtsWithFilters}
          disabled={viewport.zoom <= 11}
          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center gap-2 shadow-lg ${
            viewport.zoom <= 11
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : externalLoading
              ? 'bg-blue-100 text-blue-600 cursor-wait'
              : externalNeedsNewSearch
              ? 'bg-orange-500 hover:bg-orange-600 text-white shadow-md hover:shadow-lg animate-pulse'
              : 'bg-gray-400 hover:bg-gray-500 text-white shadow-md hover:shadow-lg'
          }`}
          title={externalNeedsNewSearch ? "New area detected - click to search this location" : "Filters auto-update, but you can manually refresh if needed"}
        >
          {externalLoading ? (
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          ) : externalNeedsNewSearch ? (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search Area
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search Area
            </>
          )}
        </button>
      </div>

      <Map
        initialViewState={initialViewState}
        onMove={evt => setViewport(evt.viewState)}
        onLoad={() => {
          // Map loaded
          setMapLoaded(true);
        }}
        onError={(error) => {
          // Map error occurred
        }}
        style={{ width: '100%', height: '100%' }}
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

        {mapLoaded && selectedCluster && !selectedCluster.properties.cluster && (
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
              <h3 className="font-semibold text-lg mb-1">
                {selectedCluster.properties.cluster_group_name}
              </h3>
              
              {/* Show individual court name if available */}
              {selectedCluster.properties.name && selectedCluster.properties.name !== selectedCluster.properties.cluster_group_name && (
                <p className="text-sm text-gray-600 mb-2 font-medium">
                  {selectedCluster.properties.name}
                </p>
              )}
              
              <div className="space-y-2 text-sm mb-3">
                <p><span className="font-medium">Type:</span> {selectedCluster.properties.type}</p>
                <p><span className="font-medium">Surface:</span> {selectedCluster.properties.surface}</p>
                <p><span className="font-medium">Public:</span> {selectedCluster.properties.is_public ? 'Yes' : 'No'}</p>
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Map Type Toggle - Bottom Right */}
      <MapTypeToggle 
        currentMapType={mapType}
        onMapTypeChange={handleMapTypeChange}
      />
    </div>
  );
}


