# Contributing to Leviathan

Thanks for wanting to improve Leviathan. A few ground rules keep the project healthy:

## Workflow

1. Fork and create a branch: `feat/<name>`, `fix/<name>` or `docs/<name>`.
2. Keep PRs focused — one change per PR.
3. Open the PR against `master` and fill the template.

## Requirements by area

- **MQL5** (`mql5/`): must compile in MetaEditor with **zero errors and zero warnings**. Do not commit compiled `.ex5` binaries.
- **Python** (`python/`): `pytest python/tests -q` must be green, and new behavior needs a test.
- **Strategy logic** (either side): [docs/STRATEGY.md](docs/STRATEGY.md) is the single source of truth for both implementations. Any change to trading rules MUST update the spec in the same PR, and the other implementation must be updated (or an issue opened) to keep them in sync.

## Good first contributions

- New candle-pattern entry triggers (spec + both implementations + tests)
- New data loaders (Dukascopy, other exchanges)
- Additional filters (day-of-week, news CSV)
- Translations of the docs

## Not welcome

- Real account credentials, broker data dumps, or market data files in PRs
- "Guaranteed profit" claims in docs — this is an educational project

Be respectful in issues and reviews.
