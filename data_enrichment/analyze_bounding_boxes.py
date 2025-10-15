#!/usr/bin/env python3
"""
Diagnostic tool to analyze why bounding box matches are being missed.
Shows distance analysis, extent data availability, and proximity patterns.
"""

import json
import sys
import os
from typing import Dict, List, Any, Tuple
import argparse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_photon_geocoding import PhotonGeocodingProvider

def analyze_court_bounding_boxes(lat: float, lon: float, court_name: str = "Unknown Court"):
    """Analyze bounding box matches for a specific court"""
    
    print("="*80)
    print(f"🔍 BOUNDING BOX ANALYSIS: {court_name}")
    print("="*80)
    print(f"📍 Coordinates: {lat}, {lon}")
    print("="*80)
    
    provider = PhotonGeocodingProvider()
    
    # Test each search type individually
    search_types = [
        {
            'name': 'Parks/Playgrounds',
            'method': lambda: provider._try_search_with_bounding_box(lat, lon, 'park', [
                {'osm_tag': 'leisure:park', 'q': 'park'},
                {'osm_tag': 'leisure:playground', 'q': 'playground'}
            ], 1000),
            'radius_km': 0.305  # 1000ft
        },
        {
            'name': 'Schools/Universities', 
            'method': lambda: provider._try_school_search_with_bounding_box(lat, lon),
            'radius_km': 0.152  # 500ft
        },
        {
            'name': 'Community Centers',
            'method': lambda: provider._try_community_centre_search_with_bounding_box(lat, lon),
            'radius_km': 0.305  # 1000ft
        },
        {
            'name': 'Sports Clubs',
            'method': lambda: provider._try_sports_club_search_with_bounding_box(lat, lon),
            'radius_km': 0.305  # 1000ft
        },
        {
            'name': 'Places of Worship',
            'method': lambda: provider._try_place_of_worship_search_with_bounding_box(lat, lon),
            'radius_km': 0.152  # 500ft
        },
        {
            'name': 'Sports Centers',
            'method': lambda: provider._try_sports_centre_search_with_bounding_box(lat, lon),
            'radius_km': 0.305  # 1000ft
        }
    ]
    
    total_results = 0
    total_with_extent = 0
    total_inside_bounding_box = 0
    proximity_analysis = []
    
    for search_type in search_types:
        print(f"\n🔍 {search_type['name']} Analysis:")
        print("-" * 50)
        
        try:
            results = search_type['method']()
            
            if not results:
                print("   ❌ No results found")
                continue
            
            print(f"   📊 Found {len(results)} results")
            
            search_stats = {
                'name': search_type['name'],
                'total_results': len(results),
                'with_extent': 0,
                'inside_bounding_box': 0,
                'closest_distance': float('inf'),
                'closest_name': None,
                'extent_distances': []
            }
            
            for i, result in enumerate(results):
                name = result['name']
                distance = result['distance']
                has_extent = 'extent' in result.get('data', {}).get('properties', {})
                is_inside = result.get('is_inside_facility', False)
                
                # Track closest result
                if distance < search_stats['closest_distance']:
                    search_stats['closest_distance'] = distance
                    search_stats['closest_name'] = name
                
                if has_extent:
                    search_stats['with_extent'] += 1
                    search_stats['extent_distances'].append(distance)
                    
                    if is_inside:
                        search_stats['inside_bounding_box'] += 1
                        print(f"   ✅ {name} - INSIDE bounding box ({distance:.3f}km)")
                    else:
                        print(f"   📏 {name} - outside bounding box ({distance:.3f}km)")
                else:
                    print(f"   ❌ {name} - no extent data ({distance:.3f}km)")
            
            # Summary for this search type
            print(f"   📈 Summary:")
            print(f"      • Total results: {search_stats['total_results']}")
            print(f"      • With extent data: {search_stats['with_extent']}")
            print(f"      • Inside bounding box: {search_stats['inside_bounding_box']}")
            print(f"      • Closest facility: {search_stats['closest_name']} ({search_stats['closest_distance']:.3f}km)")
            
            # Add to overall stats
            total_results += search_stats['total_results']
            total_with_extent += search_stats['with_extent']
            total_inside_bounding_box += search_stats['inside_bounding_box']
            
            proximity_analysis.append(search_stats)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Overall analysis
    print("\n" + "="*80)
    print("📊 OVERALL ANALYSIS:")
    print("="*80)
    print(f"Total results found: {total_results}")
    print(f"Results with extent data: {total_with_extent} ({total_with_extent/total_results*100:.1f}%)")
    print(f"Results inside bounding boxes: {total_inside_bounding_box} ({total_inside_bounding_box/total_results*100:.1f}%)")
    
    # Proximity analysis
    print(f"\n🎯 PROXIMITY ANALYSIS:")
    print("-" * 50)
    
    for search_stats in proximity_analysis:
        if search_stats['total_results'] > 0:
            closest_km = search_stats['closest_distance']
            closest_ft = closest_km * 3281
            print(f"{search_stats['name']:20} | Closest: {closest_ft:6.0f}ft ({closest_km:.3f}km)")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 50)
    
    if total_inside_bounding_box == 0:
        print("❌ No bounding box matches found")
        print("   Possible reasons:")
        print("   1. Court is not physically inside any facility")
        print("   2. Facilities don't have extent data in Photon API")
        print("   3. Extent data is inaccurate or incomplete")
        print("   4. Court is adjacent to but not inside facilities")
        
        # Find closest facilities
        closest_facilities = []
        for search_stats in proximity_analysis:
            if search_stats['closest_distance'] < float('inf'):
                closest_facilities.append((search_stats['closest_distance'], search_stats['closest_name'], search_stats['name']))
        
        closest_facilities.sort()
        
        if closest_facilities:
            print(f"\n   Closest facilities:")
            for distance, name, search_type in closest_facilities[:3]:
                distance_ft = distance * 3281
                print(f"   • {name} ({search_type}) - {distance_ft:.0f}ft away")
    else:
        print(f"✅ Found {total_inside_bounding_box} bounding box matches!")
    
    return {
        'total_results': total_results,
        'with_extent': total_with_extent,
        'inside_bounding_box': total_inside_bounding_box,
        'proximity_analysis': proximity_analysis
    }

def test_multiple_courts(way_ids: List[str]):
    """Test multiple courts and provide aggregate analysis"""
    
    print("="*80)
    print("🔍 MULTI-COURT BOUNDING BOX ANALYSIS")
    print("="*80)
    
    # Load the way data
    with open('export.geojson', 'r') as f:
        geojson_data = json.load(f)
    
    # Find ways
    ways = {}
    for feature in geojson_data.get('features', []):
        properties = feature.get('properties', {})
        osm_id = properties.get('osm_id')
        if osm_id in way_ids:
            ways[osm_id] = feature
    
    if not ways:
        print("❌ No ways found in export.geojson")
        return
    
    # Analyze each court
    all_results = []
    
    for way_id in way_ids:
        if way_id not in ways:
            print(f"❌ Way {way_id} not found")
            continue
        
        feature = ways[way_id]
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        
        # Extract coordinates
        if geometry.get('type') == 'Polygon':
            coords = geometry.get('coordinates', [[]])[0]
            if coords:
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                lat = sum(lats) / len(lats)
                lon = sum(lons) / len(lons)
                
                sport = properties.get('sport', 'unknown')
                hoops = properties.get('hoops', 'unknown')
                court_name = f"{way_id} ({sport}, {hoops} hoops)"
                
                print(f"\n{'='*20} {court_name} {'='*20}")
                result = analyze_court_bounding_boxes(lat, lon, court_name)
                all_results.append(result)
    
    # Aggregate analysis
    if all_results:
        print("\n" + "="*80)
        print("📊 AGGREGATE ANALYSIS:")
        print("="*80)
        
        total_results = sum(r['total_results'] for r in all_results)
        total_with_extent = sum(r['with_extent'] for r in all_results)
        total_inside = sum(r['inside_bounding_box'] for r in all_results)
        
        print(f"Courts analyzed: {len(all_results)}")
        print(f"Total facility results: {total_results}")
        print(f"Results with extent data: {total_with_extent} ({total_with_extent/total_results*100:.1f}%)")
        print(f"Bounding box matches: {total_inside} ({total_inside/total_results*100:.1f}%)")
        
        # Find patterns
        courts_with_matches = sum(1 for r in all_results if r['inside_bounding_box'] > 0)
        print(f"Courts with at least 1 bounding box match: {courts_with_matches}/{len(all_results)} ({courts_with_matches/len(all_results)*100:.1f}%)")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Analyze bounding box matches for courts')
    parser.add_argument('--way', type=str, help='Test a single way (e.g., "way/24307674")')
    parser.add_argument('--ways', nargs='+', help='Test multiple ways (e.g., "way/24307674" "way/28283137")')
    parser.add_argument('--lat', type=float, help='Test specific coordinates (requires --lon)')
    parser.add_argument('--lon', type=float, help='Test specific coordinates (requires --lat)')
    
    args = parser.parse_args()
    
    if args.way:
        # Load way data
        with open('export.geojson', 'r') as f:
            geojson_data = json.load(f)
        
        # Find the way
        target_way = None
        for feature in geojson_data.get('features', []):
            properties = feature.get('properties', {})
            if properties.get('osm_id') == args.way:
                target_way = feature
                break
        
        if not target_way:
            print(f"❌ Way {args.way} not found in export.geojson")
            return
        
        # Extract coordinates
        geometry = target_way.get('geometry', {})
        if geometry.get('type') == 'Polygon':
            coords = geometry.get('coordinates', [[]])[0]
            if coords:
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                lat = sum(lats) / len(lats)
                lon = sum(lons) / len(lons)
                
                properties = target_way.get('properties', {})
                sport = properties.get('sport', 'unknown')
                hoops = properties.get('hoops', 'unknown')
                court_name = f"{args.way} ({sport}, {hoops} hoops)"
                
                analyze_court_bounding_boxes(lat, lon, court_name)
            else:
                print("❌ No coordinates found")
        else:
            print(f"❌ Unsupported geometry type: {geometry.get('type')}")
    
    elif args.ways:
        test_multiple_courts(args.ways)
    
    elif args.lat and args.lon:
        analyze_court_bounding_boxes(args.lat, args.lon, f"Custom location ({args.lat}, {args.lon})")
    
    else:
        print("❌ Please specify --way, --ways, or --lat/--lon")
        parser.print_help()

if __name__ == "__main__":
    main()
