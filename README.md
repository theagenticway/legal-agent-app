# RCM
# RCM Pro - Backend

This repository contains the backend services for the **RCM Pro** application, a comprehensive Revenue Cycle Management solution. It provides a robust database structure, a Node.js Express server, and API endpoints to support all the functionalities seen in the React front end.

## Features

-   **RESTful API**: A complete set of API endpoints to manage patients, appointments, claims, and other RCM entities.
-   **PostgreSQL Database**: A scalable and relational database schema to ensure data integrity and complex querying.
-   **Payer Integration (Simulated)**: A mock integration layer for communicating with insurance payers for eligibility checks and claim submissions using the standard X12 EDI format.
-   **Secure and Scalable**: Built with best practices to ensure the application is ready for production environments.

## Technologies Used

-   **Node.js**: A JavaScript runtime for building the server-side application.
-   **Express.js**: A web application framework for Node.js, used to create the RESTful API.
-   **PostgreSQL**: A powerful, open-source object-relational database system.
-   **pg (node-postgres)**: A Node.js module for interfacing with the PostgreSQL database.
-   **Axios**: A promise-based HTTP client for making requests to external services (like payer APIs).

## Project Setup

### Prerequisites

-   [Node.js](https://nodejs.org/) (v14.x or later)
-   [PostgreSQL](https://www.postgresql.org/download/)
-   `npm` or `yarn`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd rcm-pro-backend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Set up the database:**
    -   Make sure your PostgreSQL server is running.
    -   Create a new database for the application (e.g., `rcm_pro_db`).
    -   Connect to your new database and run the schema script to create the tables:
        ```bash
        psql -U your_postgres_user -d rcm_pro_db -f db/schema.sql
        ```

4.  **Configure Environment Variables:**
    -   Create a `.env` file in the root of the project.
    -   Add the following environment variables, replacing the placeholder values with your actual database credentials:
        ```
        DB_USER=your_postgres_user
        DB_HOST=localhost
        DB_DATABASE=rcm_pro_db
        DB_PASSWORD=your_postgres_password
        DB_PORT=5432
        PORT=3001
        ```

5.  **Run the server:**
    ```bash
    npm start
    ```
    The server should now be running on `http://localhost:3001`.

## API Endpoints

A detailed list of API endpoints can be found in the `server.js` file and will be expanded upon in future documentation. Key resources include:

-   `/api/patients`
-   `/api/appointments`
-   `/api/claims`
-   `/api/kpis`
-   `/api/verify-eligibility`
-   `/api/submit-claim`

## How to Contribute

Contributions are welcome! Please feel free to submit a pull request or open an issue for any bugs or feature requests.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -am 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Create a new Pull Request.

---

*This README provides a comprehensive guide to setting up and running the RCM Pro backend. For any questions, please contact the repository owner.*
