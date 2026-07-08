# Design Pipeline

The build loop starts with a spoken or sketched mechanical idea, then turns it into a concrete prompt for LLM-assisted CAD work. The output is reviewed as Python build123d source, regenerated in CI, rendered for the public dashboard, exported as printable artifacts, and finally checked against physical fit tests.

Every public update is human-approved. LLM and CAD changes land in branches and pull requests, CI produces previews, and the workshop dashboard updates only after the change merges to `main`.
