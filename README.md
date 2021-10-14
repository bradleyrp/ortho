# Orthopraxy

A catchall grab-bag of miscellaneous Python extrana.

## History

### Circa `2021.09.08`

- Built the first feature, which specifically facilitates interactive development.
- Added a hook to use an automatic debugger which brings the developer to the site of an exception.
- Added a boilerplate example for building an application with a command-line interface (CLI) provided by click, including a hook to enable the automatic debugger. This pattern has minimal dependencies and is useful for many other academic projects, so we included it as an example rather than a feature that requires ortho.
- Started building Sphinx docs. A minimal deployment of docs includes a few simple steps. First, use the quickstart command: `sphinx-quickstart docs -p ortho -a 'Ryan Patrick Bradley' --sep -r 0.1 -l en --makefile --no-batchfile`. Then add `autodoc` to the `conf.py` along with a complete `.. automodule:: ortho` directive including `:members:` in the `index.rst`. This was completed on ortho commit `ad7cebe` at which point we can see docstrings in the html docs.

### Circa `2021.10.04`

- Started porting the `Handler` class into ortho.
- Development roadmap: refactor the `Handler` for elegant "multiple dispatch by signature" functionality (note that it took a while to come up with the right name for this) and then use it to integrate with YAML to manage docker containers and associated workflows.