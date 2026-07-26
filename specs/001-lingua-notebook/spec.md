# Feature Specification: LinguaNotebook

**Feature Branch**: `001-lingua-notebook`

**Created**: 2026-07-25

**Status**: Draft

**Input**: User description: "Build LinguaNotebook — a cross-platform, open-source web and mobile application for deep language learning powered by personal documents, advanced RAG, customizable schedules, daily AI-powered lessons, and multilingual text-to-speech. Works fully offline, open source on GitHub."

## Clarifications

### Session 2026-07-25

- Q: What distinct user roles exist and what can each do? → A: Three in-app roles: Learner (study, upload own documents), Team Admin (invite members, manage shared library, billing), Instance Admin (self-hosted only: system configuration, no tier limits). GitHub contributor is an external community role, not an in-app account role.
- Q: What is the feature split between free and paid? → A: No split — all features are completely free for all users. Voluntary donations via GitHub Sponsors/Ko-fi for project sustainability only. (Amended 2026-07-26 per constitution v2.0.0)
- Q: Must self-hosted instances have GPU access for document parsing, or is CPU-only acceptable? → A: CPU fallback is required. Self-hosted MUST support CPU-only parsing as the default path (slow, ~2-3 minutes per page). GPU acceleration and cloud parsing endpoints are documented but optional optimizations. Setup guide clearly states expected performance for each hardware path.
- Q: What is the expected uptime/availability target for the cloud-hosted service? → A: 99.5% uptime (~3.65 hours max downtime per month). Single-region deployment with basic redundancy, automated backups with under 1-hour recovery time objective. Appropriate for consumer SaaS v1; can be upgraded post-launch.
- Q: How should flashcards, grammar exercises, and reading questions be generated from user documents? → A: LLM-powered extraction using a lightweight model (Qwen3-0.6B or similar) running server-side. Generates flashcards (10-20 per chapter with source context), reading questions (3-5 MCQs per passage), and grammar exercises (fill-in-the-blank with plausible distractors). Runs post-parse; works offline for self-hosted users.
- Q: Which open source license? → A: MIT license. Simple, permissive, most widely adopted, compatible with all project dependencies.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Document Upload & Parsing (Priority: P1) 🎯 MVP

As a language learner, I want to upload my foreign-language PDF textbook and have the system automatically parse every page into structured, searchable text so I can learn directly from my own study materials.

**Why this priority**: This is the foundation — without parsed documents, there is no content for the knowledge base, no lessons, no flashcards. The entire value proposition starts here.

**Independent Test**: Upload a 10-page PDF → watch real-time parsing progress via progress bar → receive structured output with correct headings, paragraphs, and tables identified. Can be fully tested by uploading a PDF and verifying the parsed output.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they upload a valid PDF (under 500MB), **Then** the system starts parsing and streams real-time progress showing current page, total pages, elapsed time, and estimated time remaining
2. **Given** a parsing job in progress, **When** the user views the progress display, **Then** they see the current page number, total pages, elapsed time, estimated time remaining, and any errors updated in real-time
3. **Given** a completed parsing job, **When** the user views the results, **Then** each page shows structured content with headings, paragraphs, tables, and their positions on the page clearly identified
4. **Given** a parsing job with a corrupted page, **When** that page fails, **Then** the error is recorded with the page number and error message, and parsing continues with remaining pages
5. **Given** a user uploads a PDF in Vietnamese, French, Japanese, or Chinese, **When** parsing completes, **Then** the text content is correctly recognized in the source language with proper character encoding

---

### User Story 2 — Knowledge Base & Search (Priority: P1) 🎯 MVP

As a language learner, I want all my parsed documents to be stored in an intelligent knowledge base so I can search for any word, phrase, or concept across all my materials and get contextually relevant results.

**Why this priority**: The knowledge base is the engine that powers every learning interaction. Without searchable, retrievable content, the system cannot generate lessons, flashcards, or quizzes.

**Independent Test**: Upload and parse 3 PDFs → content is automatically chunked and indexed → search for a word → get ranked results from all 3 documents with surrounding context. Can be tested with: upload → wait for indexing → search query → verify results.

**Acceptance Scenarios**:

1. **Given** parsed document content, **When** indexing runs automatically, **Then** content is split into semantically meaningful segments that preserve headings, full tables, and coherent paragraphs
2. **Given** indexed content, **When** the indexing process completes, **Then** each content segment is searchable with metadata including language, content type, difficulty level, source document, and page number
3. **Given** a user searches for a keyword or concept, **When** the search executes, **Then** results include both conceptually similar matches AND exact keyword matches, ranked by relevance, returned quickly even across thousands of content segments
4. **Given** an existing knowledge base index, **When** a user uploads a new PDF, **Then** only the new document's content is indexed — previously indexed content is not reprocessed

---

### User Story 3 — Study Schedule & Daily Lessons (Priority: P1) 🎯 MVP

As a language learner, I want to set my study schedule (when, how often, what to focus on) and receive an auto-generated daily lesson drawn from my own documents so I can maintain a consistent learning habit.

**Why this priority**: This is the core user-facing loop — schedule + auto-generated lessons is what the user interacts with every day. Combined with US1+US2, this completes the MVP.

**Independent Test**: Create a schedule (e.g., Mon/Wed/Fri at 8am, focus on vocabulary from French textbook) → system generates a daily lesson with flashcards, a reading passage, and quiz questions → complete the lesson → see results. Can be tested by creating a schedule and verifying lesson generation.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they create a schedule specifying days, time, duration, and content preferences, **Then** the schedule is saved and the system prepares to generate daily lessons
2. **Given** an active schedule, **When** the system generates a daily lesson, **Then** the lesson contains: vocabulary flashcards (with definitions and examples from source documents), a reading passage with comprehension questions, and grammar exercises — all sourced from the user's knowledge base
3. **Given** a daily lesson, **When** the user completes all items, **Then** a score is calculated, completed items feed into the spaced repetition system, and the lesson is marked as done for that day
4. **Given** a user changes their schedule, **When** the next daily lesson is generated, **Then** it reflects the new preferences in content types, duration, and difficulty

---

### User Story 4 — Text-to-Speech Voice System (Priority: P2)

As a language learner, I want to hear any word, sentence, or passage spoken aloud with natural pronunciation so I can practice listening comprehension and improve my accent.

**Why this priority**: Listening is a core language skill. This enhances all three P1 stories by adding audio to flashcards, reading passages, and quizzes. However, the core learning loop (upload → parse → knowledge base → lessons) works without it.

**Independent Test**: Open any flashcard or reading passage → click the play button → hear natural audio within 2 seconds → see an animated audio visualization → switch language, voice, or speed. Can be tested by playing audio from any content item.

**Acceptance Scenarios**:

1. **Given** a text content item (word, sentence, or paragraph), **When** the user clicks play, **Then** audio plays within 2 seconds (when previously generated) using the configured voice and language
2. **Given** audio is playing, **When** the user views the audio player, **Then** an animated visualization is displayed tracking the audio progress
3. **Given** the audio player, **When** the user changes voice gender, speed, or language, **Then** subsequent playback uses the new settings
4. **Given** audio has been generated for a text, **When** the same text is played again, **Then** the saved audio is replayed instantly without delay
5. **Given** the user has previously played audio while online, **When** they play the same content without internet access, **Then** the audio still plays using locally saved data

---

### User Story 5 — Spaced Repetition System (Priority: P2)

As a language learner, I want the system to automatically schedule vocabulary review using spaced repetition so I retain what I've learned with minimal effort.

**Why this priority**: Spaced repetition dramatically improves long-term retention but the core learning loop (P1 stories) already delivers value with one-time learning. SRS makes learning stick.

**Independent Test**: Complete a lesson with 10 flashcards → review cards are created with scheduling parameters → next day, review cards appear in the daily lesson → rate each card → intervals adjust. Can be tested by completing flashcards and verifying review scheduling.

**Acceptance Scenarios**:

1. **Given** a user completes a flashcard, **When** the session ends, **Then** a review card is created with default parameters: initial interval of 1 day, scheduled for review the next day
2. **Given** review cards are due, **When** the daily lesson is generated, **Then** due review cards are mixed in with new content items
3. **Given** a user rates a review card on a scale from "forgot" to "easy", **When** the rating is submitted, **Then** the scheduling algorithm recalculates the review interval based on the rating
4. **Given** consistent correct answers over time, **When** intervals grow, **Then** review frequency decreases following a progression from 1 day to several days to weeks to months

---

### User Story 6 — Progress Dashboard (Priority: P2)

As a language learner, I want a visual dashboard showing my learning progress — streaks, vocabulary growth, study time, and performance trends — so I stay motivated and see my improvement over time.

**Why this priority**: Motivation and visibility are key to long-term engagement. However, the core learning functionality works without it.

**Independent Test**: After studying for several days → open the dashboard → see streak count, a calendar view of study days, vocabulary growth chart, study time breakdown, and accuracy by content type. Can be tested by generating learning data and verifying dashboard renders correctly.

**Acceptance Scenarios**:

1. **Given** a user with 7 consecutive days of completed lessons, **When** they view the dashboard, **Then** the streak counter shows "7" with a calendar highlighting studied days
2. **Given** accumulated learning data, **When** the dashboard loads, **Then** charts display: vocabulary learned over time, study minutes by day, and accuracy by content type
3. **Given** a user clicks "Export Report", **When** the report is generated, **Then** it contains a summary of all dashboard metrics formatted for printing or sharing

---

### User Story 7 — Offline-First Learning (Priority: P1) 🎯 MVP

As a language learner with limited or intermittent internet access, I want the entire learning experience to work offline — including browsing my documents, completing daily lessons, listening to audio, and reviewing flashcards — with my progress syncing automatically when I reconnect.

**Why this priority**: Offline capability is core to the value proposition. Users in transit, in areas with poor connectivity, or those who simply prefer privacy must be able to learn without interruption. This is elevated to P1 because it fundamentally shapes the architecture.

**Independent Test**: Go offline (airplane mode) → open the app → browse previously uploaded documents → complete a full lesson with audio → go back online → verify that progress synced to the cloud without data loss or conflicts. Can be tested by toggling connectivity and verifying data integrity.

**Acceptance Scenarios**:

1. **Given** the user goes offline, **When** they open the app, **Then** all previously downloaded documents, lessons, flashcards, and audio are fully accessible and functional
2. **Given** a user completes a lesson while offline, **When** they reconnect to the internet, **Then** their progress (completed items, scores, SRS updates, streak) syncs automatically without data loss
3. **Given** a user uploads a new PDF while online, **When** parsing completes, **Then** the parsed content and generated audio are automatically downloaded and available for offline use
4. **Given** the user is offline, **When** they attempt an online-only action (upload new PDF, process payment), **Then** a clear message explains the action requires internet and will be available upon reconnection
5. **Given** a user uses the app on two devices (e.g., phone and laptop), **When** both devices sync after being offline, **Then** learning progress is merged correctly without duplication or data loss

---

### User Story 8 — Cross-Platform Mobile & Desktop Apps (Priority: P2)

As a language learner, I want to use LinguaNotebook seamlessly across my phone, tablet, and computer — with a native-feeling experience on each platform — so I can learn wherever I am, on whatever device is at hand.

**Why this priority**: Multi-platform access maximizes learning opportunities. The web app (P1) covers desktop; native mobile apps make on-the-go learning practical. P2 because the responsive web app already works on mobile browsers.

**Independent Test**: Install the app on an iPhone from the App Store, on an Android phone from Google Play, and open the web app on a laptop → log into the same account on all three → study on one device → verify progress appears on all others. Can be tested by installing on each platform and verifying cross-device sync.

**Acceptance Scenarios**:

1. **Given** a user visits the app store for their device (iOS App Store, Google Play), **When** they search for LinguaNotebook, **Then** they can download and install the native app
2. **Given** the native mobile app is installed, **When** the user launches it, **Then** the app loads quickly (under 3 seconds) and presents the same learning experience as the web version, adapted for the device screen size and interaction patterns
3. **Given** a user is studying on their phone app, **When** they switch to the desktop web app, **Then** all progress, documents, schedules, and settings are identical across both platforms
4. **Given** a user receives a push notification about their daily lesson on their phone, **When** they tap it, **Then** the app opens directly to today's lesson

---

### User Story 9 — Open Source & Community (Priority: P2)

As a developer or power user, I want LinguaNotebook to be fully open source on GitHub with clear contribution guidelines so I can self-host it, audit the code, add features, fix bugs, and adapt it to my own language learning needs or niche use cases.

**Why this priority**: Open source drives adoption, trust, and community contributions. It enables self-hosting for privacy-conscious users and creates an ecosystem. P2 because the product must be functional before the community can contribute meaningfully.

**Independent Test**: Visit the public GitHub repository → read the README, CONTRIBUTING guide, and LICENSE → clone the repo → follow the setup guide in the docs → run the full stack locally via a single command → make a change → open a PR following the contribution template. Can be tested by a new contributor going through the entire flow.

**Acceptance Scenarios**:

1. **Given** a visitor to the GitHub repository, **When** they read the README, **Then** they understand what the project does, how to install it, how to contribute, and what license it uses within 5 minutes
2. **Given** a developer clones the repository, **When** they follow the setup guide, **Then** they can run the full application locally (web + API + database) with a single command
3. **Given** a developer wants to self-host, **When** they follow the deployment guide, **Then** they can deploy their own instance with their own documents and data, fully independent of any cloud service
4. **Given** a community contributor submits a pull request, **When** it passes automated checks (tests, linting, code coverage), **Then** maintainers can review and merge it following documented guidelines
5. **Given** a user wants offline-only usage without any cloud dependency, **When** they run the self-hosted version, **Then** all features work without requiring any external service or internet connection

---

### User Story 10 — Authentication & User Management (Priority: P3)

As a user, I want to create an account, log in securely, and know that my learning data, documents, and progress are private and accessible only to me.

**Why this priority**: Authentication is necessary for data isolation and premium tiers, but the core learning experience could be built as a single-user app first. P3 because it gates multi-user access and monetization.

**Independent Test**: Register with email → verify email → log in → upload documents → log out → log back in → documents and progress are still there. Register with a third-party account (Google) → same flow. Can be tested by creating accounts and verifying data persistence and isolation.

**Acceptance Scenarios**:

1. **Given** a new visitor, **When** they register with email and password, **Then** an account is created, a verification message is sent, and they cannot access protected areas until verified
2. **Given** an unverified account, **When** the user completes verification, **Then** the account is activated and they are guided through initial setup
3. **Given** User A and User B are both logged in, **When** User A uploads documents, **Then** User B cannot see, search, or access User A's documents under any circumstances
4. **Given** a user requests account deletion, **When** confirmed, **Then** all user data (documents, content segments, schedules, lessons, review cards) is permanently deleted within 30 days

---

### User Story 11 — Community Support & Sustainability (Priority: P3)

As a user who values the application, I want a way to support the project financially through voluntary donations or GitHub Sponsors so the developers can sustain the free service and continue improving it. All features remain completely free for everyone, forever.

**Why this priority**: Sustainability matters for long-term maintenance, but the product must demonstrate value first. P3 because donations are entirely optional and do not affect the user experience.

**Independent Test**: Visit the donation page → choose a support option (GitHub Sponsors, Ko-fi, etc.) → complete a voluntary contribution → receive a thank-you acknowledgment. No features change. Can be tested by going through the donation flow.

**Acceptance Scenarios**:

1. **Given** any user (cloud or self-hosted), **When** they access the application, **Then** all features are fully available with no limits, no paywalls, and no feature gates of any kind
2. **Given** a user who wants to support the project, **When** they visit the support page, **Then** they see voluntary contribution options (GitHub Sponsors, Ko-fi, etc.) with a clear statement that donations are optional and do not unlock additional features
3. **Given** a user completes a donation, **When** the contribution is processed, **Then** they receive a thank-you acknowledgment. No feature changes occur — the experience is identical before and after donating.

---

### Edge Cases

- What happens when a user uploads a PDF that is entirely handwritten (no machine-readable text)? → System detects minimal text extraction, warns the user, and still stores page images for reference
- What happens when parsing encounters a page with no detectable layout blocks? → Page is stored as unstructured text; user can manually organize content via the editor
- What happens when the parsing service is at capacity (multiple concurrent jobs)? → Jobs are queued in order; user sees "waiting in queue" status with position indicator
- What happens when cloud infrastructure costs exceed donation income? → Core services remain operational; the project communicates transparently with the community about funding needs and may adjust infrastructure scale. The service is never shut down without at least 30 days notice and data export availability.
- What happens when a user uploads a PDF in a language not supported by text-to-speech? → Content is still parsed and usable for reading and writing; voice playback shows "language not supported" with an option to request it
- How does the system handle a 500-page PDF upload on a slow connection? → Upload supports resuming if interrupted with progress indication; parsing starts only after full upload completes
- What happens when a user deletes a document that is the source of active review cards? → User is warned about dependent review cards before deletion; cards retain their content independently
- What happens when a daily lesson is scheduled but the user has no new content to learn? → Lesson consists entirely of review cards; system suggests uploading new documents
- What happens when a user goes offline mid-lesson on the mobile app? → Lesson state is saved locally; when reconnected, partial progress syncs and the user can resume where they left off
- What happens when offline and online data conflict (e.g., user studied the same flashcard on two offline devices)? → Last-write-wins with timestamp resolution; both attempts are logged; the user is notified of the conflict
- How does the self-hosted version handle document parsing without cloud GPU access? → Self-hosted instances run CPU-only parsing by default (slower but fully functional, approximately 2-3 minutes per page). Users with a local GPU can enable GPU acceleration via configuration. A cloud parsing endpoint is also documented as an optional optimization. The setup guide clearly states expected performance for each hardware path.
- What happens when a community contributor submits a PR that modifies core architecture? → PR triggers full CI pipeline; architecture changes require a design document and maintainer approval per CONTRIBUTING guidelines
- What happens when the mobile app is backgrounded during a parsing progress SSE stream? → The connection is gracefully re-established when the app returns to foreground; parsing continues on the server regardless

## Requirements *(mandatory)*

### Functional Requirements

**Core Platform:**
- **FR-001**: System MUST allow user registration and login via email with password AND via third-party account providers (Google, GitHub)
- **FR-002**: System MUST support document uploads up to 500MB and automatically parse them into structured content with identified headings, paragraphs, tables, and their page positions
- **FR-003**: System MUST parse documents using a pipeline that: renders each page → identifies layout structure through visual analysis → extracts text and layout information into structured output with content blocks and their bounding positions. The parsing pipeline MUST support CPU-only execution as the default self-hosted path (approximately 2-3 minutes per page), with GPU acceleration available as an optional configuration.
- **FR-004**: System MUST display real-time parsing progress showing: current page, total pages, elapsed time, estimated time remaining, and processing speed
- **FR-005**: System MUST intelligently segment parsed content by content type (headings, paragraphs, tables, lists) and generate searchable representations for each segment
- **FR-006**: System MUST store content segments with hybrid search capability combining conceptual similarity search, keyword search, and filtering by metadata (language, content type, difficulty, source)
- **FR-007**: System MUST incrementally update the knowledge base index when new documents are uploaded without requiring full re-indexing of existing content
- **FR-008**: Users MUST be able to create customizable study schedules with: time of day, days of week, content type preferences, and daily session size
- **FR-009**: System MUST auto-generate daily learning sessions combining new content from the knowledge base and review items from spaced repetition
- **FR-010**: System MUST integrate a spaced repetition system that schedules reviews based on user performance, adjusting intervals from daily to monthly based on recall success

**Voice & Audio:**
- **FR-011**: System MUST support text-to-speech playback in at least 8 languages (English, Vietnamese, Chinese, Japanese, Korean, French, German, Spanish) with both online and offline playback capability
- **FR-012**: System MUST save generated audio to avoid redundant generation for identical content, keeping audio for at least 30 days
- **FR-013**: System MUST display an animated audio visualization during playback

**Dashboard & Reporting:**
- **FR-014**: System MUST provide a progress dashboard showing: consecutive study days (with calendar view), vocabulary growth, cumulative study time, and accuracy breakdown by content type
- **FR-015**: System MUST support exporting learning progress reports as downloadable documents

**Monetization:**
- **FR-016**: All features MUST be completely free for all users — no paywalls, no tiered access, no feature gating of any kind. The cloud-hosted version and self-hosted version MUST offer identical, complete feature sets.
- **FR-017**: Project MUST provide voluntary donation/support options (GitHub Sponsors, Ko-fi, or similar) that are entirely optional and do not affect the user experience in any way.

**Multi-Platform:**
- **FR-018**: System MUST provide a responsive web application accessible from any modern desktop or mobile browser
- **FR-019**: System MUST provide native mobile applications for iOS (iPhone, iPad) and Android (phones, tablets) available through their respective app stores
- **FR-020**: System MUST provide a consistent user experience across all platforms (web, iOS, Android) — the same features, data, and visual design language

**Offline-First:**
- **FR-021**: System MUST allow users to download their full document library, knowledge base, lessons, and audio for offline access
- **FR-022**: System MUST support completing full learning sessions (flashcards, reading, grammar, listening) while completely offline
- **FR-023**: System MUST automatically sync all offline progress (completed items, scores, SRS updates, streaks) when internet connectivity is restored, without data loss or corruption
- **FR-024**: System MUST resolve sync conflicts between offline sessions on different devices using timestamp-based conflict resolution with user notification
- **FR-025**: System MUST clearly indicate which features require internet connectivity and which are available offline
- **FR-026**: System MUST store all user data (documents, progress, schedules, settings) locally on-device in addition to cloud sync

**Open Source:**
- **FR-027**: The complete source code MUST be publicly available on GitHub under the MIT license
- **FR-028**: Repository MUST include: README with clear project description and quickstart, CONTRIBUTING guide with code of conduct, LICENSE file, and issue/PR templates
- **FR-029**: Project MUST have automated CI/CD via GitHub Actions that runs tests, linting, and builds on every PR and merge to main
- **FR-030**: Documentation MUST include a self-hosting guide allowing anyone to deploy their own instance with a single command or minimal configuration
- **FR-031**: Repository MUST include a public roadmap and accept community feature requests through GitHub Issues with a standardized template

**Cross-Cutting:**
- **FR-032**: System MUST enforce strict user data isolation: each user accesses only their own documents, schedules, and learning data
- **FR-032a**: Cloud-hosted service MUST maintain 99.5% uptime with automated database backups and a recovery time objective under 1 hour. Status page or health endpoint MUST be publicly accessible.
- **FR-033**: System MUST support three distinct in-app roles: Learner (study and upload own documents), Team Admin (Learner permissions plus invite members and manage shared document library), and Instance Admin (self-hosted only: full system configuration, all features). Team management features (shared library, member invites, admin panel) are P3 scope — implement after core learning MVP. GitHub contributor is an external community role, not an in-app account.
- **FR-034**: System MUST support dark and light visual themes with automatic detection of system preference across all platforms
- **FR-035**: Users MUST be able to view, edit, categorize, and organize parsed document content

### Key Entities

- **User**: An account with email, authentication method, and an assigned role (Learner, Team Admin, or Instance Admin). Each user has proficiency level per language, target languages, and a subscription tier (cloud only). Owns all personal data. Can sync across multiple devices. Instance Admin exists only in self-hosted deployments and has no tier restrictions.
- **Device**: A registered phone, tablet, or computer belonging to a user, tracking last sync timestamp, offline data storage location, and platform type (web, iOS, Android).
- **Document**: A user-uploaded PDF file with metadata (filename, size, page count, language, processing status) and the full parsed content output. Can be downloaded for offline access.
- **Content Block**: A parsed segment of a document — a heading, paragraph, table, or list item — with its content, block type, page position, language, and estimated difficulty.
- **Knowledge Segment**: A searchable unit created from one or more content blocks, stored with its semantic representation and metadata for hybrid retrieval.
- **Study Schedule**: A user-defined recurring plan specifying which days, at what time, for how long, and what content types to study.
- **Lesson**: A daily learning session generated from the schedule and knowledge base, containing a sequence of learning items. Can be completed offline.
- **Lesson Item**: An individual activity within a lesson — a flashcard, a reading passage with questions, a grammar exercise, or a listening exercise — with the user's response and correctness.
- **Review Card**: A spaced-repetition record for a previously learned item, tracking ease factor, review interval, repetition count, and next scheduled review date.
- **Progress Snapshot**: A daily record of the user's learning activity: words studied, time spent, streak continuation, and performance scores. Synced across devices.
- **Sync Log**: A record of data synchronization events between a device and the cloud, tracking timestamps, conflicts detected, and resolution actions taken.
- **Donation**: A voluntary financial contribution from a user via GitHub Sponsors, Ko-fi, or similar platform, tracking the platform, amount (optional), and date. For project sustainability only; does not affect feature access.
- **GitHub Contribution**: A record linking the public repository to community activity: issues, pull requests, discussions, and releases.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can upload a 100-page document and have it fully parsed and ready for learning in under 5 minutes
- **SC-002**: Document parsing correctly identifies structural elements (headings, paragraphs, tables) with at least 90% accuracy
- **SC-003**: Knowledge base search returns relevant results within 1 second for a library containing 10,000 or more content segments
- **SC-004**: A new user can complete account creation, initial setup, and schedule configuration in under 3 minutes
- **SC-005**: 80% of active users maintain a study streak of at least 7 consecutive days (measured 30 days after signup)
- **SC-006**: Audio playback starts within 2 seconds of pressing play for previously generated audio; within 5 seconds for new audio generation
- **SC-007**: System handles 1,000 concurrent cloud users without noticeable degradation — users perceive the application as responsive
- **SC-008**: Web application achieves a Lighthouse score above 90 for Performance, Accessibility, Best Practices, and SEO
- **SC-009**: The application becomes interactive within 3 seconds on desktop and within 5 seconds on mobile devices (on 4G connections)
- **SC-010**: Project receives sufficient community financial support (donations, sponsorships) to cover cloud infrastructure costs within 12 months of public launch
- **SC-011**: A user can complete a full learning session (flashcards, reading, listening) without any internet connectivity, and all progress syncs correctly within 30 seconds of reconnecting
- **SC-012**: The native mobile app cold-launches to the learning screen in under 3 seconds on a mid-range device (2023 equivalent or newer)
- **SC-013**: A new developer can clone the repository and run the full application locally within 15 minutes by following the README setup guide
- **SC-014**: The GitHub repository receives at least 100 stars and 10 unique community contributors within 6 months of going public
- **SC-015**: Cross-device sync between 3 devices (phone, tablet, laptop) resolves within 30 seconds with zero data loss in standard usage scenarios
- **SC-016**: Cloud-hosted service maintains 99.5% uptime (maximum 3.65 hours downtime per month), with automated backups enabling recovery within 1 hour of a catastrophic failure

## Assumptions

- Users have occasional internet access for initial document upload, cloud sync, and app installation — but daily learning happens primarily offline
- Users own or have legal rights to the PDF documents they upload to the platform
- The cloud-hosted parsing system has access to GPU hardware for fast processing (under 5 minutes per 100-page document). Self-hosted instances default to CPU-only parsing (~2-3 min/page) with optional GPU acceleration.
- Uploaded PDFs contain machine-readable text (text-based PDFs or high-quality scans; handwritten text recognition is out of scope)
- Users have basic reading proficiency in the target language — the tool serves learners who can already read simple text, not absolute beginners learning a new writing system
- Target audience is self-directed learners aged 16 and older who already possess or can acquire foreign-language reading materials
- The native mobile apps share a common codebase with the web app for business logic, with platform-specific UI adaptations for iOS and Android
- The MIT license permits commercial use, private modifications, and distribution — enabling both community contributions and the free cloud service
- Self-hosted users accept responsibility for their own infrastructure. CPU-only parsing is fully supported and tested; GPU acceleration is documented but optional.
- Initial open source release includes the complete application — all features available to all users. Community sustainability through voluntary donations is established as a secondary goal, not a prerequisite for launch.
