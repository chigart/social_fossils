import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend unavailable");
        }

        return response.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <main
      style={{
        maxWidth: 800,
        margin: "80px auto",
        padding: "0 24px",
        fontFamily: "sans-serif"
      }}
    >
      <p>PERSONAL DATA ANALYTICS</p>
      <h1>Social Fossils</h1>
      <p>Explore the history of your conversations.</p>

      <hr />

      <h2>Application status</h2>

      {health && <p>Backend: {health.status}</p>}
      {error && <p>Backend connection failed.</p>}
      {!health && !error && <p>Connecting to backend...</p>}
    </main>
  );
}