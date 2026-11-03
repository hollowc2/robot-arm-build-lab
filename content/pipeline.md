# Design Pipeline

The mechanical build loop starts with a spoken or sketched idea, turns it into reviewed Python build123d source, and produces printable artifacts for physical fit testing. The public site also contains a browser-only sorting-factory demo built from the exported CAD arm.

## CAD and Site Pipeline

CI runs for pull requests and pushes to `main`. On an exact validated CAD cache hit it reuses exports; otherwise it runs CAD tests and regenerates the models. Revision-specific catalog and progress JSON regenerate on every run. The site job then builds the Vite application, runs motion/CAD-contact regressions, and runs desktop/mobile browser checks with one worker. It publishes the tested `robot-arm-site-dist` artifact.

Successful push CI on `main` triggers the deployment workflow. The workflow checks whether the revision is still current when preparing the release, downloads the tested site artifact, and syncs it to Helios through the production GitHub Environment. Direct pushes to `main` also trigger this path; a merge is not required by the workflow. Manual deployment dispatch instead rebuilds the site and defaults to a dry run.

CI success and production deployment success are separate outcomes. Deployment requires working SSH and Tailscale credentials and must be checked against the public page. Use the [deployment runbook](../docs/deployment.md) for the targeted SSH fallback, validation, and rollback. Repository documentation changes do not themselves prove that production has updated.

## Current Demo

The live application exposes **Factory** and **Joints**. It sorts six stud-free block proxies into three color trays using predefined poses. It has no LEGO building mode and does not send commands to the real arm. See [the factory guide](../docs/sorting-factory.md) for behavior, source files, tests, and physical validation limits.
