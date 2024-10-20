# firehose2 [Draft/WIP]

Disclaimer: These are just my ideas as an individual, and is in no way authoritative with regards to future protocol changes. If you're reading this in the future and a "firehose v2" concretely exists, it's likely that this document does not accurately describe it. 

## TODO:

- The rest of the document.
- Write some code that quantifies and compares bandwidth requirements for the current firehose, firehose2, and jetstream.

## Introduction

The "firehose" is more formally known as the `com.atproto.sync.subscribeRepos` [Event Stream](https://atproto.com/specs/event-stream). It's the main primitive for real-time synchronisation of repos within atproto. There are a few broad categories of event stream consumers (names made up by me):

1. "**Full Sync**" - An entity such as a Relay that maintains complete and authenticated copies of upstream repos, keeping them synchronised in close-to-real-time. This implies performing cryptographic verification.
2. "**Authenticated Streaming**" - An entity such as a Feed Generator that watches the event stream in real time, but doesn't try to store a full copy of the data (maybe it only cares about trying to count likes on posts from the previous 24h, for example). It verifies commit signatures, but it is unable to perform rigorous verification of changes to the MST (due to not storing a copy of the previous MST state).
3. "**Unauthenticated Streaming**" - As above, but without bothering to verify signatures (for many "low stakes" use cases, there is no strong desire to authenticate data cryptographically).
4. "**Filtered Streaming**" - Similar to the above, but only interested in a subset of events (e.g. "only `app.bsky.feed.post` record creation events from this list of DIDs").

At present, consuming the firehose from Bluesky PBC's relay (`bsky.network`) is rather bandwidth intensive, using in excess of 2TB of network bandwidth per month. This number will only go up as atproto rises in popularity.

[Jetstream](https://docs.bsky.app/blog/jetstream) improves the story for use cases 3 and 4, but since it lacks authentication, it is unable to help for the others.

This document aims to address use cases 1, 2 and 3, reducing the required bandwidth *without* making any sacrifices in terms of cryptographic authentication of events. (Filtered Streaming could be addressed too, but that's out of scope for this document). A sub-goal is to lower the marginal cost/complexity of making use of cryptographic verification, thereby increasing its prevalence.

## Repo v4

Before I get on to the firehose changes, I need to make a small addition to the [repo Commit object](https://atproto.com/specs/repository). A new field will be added, `opsCid`, which contains the hash (in CID format) of the DAG-CBOR-encoded list of operations that produced this commit, relative to the previous commit. The format of this list is the same as defined in the [subscribeRepos lexicon](https://github.com/bluesky-social/atproto/blob/81ae1b12389f1c2b1ca9aa5ed0660a0f569c4c9d/lexicons/com/atproto/sync/subscribeRepos.json#L92-L100). Note that the *contents* of this list are not stored in the Commit object, merely the CID.

## `subscribeRepos` v2

The [format](https://github.com/bluesky-social/atproto/blob/81ae1b12389f1c2b1ca9aa5ed0660a0f569c4c9d/lexicons/com/atproto/sync/subscribeRepos.json) actually remains completely untouched, in terms of schema, *except* the `blocks` CAR archive no longer includes any MST blocks, *only* the contents of any added or updated records, along with the signed commit object.

You might be thinking that this breaks the "Full Sync" use case, but it doesn't! Assuming the consumer has a full copy of the previous repo state, it can efficiently perform the MST update operation for itself, and check that the MST root CID matches the one specified in the `data` field of the Commit object.

For the not-full-sync use cases, it simplifies and enhances the ability of the consumer to authenticate the operations list, notably for deletions. Such consumers just need to verify that the CID of the `ops` array matches that specified in the signed commit's `opsCid` field, and they know it's genuine.

## Event Stream Wire Protocol v1

https://atproto.com/specs/event-stream

TODO - compression stuff
 
