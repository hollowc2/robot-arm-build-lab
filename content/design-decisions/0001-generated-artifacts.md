# Generated Artifacts Stay Out of Git

STEP, STL, glTF, rendered images, and other large generated files are excluded from normal source commits. CI regenerates them from Python CAD source, uploads heavyweight files as build artifacts, and publishes only small JSON plus optimized web assets to the static site.
