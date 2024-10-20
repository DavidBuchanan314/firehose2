# firehose2 [Draft/WIP]

Disclaimer: These are just my ideas as an individual, and is in no way authoritative with regards to future protocol changes. If you're reading this in the future and a "firehose v2" concretely exists, it's likely that this document does not accurately describe it. 

The "firehose" is more formally known as the `com.atproto.sync.subscribeRepos` [Event Stream](https://atproto.com/specs/event-stream). This is the main primitive for real-time synchronosation of repos within atproto. There are a few broad categories of event stream consumers (names made up by me):

1. "**Full Sync**" - An entity such as a Relay that maintains complete and authenticated copies of upstream repos, keeping them synchronised in close-to-real-time. This implies performing cryptographic verification.
2. "**Authenticated Streaming**" - An entity such as a Feed Generator that watches the event stream in real time, but doesn't try to store a full copy of the data (maybe it only cares about trying to count likes on posts from the previous 24h, for example). It verifies commit signatures, but it is unable to perform rigorous verification of changes to the MST (due to not storing a copy of the previous MST state).
3. "**Unauthenticated Streaming**" - As above, but without bothering to verify signatures.
4. "**Filtered Streaming**" - Similar to the above, but only interested in a subset of events (e.g. "only `app.bsky.feed.post` record creation events from this list of DIDs").

At present, consuming the firehose from Bluesky PBC's relay (`bsky.network`) is rather bandwidth intensive, using in excess of 2TB of network bandwidth per month, and this number will only go up as atproto rises in popularity.

[Jetstream](https://docs.bsky.app/blog/jetstream) improves the story for use cases 3 and 4, but since it lacks authentication, it is unable to help for the others.

This document aims to address use cases 1, 2 and 3, reducing the required bandwidth *without* making any sacrifices in terms of cryptographic authentication of events. (Filtered Streaming could be addressed too, but that's out of scope for this document)
