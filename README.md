# Q-rious 
##### _Satisfy your Q-riousity_

**Built at OxHack 2026 | Theme: Time**

Q-rious is an AI-powered, location-based queue prediction and recommendation web application designed to help people spend less time waiting and more time exploring.

By combining interactive maps, queue estimates, intelligent recommendations, conversational AI and voice interaction, Q-rious helps users decide **where to go, when to go and whether there's a faster alternative.**

Our working prototype focuses on Oxford, with the potential to expand to other cities, campuses and events.
<hr>

## The Problem

We've all been there. You walk across town to your favourite café, only to discover a queue stretching out the door.

Do you wait? Find somewhere else? How do you know whether the alternative will actually save you time?

Existing mapping applications help users navigate to destinations, but they don't necessarily account for the time spent waiting after arrival.

> **The closest destination isn't always the quickest option.**

<hr> 
## Our Solution

Q-rious combines location discovery, queue estimates and AI-powered recommendations in one integrated platform.

Users can explore questions such as:

- Where can I get coffee the fastest?
- Which nearby destination has the shortest estimated wait?
- Is walking further actually worth it?
- What alternatives could save me time?

Rather than prioritising proximity alone, Q-rious helps users compare the overall time associated with visiting different locations.

<hr>

## Key Features

### 🗺️ Interactive Google Maps
An interactive map powered by the Google Maps JavaScript API and Google Places API, enabling users to explore locations and access place information.

### ⏳ Queue Estimation
Estimated queue and waiting-time information helps users understand potential delays before visiting a destination.

For the hackathon, queue functionality was demonstrated using simulated queue data.

### 📍 Smart Alternatives and Recommendations
Q-rious helps users compare nearby destinations based on location, estimated waiting time and overall convenience.

A central principle is:

**Total time = Travel time + Estimated queue time**

This shifts the focus from finding the nearest destination to identifying options that could save the most time.

### 🤖 Google Gemini AI Assistant
Google Gemini is integrated into Q-rious to provide conversational assistance, helping users explore destinations and receive contextual recommendations through natural-language interaction.

### 🎙️ ElevenLabs Voice Integration
ElevenLabs powers voice functionality, adding a more natural and accessible way for users to interact with the application.

### 📊 Tiger Data Integration
Tiger Data is integrated into the backend to support the storage and management of time-dependent queue information, providing a foundation for analysing queue patterns and developing more advanced predictive capabilities.

### 📱 Responsive Web Interface
A mobile-oriented, app-like web experience built using HTML, CSS and JavaScript, with integrated navigation between maps, recommendations and AI-powered features.

## How It Works

1. **Explore:** Open Q-rious and discover nearby locations through Google Maps.
2. **Compare:** View queue estimates and relevant place information.
3. **Discover alternatives:** Identify other destinations that may offer a shorter overall journey and wait.
4. **Ask Q-rious:** Use the Gemini-powered assistant for additional guidance.
5. **Interact by voice:** Access voice functionality through ElevenLabs.
6. **Decide:** Choose a destination based on estimated time and personal priorities.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend logic and integrations |
| Flask | Web server and API endpoints |
| HTML5 | Frontend structure |
| CSS3 | Styling and responsive interface |
| JavaScript | Frontend interactivity |
| Google Maps JavaScript API | Interactive mapping |
| Google Places API | Place discovery and information |
| Google Gemini | AI-powered conversational assistance |
| ElevenLabs | Voice interaction |
| Tiger Data | Time-series queue data storage and management |


<hr>

## Technical Architecture

Q-rious connects its frontend, backend, database and external services to deliver a unified user experience.

### Frontend
**HTML, CSS and JavaScript**

- Interactive Google Maps interface
- Location selection and discovery
- Queue information and recommendations
- Conversational AI interface
- Voice interaction controls
- Responsive, app-like navigation

### Backend
**Python and Flask**

- Handles frontend requests
- Coordinates application logic
- Processes queue-related information
- Supports recommendations
- Connects to external APIs and database services

### AI and Voice
**Google Gemini and ElevenLabs**

- Gemini supports natural-language interactions and AI-assisted recommendations.
- ElevenLabs provides voice capabilities within the application.

### Database
**Tiger Data**

- Supports storage and retrieval of time-dependent queue information.
- Provides infrastructure for analysing historical observations and developing future queue prediction models.

### Location Services
**Google Maps and Google Places**

- Display geographic locations.
- Provide place discovery and relevant location information.
- Support the location-based user experience.


<hr>

## Demonstration and Validation

Q-rious was built as a working, end-to-end hackathon prototype.

The demonstration showcases the integration of:

- Interactive maps and location discovery
- Queue estimates and alternative recommendations
- Google Gemini conversational AI
- ElevenLabs voice functionality
- Tiger Data backend integration

**Data transparency:** The demonstration uses simulated queue data. While the application's components are integrated and functional, the queue estimates have not been validated against live, real-world waiting times.

This distinction is important: the prototype demonstrates the functionality of the system, not the proven accuracy of a deployed queue prediction service.

<hr>

## Challenges and Technical Decisions

### Building an Integrated Experience
Rather than developing disconnected demonstrations, we focused on bringing maps, queues, recommendations, AI and voice into a single application.

### Balancing Functionality and Time
Working within the hackathon timeframe required prioritising an end-to-end prototype while keeping the architecture open to further development.

### Queue Data Availability
Reliable, publicly accessible real-time queue information is limited. We used simulated data to demonstrate the product experience without misrepresenting it as live observations.

### Combining Multiple Services
Integrating Google Maps, Google Gemini, ElevenLabs and Tiger Data required coordinating different services across the frontend and Flask backend.


<hr>

## Future Development

- Integrate real-world queue data from participating businesses or opt-in users.
- Develop and evaluate time-dependent queue prediction models.
- Incorporate historical trends and service rates.
- Measure prediction accuracy against observed waiting times.
- Improve personalisation and accessibility.
- Expand coverage beyond Oxford.
- Introduce additional venue categories and event-specific recommendations.

<br> <br> <hr> <hr>
<br> <br>
## Built at OxHack 2026

Q-rious was developed by a team of four at OxHack 2026, responding to the theme **Time**.

Our aim was to tackle a familiar but often overlooked problem: the time lost to queues, uncertainty and inefficient decisions.

By combining geospatial technology, time-dependent data, conversational AI and voice interaction, we created a working prototype that demonstrates a more time-conscious way to explore a city.

<hr>

## Our Vision

**Time is valuable. Finding somewhere to go shouldn't waste it.**

Q-rious helps people make more informed decisions about how they spend theirs.

---

