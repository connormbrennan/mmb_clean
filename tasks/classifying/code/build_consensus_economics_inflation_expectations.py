# Purpose: Build a vintage panel of Consensus Economics inflation expectations from WRDS Datastream.
# Inputs: WRDS Datastream Econ tables and ../config/params.yaml.
# Outputs: A next-/two-calendar-year inflation expectations panel, raw forecast vintages, metadata, and codebook in ../output/.
# Run instructions: From tasks/classifying/code, run `make all`.

from pathlib import Path

import numpy as np
import pandas as pd
import wrds
import yaml


code_dir = Path(__file__).parent
task_dir = code_dir.parent
config_path = task_dir / "config" / "params.yaml"
output_dir = task_dir / "output"

with open(config_path, "r") as f:
    params = yaml.safe_load(f)

output_dir.mkdir(parents=True, exist_ok=True)

wrds_username = params["wrds"]["username"]
library = params["datastream"]["library"]
info_table = params["datastream"]["info_table"]
data_table = params["datastream"]["data_table"]
source_code = params["datastream"]["consensus_source_code"]
description_terms = params["datastream"]["description_terms"]
expectation_statistic = params["datastream"]["expectation_statistic"].lower()
keep_horizons = params["datastream"]["keep_horizons"]
output_files = params["output_files"]

# Step 1: Find Datastream Econ series that are explicitly sourced to Consensus Economics
# and describe annual consumer-price forecasts. This excludes realized CPI codes like CONPRC*.
where_clauses = ["srccode = %(source_code)s"]
sql_params = {"source_code": source_code}
for i, term in enumerate(description_terms):
    where_clauses.append(f"lower(coalesce(desc_english, '')) like %(term_{i})s")
    sql_params[f"term_{i}"] = f"%{term.lower()}%"

metadata_query = f"""
    select ecoseriesid, dsnumber, dsmnemonic, startdate, isforecast,
           mktcode, mktdesc, srccode, srccodedesc, statcode, scalecode,
           unitcode, unitcodedesc, freqcode, clstype1desc, clstype2desc,
           desc_english
    from {library}.{info_table}
    where {" and ".join(where_clauses)}
    order by mktdesc, dsmnemonic
"""

db = wrds.Connection(wrds_username=wrds_username)
series_metadata = db.raw_sql(metadata_query, params=sql_params)

series_metadata["description_lower"] = series_metadata["desc_english"].fillna("").str.lower()
series_metadata["statistic"] = np.select(
    [
        series_metadata["description_lower"].str.contains("mean", na=False),
        series_metadata["description_lower"].str.contains("stdev", na=False),
        series_metadata["description_lower"].str.contains("median", na=False),
        series_metadata["description_lower"].str.contains("high", na=False),
        series_metadata["description_lower"].str.contains("low", na=False),
    ],
    ["mean", "stdev", "median", "high", "low"],
    default="unknown",
)
series_metadata = series_metadata.drop(columns=["description_lower"])
series_metadata.to_csv(output_dir / output_files["series_metadata_csv"], index=False)

# Step 2: Pull all forecast vintages for these series. The important date for a forecast
# panel is announceddate, because perioddate is the target annual inflation year.
if len(series_metadata) > 0:
    series_ids = ",".join(series_metadata["ecoseriesid"].astype(int).astype(str).tolist())
    data_query = f"""
        select d.ecoseriesid, d.perioddate, d.announceddate, d.changeseq,
               d.series_value,
               i.dsmnemonic, i.mktcode, i.mktdesc, i.srccode, i.srccodedesc,
               i.desc_english, i.freqcode, i.unitcodedesc
        from {library}.{data_table} d
        inner join {library}.{info_table} i
            on d.ecoseriesid = i.ecoseriesid
        where d.ecoseriesid in ({series_ids})
        order by i.dsmnemonic, d.perioddate, d.announceddate, d.changeseq
    """
    vintages = db.raw_sql(data_query)
else:
    vintages = pd.DataFrame()

# Step 2a: Audit nearby WRDS metadata locations so sparse coverage is a recorded fact,
# not just an assumption from the main filter.
audit_lines = []
audit_lines.append("WRDS availability audit for Consensus Economics inflation forecasts")
audit_lines.append("")
audit_lines.append("Why this audit exists")
audit_lines.append("- Public LSEG documentation says the full Consensus Economics product exists on Datastream.")
audit_lines.append("- This task checks what the WRDS-hosted Datastream Economics SQL product exposes to this account.")
audit_lines.append("")
audit_lines.append("Primary WRDS product checked")
audit_lines.append(f"- Product/schema: {library}")
audit_lines.append(f"- Metadata table: {library}.{info_table}")
audit_lines.append(f"- Data table: {library}.{data_table}")
audit_lines.append("")

schemas_to_check = ["tr_ds_econ", "trdstrm", "tr_ds_econ_old", "trsamp_dsecon", "trdssamp"]
tables_to_check = ["wrds_ecoinfo", "ecoinfo", "ecocode", "ecoclscode"]
candidate_codes = [source_code, "US97", "CBS", "EC1"]
text_columns = [
    "dsnumber", "dsmnemonic", "mktcode", "mktdesc", "currcode", "currcodedesc",
    "adjcode", "adjcodedesc", "statcode", "scalecode", "seriestypecode",
    "unitcode", "unitcodedesc", "freqcode", "srccode", "srccodedesc",
    "cnvcode", "cnvcodedesc", "clstype1desc", "clstype2desc", "desc_english",
]
search_blob = " || ' ' || ".join([f"coalesce({col}, '')" for col in text_columns])

audit_lines.append("Schema/table counts")
for schema in schemas_to_check:
    existing_tables = db.raw_sql(
        """
        select table_name
        from information_schema.tables
        where table_schema = %(schema)s
          and table_name in ('wrds_ecoinfo', 'ecoinfo', 'ecocode', 'ecoclscode')
        order by table_name
        """,
        params={"schema": schema},
    )
    audit_lines.append(f"- {schema}: {', '.join(existing_tables['table_name'].tolist()) if len(existing_tables) else 'no checked tables found'}")

    if "wrds_ecoinfo" in existing_tables["table_name"].tolist():
        total_rows = db.raw_sql(f"select count(*) as n from {schema}.wrds_ecoinfo")["n"].iloc[0]
        source_rows = db.raw_sql(
            f"select count(*) as n from {schema}.wrds_ecoinfo where srccode = %(source_code)s",
            params={"source_code": source_code},
        )["n"].iloc[0]
        regex_rows = db.raw_sql(
            f"""
            select count(*) as n
            from {schema}.wrds_ecoinfo
            where upper(dsmnemonic) ~ '^[A-Z0-9]{{2}}C[A-Z]CPR[A-Z]$'
            """
        )["n"].iloc[0]
        suffix_rows = db.raw_sql(
            f"""
            select count(*) as n
            from {schema}.wrds_ecoinfo
            where upper(dsmnemonic) ~ 'CPR[A-Z]$'
            """
        )["n"].iloc[0]
        cemain_rows = db.raw_sql(
            f"select count(*) as n from {schema}.wrds_ecoinfo where upper({search_blob}) like %(term)s",
            params={"term": "%CEMAIN%"},
        )["n"].iloc[0]
        forecast_word_rows = db.raw_sql(
            f"""
            select count(*) as n
            from {schema}.wrds_ecoinfo
            where upper({search_blob}) like %(forecast)s
              and (
                    upper({search_blob}) like %(inflation)s
                 or upper({search_blob}) like %(cpi)s
                 or upper({search_blob}) like %(consumer_prices)s
              )
            """,
            params={
                "forecast": "%FORECAST%",
                "inflation": "%INFLATION%",
                "cpi": "%CPI%",
                "consumer_prices": "%CONSUMER PRICE%",
            },
        )["n"].iloc[0]
        audit_lines.append(
            f"  wrds_ecoinfo rows={total_rows}; {source_code} source rows={source_rows}; "
            f"regex ^[A-Z0-9]{{2}}C[A-Z]CPR[A-Z]$ rows={regex_rows}; "
            f"suffix CPR[A-Z] rows={suffix_rows}; CEMAIN rows={cemain_rows}; "
            f"forecast+inflation text rows={forecast_word_rows}"
        )

audit_lines.append("")
audit_lines.append("Consensus-like code table entries")
consensus_codes = db.raw_sql(
    f"""
    select series_type, code, description
    from {library}.ecocode
    where upper(coalesce(code, '') || ' ' || coalesce(description, '')) like %(term)s
    order by code
    """,
    params={"term": "%CONSENSUS%"},
)
if len(consensus_codes):
    audit_lines.append(consensus_codes.to_string(index=False))
else:
    audit_lines.append("No Consensus-like rows found in ecocode.")

audit_lines.append("")
audit_lines.append("Attachment counts for Consensus-like codes in wrds_ecoinfo")
code_columns = [
    "dsnumber", "dsmnemonic", "mktcode", "currcode", "adjcode", "statcode",
    "scalecode", "seriestypecode", "unitcode", "freqcode", "srccode", "cnvcode",
]
for candidate_code in candidate_codes:
    code_where = " or ".join([f"{col} = %(candidate_code)s" for col in code_columns])
    count = db.raw_sql(
        f"select count(*) as n from {library}.{info_table} where {code_where}",
        params={"candidate_code": candidate_code},
    )["n"].iloc[0]
    audit_lines.append(f"- {candidate_code}: {count} attached rows")

audit_lines.append("")
audit_lines.append("Rows from the explicit Consensus Economics source")
if len(series_metadata):
    audit_rows = series_metadata[
        [
            "ecoseriesid", "dsmnemonic", "mktdesc", "srccode", "srccodedesc",
            "desc_english", "clstype1desc", "clstype2desc", "freqcode",
            "unitcodedesc", "startdate", "statistic",
        ]
    ]
    audit_lines.append(audit_rows.to_string(index=False))
else:
    audit_lines.append("No rows returned from the explicit Consensus Economics source.")
audit_lines.append("")
audit_lines.append("Interpretation")
audit_lines.append("- The full Consensus Economics product appears to exist in LSEG Datastream, but this WRDS SQL product exposes only the rows above.")
audit_lines.append("- The script therefore writes the available explicit WRDS Consensus Economics forecast rows and does not substitute realized CPI series.")

db.close()

# Step 3: Make the vintage panel transparent: survey_date is when the forecast was observed,
# target_year is the annual CPI inflation year being forecast.
if len(vintages) > 0:
    vintages["perioddate"] = pd.to_datetime(vintages["perioddate"])
    vintages["survey_date"] = pd.to_datetime(vintages["announceddate"])
    vintages["forecast_value"] = pd.to_numeric(vintages["series_value"], errors="coerce")
    vintages["target_year"] = vintages["perioddate"].dt.year
    vintages["survey_year"] = vintages["survey_date"].dt.year
    vintages["horizon_years"] = vintages["target_year"] - vintages["survey_year"]
    vintages["country"] = vintages["mktdesc"].str.strip().str.title()
    vintages["description_lower"] = vintages["desc_english"].fillna("").str.lower()
    vintages["statistic"] = np.select(
        [
            vintages["description_lower"].str.contains("mean", na=False),
            vintages["description_lower"].str.contains("stdev", na=False),
            vintages["description_lower"].str.contains("median", na=False),
            vintages["description_lower"].str.contains("high", na=False),
            vintages["description_lower"].str.contains("low", na=False),
        ],
        ["mean", "stdev", "median", "high", "low"],
        default="unknown",
    )
    vintages["is_expectation"] = vintages["statistic"].eq(expectation_statistic)
    vintages["source_check"] = vintages["srccodedesc"].fillna("")
    vintages["old_cpi_mnemonic_check"] = vintages["dsmnemonic"].str.contains("CONPRC", na=False)

    vintages = vintages[
        [
            "survey_date",
            "target_year",
            "horizon_years",
            "country",
            "mktcode",
            "dsmnemonic",
            "statistic",
            "forecast_value",
            "unitcodedesc",
            "freqcode",
            "perioddate",
            "changeseq",
            "ecoseriesid",
            "desc_english",
            "source_check",
            "is_expectation",
            "old_cpi_mnemonic_check",
        ]
    ].sort_values(["country", "statistic", "target_year", "survey_date", "changeseq"])
else:
    vintages = pd.DataFrame(
        columns=[
            "survey_date", "target_year", "horizon_years", "country", "mktcode",
            "dsmnemonic", "statistic", "forecast_value", "unitcodedesc", "freqcode",
            "perioddate", "changeseq", "ecoseriesid", "desc_english", "source_check",
            "is_expectation", "old_cpi_mnemonic_check",
        ]
    )

vintages.to_csv(output_dir / output_files["vintages_csv"], index=False)

# Step 4: The main output is the mean inflation expectation for next/two-calendar-year targets.
# If Datastream exposes no two-year-ahead rows, the codebook records that rather than inventing it.
panel = vintages[
    vintages["is_expectation"] & vintages["horizon_years"].isin(keep_horizons)
].copy()
panel = panel.rename(columns={"forecast_value": "inflation_expectation_pct"})
panel = panel[
    [
        "survey_date",
        "country",
        "mktcode",
        "target_year",
        "horizon_years",
        "inflation_expectation_pct",
        "dsmnemonic",
        "ecoseriesid",
        "desc_english",
        "source_check",
        "unitcodedesc",
        "freqcode",
        "changeseq",
    ]
].sort_values(["country", "survey_date", "target_year", "changeseq"])

panel.to_csv(output_dir / output_files["panel_csv"], index=False)
panel.to_parquet(output_dir / output_files["panel_parquet"], index=False)

# Step 5: Write a plain-text codebook so the binary parquet and the WRDS selection are inspectable.
codebook_lines = []
codebook_lines.append("Consensus Economics inflation expectations panel")
codebook_lines.append("")
codebook_lines.append("Source and selection")
codebook_lines.append(f"- WRDS library/table: {library}.{info_table} joined to {library}.{data_table}")
codebook_lines.append(f"- Source filter: srccode == {source_code} ({params['datastream']['consensus_source_name']})")
codebook_lines.append(f"- Description terms: {', '.join(description_terms)}")
codebook_lines.append(f"- Main panel statistic: {expectation_statistic}")
codebook_lines.append(f"- Main panel horizons: {keep_horizons}")
codebook_lines.append("- The script keeps announceddate as survey_date; perioddate is the target annual inflation year.")
codebook_lines.append("- Realized CPI series from the old notebook are excluded because they are not sourced to Consensus Economics and have CONPRC-style mnemonics.")
codebook_lines.append("")
codebook_lines.append("Output files")
for key, filename in output_files.items():
    codebook_lines.append(f"- {key}: {filename}")
codebook_lines.append("")
codebook_lines.append("Main panel dimensions")
codebook_lines.append(f"- Rows: {len(panel)}")
codebook_lines.append(f"- Columns: {panel.shape[1]}")
codebook_lines.append(f"- Countries: {panel['country'].nunique() if len(panel) else 0}")
codebook_lines.append(f"- Survey date range: {panel['survey_date'].min() if len(panel) else 'NA'} to {panel['survey_date'].max() if len(panel) else 'NA'}")
codebook_lines.append(f"- Target years: {sorted(panel['target_year'].dropna().unique().tolist()) if len(panel) else []}")
codebook_lines.append("")
codebook_lines.append("Available Consensus Economics CPI forecast series found on WRDS")
if len(series_metadata) > 0:
    for _, row in series_metadata.iterrows():
        codebook_lines.append(
            f"- {row['dsmnemonic']}: {row['mktdesc']}, {row['desc_english']}, "
            f"{row['freqcode']}, {row['unitcodedesc']}, statistic={row['statistic']}"
        )
else:
    codebook_lines.append("- None")
codebook_lines.append("")
codebook_lines.append("Vintage coverage by statistic and horizon")
if len(vintages) > 0:
    coverage = (
        vintages.groupby(["country", "statistic", "horizon_years"])
        .agg(
            rows=("forecast_value", "size"),
            min_survey_date=("survey_date", "min"),
            max_survey_date=("survey_date", "max"),
            min_target_year=("target_year", "min"),
            max_target_year=("target_year", "max"),
        )
        .reset_index()
    )
    codebook_lines.append(coverage.to_string(index=False))
else:
    codebook_lines.append("No vintage rows returned.")
codebook_lines.append("")
codebook_lines.append("Column dtypes")
codebook_lines.append(panel.dtypes.astype(str).to_string())
codebook_lines.append("")
codebook_lines.append("First rows")
codebook_lines.append(panel.head(10).to_string(index=False))

with open(output_dir / output_files["codebook_txt"], "w") as f:
    f.write("\n".join(codebook_lines))

with open(output_dir / output_files["availability_audit_txt"], "w") as f:
    f.write("\n".join(audit_lines))
