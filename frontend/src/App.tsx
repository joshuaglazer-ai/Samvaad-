import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, LazyMotion, domAnimation, m } from "framer-motion";
import { useTranslation } from "react-i18next";
import Header from "./components/ui/Header";
import Footer from "./components/ui/Footer";
import Landing from "./pages/Landing";
import Onboarding from "./pages/Onboarding";
import { useAppState } from "./lib/state";

// Heavier screens are code-split so the family journey's first load stays small.
const Alignment = lazy(() => import("./pages/Alignment"));
const Mood = lazy(() => import("./pages/Mood"));
const Join = lazy(() => import("./pages/Join"));
const Chat = lazy(() => import("./pages/Chat"));
const Summary = lazy(() => import("./pages/Summary"));
const Counsellor = lazy(() => import("./pages/Counsellor"));
const Admin = lazy(() => import("./pages/Admin"));

function Loading() {
  const { t } = useTranslation();
  return <p className="p-8 text-center text-ink-600" role="status">{t("app.loading")}</p>;
}

export default function App() {
  const location = useLocation();
  const { lite } = useAppState();
  const wide = location.pathname.startsWith("/admin") || location.pathname.startsWith("/counsellor");

  return (
    <LazyMotion features={domAnimation} strict>
    <div className="relative flex min-h-screen flex-col">
      <div className="static-stars" aria-hidden="true" />
      <Header />
      <main className={`relative z-10 mx-auto w-full flex-1 px-4 pb-8 ${wide ? "max-w-7xl" : "max-w-3xl"}`}>
        <Suspense fallback={<Loading />}>
          <AnimatePresence mode="wait">
            <m.div
              key={location.pathname}
              initial={lite ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={lite ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              <Routes location={location}>
                <Route path="/" element={<Landing />} />
                <Route path="/start" element={<Onboarding />} />
                <Route path="/alignment" element={<Alignment />} />
                <Route path="/join" element={<Join />} />
                <Route path="/mood/:phase" element={<Mood />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/summary/:sessionId?" element={<Summary />} />
                <Route path="/counsellor" element={<Counsellor />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="*" element={<Landing />} />
              </Routes>
            </m.div>
          </AnimatePresence>
        </Suspense>
      </main>
      <Footer />
    </div>
    </LazyMotion>
  );
}
