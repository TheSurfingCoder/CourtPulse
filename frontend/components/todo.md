I think it would make more sense to cache the individual mappoints versus caching the clusters


[4 tools called]

**The cluster cache data structure looks like this:**

```typescript
const clusterCache = useRef<Record<string, any[]>>({});
```

**Cache Key Structure:**
```typescript
// Example cache key: "11:-122.5,37.7,-122.4,37.8"
const cacheKey = `${roundedZoom}:${roundedBbox.join(',')}`;
```

**Cache Value Structure:**
```typescript
// Each cached value is an array of GeoJSON cluster features:
[
  {
    id: "cluster-1",
    type: "Feature",
    geometry: { type: "Point", coordinates: [-122.4194, 37.7749] },
    properties: {
      cluster: true,
      point_count: 5,
      point_count_abbreviated: "5"
    }
  },
  {
    id: "point-123",
    type: "Feature", 
    geometry: { type: "Point", coordinates: [-122.4200, 37.7750] },
    properties: {
      cluster: false,
      id: 123,
      name: "Golden Gate Park Court",
      type: "basketball",
      surface: "concrete",
      is_public: true
    }
  }
  // ... more clusters/points
]
```

**Example cache object:**
```typescript
{
  "11:-122.5,37.7,-122.4,37.8": [cluster1, cluster2, point1, ...],
  "11.5:-122.6,37.6,-122.3,37.9": [cluster3, point2, ...],
  "12:-122.45,37.75,-122.42,37.78": [point3, point4, ...]
}
```

The cache stores clustering results keyed by viewport position and zoom level to avoid recalculating clusters for the same map areas.