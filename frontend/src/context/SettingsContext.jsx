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
                energy_draw: 1000,
                carbon_emissions: 500
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
