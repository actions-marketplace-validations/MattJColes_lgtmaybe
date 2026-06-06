"""github — GitHub REST adapter for lgtmaybe.

Public surface:
- RestGitHubGateway: implements GitHubGateway against the GitHub REST API.
- build_position_map: parse a unified diff into a (file, line) → position map.
- is_reviewable: predicate that rejects lockfiles, minified, vendored, binary paths.
"""

from .diff import build_position_map, is_reviewable
from .rest_gateway import RestGitHubGateway

__all__ = ["RestGitHubGateway", "build_position_map", "is_reviewable"]
