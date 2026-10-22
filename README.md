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

## Streamlit interface

The prototype UI provides a guided form for entering:

- material name and description;
- production country and region;
- target production amount;
- synthesis-route description;
- chemical inputs and their process roles.

The form is converted internally into a typed `ScaleUpScenario`.

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

See [SECURITY.md](SECURITY.md) for additional information.
