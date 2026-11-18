import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import App from "./App";
import "leaflet/dist/leaflet.css";
import "@/store/theme";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <MotionConfig reducedMotion="user"><BrowserRouter>
        <App />
      </BrowserRouter></MotionConfig>
    </QueryClientProvider>
  </React.StrictMode>
);
