# Harmonia Plugin System

> Version: 0.1 Draft

## Purpose

The plugin system allows Harmonia to be extended without modifying the
core application. Every optional capability---metadata providers,
artwork providers, lyrics, analytics, exporters, importers---should be
implemented as plugins.

The core must remain small, stable, and independent.

------------------------------------------------------------------------

# Design Goals

-   Stable public interfaces
-   Zero core modifications for new providers
-   Runtime discovery
-   Configuration-driven enable/disable
-   Version compatibility
-   Safe failure isolation

------------------------------------------------------------------------

# Plugin Categories

## Metadata Providers

Examples:

-   MusicBrainz
-   Discogs
-   Last.fm
-   Local NFO files

Responsibilities:

-   Search artists
-   Search albums
-   Search tracks
-   Fetch metadata

------------------------------------------------------------------------

## Artwork Providers

Examples:

-   Apple Music
-   Qobuz
-   Cover Art Archive
-   Deezer
-   iTunes

Responsibilities:

-   Album search
-   Artwork lookup
-   Download artwork
-   Report artwork resolution

------------------------------------------------------------------------

## Audio Analysis

Examples:

-   ReplayGain
-   Dynamic Range
-   Spectral Analysis
-   Fingerprinting

------------------------------------------------------------------------

## Import / Export

Examples:

-   CSV
-   JSON
-   Playlist formats
-   foobar2000
-   MusicBee

------------------------------------------------------------------------

# Plugin Lifecycle

``` text
Discover
   │
Load
   │
Validate
   │
Initialize
   │
Run
   │
Shutdown
```

Plugins should never crash the application.

Failures are logged and the plugin is disabled.

------------------------------------------------------------------------

# Provider Interface

Example artwork provider:

``` python
class ArtworkProvider:
    name: str
    priority: int

    async def search_album(self, album, artist):
        ...

    async def download_artwork(self, result):
        ...

    async def health_check(self):
        ...
```

Metadata providers follow a similar contract.

------------------------------------------------------------------------

# Priority System

Multiple providers may return results.

Example order:

1.  Apple Music
2.  Qobuz
3.  Cover Art Archive
4.  MusicBrainz
5.  iTunes
6.  Deezer

The core merges results and selects the highest-quality match.

------------------------------------------------------------------------

# Discovery

Plugins are discovered from:

``` text
harmonia/providers/

or

~/.config/harmonia/plugins/
```

Future releases may support Python entry points for third-party
packages.

------------------------------------------------------------------------

# Configuration

Example:

``` toml
[providers]
enabled = [
    "apple",
    "qobuz",
    "musicbrainz",
]

priority = [
    "apple",
    "qobuz",
    "coverartarchive",
]
```

Users can enable, disable, or reorder providers without changing code.

------------------------------------------------------------------------

# Security

Plugins execute with the user's permissions.

Recommendations:

-   No automatic installation
-   Signed releases for official plugins (future)
-   Explicit user opt-in
-   Network access only when required

------------------------------------------------------------------------

# Compatibility

Every plugin declares:

-   Name
-   Version
-   Supported Harmonia versions
-   Author
-   License
-   Homepage

Example:

``` yaml
name: Apple Music
version: 1.0.0
requires: ">=0.4.0"
license: MIT
```

------------------------------------------------------------------------

# Error Handling

Plugins return structured errors instead of raising UI-facing
exceptions.

The core records:

-   provider
-   request
-   error type
-   retry recommendation

------------------------------------------------------------------------

# Future Ideas

-   Community plugin marketplace
-   Automatic updates
-   Plugin sandboxing
-   Plugin dependency resolution
-   Remote providers
-   AI metadata providers

------------------------------------------------------------------------

## Guiding Principle

The Harmonia core should never know *how* a provider works.

It should only know *what* capability the provider offers.

This keeps the architecture modular, testable, and easy for contributors
to extend.
