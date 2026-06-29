# Frontend

React reviewer interface for Clinical Review Agent.

This first slice displays the available synthetic cases from the backend and lets a reviewer select one. Review execution, evidence cards, graph display, and reviewer actions will be added in later slices.

## Run

From the `frontend/` directory:

```bash
npm install
npm run dev
```

The app expects the backend API at `http://127.0.0.1:8000` by default. Set `VITE_API_BASE_URL` to use another backend URL.

