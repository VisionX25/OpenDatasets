# OpenDatasets — Frontend

Web application for OpenDatasets built with React, TypeScript, Vite, Tailwind CSS, React Router, and Lucide React.

## Scripts

Inside `frontend/`:

- `npm run dev`: Start Vite development server with Hot Module Replacement (HMR).
- `npm run build`: Run TypeScript compiler (`tsc -b`) and build for production (`vite build`).
- `npm run lint`: Run ESLint across source files.
- `npm run preview`: Locally preview production build artifacts.

## Structure

- `src/components/`: Shared UI components (Layout, Header, Footer, Icons)
- `src/pages/`: Route page components (HomePage, ExplorePage, AboutPage)
- `src/App.tsx`: React Router configuration
- `src/index.css`: Tailwind CSS entrypoint
- `src/main.tsx`: React DOM mount point
