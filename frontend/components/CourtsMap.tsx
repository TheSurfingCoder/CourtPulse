'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import Map, { Marker, Popup, MapRef } from 'react-map-gl/maplibre';
import Supercluster from 'supercluster';
import 'maplibre-gl/dist/maplibre-gl.css';
import { logEvent, logError } from '../lib/logger-with-backend';
import MapTypeToggle from './MapTypeToggle';
import EditCourtModal from './EditCourtModal';


interface Court {
  id: number;
  name: string | null;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean | null;
  school: boolean;
  cluster_group_name: string | null;
  created_at: string;
  updated_at: string;
}

interface CourtsMapProps {
  className?: string;
  filters: {
    sport: string[];
    surface_type: string[];
    school: boolean | undefined;
    is_public: boolean | null | undefined; // true = public, false = private, null = unknown, undefined = all
  };
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
  filters, 
  loading: externalLoading, 
  needsNewSearch: externalNeedsNewSearch, 
  viewport: externalViewport,
  onLoadingChange,
  onNeedsNewSearchChange,
  onViewportChange,
  onRateLimitExceeded
}: CourtsMapProps) {

  const [courts, setCourts] = useState<Court[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapType, setMapType] = useState<'streets' | 'satellite'>('streets');
  const [editingCourt, setEditingCourt] = useState<Court | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [viewport, setViewport] = useState(externalViewport);
  const [debouncedViewport, setDebouncedViewport] = useState(externalViewport);

  const mapRef = useRef<MapRef | null>(null);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    onViewportChange(viewport);
  }, [viewport, onViewportChange]);
  
  // Helper function to get sport-specific icon
  const getSportIcon = (sportType: string): string => {
    const icons: Record<string, string> = {
      'basketball': '🏀',
      'tennis': '🎾',
      'soccer': '⚽',
      'volleyball': '🏐',
      'pickleball': '🏓',
      'beachvolleyball': '🏐',
      'american_football': '🏈',
      'baseball': '⚾',
      'other': '🏟️'
    };
    return icons[sportType] || icons['other'];
  };
  
  // Track searched areas by bbox keys (format: "west,south,east,north")
  // Set for fast lookup, array for insertion order (for eviction)
  const courtCache = useRef<Set<string>>(new Set());
  const cacheKeysOrder = useRef<string[]>([]); // Track insertion order for eviction
  // Map to track which courts belong to which bbox (for eviction only)
  const courtsByBbox = useRef<Record<string, Court[]>>({});
  const MAX_CACHE_SIZE = 10;

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

  // Helper function to merge courts arrays, removing duplicates by ID
  const mergeCourts = (existingCourts: Court[], newCourts: Court[]): Court[] => {
    const courtMap: Record<number, Court> = {};
    
    // Add existing courts to map
    existingCourts.forEach(court => {
      courtMap[court.id] = court;
    });
    
    // Add new courts to map (will overwrite duplicates with newer data)
    newCourts.forEach(court => {
      courtMap[court.id] = court;
    });
    
    return Object.values(courtMap);
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


  // Helper function to check if user has moved to a new area requiring search
  const shouldTriggerNewSearch = (currentBbox: [number, number, number, number]) => {
    // If no areas have been searched, don't trigger new search (let initial search run elsewhere)
    if (courtCache.current.size === 0) return false;
    
    // Round current bbox to same precision as cache keys
    const roundedCurrentBbox: [number, number, number, number] = currentBbox.map(coord => Math.round(coord * 10) / 10) as [number, number, number, number];
    
    // Check if current area is contained within any searched area
    for (const cacheKey of Array.from(courtCache.current)) {
      const [cacheWest, cacheSouth, cacheEast, cacheNorth] = cacheKey.split(',').map(Number);
      const cacheBbox: [number, number, number, number] = [cacheWest, cacheSouth, cacheEast, cacheNorth];
      
      if (isBboxContained(roundedCurrentBbox, cacheBbox)) {
        return false; // Area is fully contained in a searched area, no need to search
      }
    }
    
    // Check if current area has < 50% overlap with ANY searched area
    // If >= 50% overlap with any searched area, we might not need a new search
    for (const cacheKey of Array.from(courtCache.current)) {
      const [cacheWest, cacheSouth, cacheEast, cacheNorth] = cacheKey.split(',').map(Number);
      const cacheBbox: [number, number, number, number] = [cacheWest, cacheSouth, cacheEast, cacheNorth];
      const overlap = calculateBboxOverlap(currentBbox, cacheBbox);
      if (overlap >= 0.5) {
        return false; // Significant overlap with searched area, no need to search
      }
    }
    
    // No overlap with any searched area - trigger new search
    return true;
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


  // Filter accumulated courts based on current filters (regardless of viewport)
  const filteredCourts = useMemo(() => {
    return courts.filter((court: Court) => {
      // If no sports selected, show nothing
      if (filters.sport.length === 0) return false;
      // Apply sport filter
      if (!filters.sport.includes(court.type)) return false;
      
      // If no surfaces selected, show nothing
      if (filters.surface_type.length === 0) return false;
      // Apply surface filter
      if (!filters.surface_type.includes(court.surface)) return false;
      
      // Apply school filter if school is specified
      if (filters.school !== undefined && court.school !== filters.school) return false;
      
      // Apply is_public filter if specified (undefined = show all)
      if (filters.is_public !== undefined) {
        // filters.is_public can be true (public), false (private), or null (unknown)
        if (filters.is_public === null) {
          // Show only courts with unknown access
          if (court.is_public !== null) return false;
        } else {
          // Show only courts with matching access
          if (court.is_public !== filters.is_public) return false;
        }
      }
      
      return true;
    });
  }, [courts, filters]);

  // Convert filtered courts to GeoJSON features for supercluster
  //takes the filtered courts and stores it in mappoints which is an array of objects
  const mapPoints = useMemo(() => {
    return filteredCourts.map(court => ({
      type: 'Feature' as const,
      properties: { 
        id: court.id,
        name: court.name,
        type: court.type,
        surface: court.surface,
        is_public: court.is_public,
        school: court.school,
        cluster_group_name: court.cluster_group_name
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [court.lng, court.lat] // GeoJSON format: [longitude, latitude]
      }
    }));
  }, [filteredCourts]);

  // DEBUGGING: Comment out ALL clustering logic
  const [supercluster, setSupercluster] = useState<Supercluster | null>(null);

  // Initialize Supercluster when filtered courts change
  useEffect(() => {
    if (filteredCourts.length > 0) {
  // Initializing supercluster
      
      try {
        console.time('cluster-init');
        const initStartTime = performance.now();
        
        const cluster = new Supercluster({
          radius: 30,  // Reduced from 40 - points need to be closer together to cluster (moderately more declustered)
          maxZoom: 14,  // Reduced from 16 - stop clustering at zoom 14, individual points show from zoom 14+ (moderately earlier declustering)
          minZoom: 0,
          minPoints: 3  // Increased from 2 - need 3+ points to form a cluster (moderately less aggressive clustering)
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
    }, 200);
    
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
    
    if (!supercluster) return [];
    
    console.time('cluster-calc');
    
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
      fetchCourtsForArea();
    }, 100);
    
    return () => clearTimeout(timer);
  }, []);

  // Handle filter changes - filters are applied client-side to accumulated courts
  // No API call needed, just filter the existing courts state
  useEffect(() => {
    // Skip initial render to prevent double calls with initial useEffect
    const isInitialRender = courtCache.current.size === 0;
    if (isInitialRender) {
      return;
    }
    
    // Filters are applied via filteredCourts useMemo, no action needed here
    // Just log the filter change
    logEvent('filter_applied', {
      filters: filters,
      totalCourts: courts.length,
      filteredCourts: filteredCourts.length
    });
  }, [filters.sport, filters.surface_type, filters.school, filters.is_public, courts.length, filteredCourts.length]);

  // Detect when user has moved to a new area requiring search (using debounced viewport to avoid excessive calculations)
  useEffect(() => {
    if (courtCache.current.size === 0) return; // Skip if no areas searched yet
    
    const { bbox } = calculateBoundingBox(debouncedViewport);
    const shouldSearch = shouldTriggerNewSearch(bbox);
    
    // Update needsNewSearch state
    onNeedsNewSearchChange(shouldSearch);
  }, [debouncedViewport.longitude, debouncedViewport.latitude, debouncedViewport.zoom]);


  const fetchCourtsForArea = async () => {
    // Prevent multiple simultaneous requests
    if (externalLoading) {
      return;
    }
    
    try {
      onLoadingChange(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      
      // Calculate bounding box from current viewport
      const { bbox } = calculateBoundingBox(viewport);
      const cacheKey = createCacheKey(bbox);
      
      // Check if this area has already been searched
      if (courtCache.current.has(cacheKey)) {
        logEvent('area_already_searched', {
          cacheKey: cacheKey,
          cacheSize: courtCache.current.size
        });
        onNeedsNewSearchChange(false);
        onLoadingChange(false);
        return;
      }
      
      // Check if zoom level allows searching
      if (viewport.zoom <= 11) {
        logEvent('search_skipped_low_zoom', {zoom: viewport.zoom});
        onLoadingChange(false);
        return;
      }
      
      // Manage cache size - evict oldest if at max
      if (courtCache.current.size >= MAX_CACHE_SIZE) {
        const oldestKey = cacheKeysOrder.current[0];
        if (oldestKey) {
          // Remove from cache
          courtCache.current.delete(oldestKey);
          cacheKeysOrder.current.shift();
          
          // Remove courts from state that belong to this bbox
          const courtsToRemove = courtsByBbox.current[oldestKey] || [];
          const courtIdsToRemove = new Set(courtsToRemove.map((c: Court) => c.id));
          setCourts(prevCourts => prevCourts.filter(court => !courtIdsToRemove.has(court.id)));
          delete courtsByBbox.current[oldestKey];
          
          logEvent('cache_evicted', {
            evictedKey: oldestKey,
            courtsRemoved: courtsToRemove.length
          });
        }
      }
      
      // Build query parameters - get all courts in area (no filters)
      const queryParams = new URLSearchParams({
        zoom: viewport.zoom.toString(),
        bbox: bbox.join(',')
      });
      
      logEvent('api_search_started', {
        bbox: bbox,
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
      
      if (result.success && Array.isArray(result.data)) {
        // Add bbox to cache
        courtCache.current.add(cacheKey);
        cacheKeysOrder.current.push(cacheKey);
        
        // Track which courts belong to this bbox (for eviction)
        courtsByBbox.current[cacheKey] = result.data;
        
        // Add all courts to accumulated state (no filtering - filters applied via filteredCourts)
        setCourts(prevCourts => mergeCourts(prevCourts, result.data));
        
        logEvent('courts_fetched', {
          courtCount: result.data.length,
          cacheKey: cacheKey,
          cacheSize: courtCache.current.size
        });
        
        onNeedsNewSearchChange(false);
      } else {
        throw new Error(result.message || 'Failed to fetch courts');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch courts';
      logEvent('fetch_courts_error', {error: errorMessage});
      onNeedsNewSearchChange(false);
    } finally {
      onLoadingChange(false);
    }
  };

  // Handle cluster clicks to show popup with cluster details
  const handleClusterClick = (cluster: any) => {
    const [lng, lat] = cluster.geometry.coordinates;
    
    if (cluster.properties.cluster && supercluster) {
      // It's a cluster - center and zoom in
      logEvent('cluster_clicked', {
        clusterId: cluster.id,
        pointCount: cluster.properties.point_count,
        coordinates: { lng, lat }
      });
      
      // Zoom in on the cluster
      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [lng, lat],
          zoom: viewport.zoom + 2, // Zoom in by 2 levels
          duration: 1000 // 1 second smooth animation
        });
      }
    } else {
      // It's an individual court - center on it and show popup
      logEvent('court_clicked', {
        courtId: cluster.properties.id || cluster.id,
        courtName: cluster.properties.name,
        coordinates: { lng, lat }
      });
      
      // Center on the individual court without changing zoom
      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [lng, lat],
          zoom: viewport.zoom, // Keep current zoom level
          duration: 1000 // 1 second smooth animation
        });
      }
      
      // Convert to Court object and show popup
      const courtDetail = {
        id: cluster.properties.id || cluster.id,
        name: cluster.properties.name || 'Unknown Court',
        type: cluster.properties.type || 'unknown',
        lat: lat,
        lng: lng,
        surface: cluster.properties.surface || 'Unknown',
        is_public: cluster.properties.is_public,
        school: cluster.properties.school || false,
        cluster_group_name: cluster.properties.cluster_group_name || 'Unknown Group',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
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

  // Handle edit button click
  const handleEditClick = (court: Court) => {
    setEditingCourt(court);
    setIsEditModalOpen(true);
    setSelectedCluster(null); // Close popup when opening edit modal
  };

  // Handle save from edit modal
  const handleSaveCourt = async (updatedCourt: Court) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
      
      // Map frontend fields to backend fields
      const updateData: Record<string, any> = {
        name: updatedCourt.name,
        type: updatedCourt.type,
        surface: updatedCourt.surface,
        is_public: updatedCourt.is_public,
        school: updatedCourt.school
      };

      const clusterFields: Record<string, string | null> = {};
      // Track previous (current stored label) vs next (user-entered) cluster name to decide if we need a cluster-wide rename
      const nextClusterName = updatedCourt.cluster_group_name ?? null;
      
      // Get previous cluster name from editingCourt if it matches, otherwise look it up in courts array
      let previousClusterName: string | null = null;
      if (editingCourt && editingCourt.id === updatedCourt.id) {
        previousClusterName = editingCourt.cluster_group_name ?? null;
      } else {
        // Fallback: look up the current court in the courts array to get its previous cluster name
        const currentCourt = courts.find(c => c.id === updatedCourt.id);
        previousClusterName = currentCourt?.cluster_group_name ?? null;
      }

      // Only send cluster_fields if the cluster name actually changed
      if (previousClusterName !== nextClusterName) {
        clusterFields.cluster_group_name = nextClusterName;
      }

      // Only send cluster_fields when at least one shared field changes; keeps per-court edits scoped
      if (Object.keys(clusterFields).length > 0) {
        updateData.cluster_fields = clusterFields;
      }
      
      const response = await fetch(`${apiUrl}/api/courts/${updatedCourt.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData)
      });

      if (!response.ok) {
        throw new Error('Failed to update court');
      }

      // Parse server response to get the updated court data
      const result = await response.json();
      if (!result.success || !result.data) {
        throw new Error('Invalid response from server');
      }

      const serverUpdatedCourt = result.data;
      
      logEvent('court_updated', {
        courtId: serverUpdatedCourt.id,
        updatedData: serverUpdatedCourt
      });

      // Clear current viewport's cache and re-fetch to get fresh data
      // This ensures we see updated names (including cluster-wide changes)
      const { bbox } = calculateBoundingBox(viewport);
      const cacheKey = createCacheKey(bbox);
      
      // Remove current viewport's cache entry
      if (courtCache.current.has(cacheKey)) {
        courtCache.current.delete(cacheKey);
        // Remove from order tracking
        const orderIndex = cacheKeysOrder.current.indexOf(cacheKey);
        if (orderIndex > -1) {
          cacheKeysOrder.current.splice(orderIndex, 1);
        }
        // Remove courts belonging to this bbox from state
        const courtsToRemove = courtsByBbox.current[cacheKey] || [];
        const courtIdsToRemove = new Set(courtsToRemove.map((c: Court) => c.id));
        setCourts(prevCourts => prevCourts.filter(court => !courtIdsToRemove.has(court.id)));
        delete courtsByBbox.current[cacheKey];
      }
      
      // Re-fetch fresh data for the current viewport
      // Small delay to ensure state updates have propagated
      setTimeout(() => {
        fetchCourtsForArea();
      }, 100);
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      logError(err, { context: 'Failed to update court' });
      alert('Failed to update court. Please try again.');
    }
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
          onClick={fetchCourtsForArea}
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
        ref={mapRef}
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
        {mapLoaded && clusters && clusters.map((cluster, index) => {
          const isCluster = cluster.properties.cluster;
          const pointCount = cluster.properties.point_count || 1;
          const displayName = isCluster 
            ? `${pointCount} courts`
            : cluster.properties.name;
            
          const markerSize = isCluster ? 40 : 30;
          
          // Create a unique key using coordinates and index as fallback
          const uniqueKey = cluster.id || `cluster-${cluster.geometry.coordinates[0]}-${cluster.geometry.coordinates[1]}-${index}`;
          
          return (
            <Marker
              key={uniqueKey}
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
                {isCluster ? pointCount : getSportIcon(cluster.properties.type)}
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
                <p><span className="font-medium">Public:</span> {selectedCluster.properties.is_public === true ? 'Yes' : selectedCluster.properties.is_public === false ? 'No' : 'Unknown'}</p>
                <p><span className="font-medium">School:</span> {selectedCluster.properties.school ? 'Yes' : 'No'}</p>
              </div>
              
              <div className="flex justify-center">
                <button
                  onClick={() => {
                    const courtDetail = {
                      id: selectedCluster.properties.id || selectedCluster.id,
                      name: selectedCluster.properties.name || 'Unknown Court',
                      type: selectedCluster.properties.type || 'unknown',
                      lat: selectedCluster.geometry.coordinates[1],
                      lng: selectedCluster.geometry.coordinates[0],
                      surface: selectedCluster.properties.surface || 'Unknown',
                      is_public: selectedCluster.properties.is_public ?? null, // Preserve null for unknown access
                      school: selectedCluster.properties.school || false,
                      cluster_group_name: selectedCluster.properties.cluster_group_name || 'Unknown Group',
                      created_at: new Date().toISOString(),
                      updated_at: new Date().toISOString()
                    };
                    handleEditClick(courtDetail);
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors max-w-[calc(100%-1.5rem)]"
                >
                  Edit Court
                </button>
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

      {/* Edit Court Modal */}
      <EditCourtModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingCourt(null);
        }}
        court={editingCourt}
        onSave={handleSaveCourt}
      />
    </div>
  );
}


