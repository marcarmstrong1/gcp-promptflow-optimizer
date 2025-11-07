# gcp-promptflow-optimizer

Project Goal (The "Elevator Pitch")

To build a scalable, event-driven web service on Google Cloud that automatically discovers the optimal prompt for a given task. The system will take a base prompt, a test dataset, and an evaluation metric, then use an evolutionary algorithm to intelligently test thousands of prompt variations in parallel. The final output is the single highest-performing prompt, "forged" by this cloud-native process.

Core Architecture & Components

This is a serverless, event-driven architecture. Each component is a separate microservice that communicates via API calls and database events.
Component,Google Cloud Service,Purpose
1. API Front-End,Cloud Run,"Provides a REST API for users to submit, monitor, and retrieve optimization jobs."
2. State Database,Firestore,"Stores all data: job configurations, real-time status, and the results of every prompt test."
3. Main Orchestrator,Cloud Workflows,"The ""brains"" of the operation. It controls the entire optimization loop and manages the state."
4. Parallel Worker,Cloud Functions,A fleet of elastic workers. Each function tests one prompt variation and reports its score.
5. AI Model,Vertex AI (Gemini API),The LLM that the system is optimizing.
