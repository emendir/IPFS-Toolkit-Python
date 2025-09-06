# Docs Tools
_a set of tools for generating and processing documentation_

## Docs Processing Commands

Get an overview of available docs processing tools:
```sh
make help
```

## Documentation Components

### Markdown Docs

This project's `/docs` folder contains hand-written documentation in markdown format.

### API-Reference

The `/docs/API-Reference` is an HTML website generated from the source code's docstrings using `sphinx`.

```sh
make api
```

### Full Docs HTML Website

A website can be generated at `/docs/html` including both the API-Reference and the hand-written documentation.

```sh
make all
```
