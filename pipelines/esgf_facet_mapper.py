from typing import List, Optional

from pydantic import BaseModel

# --- Canonical ESGF facet mappings ---
VARIABLE_MAP = {
    "tas": [
        "tas",
        "surface air temperature",
        "air surface temperature",
        "near-surface air temperature",
    ],
    "ta": ["ta", "air_temperature", "air temperature", "air temp"],
    "tasmax": [
        "tasmax",
        "maximum daily air temperature",
        "daily max temp",
        "maximum air temperature",
    ],
    "tasmin": [
        "tasmin",
        "minimum daily air temperature",
        "daily min temp",
        "minimum air temperature",
    ],
    "pr": ["pr", "precipitation", "precipitation flux", "rainfall"],
    "prc": ["prc", "convective precipitation"],
    "psl": ["psl", "sea level pressure", "surface pressure"],
    "ua": ["ua", "zonal wind", "u wind component"],
    "va": ["va", "meridional wind", "v wind component"],
    "es": ["es", "bare soil evaporation", "soil evaporation"],
    "mrso": ["mrso", "total soil moisture content", "soil moisture"],
    "wa": ["wa", "upward air velocity", "air velocity"],
    "gpp": [
        "gpp",
        "gross primary production",
        "gross primary productivity",
        "photosynthesis",
    ],
    "zg": ["zg", "geopotential height"],
    "rsds": [
        "rsds",
        "surface downwelling shortwave radiation",
        "downward shortwave radiation",
    ],
    "hus": ["hus", "specific humidity", "humidity"],
    "sfcWind": [
        "sfcWind",
        "surface wind speed",
        "surface wind",
        "wind speed at surface",
        "daily mean near-surface wind speed",
        "near-surface wind speed",
    ],
    "hfss": [
        "hfss",
        "surface sensible heat flux",
        "sensible heat flux at surface",
        "surface sensible heat flux",
        "surface heat flux",
    ],
    "hfls": [
        "hfls",
        "surface latent heat flux",
        "latent heat flux at surface",
        "surface latent heat flux",
    ],
    "clt": [
        "clt",
        "total cloud coverage",
        "total cloud coverage percentage",
        "cloud coverage",
        "cloud area fraction",
    ],
    "wap": [
        "wap",
        "vertical air velocity",
        "vertical velocity in pressure coordinates",
        "langrangian tendency of air pressure",
    ],
    "rlut": [
        "rlut",
        "toa outgoing longwave radiation",
        "top of atmosphere outgoing longwave radiation",
    ],
    "rsds": [
        "rsds",
        "surface downwelling shortwave radiation",
        "downward shortwave radiation at surface",
        "surface downwelling shortwave flux in the air",
        "surface radiation",
    ],
    "uas": [
        "uas",
        "eastward near-surface wind",
        "eastward near-surface wind component",
        "eastward wind",
    ],
    "vas": [
        "vas",
        "northward near-surface wind",
        "northward near-surface wind component",
        "northward wind",
    ],
    "huss": [
        "huss",
        "specific humidity near surface",
        "near-surface specific humidity",
        "near surface humidity",
    ],
    "ps": ["ps", "surface air pressure", "pressure at surface", "surface pressure"],
    "prsn": [
        "prsn",
        "snowfall",
        "snow precipitation",
        "snowfall flux",
        "rate of snowfall",
    ],
    "ts": [
        "ts",
        "surface temperature",
        "lower boundary temperature",
        "land surface temperature",
    ],
    "rsut": [
        "rsut",
        "toa outgoing shortwave radiation",
        "top of atmosphere outgoing shortwave radiation",
    ],
    "rsus": [
        "rsus",
        "surface upwelling shortwave radiation",
        "upward shortwave radiation at surface",
        "surface upwelling shortwave flux in the air",
    ],
    "rlus": [
        "rlus",
        "surface upwelling longwave radiation",
        "upward longwave radiation at surface",
        "surface upwelling longwave flux in the air",
    ],
    "rsdt": [
        "rsdt",
        "toa downwelling shortwave radiation",
        "top of atmosphere downwelling shortwave radiation",
    ],
    "rlutcs": [
        "rlutcs",
        "toa outgoing longwave radiation clear sky",
        "top of atmosphere outgoing longwave radiation clear sky",
    ],
    "hur": ["hur", "relative humidity", "relative humidity percentage"],
    "evspsbl": [
        "evspsbl",
        "evapotranspiration",
        "total surface evaporation",
        "evaporation at surface",
        "evaporation with transpiration",
    ],
    "tauu": [
        "tauu",
        "surface downward eastward stress",
        "downward eastward wind stress at surface",
    ],
    "tauv": [
        "tauv",
        "surface downward northward stress",
        "downward northward wind stress at surface",
    ],
    "tos": ["tos", "sea surface temperature", "ocean surface temperature"],
    # Add other variables as needed in chunks from most datasets to least
}

SCENARIO_MAP = {
    "ssp126": ["ssp1-2.6", "ssp126", "1.26 scenario", "low forcing scenario"],
    "ssp245": ["ssp2-4.5", "ssp245", "2.45 scenario", "medium forcing scenario"],
    "ssp370": ["ssp3-7.0", "ssp370", "3.70 scenario", "high forcing scenario"],
    "ssp585": ["ssp5-8.5", "ssp585", "5.85 scenario", "very high forcing scenario"],
    "dcppA-hindcast": [
        "dcppA-hindcast",
        "hindcast with historical forcing",
        "decadal hindcast",
    ],
    "pdSST-futArcSIC": [
        "pdSST-futArcSIC",
        "future arctic sea ice conditions with present-day sst",
        "Atmosphere time slice with present day SST and future Arctic SIC",
        "future sea ice loss with present-day conditions",
    ],
    "historical": [
        "historical",
        "historical forcing",
        "historical climate data",
        "pre industrial scenario",
    ],
}

INSTITUTION_MAP = {
    "MPI-M": ["max planck institute", "mpi-m"],
    "NCAR": ["national center for atmospheric research", "ncar"],
    "CESM": ["community earth system model", "cesm"],
    "IPSL": ["institut pierre-simon laplace", "ipsl", "ipsl-cm"],
    "UCI": ["university of california, irvine", "uc irvine", "uci"],
    # Add other institutions as needed
}

FREQUENCY_MAP = {
    "1hr": ["1hr", "1 hour", "1-hour", "hourly", "hour", "one hour"],
    "1hrCM": [
        "1hrCM",
        "1 hour means",
        "monthly-mean diurnal cycle resolving each day into 1-hour means",
        "hourly means over month",
    ],
    "1hrPt": [
        "1hrPt",
        "1 hour point",
        "1-hourly point",
        "hourly point",
        "one hour point",
    ],
    "3hr": ["3hr", "3 hour", "3-hour", "3 hourly", "3 hour mean", "three hour"],
    "3hrPt": [
        "3hrPt",
        "3 hour point",
        "3-hourly point",
        "3 hourly point",
        "three hour point",
    ],
    "6hr": ["6hr", "6 hour", "6-hour", "6 hourly", "6 hour mean", "six hour"],
    "6hrPt": [
        "6hrPt",
        "6 hour point",
        "6-hourly point",
        "6 hourly point",
        "six hour point",
    ],
    "day": ["day", "daily", "day mean", "per day"],
    "dec": ["dec", "decadal", "decadal mean"],
    "fx": ["fx", "fixed", "time invariant", "fixed time"],
    "mon": ["mon", "monthly", "month", "monthly mean"],
    "monPt": ["monPt", "month point", "monthly point"],
    "monC": ["monC", "monthly climatology", "month climatology"],
    "yr": ["yr", "yearly", "annual", "year", "annual mean"],
    "yrPt": ["yrPt", "year point", "yearly point"],
    "subhrPt": ["subhrPt", "sub-hourly point", "sub hourly point"],
}

SOURCE_MAP = {
    "CanESM5": [
        "CanESM5",
        "canadian earth system model version 5",
        "canesm5",
        "can esm5",
    ],
    "CESM2": ["CESM2", "community earth system model version 2", "cesm2", "cesm 2"],
    "MIROC6": [
        "MIROC6",
        "model for interdisciplinary research on climate version 6",
        "miroc6",
        "miroc 6",
    ],
    "IPSL-CM6A-LR": [
        "IPSL-CM6A-LR",
        "institut pierre-simon laplace climate model 6a low resolution",
        "ipsl-cm6a-lr",
        "ipsl cm6a lr",
    ],
    # Add other sources as needed
}


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = ["*"]  # applies to all pipelines
        priority: int = 1  # run early but after the user limit filter

    def __init__(self):
        self.type = "filter"
        self.name = "ESGF Facet Mapper"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"{self.name} started")

    async def on_shutdown(self):
        print(f"{self.name} stopped")

    # --- Find all matches ---
    def find_all_matches(self, text: str, mapping: dict) -> list[str]:
        text_lower = text.lower()
        candidates = []

        for match, aliases in mapping.items():
            for alias in aliases:
                alias_lower = alias.lower().strip()
                start = text_lower.find(alias_lower)

                while start != -1:
                    end = start + len(alias_lower)

                    if alias_lower.isalnum():
                        before_ok = start == 0 or not text_lower[start - 1].isalnum()
                        after_ok = (
                            end == len(text_lower) or not text_lower[end].isalnum()
                        )
                        if not (before_ok and after_ok):
                            start = text_lower.find(alias_lower, start + 1)
                            continue

                    candidates.append(
                        {
                            "match": match,
                            "start": start,
                            "end": end,
                            "length": len(alias_lower),
                        }
                    )
                    start = text_lower.find(alias_lower, start + 1)

        candidates.sort(key=lambda item: (-item["length"], item["start"]))

        selected = {}
        used_ranges = []
        for candidate in candidates:
            if candidate["match"] in selected:
                continue

            overlaps = any(
                not (candidate["end"] <= used_start or candidate["start"] >= used_end)
                for used_start, used_end in used_ranges
            )
            if overlaps:
                continue

            selected[candidate["match"]] = candidate
            used_ranges.append((candidate["start"], candidate["end"]))

        ordered = sorted(selected.values(), key=lambda item: item["start"])
        filtered = []
        for candidate in ordered:
            contained = any(
                candidate is not other
                and candidate["start"] >= other["start"]
                and candidate["end"] <= other["end"]
                for other in ordered
            )
            if not contained:
                filtered.append(candidate)

        return [item["match"] for item in filtered]

    # --- Core helper: detect and normalize ESGF facets ---
    def normalize_facets(self, text: str) -> dict:
        normalized = {}
        vars_found = self.find_all_matches(text, VARIABLE_MAP)
        scens_found = self.find_all_matches(text, SCENARIO_MAP)
        insts_found = self.find_all_matches(text, INSTITUTION_MAP)
        freqs_found = self.find_all_matches(text, FREQUENCY_MAP)
        sources_found = self.find_all_matches(text, SOURCE_MAP)

        if vars_found:
            normalized["variable"] = vars_found
        if scens_found:
            normalized["scenario"] = scens_found
        if insts_found:
            normalized["institution"] = insts_found
        if freqs_found:
            normalized["frequency"] = freqs_found
        if sources_found:
            normalized["source_id"] = sources_found
        return normalized

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"pipe:{__name__}")

        # Extract user input (depends on message format)
        user_input = ""
        if "input" in body:
            user_input = body["input"]
        elif "messages" in body and body["messages"]:
            user_input = body["messages"][-1].get("content", "")

        print(f"User input detected: {user_input}")

        # Normalize facets
        normalized_facets = self.normalize_facets(user_input)
        print(f"Normalized facets: {normalized_facets}")

        # Inject canonical info into prompt if anything found
        if normalized_facets:
            annotation_parts = []
            for key, values in normalized_facets.items():
                annotation_parts.append(f"{key}: {values}")
            annotation = ", ".join(annotation_parts)

            injected_note = f"\n\n(Note: normalized ESGF facets — {annotation})"
            body["input"] = f"{user_input}{injected_note}"

            if "messages" in body and body["messages"]:
                body["messages"][-1]["content"] = f"{user_input}{injected_note}"

        return body
