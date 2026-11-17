"""Build the map files for the site from Eurostat GISCO data.

Usage:
    python tools/make_geo.py CNTR_RG_20M_2020_4326.geojson country_label_2020.geojson site/static/geo

Inputs (both from Eurostat GISCO, (c) EuroGeographics for the administrative boundaries):
    CNTR_RG_20M_2020_4326.geojson  country polygons, 1:20 million
        https://gisco-services.ec.europa.eu/distribution/v2/countries/
    country_label_2020.geojson     label points (copied from the old Drupal site)
Outputs:
    europe.json   polygons of the countries shown on the maps, keyed by ISO3 code
    labels.json   {ISO3: {"name": ..., "coord": [lon, lat]}} for labels and flow lines
"""
import json
import sys
from pathlib import Path

# The countries the old maps showed (GISCO country IDs: EL = Greece, UK = United Kingdom).
EUROPE = {"BE", "EL", "LT", "PT", "BG", "ES", "LU", "RO", "CZ", "FR", "HU", "SI", "DK", "HR",
          "MT", "SK", "DE", "IT", "NL", "FI", "EE", "CY", "AT", "SE", "IE", "LV", "PL", "IS",
          "NO", "LI", "CH", "UK", "FO", "BY", "UA", "MD", "TR", "BA", "RS", "ME", "XK", "MK",
          "AL", "RU"}


def rounded(coords, digits=2):
    if isinstance(coords[0], (int, float)):
        return [round(c, digits) for c in coords]
    return [rounded(c, digits) for c in coords]


def main(polygons: Path, labels: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    world = json.loads(polygons.read_text(encoding="utf8"))
    features = []
    for f in world["features"]:
        p = f["properties"]
        if p["CNTR_ID"] in EUROPE:
            code = p.get("ISO3_CODE") or p["CNTR_ID"]
            geometry = {"type": f["geometry"]["type"],
                        "coordinates": rounded(f["geometry"]["coordinates"])}
            features.append({"type": "Feature", "properties": {"name": code,
                             "label": p["NAME_ENGL"]}, "geometry": geometry})
    (out / "europe.json").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))

    points = {}
    for f in json.loads(labels.read_text(encoding="utf8"))["features"]:
        p = f["properties"]
        if p.get("ISO3_CODE"):
            points[p["ISO3_CODE"]] = {"name": p["NAME_ENGL"],
                                      "coord": rounded(f["geometry"]["coordinates"])}
    # The old site drew the "Rest of the World" in the Atlantic Ocean.
    points["ROW"] = {"name": "Rest of the World", "coord": [-25.0, 40.0]}
    (out / "labels.json").write_text(json.dumps(points, separators=(",", ":"), sort_keys=True))
    print(f"{len(features)} countries, {len(points)} label points")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
