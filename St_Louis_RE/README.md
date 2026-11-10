# St. Louis Parcel Atlas

An interactive map of parcels in the thesis exports with a recorded distance of at most three miles from the Rams' former stadium. Click a parcel or search for its full HANDLE.

## Preview and publish

Run `python3 -m http.server 8000` from this folder and visit `http://localhost:8000`. The map uses Leaflet and OpenStreetMap tiles over the internet.

For GitHub Pages, put `index.html`, `map.js`, `parcels.geojson`, and the `css/` folder together in your publishing folder. If your portfolio already has a homepage, keep these files in a subfolder and link to its `index.html` from your portfolio.

## Rebuild the data

Install `pyproj` and `shapely` in your Python environment, then run `python3 build_data.py "/path/to/data_export"`. The script opens both GeoPackages read-only and writes only the map fields and simplified parcel polygons to `parcels.geojson`.

The map summarizes available records by HANDLE for 2010–2015 and 2016–2019. Sales use the median of the supplied priced transaction rows, which can include multiple transactions per period. The geometry is the most recent available within-radius assessment geometry, falling back to the most recent within-radius sale geometry. It is simplified at one foot in the source projection before conversion to WGS 84.
