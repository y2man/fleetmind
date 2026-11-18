import { useGPS } from "./hooks/useGPS";

export default function GPSTest() {
  const { location, error, startGPS } = useGPS();

  return (
    <div>
      <button onClick={startGPS}>Start GPS</button>

      {location && (
        <p>
          Latitude: {location.latitude}
          <br />
          Longitude: {location.longitude}
          <br />
          Accuracy: {location.accuracy} meters
        </p>
      )}

      {error && <p>{error}</p>}
    </div>
  );
}