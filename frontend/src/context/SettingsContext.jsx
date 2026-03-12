import { createContext, useContext, useState, useEffect } from 'react';

const SettingsContext = createContext();

export function SettingsProvider({ children }) {
    // Attempt to load from localStorage
    const loadSettings = () => {
        const saved = localStorage.getItem('ecoshift_settings');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) {
                console.error("Failed to parse settings", e);
            }
        }
        return {
            unitPreference: 'standard', // 'standard' or 'large'
            thresholds: {
                energy_draw: 300,       // kWh — matches backend PEAK_GRID_DRAW default
                carbon_emissions: 60    // kgCO2 — matches backend MAX_CARBON_EMISSIONS default
            }
        };
    };

    const [settings, setSettings] = useState(loadSettings);

    // Persist on change
    useEffect(() => {
        localStorage.setItem('ecoshift_settings', JSON.stringify(settings));
    }, [settings]);

    const updateSettings = (newSettings) => {
        setSettings(prev => ({ ...prev, ...newSettings }));
    };

    return (
        <SettingsContext.Provider value={{ settings, updateSettings }}>
            {children}
        </SettingsContext.Provider>
    );
}

export function useSettings() {
    return useContext(SettingsContext);
}
