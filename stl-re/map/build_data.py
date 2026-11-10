"""Build the public parcel layer from the two thesis GeoPackages."""
import argparse
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from statistics import median

from pyproj import CRS, Transformer
from shapely import wkb
from shapely.geometry import mapping
from shapely.ops import transform


def connect(path):
    return closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True))


def geometry(blob, project):
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    start = 8 + envelope_sizes[(blob[3] >> 1) & 7]
    shape = wkb.loads(blob[start:]).simplify(1, preserve_topology=True)
    return mapping(transform(project, shape))


def rounded(value):
    if isinstance(value, (list, tuple)):
        return [rounded(part) for part in value]
    return round(value, 6)


def build(directory):
    features = {}
    with connect(directory / "assessment_panel.gpkg") as db:
        definition, = db.execute(
            "SELECT definition FROM gpkg_spatial_ref_sys WHERE srs_id=102696"
        ).fetchone()
        project = Transformer.from_crs(CRS.from_wkt(definition), 4326, always_xy=True).transform
        for handle, distance, pre, post, npre, npost, blob in db.execute("""
            WITH eligible AS (
                SELECT HANDLE, Year, TotalValue, dist_stadium_mi, geom, ROW_NUMBER() OVER (PARTITION BY HANDLE ORDER BY Year DESC, fid DESC) AS recency
                FROM parcel_panel WHERE dist_stadium_mi BETWEEN 0 AND 3
                    AND Year BETWEEN 2010 AND 2019 AND HANDLE IS NOT NULL
            ), averages AS (
                SELECT HANDLE,
                    AVG(CASE WHEN Year <= 2015 THEN TotalValue END) AS pre,
                    AVG(CASE WHEN Year >= 2016 THEN TotalValue END) AS post,
                    COUNT(CASE WHEN Year <= 2015 THEN TotalValue END) AS npre,
                    COUNT(CASE WHEN Year >= 2016 THEN TotalValue END) AS npost
                FROM eligible GROUP BY HANDLE
            )
            SELECT HANDLE, dist_stadium_mi, pre, post, npre, npost, geom
            FROM eligible JOIN averages USING (HANDLE) WHERE recency = 1
        """):
            change = 100 * (post - pre) / pre if pre and post is not None else None
            features[handle] = (blob, dict(
                HANDLE=handle, miles=distance, assessmentPre=pre, assessmentPost=post,
                yearsPre=npre, yearsPost=npost, change=change
            ))

    prices = defaultdict(lambda: ([], []))
    with connect(directory / "sale_transactions.gpkg") as db:
        for handle, year, price, distance, fid in db.execute("""
            SELECT HANDLE, SaleYear, SalePrice, dist_stadium_mi, fid
            FROM parcel_panel WHERE dist_stadium_mi BETWEEN 0 AND 3
                AND SaleYear BETWEEN 2010 AND 2019 AND HANDLE IS NOT NULL
            ORDER BY SaleYear DESC, SaleDate DESC, fid DESC
        """):
            if handle not in features:
                blob, = db.execute("SELECT geom FROM parcel_panel WHERE fid=?", (fid,)).fetchone()
                features[handle] = (blob, dict(HANDLE=handle, miles=distance))
            if price is not None:
                prices[handle][year >= 2016].append(price)

    parcels = []
    for handle, (blob, properties) in sorted(features.items()):
        pre, post = prices[handle]
        properties.update(salePre=median(pre) if pre else None,
                          salePost=median(post) if post else None,
                          salesPre=len(pre), salesPost=len(post))
        shape = geometry(blob, project)
        shape["coordinates"] = rounded(shape["coordinates"])
        parcels.append(dict(type="Feature", geometry=shape, properties=properties))
    return dict(type="FeatureCollection", features=parcels)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory containing both GeoPackages")
    data = build(parser.parse_args().directory)
    output = Path(__file__).with_name("parcels.geojson")
    output.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    print(f"{len(data['features']):,} parcels written to {output.name}")
