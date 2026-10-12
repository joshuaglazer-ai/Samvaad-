import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./styles/index.css";
import "./i18n";
import App from "./App";
import { AppStateProvider } from "./lib/state";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppStateProvider>
        <App />
      </AppStateProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
