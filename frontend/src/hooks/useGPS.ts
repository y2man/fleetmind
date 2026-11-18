
import { useState } from "react";

export function useGPS() {
  const [location, setLocation] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
  } | null>(null);

  const [error, setError] = useState("");

  function startGPS() {
    if (!navigator.geolocation) {
      setError("GPS is not supported by this browser.");
      return;
    }

    navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setError("");
      },
      (err) => setError(err.message),
      {
        enableHighAccuracy: true,
        maximumAge: 5000,
        timeout: 15000,
      }
    );
  }

  return { location, error, startGPS };
}
