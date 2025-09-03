Coding LLM Agent: Detailed Architecture Plan
This document outlines the architecture for a scalable, non-blocking backend system designed to provide a coding LLM with developer tools. The primary goal is to handle multiple, concurrent requests for different projects—including long-running terminal commands—without any request blocking another.

1. Core Principles
Asynchronous Backend: The core of the system uses a job queue to process tasks asynchronously. This is the key to preventing long-running jobs (like builds or tests) from blocking short, fast tasks (like reading a file).

Synchronous API Facade: While the backend is asynchronous, the API presented to the LLM behaves synchronously. The LLM makes a simple request and waits for a result in the same connection, which is essential for standard tool-calling integrations.

Decoupled Components: The Central API (the request handler) and the Workers (the task executors) are completely separate processes. This separation is fundamental to the non-blocking design.

On-Demand Environments: Project code is not kept on the execution VM permanently. It's synced from a central source of truth (Azure Blob Storage) on demand and cached locally for a configurable period (e.g., 24 hours).

2. System Components
1. Azure Virtual Machine (The "Developer Computer")

Instance Sizing:

Initial Testing (Under $50/mo): Standard_B2s (2 vCPUs, 4 GB RAM). This is a cost-effective, burstable instance perfect for development and testing.

Production / High-Performance: Standard_D4s_v5 (4 vCPUs, 16 GB RAM) or larger, for sustained CPU performance.

OS: Ubuntu 22.04 LTS.

Role: This is the execution environment. It hosts the Central API, the Worker processes, and the temporary local cache of project files in a /projects directory.

2. Central API (The Orchestrator)

Technology: A Python asynchronous web framework like FastAPI. This is crucial for its ability to handle thousands of concurrent "waiting" connections efficiently without consuming CPU.

Role:

Receives all HTTP requests from the LLM on endpoints like /execute, /file/read, /search.

Manages Project Cache: Before processing, it checks if the requested project's code exists locally. If not, it downloads and unzips it from Azure Blob Storage. It also updates a "last-accessed" timestamp.

Job Dispatch: Generates a unique job_id and dispatches a detailed job message to the Azure Queue.

Waits Efficiently: It uses async/await to poll for a result file in the Result Store. This frees up the process to handle other incoming requests while it waits.

Returns the final result to the LLM and cleans up the result file.

3. Azure Queue Storage (The Job Queue)

Service: A simple, reliable message queue.

Role: Acts as the buffer between the fast API and the potentially slower workers. It ensures that every request is captured instantly, no matter how busy the workers are.

4. Worker Pool (The "Doers")

Technology: A pool of independent Python scripts, run as separate processes using a process manager like systemd or supervisor.

Configuration: A good starting point is (2 * number_of_vCPUs) + 1 workers. For the B2s VM, this means 5 worker processes running in parallel.

Role:

Each worker runs an infinite loop, constantly asking the Job Queue for a new task.

Upon receiving a job, it executes the action within the correct project's directory (/projects/project-123/). This isolates the operation.

It writes the complete output (stdout, stderr, file content, etc.) into a unique JSON file in the Result Store, named after the job_id.

5. Result Store (The "Counter")

Technology: A simple file-based cache on the VM's local disk (e.g., a /results directory). This is highly effective for a single-VM architecture. For multi-VM scaling, this could be upgraded to Redis.

Role: A temporary location for workers to drop off the results of a completed job.

6. Azure Blob Storage (Source of Truth)

Service: Azure's object storage.

Role: The permanent, central repository for all project codebases, likely stored as zip archives.

5. Cost Optimization for Testing
The primary cost of this architecture is the Virtual Machine. The following strategies will keep your monthly bill well under $50 during the testing phase.

Select a Burstable VM: The Standard_B2s instance is ideal. It provides a baseline performance and can "burst" to use the full power of its 2 vCPUs when needed for short periods, like running a quick test.

Deallocate the VM When Not in Use: This is the most effective way to save money.

In the Azure Portal, on your VM's overview page, click the "Stop" button. This deallocates the VM, meaning you are no longer charged for compute hours.

You are only billed a very small amount for the stored disk.

When you are ready to test again, simply click "Start". Your public IP and all your files will be just as you left them.
