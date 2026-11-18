export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
/** Shows the demo accounts on the sign-in page. Only set VITE_DEMO_LOGIN=true for a demo deployment. */
export const DEMO_LOGIN: boolean = import.meta.env.VITE_DEMO_LOGIN === "true";
