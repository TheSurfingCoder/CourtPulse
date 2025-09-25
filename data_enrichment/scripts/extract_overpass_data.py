#!/usr/bin/env python3
"""
Extract court data from Overpass API for specific regions
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# Region configurations with bounding boxes
REGIONS = {
    'sf_bay': {
        'bbox': [37.7, -122.5, 37.8, -122.3],  # [south, west, north, east]
        'name': 'San Francisco Bay Area'
    },
    'nyc': {
        'bbox': [40.6, -74.1, 40.8, -73.9],
        'name': 'New York City'
    },
    'london': {
        'bbox': [51.4, -0.2, 51.6, 0.0],
        'name': 'London'
    }
}

def build_overpass_query(bbox):
    """Build Overpass API query for basketball courts in bounding box"""
    south, west, north, east = bbox
    
    query = f"""
    [out:json][timeout:300];
    (
      way["leisure"="pitch"]["sport"="basketball"]({south},{west},{north},{east});
      way["leisure"="sports_centre"]["sport"="basketball"]({south},{west},{north},{east});
      way["amenity"="sports_centre"]["sport"="basketball"]({south},{west},{north},{east});
      node["leisure"="pitch"]["sport"="basketball"]({south},{west},{north},{east});
      node["leisure"="sports_centre"]["sport"="basketball"]({south},{west},{north},{east});
      node["amenity"="sports_centre"]["sport"="basketball"]({south},{west},{north},{east});
    );
    out geom;
    """
    return query

def extract_data_from_overpass(region: str, output_file: str):
    """Extract data from Overpass API"""
    if region not in REGIONS:
        print(f"❌ Unknown region: {region}")
        print(f"Available regions: {list(REGIONS.keys())}")
        sys.exit(1)
    
    region_config = REGIONS[region]
    bbox = region_config['bbox']
    name = region_config['name']
    
    print(f"🌍 Extracting data for {name}")
    print(f"   Bounding box: {bbox}")
    
    # Build query
    query = build_overpass_query(bbox)
    
    # Overpass API endpoint
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    try:
        print("🔄 Querying Overpass API...")
        response = requests.post(overpass_url, data={'data': query}, timeout=300)
        response.raise_for_status()
        
        data = response.json()
        features = data.get('elements', [])
        
        print(f"✅ Retrieved {len(features)} features from Overpass API")
        
        # Convert to GeoJSON format
        geojson = {
            "type": "FeatureCollection",
            "generator": "overpass-turbo",
            "copyright": "The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.",
            "timestamp": datetime.now().isoformat() + "Z",
            "features": []
        }
        
        for element in features:
            feature = convert_element_to_geojson(element)
            if feature:
                geojson['features'].append(feature)
        
        # Save to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"✅ Data saved to: {output_file}")
        print(f"   Features: {len(geojson['features'])}")
        
        return len(geojson['features'])
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Overpass API request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Data extraction failed: {e}")
        sys.exit(1)

def convert_element_to_geojson(element):
    """Convert Overpass element to GeoJSON feature"""
    try:
        # Extract properties
        tags = element.get('tags', {})
        properties = {
            'osm_id': f"{element['type']}/{element['id']}",
            '@id': f"{element['type']}/{element['id']}",
            'sport': tags.get('sport', 'basketball'),
            'leisure': tags.get('leisure', 'pitch'),
            'covered': tags.get('covered', 'no'),
            'fee': tags.get('fee', 'no'),
            'indoor': tags.get('indoor', 'no'),
            'hoops': tags.get('hoops', '1')
        }
        
        # Extract geometry
        if element['type'] == 'way' and 'geometry' in element:
            # Way with geometry
            coordinates = element['geometry']
            if len(coordinates) >= 3:  # Valid polygon
                geometry = {
                    'type': 'Polygon',
                    'coordinates': [coordinates]
                }
            else:
                return None  # Skip invalid ways
        elif element['type'] == 'node':
            # Node
            lat = element.get('lat')
            lon = element.get('lon')
            if lat and lon:
                geometry = {
                    'type': 'Point',
                    'coordinates': [lon, lat]
                }
            else:
                return None  # Skip nodes without coordinates
        else:
            return None  # Skip elements without geometry
        
        return {
            'type': 'Feature',
            'properties': properties,
            'geometry': geometry,
            'id': f"{element['type']}/{element['id']}"
        }
        
    except Exception as e:
        print(f"⚠️  Skipping element due to conversion error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract court data from Overpass API')
    parser.add_argument('--region', required=True, help='Region to extract (sf_bay, nyc, london)')
    parser.add_argument('--output-file', required=True, help='Output GeoJSON file path')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Overpass data extraction")
    print(f"   Region: {args.region}")
    print(f"   Output: {args.output_file}")
    
    feature_count = extract_data_from_overpass(args.region, args.output_file)
    
    print(f"✅ Extraction completed successfully!")
    print(f"   Features extracted: {feature_count}")

if __name__ == "__main__":
    main()

