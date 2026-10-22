# SyntheScale

**Evidence-grounded AI assessment for early-stage materials scale-up.**

Given a computationally proposed or experimentally developed material,
production location, target scale, and synthesis route, SyntheScale asks:

> **What are the major barriers to producing this material at larger scale,
> what evidence supports those conclusions, and what should be validated
> next?**

SyntheScale combines authoritative external data, deterministic calculations,
typed domain models, and structured AI reasoning to produce transparent
scale-up assessments without treating the language model as a database.

## Why SyntheScale?

Early-stage materials research often focuses on whether a material can be
synthesized or whether it performs well in a target application. Practical
scale-up introduces a different set of questions:

- Are the required chemicals hazardous to handle at larger scale?
- Are important raw-material markets volatile or geographically concentrated?
- Does production depend heavily on imports or critical minerals?
- Are suitable precursor products commercially available?
- What evidence is still missing before a scale-up decision can be made?

Relevant information is distributed across chemical databases, commodity
datasets, mineral statistics, supplier information, and experimental
knowledge.

SyntheScale assembles this information into a common evidence model and uses
AI to interpret the evidence, identify barriers and data gaps, and recommend
the highest-value next validation steps.

## Design principles

- **Prefer authoritative structured data over LLM knowledge.**
- **Preserve the provenance of every retrieved fact.**
- **Use deterministic calculations wherever possible.**
- **Use LLMs for interpretation and synthesis, not as databases.**
- **Distinguish missing information from evidence of low risk.**
- **Distinguish upstream commodity indicators from direct precursor prices.**
- **Keep data providers independent from the core domain model.**
- **Retain a complete evidence record while supplying the LLM only a compact,
  decision-relevant context.**

## Current prototype

The current prototype evaluates evidence in five initial scale-up categories:

- **Safety**
- **Cost**
- **Market volatility**
- **Availability**
- **Supply chain**

Not every category will receive a numerical score. If the available evidence
does not support a defensible assessment, SyntheScale explicitly reports
`insufficient_data` and identifies the missing information.

### Current data sources

**PubChem**

Used for:

- chemical identity resolution;
- molecular formula and identifiers;
- GHS signal words;
- GHS pictograms;
- GHS hazard statements.

**World Bank Commodity Price Data ("Pink Sheet")**

Used for:

- commodity reference prices;
- historical monthly price series;
- price-change calculations;
- annualized historical price volatility.

**U.S. Geological Survey Mineral Commodity Summaries 2026**

Used for:

- world commodity production;
- reserves where available;
- U.S. net import reliance;
- geographic production concentration;
- U.S. critical-mineral designation.

No API credentials are required for the World Bank or USGS datasets.

**UN Comtrade (country/material availability pilot)**

Used for country-specific annual imports, reported trading partners, historical
import-value trends, partner-value concentration, and historical import unit
values. Requires `UN_COMTRADE_API_KEY`. These indicators describe trade categories,
not live inventory, exact-grade supply, supplier quotations or delivered costs.

## How it works

```text
Material + proposed synthesis route
                |
                v
        Chemical identity
            (PubChem)
                |
                v
         Safety evidence
                |
                +-----------------------+
                |                       |
                v                       v
       Commodity exposure         Market history
            mapping               (World Bank)
                |                       |
                v                       v
       Supply statistics       Price + volatility
             (USGS)              calculations
                |                       |
                +-----------+-----------+
                            |
                            v
                    AssessmentContext
                full provenance-rich record
                            |
                            v
                       LLMContext
                 compact evidence projection
                            |
                            v
                   Structured LLM analysis
                            |
                            v
                  GeneratedAssessment
                            |
             +--------------+--------------+
             |              |              |
             v              v              v
          Barriers      Data gaps      Next actions
```

The language model receives retrieved and calculated evidence rather than
being asked to research facts itself.

## Example

The current demonstration scenario evaluates production of **Zeolite 13X**
in Illinois using:

- sodium aluminate;
- sodium silicate;
- sodium hydroxide;
- water.

SyntheScale resolves the precursor identities, gathers chemical safety
evidence, maps relevant precursor exposures to aluminum and silicon
commodities, evaluates market and mineral supply data, and produces a
structured scale-up assessment.

For example, the prototype can identify:

- precursor corrosivity and other reported GHS hazards;
- upstream aluminum price and historical volatility;
- geographic concentration of aluminum and silicon production;
- U.S. net import reliance;
- critical-mineral designations;
- missing direct precursor pricing and supplier information.

Importantly, an aluminum commodity reference price is treated as an
**upstream market indicator**, not as the purchase price of sodium aluminate.

### Commodity name matching

Chemical-to-commodity exposure mapping remains curated. Once an upstream
commodity is identified, each provider resolves its name independently against
the commodities available in its loaded dataset:

1. Use an existing curated alias, provided its target exists in that dataset.
2. Try an exact catalog match, ignoring case and surrounding/repeated whitespace.
3. Try conservative full-name fuzzy matching using Python's `difflib`.
4. Return `None` for missing, weak, or ambiguous matches; the assessment records
   the existing provider-specific data gap rather than guessing.

Fuzzy matching requires a similarity score of at least 0.95 and a lead of at
least 0.05 over the next candidate. It also preserves word count and rejects
changes to short tokens (three characters or fewer), protecting short grade
and region identifiers. These scores are lexical heuristics, not probabilities
or proof of chemical equivalence. For example, `Phosphate rocck` can resolve to
`Phosphate rock`, but `silicone` does not resolve to `Silicon`.
An alias whose target is absent remains unresolved; it is not remapped to a
different commodity. Catalog names that differ only in case or whitespace
are treated as ambiguous rather than chosen arbitrarily.

The matcher uses no LLM or external API and returns the dataset's original
commodity name. Semantic synonyms still require reviewed aliases, and matching
a catalog name does not guarantee that all requested price or supply statistics
are available. This step does not extend chemical-to-commodity coverage.

## Quick start

### 1. Clone the repository

```bash
git clone <repository-url>
cd SyntheScale
```

### 2. Create and activate a Python environment

For example, using Conda:

```bash
conda create -n material-scaleup python=3.15
conda activate material-scaleup
```

### 3. Install SyntheScale

Install the development, AI, and UI dependencies:

```bash
python -m pip install -e ".[dev,ai,ui]"
```

### 4. Download external datasets

Download and validate the World Bank and USGS datasets:

```bash
python scripts/download_data.py
```

To download individual datasets:

```bash
python scripts/download_data.py --world-bank
python scripts/download_data.py --usgs
```

Downloaded source datasets are stored under `data/raw/` and are not committed
to the repository.

### 5. Configure the language model

Set an OpenAI API key and model:

```bash
export OPENAI_API_KEY="your-api-key"
export SYNTHE_SCALE_MODEL="gpt-6.1-sol"
```

Do not commit API keys to the repository.

### 6. Launch the application

```bash
streamlit run app.py
```

Open the local URL shown by Streamlit, enter a material and proposed synthesis
route, and select **Assess scale-up**.

### Country/material availability

Configure an authenticated UN Comtrade account key in the environment before
starting Streamlit:

```bash
export UN_COMTRADE_API_KEY="your-comtrade-api-key"
streamlit run app.py
```

Do not commit keys. Restart the app after changing credentials. The provider sends
the key in a request header, not query strings, exported results or UI messages.
It does not fall back to unauthenticated preview data.

Select **Country/material availability** for a standalone lookup. This workflow
does not require an OpenAI key, the OpenAI package, or local World Bank/USGS data.
Turn on the global **Enable UN Comtrade** toggle to connect. It defaults to **off**
even when an API key is configured, so opening the app on a restricted corporate
network does not trigger Comtrade requests. Enable it on a working network such
as your hotspot. Your choice persists across reruns and workflow changes within
the current Streamlit session.

1. Select a destination from the Comtrade reporting-country/area catalog.
2. Enter up to ten materials, one per line, or search using a six-digit HS code.
3. Choose a suggested HS2022 category for each material.
4. Confirm each category's scope before selecting **Retrieve trade evidence**.
5. Inspect annual results, partner records, warnings and coverage; download the
   provenance-rich JSON evidence if needed.

Reviewed pilot category suggestions cover sodium aluminate, sodium silicate,
sodium hydroxide/caustic soda and urea. Sodium aluminate uses a broad salts
category; sodium silicate and sodium hydroxide require attention to product form.
Other names use conservative catalog search suggestions. All current suggestions
require confirmation, including exact code searches. Lexical similarity and user
confirmation do not establish chemical equivalence, grade, purity or concentration.
Unresolved materials remain unresolved; no chemical is silently substituted.

Results persist across reruns. Changing country, material, selected category or
confirmation invalidates the displayed lookup. Unselected materials remain
explicit gaps; one failed period/material does not discard other results.

In **Scale-up assessment**, turn on the same **Enable UN Comtrade** toggle.
Use the same country dropdown
and classification/confirmation controls before assessing. Materials without
retrieved trade evidence are recorded as gaps. Water is omitted from the default
precursor trade lookup. Turn the toggle off to retain the existing assessment
workflow without Comtrade credentials or network access to Comtrade. Off means no
Comtrade requests in either workflow and no trade evidence attached to assessments;
other providers may still use their own network connections. Previously retrieved
trade results are cleared when disabled and must be retrieved again after enabling.
Assessments explicitly record disabled trade evidence as a data gap, not low risk.
Connection failures remain visible while enabled; the app does not silently switch
the toggle off. You can turn it off even after a failure to continue assessing.

#### Coverage and interpretation

- The provider requests up to the latest five available completed annual periods
  using **HS (reported classification)** for availability, counts and trade queries.
  Material candidates still come from the HS2022 catalog; this is not a claim
  that returned data use HS2022. Returned `classificationCode` or `clCode` metadata
  are preserved when present; missing revision metadata remains explicitly
  unverified, never defaulted to H6. A different/missing revision produces a
  category-equivalence warning. Cross-year trends are withheld unless every
  period's records match the selected catalog revision. Five periods are not
  guaranteed. Current-year data are
  excluded; missing intervening/recent years and failures are disclosed. An annual
  reporting period is not a guarantee of exhaustive customs coverage.
- Monthly continuity and numeric availability-risk scores are **not released** in
  this pilot. Existing assessments may score other independently supported
  evidence; pilot trade indicators alone must not support numerical scores.
- Requests use imports, total secondary partner, total customs and transport
  dimensions. World totals are not added to bilateral values. Each annual query
  checks a separate record count; missing, capped (1,000 records), mismatched,
  duplicate or unexpected records are rejected rather than treated as complete.
  Count-only requests omit data-display options; data requests use JSON with
  descriptions and a record cap. Neither forces a breakdown mode. Failures identify
  the count or data operation, and failed annual requests are labeled `error`,
  not `insufficient_data`.
- Concentration uses **reported partner value**, including any special or
  unspecified partner areas. It is not a count of independent suppliers or
  verified origin countries. Partner totals must reconcile to the world total
  within 0.5% or USD 1; otherwise concentration and cost benchmarks are withheld.
- Historical USD/kg is the ratio of value to net weight for the **same eligible
  partner records**. Missing/zero/estimated weights are excluded. At least 80% of
  partner trade value must have usable non-estimated weight; coverage is displayed.
  This is a conservative pilot quality gate, not a calibrated risk threshold.
- The unit-value calculation uses primary import values. Imports are generally
  CIF-valued, but country valuation exceptions are not verified. Do not assume
  transport costs can be added again. Grade, concentration, taxes, domestic
  delivery and distributor margins are not established by these benchmarks.
- Value trends are nominal USD changes, not quantity trends or price indices.
  Low imports do not establish scarcity or import dependence; domestic production
  and existing demand may be significant.
- Domestic supply, verified restrictions and logistics are explicitly **not
  checked** by this first release. Existing USGS upstream evidence remains
  separate; it does not prove direct precursor availability.
- API responses are cached in memory for up to one hour, bounded to 256 entries
  per provider. The displayed timestamp is lookup time. Each material requests at
  most five annual record counts and five annual datasets, plus shared reference
  and reporting-availability queries. Transient failures receive at most three
  attempts with bounded delays; account entitlement errors are surfaced.

Live authenticated contract validation (network access and a configured key
required):

```bash
pytest -q tests/providers/test_comtrade.py -m integration
```

An absent key skips this opt-in test; a skip does not establish live API
compatibility. Offline tests use representative mocked response contracts.

#### Troubleshooting Comtrade connectivity

The app distinguishes DNS lookup, timeout, proxy, TLS certificate and HTTP
authentication failures without displaying credentials or raw exception details.

For a DNS/connection error, test connectivity without sending your API key:

```bash
nslookup comtradeapi.un.org
nslookup comtrade.azure-api.net
curl --head --connect-timeout 5 --max-time 15 https://comtradeapi.un.org/
```

The API hostname may resolve through the Azure API Management alias. If the
alias has no address or reports `NXDOMAIN`, requests cannot reach authentication.
The main Comtrade website loading does not establish API connectivity. Check
your VPN, DNS or corporate firewall with your network administrator, or retry
after an API/DNS outage. Do not hard-code IP addresses, redirect credentials to
unverified hosts, or disable TLS verification.

For a missing key or HTTP 401/403, export `UN_COMTRADE_API_KEY` in the same
terminal used to start Streamlit, then restart Streamlit. Exporting a variable
does not update an already-running process or other terminals. Never paste the
key into diagnostic output.

## Streamlit interface

The prototype UI provides a guided form for entering:

- material name and description;
- production country and region;
- target production amount;
- synthesis-route description;
- chemical inputs and their process roles.

The form is converted internally into a typed `ScaleUpScenario`.

Chemical inputs must resolve in PubChem before assessment proceeds. If a name
is not found, the app identifies the unresolved input and asks you to check its
spelling or enter a recognized name or CAS number. It does not automatically
substitute a similar chemical or continue with an unidentified input. This is
separate from the downstream commodity-name matching described above.

Results include:

- category-level assessments;
- evidence confidence;
- supporting facts;
- major barriers;
- strengths;
- explicit data gaps;
- recommended validation actions;
- expandable evidence and source information.

## Running the Zeolite 13X example directly

The end-to-end example can also be run without the UI:

```bash
python scripts/run_zeolite_assessment.py
```

The script:

1. resolves chemical identities through PubChem;
2. retrieves safety evidence;
3. gathers World Bank and USGS commodity evidence;
4. performs deterministic market calculations;
5. constructs the assessment context;
6. generates a compact LLM context;
7. requests a structured AI assessment.

Generated runs are written to:

```text
outputs/zeolite_13x_<timestamp>/
├── assessment.json
├── assessment_context.json
└── llm_context.json
```

`assessment_context.json` preserves the complete evidence packet, while
`llm_context.json` contains the compact decision-relevant projection supplied
to the language model.

## Testing

Run the complete test suite:

```bash
pytest -q
```

Run only tests that do not access external services:

```bash
pytest -q -m "not integration"
```

Run integration tests:

```bash
pytest -q -m integration
```

Check formatting and linting:

```bash
ruff format src tests scripts
ruff check src tests scripts
```

## Project structure

```text
SyntheScale/
├── app.py
├── scripts/
│   ├── download_data.py
│   └── run_zeolite_assessment.py
├── src/
│   └── material_scaleup/
│       ├── calculations/
│       ├── models/
│       ├── providers/
│       ├── resolvers/
│       └── services/
├── tests/
├── data/
│   └── raw/                  # downloaded external datasets; not committed
├── outputs/                  # generated assessments; not committed
├── pyproject.toml
└── README.md
```

### Core layers

**Models**

Typed Pydantic schemas representing chemicals, materials, scenarios,
evidence, commodity observations, assessment contexts, and structured AI
outputs.

**Providers**

Source-specific integrations including PubChem, World Bank commodity data,
and USGS Mineral Commodity Summaries.

**Resolvers**

Domain logic connecting chemical precursors to relevant upstream commodity
exposures.

**Calculations**

Deterministic computations including commodity price change, annualized
volatility, and production concentration.

**Services**

Orchestration for evidence collection, context construction, LLM-context
compaction, prompting, and structured assessment generation.

## Current limitations

SyntheScale is an early-stage prototype.

Current limitations include:

- chemical-to-commodity mappings are curated and incomplete;
- commodity prices are upstream indicators, not direct chemical precursor
  purchase prices;
- supplier-specific price, inventory, production-origin, and lead-time data
  are not yet integrated;
- process economics cannot be estimated without precursor quantities, yield,
  utilities, and other process information;
- category and confidence scores are currently AI-generated assessment
  judgments and are not statistically calibrated probabilities;
- regulatory, environmental, infrastructure, waste, and ethical categories
  are represented in the domain model but are not yet fully supported by
  evidence providers.

These limitations are surfaced as explicit assumptions and data gaps rather
than being interpreted as low risk.

## Future directions

Potential extensions include:

- direct chemical supplier and pricing integrations;
- composition-aware chemical-to-commodity resolution;
- automated extraction of synthesis routes from literature or natural
  language;
- deterministic raw-material cost-per-kilogram calculations;
- additional environmental, regulatory, infrastructure, and waste datasets;
- deterministic evidence-coverage and confidence scoring;
- richer process-scale and techno-economic analysis;
- automated comparison of alternative synthesis routes and production
  locations.

## Security

Never commit API credentials or other secrets to the repository.

Use environment variables such as:

```bash
OPENAI_API_KEY
SYNTHE_SCALE_MODEL
```

Downloaded datasets and generated assessment runs are intentionally excluded
from version control.
