# SyntheScale

## Goal

Given a computationally proposed or experimentally developed material, production location, and intended application, what are the major barriers to producing it at kilogram-to-commercial scale, what evidence supports each conclusion, and what should be validated next?

The system combines authoritative data sources with AI-assisted analysis
to produce transparent, source-grounded feasibility assessments.

## Design principles

- Prefer authoritative structured data over LLM knowledge.
- Preserve the source of every retrieved fact.
- Use deterministic calculations where possible.
- Use LLMs for interpretation and synthesis, not as databases.
- Distinguish unavailable information from low-risk information.
- Keep external data providers independent of the domain model.

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. [Stack-specific setup instructions]
4. Run the application

## External data setup

SyntheScale uses the World Bank Pink Sheet monthly commodity-price
dataset for commodity-price and market-volatility analysis.

Download and validate the required datasets:

```bash
python scripts/download_data.py

## Development

### Prerequisites
- [List requirements]

### Installation
\`\`\`bash
# Installation steps
\`\`\`

### Running
\`\`\`bash
# Run commands
\`\`\`

## Project Structure
\`\`\`
├── src/          # Source code
├── tests/        # Tests
└── docs/         # Documentation
\`\`\`

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md)

## License
[Your License]
