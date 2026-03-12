import { useState, useEffect } from 'react';

export function useData(timeRange = '24H') {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);

        async function fetchData() {
            try {
                // Pass timeRange to the backend. In reality it affects the range.
                const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const res = await fetch(`${baseUrl}/api/v1/metrics/timeseries?range=${timeRange}`);
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                const jsonData = await res.json();
                if (isMounted) {
                    setData(jsonData);
                    setError(null);
                }
            } catch (err) {
                if (isMounted) {
                    setError(err.message || "Failed to fetch data");
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        }

        fetchData();
        // optionally set an interval to refresh
        const id = setInterval(fetchData, 60000);
        return () => {
            isMounted = false;
            clearInterval(id);
        };
    }, [timeRange]);

    return { data, loading, error };
}
