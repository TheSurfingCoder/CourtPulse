#!/usr/bin/env python3
"""
Coordinate analysis tool to understand why we're getting Jackson Playground Park
instead of James Rolph Basketball Court
"""

import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()


def analyze_coordinate_issue(lat: float, lon: float):
    """Analyze why we're getting Jackson Playground Park instead of James Rolph"""
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ No Google API key found")
        return
    
    print(f"🔍 Analyzing coordinate issue for {lat}, {lon}")
    print(f"Expected: James Rolph Basketball Court")
    print(f"Getting: Jackson Playground Park")
    
    # Test different search strategies
    strategies = [
        {
            "name": "Direct Name Search",
            "method": "text_search",
            "query": "James Rolph Basketball Court",
            "radius": 500
        },
        {
            "name": "Basketball Court Search (50m)",
            "method": "nearby_search",
            "keyword": "basketball court",
            "radius": 50
        },
        {
            "name": "Basketball Court Search (100m)",
            "method": "nearby_search", 
            "keyword": "basketball court",
            "radius": 100
        },
        {
            "name": "Basketball Court Search (200m)",
            "method": "nearby_search",
            "keyword": "basketball court", 
            "radius": 200
        },
        {
            "name": "Sports Search (100m)",
            "method": "nearby_search",
            "keyword": "sports",
            "radius": 100
        },
        {
            "name": "Park Search (100m)",
            "method": "nearby_search",
            "keyword": "park",
            "radius": 100
        },
        {
            "name": "Jackson Playground Search",
            "method": "text_search",
            "query": "Jackson Playground",
            "radius": 500
        }
    ]
    
    results = {}
    
    for strategy in strategies:
        print(f"\n--- {strategy['name']} ---")
        
        try:
            if strategy['method'] == 'nearby_search':
                params = {
                    'location': f"{lat},{lon}",
                    'radius': strategy['radius'],
                    'type': 'establishment',
                    'keyword': strategy['keyword'],
                    'key': api_key
                }
                
                response = requests.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=params,
                    timeout=10
                )
                
            elif strategy['method'] == 'text_search':
                params = {
                    'query': strategy['query'],
                    'location': f"{lat},{lon}",
                    'radius': strategy['radius'],
                    'key': api_key
                }
                
                response = requests.get(
                    "https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params=params,
                    timeout=10
                )
            
            response.raise_for_status()
            data = response.json()
            
            print(f"Status: {data.get('status')}")
            print(f"Results: {len(data.get('results', []))}")
            
            if data.get('results'):
                print("Top results:")
                for i, result in enumerate(data['results'][:3]):
                    name = result.get('name', 'No name')
                    place_id = result.get('place_id', 'No ID')
                    types = result.get('types', [])
                    vicinity = result.get('vicinity', 'No vicinity')
                    
                    print(f"  {i+1}. {name}")
                    print(f"     Place ID: {place_id}")
                    print(f"     Types: {types}")
                    print(f"     Vicinity: {vicinity}")
                    
                    # Check if this is James Rolph
                    if 'james rolph' in name.lower() or 'james rolph' in vicinity.lower():
                        print(f"     🎉 FOUND JAMES ROLPH!")
                    
                    # Check if this is Jackson Playground
                    if 'jackson playground' in name.lower() or 'jackson playground' in vicinity.lower():
                        print(f"     📍 This is Jackson Playground")
            
            results[strategy['name']] = data.get('results', [])
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results[strategy['name']] = []
        
        time.sleep(0.5)  # Rate limiting
    
    # Analysis
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")
    
    # Check if James Rolph was found in any search
    james_rolph_found = False
    for strategy_name, strategy_results in results.items():
        for result in strategy_results:
            name = result.get('name', '').lower()
            vicinity = result.get('vicinity', '').lower()
            if 'james rolph' in name or 'james rolph' in vicinity:
                print(f"✅ James Rolph found in: {strategy_name}")
                print(f"   Name: {result.get('name')}")
                print(f"   Vicinity: {result.get('vicinity')}")
                james_rolph_found = True
                break
        if james_rolph_found:
            break
    
    if not james_rolph_found:
        print("❌ James Rolph Basketball Court not found in any search")
        print("   Possible reasons:")
        print("   1. The court doesn't exist in Google's database")
        print("   2. The coordinates are not accurate")
        print("   3. The court is part of Jackson Playground Park")
        print("   4. The court has a different name in Google's database")
    
    # Check Jackson Playground distance
    jackson_found = False
    for strategy_name, strategy_results in results.items():
        for result in strategy_results:
            name = result.get('name', '').lower()
            if 'jackson playground' in name:
                print(f"📍 Jackson Playground found in: {strategy_name}")
                print(f"   Name: {result.get('name')}")
                print(f"   Vicinity: {result.get('vicinity')}")
                jackson_found = True
                break
        if jackson_found:
            break
    
    return results


def main():
    """Test with the problem coordinates"""
    
    print("🏀 Coordinate Analysis Tool")
    print("=" * 60)
    
    # Test coordinates
    lat, lon = 37.750086, -122.406482
    
    results = analyze_coordinate_issue(lat, lon)
    
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    print("1. If James Rolph was found:")
    print("   - Use that result as the court name")
    print("   - Update the search logic to prioritize it")
    
    print("\n2. If James Rolph was not found:")
    print("   - The court might be part of Jackson Playground Park")
    print("   - Use 'Jackson Playground Park - Basketball Court' as the name")
    print("   - Or use the smart fallback: 'Outdoor Basketball Court (2 hoops) - Area'")
    
    print("\n3. Coordinate accuracy:")
    print("   - The coordinates might be slightly off")
    print("   - Try adjusting the search radius")
    print("   - Consider using multiple coordinate points from the polygon")


if __name__ == "__main__":
    main()
