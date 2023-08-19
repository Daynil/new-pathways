Static page builder for New Pathways LLC.

Data is sourced from the client via a Wordpress admin backend. This data is
then built into a static page via a simple, zero dependency Python build script.

Run dev build with file watch with `$ ./build-start`. 

Works well with the Live Server VSCode extension, but can serve `public` directory using any server, e.g. python:
`python -m http.server --directory './public'`
