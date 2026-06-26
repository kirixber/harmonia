\# Providers



> Version: 0.1 Draft



\---



\# Purpose



Providers are Harmonia's bridge to external services.



The core application never directly communicates with Apple Music,

MusicBrainz, Qobuz, or any other service.



Instead, every external integration implements a common interface.



This keeps Harmonia modular, testable, and future-proof.



\---



\# Philosophy



The Harmonia Core should never contain provider-specific logic.



Instead:



```

Core



↓



Provider Manager



↓



Artwork Provider

Metadata Provider

Lyrics Provider

Audio Provider



↓



Apple

MusicBrainz

Qobuz

Deezer

Discogs

```



The Provider Manager decides which provider to call.



\---



\# Provider Categories



\## Metadata



Responsible for:



\- Artist search

\- Album search

\- Track search

\- Metadata lookup



Examples



\- MusicBrainz

\- Discogs

\- Last.fm



\---



\## Artwork



Responsible for:



\- Album artwork

\- Artist artwork



Examples



\- Apple Music

\- Qobuz

\- Cover Art Archive

\- Deezer



\---



\## Audio Analysis



Responsible for



\- Fingerprints

\- ReplayGain

\- Dynamic Range



Examples



\- AcoustID

\- Chromaprint



\---



\## Lyrics



Examples



\- LRCLIB

\- Genius

\- Musixmatch (if supported)



\---



\# Provider Interface



Every provider inherits from a common base.



```python

class Provider:



&#x20;   name: str



&#x20;   version: str



&#x20;   priority: int



&#x20;   async def initialize(self):

&#x20;       ...



&#x20;   async def shutdown(self):

&#x20;       ...



&#x20;   async def health\_check(self):

&#x20;       ...

```



\---



Artwork providers extend:



```python

class ArtworkProvider(Provider):



&#x20;   async def search\_album(...):



&#x20;   async def download\_artwork(...)



&#x20;   async def validate(...)

```



Metadata providers extend:



```python

class MetadataProvider(Provider):



&#x20;   async def search\_artist(...)



&#x20;   async def search\_album(...)



&#x20;   async def search\_track(...)

```



\---



\# Provider Manager



The Provider Manager is responsible for



\- discovery



\- initialization



\- ordering



\- retries



\- health monitoring



\- caching



\- shutdown



\---



\# Discovery



Providers are loaded from



```

harmonia/providers/

```



Future



```

\~/.config/harmonia/plugins/

```



Eventually



Python Entry Points



\---



\# Priority



Example



```

Artwork



Apple



↓



Qobuz



↓



Cover Art Archive



↓



MusicBrainz



↓



iTunes



↓



Deezer

```



Priority is configurable.



\---



\# Parallel Execution



Providers should execute concurrently.



Instead of



```

Apple



↓



Qobuz



↓



MusicBrainz

```



Harmonia performs



```

Apple ─────┐



Qobuz ─────┤



MusicBrainz┤



Deezer ────┘



↓



Merge Results

```



This dramatically reduces search latency.



\---



\# Result Merging



Example



Apple



3000x3000



Confidence 99%



MusicBrainz



1200x1200



Confidence 100%



Qobuz



2400x2400



Confidence 98%



↓



Artwork Engine



↓



Choose Best



\---



\# Health Checks



Every provider reports



\- online



\- degraded



\- offline



\- rate limited



The UI displays provider status.



\---



\# Rate Limiting



Providers may define



Requests / minute



Concurrent requests



Retry policy



Backoff strategy



The Provider Manager enforces these limits.



\---



\# Caching



Every request is hashed.



```

Artist



Album



Track



↓



SHA256



↓



SQLite Cache

```



Cache expiration depends on provider.



Example



Artwork



30 days



Metadata



90 days



\---



\# Error Handling



Providers never crash Harmonia.



Errors are categorized



\- Network



\- Authentication



\- Rate limit



\- Invalid response



\- Parsing



Each provider returns structured errors.



\---



\# Authentication



Some providers require no authentication.



Examples



\- MusicBrainz

\- Cover Art Archive



Others may require



\- API keys



\- OAuth



\- Cookies



Credentials are stored securely through the configuration layer.



\---



\# Configuration Example



```toml

\[providers]



enabled = \[

&#x20;   "apple",

&#x20;   "qobuz",

&#x20;   "musicbrainz",

&#x20;   "coverartarchive",

]



priority = \[

&#x20;   "apple",

&#x20;   "qobuz",

&#x20;   "coverartarchive",

&#x20;   "musicbrainz",

]

```



\---



\# Future Providers



Possible additions



\- Spotify



\- TIDAL



\- Bandcamp



\- Beatport



\- Discogs



\- Last.fm



\- Fanart.tv



\- ListenBrainz



\- YouTube Music



\---



\# Design Principles



A provider should



✓ implement one responsibility



✓ expose a stable interface



✓ support async operations



✓ be independently testable



✓ fail gracefully



✓ never modify application state directly



\---



\# Long-Term Vision



The provider system should evolve into a plugin ecosystem where third-party

developers can add new metadata, artwork, lyrics, streaming, and analytics

providers without modifying Harmonia's core.



The core engine should only know \*what capability is requested\*, never \*which

provider fulfills it\*.

