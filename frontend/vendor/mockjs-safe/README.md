# Safe MockJS compatibility surface

`@umijs/openapi` imports MockJS eagerly even when this project generates only API clients and does not enable its `mockFolder` option. The published MockJS dependency has an unresolved prototype-pollution advisory.

This private package implements only the safe `Random.extend` surface required during generator startup. Calling the unused mock-generation API fails closed. Remove this compatibility package when the OpenAPI generator no longer imports MockJS for client-only generation.
