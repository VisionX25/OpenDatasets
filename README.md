# OpenDatasets

An open-source platform for discovering, exploring, and validating machine learning datasets.

## Project Overview

OpenDatasets is an independent open-source platform by **VisionX25** built to help researchers, data scientists, and ML engineers discover verified datasets, inspect data quality metrics, and collaborate transparently.

## Tech Stack

- **Frontend**:
  - React
  - TypeScript
  - Vite
  - Tailwind CSS
  - React Router
  - Lucide React
- **Planned Backend**:
  - Python
  - FastAPI

## Project Structure

```text
OpenDatasets/
├── frontend/                # React + TypeScript + Vite frontend application
│   ├── public/              # Static assets
│   ├── src/                 # Application source code
│   │   ├── components/      # UI components (Header, Footer, Layout, Icons)
│   │   ├── pages/           # Page routes (HomePage, ExplorePage, AboutPage)
│   │   ├── App.tsx          # Client-side router configuration
│   │   ├── index.css        # Tailwind CSS styles
│   │   └── main.tsx         # Application entry point
│   ├── eslint.config.js     # ESLint configuration
│   ├── package.json         # Frontend dependencies and scripts
│   ├── tsconfig.json        # TypeScript configuration
│   └── vite.config.ts       # Vite build & Tailwind configuration
├── LICENSE                  # MIT License
└── README.md                # Project documentation
```

## Local Development Setup

### Prerequisites

- **Node.js**: v18.0.0 or later (v20+ / v24+ recommended)
- **npm**: v9.0.0 or later

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the local development server**:
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173/`.

### Quality & Verification Checks

Run the following commands inside `frontend/`:

- **TypeScript Type Checking**:
  ```bash
  npx tsc --noEmit
  ```

- **ESLint Code Quality**:
  ```bash
  npm run lint
  ```

- **Production Build**:
  ```bash
  npm run build
  ```

- **Preview Production Build**:
  ```bash
  npm run preview
  ```

## License

This project is licensed under the [MIT License](LICENSE).
