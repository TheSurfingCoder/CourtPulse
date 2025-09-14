# CourtPulse Data Enrichment Pipeline

A production-ready Python pipeline for enriching OpenStreetMap court data with reverse geocoding and storing it in a Postgres database with PostGIS support.

## Features

- **GeoJSON Processing**: Parse OpenStreetMap court data from GeoJSON files
- **Geometry Processing**: Calculate centroids using Shapely for accurate court locations
- **Reverse Geocoding**: Pluggable geocoding providers (Nominatim, Google Places, MapTiler)
- **Database Storage**: Store enriched data in Postgres with PostGIS for spatial queries
- **Structured Logging**: JSON-formatted logging for monitoring and debugging
- **Error Handling**: Robust error handling with detailed logging
- **Rate Limiting**: Built-in rate limiting for API providers

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Ensure Postgres with PostGIS is running and accessible.

## Quick Start

### Basic Usage

```python
from data_enrichment import CourtDataEnricher, DatabaseManager, NominatimProvider

# Initialize components
db_manager = DatabaseManager("postgresql://user:pass@localhost/courtpulse")
geocoding_provider = NominatimProvider()
enricher = CourtDataEnricher(db_manager, geocoding_provider)

# Create database table
db_manager.create_table_if_not_exists()

# Load and process courts
courts = enricher.load_geojson("courts.geojson")
for court in courts[:5]:  # Process first 5 courts
    enriched_court = enricher.enrich_court(court)
    db_manager.insert_court(enriched_court)
```

### Using Different Geocoding Providers

#### Nominatim (Free)
```python
from data_enrichment import NominatimProvider

provider = NominatimProvider(
    base_url="https://nominatim.openstreetmap.org",
    user_agent="YourApp/1.0",
    delay=1.0  # Rate limiting delay
)
```

#### Google Places API
```python
from data_enrichment import GooglePlacesProvider

provider = GooglePlacesProvider(
    api_key="your_google_places_api_key",
    delay=0.1
)
```

## Database Schema

The pipeline creates a `courts` table with the following structure:

```sql
CREATE TABLE courts (
    id SERIAL PRIMARY KEY,
    osm_id VARCHAR(255) UNIQUE NOT NULL,
    geom GEOMETRY(POINT, 4326),
    sport VARCHAR(100),
    hoops VARCHAR(10),
    fallback_name VARCHAR(255),
    google_place_id VARCHAR(255),
    enriched_name VARCHAR(255),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
- `idx_courts_osm_id`: On osm_id for fast lookups
- `idx_courts_geom`: GIST index on geometry for spatial queries
- `idx_courts_sport`: On sport for filtering

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `DB_NAME` | Database name | courtpulse |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | (empty) |
| `GOOGLE_PLACES_API_KEY` | Google Places API key | (empty) |
| `MAPTILER_API_KEY` | MapTiler API key | (empty) |
| `NOMINATIM_BASE_URL` | Nominatim base URL | https://nominatim.openstreetmap.org |
| `NOMINATIM_USER_AGENT` | User agent for Nominatim | CourtPulse/1.0 |
| `NOMINATIM_DELAY` | Rate limiting delay | 1.0 |

## API Providers

### Nominatim
- **Cost**: Free
- **Rate Limit**: 1 request/second (configurable)
- **Coverage**: Global
- **Accuracy**: Good for most locations

### Google Places
- **Cost**: Paid (per request)
- **Rate Limit**: Configurable
- **Coverage**: Excellent
- **Accuracy**: Very high

### MapTiler
- **Cost**: Paid (subscription-based)
- **Rate Limit**: Based on subscription
- **Coverage**: Global
- **Accuracy**: High

## Logging

The pipeline uses structured JSON logging for all operations:

```json
{
  "event": "court_enriched",
  "osm_id": "way/28283137",
  "coordinates": {"lat": 37.7500036, "lon": -122.4063442},
  "has_address": true,
  "has_place_id": true
}
```

### Key Events Logged
- Pipeline startup/shutdown
- GeoJSON loading
- Court enrichment
- Database operations
- API provider errors
- Rate limiting

## Error Handling

The pipeline includes comprehensive error handling:

- **Network Errors**: Retry logic for API calls
- **Database Errors**: Transaction rollback and detailed logging
- **Geometry Errors**: Skip invalid geometries with logging
- **Rate Limiting**: Automatic delays between API calls

## Performance Considerations

### Rate Limiting
- Nominatim: 1 request/second (configurable)
- Google Places: Configurable based on quota
- MapTiler: Based on subscription limits

### Database Performance
- Spatial indexes for fast geometry queries
- Unique constraints to prevent duplicates
- Batch processing support

### Memory Usage
- Processes one court at a time to minimize memory usage
- Supports large GeoJSON files through streaming

## Examples

See `example_usage.py` for comprehensive examples including:

- Basic pipeline usage
- Different geocoding providers
- Batch processing
- Error handling

## Running Examples

```bash
# Run all examples
python example_usage.py

# Run main pipeline with sample data
python data_enrichment.py
```

## Development

### Adding New Geocoding Providers

1. Create a new class inheriting from `GeocodingProvider`
2. Implement the `reverse_geocode(lat, lon)` method
3. Return a tuple of `(address, place_id)`

Example:
```python
class CustomProvider(GeocodingProvider):
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        # Your implementation
        return address, place_id
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Update documentation
5. Submit a pull request

## License

This project is part of CourtPulse and follows the same license terms.

