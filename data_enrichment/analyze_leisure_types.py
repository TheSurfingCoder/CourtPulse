"""
Quick analysis script to see which leisure types are finding successful names
"""

import json
import logging
from test_photon_geocoding import PhotonGeocodingProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_leisure_types():
    """Analyze which leisure types are finding successful names"""
    
    # Initialize the geocoding provider
    provider = PhotonGeocodingProvider()
    
    # Test coordinates from our previous successful test
    test_coordinates = [
        (37.75006984, -122.40645443999999),  # James Rolph Jr. Playground
        (37.7334692, -122.3762353),          # India Basin Shoreline Park
        (37.73874528, -122.48345343999999),  # Parkside Square
        (37.736954780000005, -122.42037580000002),  # Holly Park
        (37.733429060000006, -122.42112293999999),  # Saint Mary's Playground
    ]
    
    leisure_types = [
        {'osm_tag': 'leisure:pitch', 'q': 'pitch'},
        {'osm_tag': 'leisure:park', 'q': 'park'},
        {'osm_tag': 'leisure:playground', 'q': 'playground'},
        {'osm_tag': 'leisure:sports_centre', 'q': 'sports'},
        {'osm_tag': 'leisure:sports_hall', 'q': 'sports hall'}
    ]
    
    results = {
        'leisure:pitch': {'successful': 0, 'total': 0, 'names': []},
        'leisure:park': {'successful': 0, 'total': 0, 'names': []},
        'leisure:playground': {'successful': 0, 'total': 0, 'names': []},
        'leisure:sports_centre': {'successful': 0, 'total': 0, 'names': []},
        'leisure:sports_hall': {'successful': 0, 'total': 0, 'names': []}
    }
    
    print("🔍 Analyzing Leisure Type Success Rates...")
    print("=" * 60)
    
    for i, (lat, lon) in enumerate(test_coordinates, 1):
        print(f"\n📍 Test {i}: ({lat:.6f}, {lon:.6f})")
        
        for leisure_type in leisure_types:
            try:
                name, data = provider._perform_single_search(lat, lon, leisure_type)
                results[leisure_type['osm_tag']]['total'] += 1
                
                if name and provider._is_high_quality_name(name):
                    if provider._is_nearby_result(data, lat, lon):
                        results[leisure_type['osm_tag']]['successful'] += 1
                        results[leisure_type['osm_tag']]['names'].append(name)
                        print(f"  ✅ {leisure_type['osm_tag']}: {name}")
                    else:
                        print(f"  ❌ {leisure_type['osm_tag']}: {name} (too far)")
                else:
                    print(f"  ❌ {leisure_type['osm_tag']}: No result")
                    
            except Exception as e:
                print(f"  ❌ {leisure_type['osm_tag']}: Error - {e}")
                results[leisure_type['osm_tag']]['total'] += 1
    
    print("\n" + "=" * 60)
    print("📊 LEISURE TYPE SUCCESS RATES")
    print("=" * 60)
    
    for leisure_type, stats in results.items():
        if stats['total'] > 0:
            success_rate = (stats['successful'] / stats['total']) * 100
            print(f"{leisure_type:20} | {stats['successful']:2}/{stats['total']:2} | {success_rate:5.1f}% | {len(set(stats['names'])):2} unique names")
            if stats['names']:
                unique_names = list(set(stats['names']))
                print(f"{'':20} | Names: {', '.join(unique_names[:3])}{'...' if len(unique_names) > 3 else ''}")
        else:
            print(f"{leisure_type:20} | No tests")
    
    print("\n💡 RECOMMENDATIONS:")
    
    # Sort by success rate
    sorted_types = sorted(results.items(), key=lambda x: x[1]['successful'] / max(x[1]['total'], 1), reverse=True)
    
    print("1. Most successful leisure types:")
    for leisure_type, stats in sorted_types[:3]:
        if stats['total'] > 0:
            success_rate = (stats['successful'] / stats['total']) * 100
            print(f"   - {leisure_type}: {success_rate:.1f}% success rate")
    
    print("\n2. Consider removing low-performing types:")
    for leisure_type, stats in sorted_types[3:]:
        if stats['total'] > 0:
            success_rate = (stats['successful'] / stats['total']) * 100
            if success_rate < 20:
                print(f"   - {leisure_type}: {success_rate:.1f}% success rate (consider removing)")

if __name__ == "__main__":
    analyze_leisure_types()


